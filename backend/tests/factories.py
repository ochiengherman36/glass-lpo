from __future__ import annotations

from datetime import datetime
from typing import Any

from app.extract import ExtractionResult
from app.lpo import LpoDocument
from app.schema import DrawingExtraction, Hole, Notch, Panel, Reading, TextReading
from app.validate import validate_drawing

ISSUED_AT = datetime(2026, 11, 25, 14, 30, 5)


def clear(value: float) -> Reading:
    return Reading(value=value, status="clear", raw_text=str(int(value)) if value == int(value) else str(value))


def unclear(raw_text: str, value: float | None = None) -> Reading:
    return Reading(value=value, status="unclear", raw_text=raw_text)


def not_shown() -> Reading:
    return Reading(value=None, status="not_shown", raw_text=None)


def text(value: str | None) -> TextReading:
    return TextReading(text=value, status="clear" if value else "not_shown")


def hole(diameter: float = 25, x: float | None = None, y: float | None = None) -> Hole:
    return Hole(
        diameter_mm=clear(diameter),
        x_mm=clear(x) if x is not None else not_shown(),
        y_mm=clear(y) if y is not None else not_shown(),
        position_description=None,
    )


def notch(width: float = 50, depth: float = 50, position: str = "top-right corner") -> Notch:
    return Notch(kind="offcut", width_mm=clear(width), depth_mm=clear(depth), position=position)


def panel(panel_id: str = "P1", width: float = 900, height: float = 1200, **overrides: Any) -> Panel:
    fields: dict[str, Any] = {
        "panel_id": panel_id,
        "width_mm": clear(width),
        "height_mm": clear(height),
        "qty": clear(1),
        "thickness_mm": clear(6),
        "glass_type": text("clear"),
        "holes": [],
        "notches": [],
        "edge_work": text(None),
        "notes": None,
        "confidence": "high",
        "confidence_reason": "all values clearly written",
    }
    fields.update(overrides)
    return Panel(**fields)


def drawing(panels: list[Panel] | None = None, **overrides: Any) -> DrawingExtraction:
    panels = panels if panels is not None else [panel(holes=[hole(x=150, y=600), hole(x=750, y=600)])]
    fields: dict[str, Any] = {
        "overall_width_mm": clear(900),
        "overall_height_mm": clear(1200),
        "stated_hole_count": clear(2),
        "panels": panels,
        "general_notes": [],
        "unreadable_items": [],
    }
    fields.update(overrides)
    return DrawingExtraction(**fields)


def lpo_document(extraction: DrawingExtraction | None = None, lpo_no: str = "LPO-20261125-143005") -> LpoDocument:
    return LpoDocument(
        lpo_no=lpo_no,
        issued_at=ISSUED_AT,
        source_name="simple.jpeg",
        drawing=validate_drawing(extraction or drawing()),
    )


class FakeExtractor:
    def __init__(self, extraction: DrawingExtraction | None = None, error: Exception | None = None) -> None:
        self.extraction = extraction or drawing()
        self.error = error
        self.calls: list[tuple[Any, Any]] = []

    def __call__(self, enhanced_path: Any, original_path: Any) -> ExtractionResult:
        self.calls.append((enhanced_path, original_path))
        if self.error is not None:
            raise self.error
        return ExtractionResult(
            drawing=self.extraction, model="fake-model", input_tokens=10, output_tokens=20, fallback_used=False
        )


def many_panels(count: int, **panel_overrides: Any) -> DrawingExtraction:
    panels = [panel(f"P{index}", 500, 2100, **panel_overrides) for index in range(1, count + 1)]
    return drawing(panels, overall_width_mm=not_shown(), overall_height_mm=not_shown(), stated_hole_count=not_shown())
