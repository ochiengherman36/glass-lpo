from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.schema import DrawingExtraction, Hole, Item, LengthUnit, Notch, Panel, Reading

MM_PER_UNIT: dict[str, float] = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4, "ft": 304.8}

Kind = Literal["size", "small"]

UNIT_PATTERNS: tuple[tuple[str, LengthUnit], ...] = (
    (r"mm\b|millimet", "mm"),
    (r"cm\b|centimet", "cm"),
    (r"m\b|met(?:re|er)", "m"),
    (r"\"|''|in\b|inch", "in"),
    (r"'|ft\b|fe+t|foot", "ft"),
)
NUMBER = re.compile(r"(\d+)\s+(\d+)\s*/\s*(\d+)|(\d+)\s*/\s*(\d+)|(\d+(?:\.\d+)?)")
FEET_INCHES = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:'|ft\b|fe+ts?\b|foot)\s*(?:(\d+)\s+(\d+)\s*/\s*(\d+)|(\d+)\s*/\s*(\d+)|(\d+(?:\.\d+)?))"
    r"\s*(?:\"|''|in\b|inch)"
)
QUOTES = str.maketrans({"’": "'", "′": "'", "”": '"', "″": '"'})


@dataclass(frozen=True)
class UnitRules:
    decimals: int = 0
    min_mismatch_mm: float = 1.0
    max_mismatch_ratio: float = 0.01


DEFAULT_UNIT_RULES = UnitRules()


@dataclass(frozen=True)
class ParsedLength:
    value: float
    unit: LengthUnit | None
    fraction: bool


def number_from(match: re.Match[str], offset: int = 0) -> tuple[float, bool]:
    whole, num, den, lone_num, lone_den, plain = (match.group(offset + i) for i in range(1, 7))
    if num is not None:
        return int(whole) + int(num) / int(den), True
    if lone_num is not None:
        return int(lone_num) / int(lone_den), True
    return float(plain), False


def unit_after(text: str) -> LengthUnit | None:
    head = text.lstrip()
    for pattern, unit in UNIT_PATTERNS:
        if re.match(pattern, head):
            return unit
    return None


def parse_length(raw: str | None) -> ParsedLength | None:
    if not raw:
        return None
    text = raw.lower().translate(QUOTES)

    feet_inches = FEET_INCHES.search(text)
    if feet_inches:
        inches, fraction = number_from(feet_inches, offset=1)
        return ParsedLength(float(feet_inches.group(1)) * 12 + inches, "in", fraction)

    numbers = list(NUMBER.finditer(text))
    if len(numbers) != 1:
        return None
    match = numbers[0]
    value, fraction = number_from(match)
    return ParsedLength(value, unit_after(text[match.end():]), fraction)


def unit_label(unit: str) -> str:
    return {"in": "inches", "ft": "feet"}.get(unit, unit)


class UnitConverter:
    def __init__(self, extraction: DrawingExtraction, rules: UnitRules = DEFAULT_UNIT_RULES) -> None:
        self.rules = rules
        self.drawing_unit = extraction.drawing_unit
        self.sheet_units = self.size_units(extraction) - {"mm"}

    @staticmethod
    def size_units(extraction: DrawingExtraction) -> set[str]:
        readings = [extraction.overall_width_mm, extraction.overall_height_mm]
        readings += [reading for item in extraction.items for reading in (item.overall_width_mm, item.overall_height_mm)]
        readings += [reading for panel in extraction.panels for reading in (panel.width_mm, panel.height_mm)]
        units = set()
        for reading in readings:
            parsed = parse_length(reading.raw_text)
            unit = reading.unit or (parsed.unit if parsed else None)
            if unit:
                units.add(unit)
        return units

    def resolve_unit(self, reading: Reading, parsed: ParsedLength | None, kind: Kind) -> tuple[str, list[str]]:
        if reading.unit:
            return reading.unit, []
        if parsed and parsed.unit:
            return parsed.unit, []
        if self.drawing_unit:
            return self.drawing_unit, []
        if parsed and parsed.fraction:
            return "in", ["unit not written, inches assumed from the fraction"]
        if kind == "size" and len(self.sheet_units) == 1:
            unit = next(iter(self.sheet_units))
            return unit, [f"unit not written, {unit_label(unit)} assumed like the rest of the sheet"]
        if kind == "size" and self.sheet_units:
            units = ", ".join(sorted(unit_label(unit) for unit in self.sheet_units))
            return "mm", [f"unit not written and the sheet mixes {units}"]
        return "mm", []

    def mismatch(self, reading: Reading, parsed: ParsedLength | None, unit: str, value_mm: float) -> list[str]:
        if parsed is None or reading.status != "clear":
            return []
        written_mm = parsed.value * MM_PER_UNIT[parsed.unit or unit]
        allowed = max(self.rules.min_mismatch_mm, self.rules.max_mismatch_ratio * written_mm)
        if abs(written_mm - value_mm) <= allowed:
            return []
        return [f"value read ({reading.value:g} {unit}) does not match what is written"]

    def reading(self, reading: Reading, kind: Kind = "size") -> tuple[Reading, bool]:
        if reading.value is None:
            return reading.model_copy(update={"unit": "mm"}), False

        parsed = parse_length(reading.raw_text)
        unit, problems = self.resolve_unit(reading, parsed, kind)
        value_mm = reading.value * MM_PER_UNIT[unit]
        if unit != "mm":
            value_mm = round(value_mm, self.rules.decimals)
        problems += self.mismatch(reading, parsed, unit, value_mm)

        update: dict[str, object] = {"value": value_mm, "unit": "mm"}
        if problems:
            update["status"] = "unclear"
            update["raw_text"] = "; ".join([reading.raw_text or f"{reading.value:g}", *problems])
        return reading.model_copy(update=update), unit != "mm"

    def hole(self, hole: Hole, index: int, converted: list[str]) -> Hole:
        update = {}
        for name, kind in (("diameter_mm", "small"), ("x_mm", "size"), ("y_mm", "size")):
            update[name] = self.track(getattr(hole, name), kind, f"hole {index} {name.removesuffix('_mm')}", converted)
        return hole.model_copy(update=update)

    def notch(self, notch: Notch, index: int, converted: list[str]) -> Notch:
        update = {
            name: self.track(getattr(notch, name), "size", f"{notch.kind} {index} {name.removesuffix('_mm')}", converted)
            for name in ("width_mm", "depth_mm")
        }
        return notch.model_copy(update=update)

    def track(self, reading: Reading, kind: Kind, label: str, converted: list[str]) -> Reading:
        result, was_converted = self.reading(reading, kind)
        if was_converted:
            converted.append(f"{label} '{reading.raw_text or reading.value}'")
        return result

    def panel(self, panel: Panel) -> Panel:
        converted: list[str] = []
        update: dict[str, object] = {
            "width_mm": self.track(panel.width_mm, "size", "width", converted),
            "height_mm": self.track(panel.height_mm, "size", "height", converted),
            "thickness_mm": self.track(panel.thickness_mm, "small", "thickness", converted),
        }
        update["holes"] = [self.hole(hole, index, converted) for index, hole in enumerate(panel.holes, start=1)]
        update["notches"] = [self.notch(notch, index, converted) for index, notch in enumerate(panel.notches, start=1)]

        notes = [f"Item: {panel.item}"] if panel.item else []
        notes += [panel.notes] if panel.notes else []
        if converted:
            notes.append("converted to mm from " + ", ".join(converted))
        update["notes"] = ". ".join(note.rstrip(". ") for note in notes) or None
        return panel.model_copy(update=update)

    def item(self, item: Item) -> Item:
        return item.model_copy(
            update={
                "overall_width_mm": self.reading(item.overall_width_mm)[0],
                "overall_height_mm": self.reading(item.overall_height_mm)[0],
            }
        )

    def drawing(self, extraction: DrawingExtraction) -> DrawingExtraction:
        return extraction.model_copy(
            update={
                "drawing_unit": "mm",
                "items": [self.item(item) for item in extraction.items],
                "overall_width_mm": self.reading(extraction.overall_width_mm)[0],
                "overall_height_mm": self.reading(extraction.overall_height_mm)[0],
                "panels": [self.panel(panel) for panel in extraction.panels],
            }
        )


def normalize_units(extraction: DrawingExtraction, rules: UnitRules = DEFAULT_UNIT_RULES) -> DrawingExtraction:
    return UnitConverter(extraction, rules).drawing(extraction)
