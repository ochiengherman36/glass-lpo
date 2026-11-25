from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.validate import CHECK, NOT_DIMENSIONED, LineItem, ValidatedDrawing, mm

COLUMNS: tuple[str, ...] = (
    "LPO No",
    "Line",
    "Panel ID",
    "Width (mm)",
    "Height (mm)",
    "Qty",
    "Thickness (mm)",
    "Glass type",
    "Area (m²)",
    "Hole count",
    "Hole diameters (mm)",
    "Hole positions",
    "Notches/offcuts",
    "Grooves/edge work",
    "Notes",
    "Confidence",
    "Needs check (Y/N)",
)

LPO_PREFIX = "LPO"


@dataclass(frozen=True)
class LpoDocument:
    lpo_no: str
    issued_at: datetime
    source_name: str
    drawing: ValidatedDrawing


def generate_lpo_number(now: datetime | None = None, prefix: str = LPO_PREFIX) -> str:
    now = now or datetime.now()
    return f"{prefix}-{now:%Y%m%d-%H%M%S}"


def is_check(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(CHECK)


def number(value: float | None) -> int | float | None:
    if value is None:
        return None
    return int(value) if float(value).is_integer() else value


def number_cell(line: LineItem, field_name: str, value: float | None) -> int | float | str | None:
    if field_name in line.check_fields:
        return CHECK if value is None else f"{CHECK} ({mm(value)}?)"
    return number(value)


def text_cell(line: LineItem, field_name: str, value: str | None) -> str:
    if field_name in line.check_fields:
        return CHECK if not value else f"{CHECK} ({value}?)"
    return value or ""


def list_cell(line: LineItem, field_name: str, values: list[str]) -> str:
    if values and all(value == NOT_DIMENSIONED for value in values):
        joined = NOT_DIMENSIONED
    else:
        joined = "; ".join(values)
    if field_name in line.check_fields:
        return f"{CHECK}: {joined}" if joined else CHECK
    return joined


def diameters_cell(line: LineItem) -> str:
    joined = ", ".join("?" if value is None else mm(value) for value in line.hole_diameters_mm)
    if "holes" in line.check_fields:
        return f"{CHECK} ({joined})"
    return joined


def notes_cell(line: LineItem) -> str:
    prefix = f"{line.panel_id}: "
    parts = [line.notes] if line.notes else []
    parts += [flag.message.removeprefix(prefix) for flag in line.flags]
    return "; ".join(parts)


def line_row(document: LpoDocument, line: LineItem) -> dict[str, Any]:
    return {
        "LPO No": document.lpo_no,
        "Line": line.line,
        "Panel ID": line.panel_id,
        "Width (mm)": number_cell(line, "width", line.width_mm),
        "Height (mm)": number_cell(line, "height", line.height_mm),
        "Qty": number_cell(line, "qty", line.qty),
        "Thickness (mm)": number_cell(line, "thickness", line.thickness_mm),
        "Glass type": text_cell(line, "glass_type", line.glass_type),
        "Area (m²)": line.area_m2 if line.area_m2 is not None else CHECK,
        "Hole count": line.hole_count,
        "Hole diameters (mm)": diameters_cell(line),
        "Hole positions": list_cell(line, "hole_positions", line.hole_positions),
        "Notches/offcuts": list_cell(line, "notches", line.notches),
        "Grooves/edge work": text_cell(line, "edge_work", line.edge_work),
        "Notes": notes_cell(line),
        "Confidence": line.confidence.capitalize(),
        "Needs check (Y/N)": "Y" if line.needs_check else "N",
    }


def rows(document: LpoDocument) -> list[dict[str, Any]]:
    return [line_row(document, line) for line in document.drawing.lines]
