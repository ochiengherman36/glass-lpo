from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.schema import Confidence, DrawingExtraction, Hole, Notch, Panel, Reading, TextReading

CHECK = "CHECK"
NOT_DIMENSIONED = "not dimensioned"
CONFIDENCE_ORDER: tuple[Confidence, ...] = ("low", "medium", "high")

Severity = Literal["critical", "minor"]


@dataclass(frozen=True)
class ValidationRules:
    sum_tolerance_mm: float = 5.0
    min_panel_mm: float = 50.0
    max_panel_mm: float = 3300.0
    standard_thicknesses_mm: tuple[float, ...] = (4, 5, 6, 8, 10, 12, 15, 19)
    min_hole_mm: float = 5.0
    max_hole_mm: float = 100.0
    area_decimals: int = 3


DEFAULT_RULES = ValidationRules()


@dataclass(frozen=True)
class Flag:
    panel_id: str | None
    field: str
    message: str
    severity: Severity


@dataclass
class LineItem:
    line: int
    panel_id: str
    width_mm: float | None
    height_mm: float | None
    qty: int | None
    thickness_mm: float | None
    glass_type: str | None
    area_m2: float | None
    hole_diameters_mm: list[float | None]
    hole_positions: list[str]
    notches: list[str]
    edge_work: str | None
    notes: str | None
    model_confidence: Confidence
    confidence: Confidence
    flags: list[Flag] = field(default_factory=list)
    check_fields: set[str] = field(default_factory=set)

    @property
    def hole_count(self) -> int:
        return len(self.hole_diameters_mm)

    @property
    def needs_check(self) -> bool:
        return bool(self.flags or self.check_fields)


@dataclass
class ValidatedDrawing:
    lines: list[LineItem]
    drawing_flags: list[Flag]
    overall_width_mm: float | None
    overall_height_mm: float | None
    general_notes: list[str]

    @property
    def flags(self) -> list[Flag]:
        return self.drawing_flags + [flag for line in self.lines for flag in line.flags]

    @property
    def needs_check(self) -> bool:
        return bool(self.drawing_flags) or any(line.needs_check for line in self.lines)

    @property
    def total_area_m2(self) -> float:
        return round(sum(line.area_m2 for line in self.lines if line.area_m2 is not None), 3)

    @property
    def area_complete(self) -> bool:
        return all(line.area_m2 is not None for line in self.lines)

    @property
    def total_holes(self) -> int:
        return sum(line.hole_count * (line.qty or 1) for line in self.lines)


def mm(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"


def raw_suffix(reading: Reading) -> str:
    return f" (raw: '{reading.raw_text}')" if reading.raw_text else ""


def lower_confidence(*levels: Confidence) -> Confidence:
    return min(levels, key=CONFIDENCE_ORDER.index)


def is_known(reading: Reading) -> bool:
    return reading.status == "clear" and reading.value is not None


class PanelValidator:
    def __init__(self, panel: Panel, rules: ValidationRules) -> None:
        self.panel = panel
        self.rules = rules
        self.flags: list[Flag] = []
        self.check_fields: set[str] = set()

    def flag(self, field_name: str, message: str, severity: Severity = "critical", check: bool = True) -> None:
        self.flags.append(Flag(self.panel.panel_id, field_name, f"{self.panel.panel_id}: {message}", severity))
        if check:
            self.check_fields.add(field_name)

    def number(self, reading: Reading, field_name: str, label: str, severity: Severity = "critical") -> bool:
        if reading.status == "not_shown":
            self.flag(field_name, f"{label} not written on drawing", severity)
            return False
        if not is_known(reading):
            self.flag(field_name, f"{label} unclear{raw_suffix(reading)}", severity)
            return False
        return True

    def text(self, reading: TextReading, field_name: str, label: str, required: bool) -> str | None:
        if reading.status == "not_shown":
            if required:
                self.flag(field_name, f"{label} not written on drawing", "minor")
            return None
        if reading.status == "unclear" or not reading.text:
            self.flag(field_name, f"{label} unclear{f' (raw: {reading.text!r})' if reading.text else ''}", "minor")
        return reading.text

    def in_range(self, value: float, field_name: str, label: str, low: float, high: float) -> bool:
        if low <= value <= high:
            return True
        self.flag(field_name, f"{label} {mm(value)} mm is outside the {mm(low)}-{mm(high)} mm range")
        return False

    def validate(self, line_number: int) -> LineItem:
        panel, rules = self.panel, self.rules

        width_ok = self.number(panel.width_mm, "width", "width")
        width_ok = width_ok and self.in_range(panel.width_mm.value, "width", "width", rules.min_panel_mm, rules.max_panel_mm)
        height_ok = self.number(panel.height_mm, "height", "height")
        height_ok = height_ok and self.in_range(
            panel.height_mm.value, "height", "height", rules.min_panel_mm, rules.max_panel_mm
        )
        size = (panel.width_mm.value, panel.height_mm.value) if is_known(panel.width_mm) and is_known(panel.height_mm) else None

        qty, qty_ok = self.validate_qty()
        self.validate_thickness()
        glass_type = self.text(panel.glass_type, "glass_type", "glass type", required=True)
        edge_work = self.text(panel.edge_work, "edge_work", "edge work", required=False)
        diameters, positions = self.validate_holes(size)
        notches = self.validate_notches(size)

        area = None
        if width_ok and height_ok and qty_ok and qty is not None:
            area = round(panel.width_mm.value * panel.height_mm.value * qty / 1_000_000, rules.area_decimals)

        return LineItem(
            line=line_number,
            panel_id=panel.panel_id,
            width_mm=panel.width_mm.value,
            height_mm=panel.height_mm.value,
            qty=qty,
            thickness_mm=panel.thickness_mm.value,
            glass_type=glass_type,
            area_m2=area,
            hole_diameters_mm=diameters,
            hole_positions=positions,
            notches=notches,
            edge_work=edge_work,
            notes=panel.notes,
            model_confidence=panel.confidence,
            confidence=lower_confidence(self.rule_confidence(), panel.confidence),
            flags=self.flags,
            check_fields=self.check_fields,
        )

    def validate_qty(self) -> tuple[int | None, bool]:
        reading = self.panel.qty
        if reading.status == "not_shown":
            self.flag("qty", "quantity not written, assumed 1", "minor", check=False)
            return 1, True
        if not self.number(reading, "qty", "quantity"):
            return None, False
        if reading.value < 1 or not float(reading.value).is_integer():
            self.flag("qty", f"quantity {mm(reading.value)} is not a whole number of panels")
            return None, False
        return int(reading.value), True

    def validate_thickness(self) -> None:
        reading = self.panel.thickness_mm
        if not self.number(reading, "thickness", "thickness", "minor"):
            return
        standard = self.rules.standard_thicknesses_mm
        if reading.value not in standard:
            allowed = ", ".join(mm(value) for value in standard)
            self.flag(
                "thickness",
                f"thickness {mm(reading.value)} mm is not a standard glass thickness ({allowed})",
                "minor",
            )

    def validate_holes(self, size: tuple[float, float] | None) -> tuple[list[float | None], list[str]]:
        diameters: list[float | None] = []
        positions: list[str] = []
        for index, hole in enumerate(self.panel.holes, start=1):
            diameters.append(hole.diameter_mm.value)
            diameter_ok = self.validate_hole_diameter(hole, index, size)
            positions.append(self.validate_hole_position(hole, index, size, diameter_ok))
        return diameters, positions

    def validate_hole_diameter(self, hole: Hole, index: int, size: tuple[float, float] | None) -> bool:
        label = f"hole {index} diameter"
        if not self.number(hole.diameter_mm, "holes", label):
            return False
        diameter = hole.diameter_mm.value
        if not self.in_range(diameter, "holes", label, self.rules.min_hole_mm, self.rules.max_hole_mm):
            return False
        if size and diameter >= min(size):
            self.flag("holes", f"{label} {mm(diameter)} mm does not fit in a {mm(size[0])} x {mm(size[1])} mm panel")
            return False
        return True

    def validate_hole_position(
        self, hole: Hole, index: int, size: tuple[float, float] | None, diameter_ok: bool
    ) -> str:
        if hole.x_mm.status == "not_shown" and hole.y_mm.status == "not_shown":
            return NOT_DIMENSIONED

        x_ok = self.number(hole.x_mm, "hole_positions", f"hole {index} x position", "minor")
        y_ok = self.number(hole.y_mm, "hole_positions", f"hole {index} y position", "minor")
        if not (x_ok and y_ok):
            return CHECK

        x, y = hole.x_mm.value, hole.y_mm.value
        radius = hole.diameter_mm.value / 2 if diameter_ok else 0
        if size and not (radius < x < size[0] - radius and radius < y < size[1] - radius):
            self.flag(
                "hole_positions",
                f"hole {index} centre (x{mm(x)}, y{mm(y)}) is outside the {mm(size[0])} x {mm(size[1])} mm panel",
            )
        return f"x{mm(x)} y{mm(y)}"

    def validate_notches(self, size: tuple[float, float] | None) -> list[str]:
        descriptions = []
        for index, notch in enumerate(self.panel.notches, start=1):
            descriptions.append(self.validate_notch(notch, index, size))
        return descriptions

    def validate_notch(self, notch: Notch, index: int, size: tuple[float, float] | None) -> str:
        label = f"{notch.kind} {index}"
        width_ok = self.number(notch.width_mm, "notches", f"{label} width")
        depth_ok = self.number(notch.depth_mm, "notches", f"{label} depth")
        position = f", {notch.position}" if notch.position else ""
        if not (width_ok and depth_ok):
            return f"{notch.kind} size {CHECK}{position}"

        width, depth = notch.width_mm.value, notch.depth_mm.value
        if size and (width >= size[0] or depth >= size[1]):
            self.flag(
                "notches",
                f"{label} ({mm(width)} x {mm(depth)} mm) is larger than the {mm(size[0])} x {mm(size[1])} mm panel",
            )
        return f"{notch.kind} {mm(width)} x {mm(depth)} mm{position}"

    def rule_confidence(self) -> Confidence:
        if any(flag.severity == "critical" for flag in self.flags):
            return "low"
        if self.flags or self.check_fields:
            return "medium"
        return "high"


def validate_drawing(extraction: DrawingExtraction, rules: ValidationRules = DEFAULT_RULES) -> ValidatedDrawing:
    lines = [PanelValidator(panel, rules).validate(index) for index, panel in enumerate(extraction.panels, start=1)]
    drawing_flags: list[Flag] = []

    if not lines:
        drawing_flags.append(Flag(None, "panels", "No glass panels found on the drawing", "critical"))

    overall_width = overall_value(extraction.overall_width_mm, "overall width", drawing_flags)
    overall_height = overall_value(extraction.overall_height_mm, "overall height", drawing_flags)

    check_sum(extraction.panels, lines, "width", overall_width, rules, drawing_flags)
    check_sum(extraction.panels, lines, "height", overall_height, rules, drawing_flags)
    check_stated_hole_count(extraction, drawing_flags)

    for item in extraction.unreadable_items:
        drawing_flags.append(Flag(None, "drawing", f"Unreadable on drawing: {item}", "minor"))

    return ValidatedDrawing(
        lines=lines,
        drawing_flags=drawing_flags,
        overall_width_mm=overall_width,
        overall_height_mm=overall_height,
        general_notes=list(extraction.general_notes),
    )


def overall_value(reading: Reading, label: str, flags: list[Flag]) -> float | None:
    if reading.status == "not_shown":
        return None
    if not is_known(reading):
        flags.append(Flag(None, label, f"{label.capitalize()} unclear{raw_suffix(reading)}", "minor"))
        return None
    return reading.value


def check_sum(
    panels: list[Panel],
    lines: list[LineItem],
    dimension: Literal["width", "height"],
    overall: float | None,
    rules: ValidationRules,
    flags: list[Flag],
) -> None:
    readings = [panel.width_mm if dimension == "width" else panel.height_mm for panel in panels]
    if overall is None or not readings or not all(is_known(reading) for reading in readings):
        return

    values = [reading.value for reading in readings]
    total = sum(values)
    tolerance = rules.sum_tolerance_mm
    adds_up = abs(total - overall) <= tolerance
    each_spans_overall = all(abs(value - overall) <= tolerance for value in values)
    if adds_up or each_spans_overall:
        return

    flags.append(
        Flag(None, dimension, f"Panel {dimension}s add up to {mm(total)} mm but the overall {dimension} is {mm(overall)} mm", "critical")
    )
    for line in lines:
        line.check_fields.add(dimension)
        line.area_m2 = None
        line.confidence = "low"


def check_stated_hole_count(extraction: DrawingExtraction, flags: list[Flag]) -> None:
    stated = extraction.stated_hole_count
    if not is_known(stated):
        return
    drawn = sum(len(panel.holes) for panel in extraction.panels)
    if int(stated.value) != drawn:
        verb = "is" if drawn == 1 else "are"
        flags.append(
            Flag(None, "holes", f"Note says {mm(stated.value)} holes but {drawn} {verb} drawn", "critical")
        )
