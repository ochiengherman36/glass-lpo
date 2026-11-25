from __future__ import annotations

from typing import Any

from app.schema import DrawingExtraction, Hole, Notch, Panel, Reading, TextReading


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
