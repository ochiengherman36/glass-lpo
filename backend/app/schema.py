from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ReadingStatus = Literal["clear", "unclear", "not_shown"]
Confidence = Literal["high", "medium", "low"]
NotchKind = Literal["notch", "offcut", "cutout", "other"]
LengthUnit = Literal["mm", "cm", "m", "in", "ft"]

STATUS_HELP = (
    "clear: written and unambiguous. "
    "unclear: written but smudged, ambiguous, corrected or partly unreadable. "
    "not_shown: not written anywhere on the drawing."
)


def default_missing(data: Any, **defaults: Any) -> Any:
    if isinstance(data, dict):
        return {**defaults, **data}
    return data


class Reading(BaseModel):
    value: float | None = Field(
        description="The number as written, in the unit it is written in (not converted). Fractions as decimals: "
        "'107 7/8' is 107.875. null when not_shown, and null when unclear unless one reading is clearly intended."
    )
    unit: LengthUnit | None = Field(
        description="Unit written next to this value: mm, cm, m, in (inch, \") or ft (feet, '). "
        "null when no unit is written next to it, and for counts such as quantity."
    )
    status: ReadingStatus = Field(description=STATUS_HELP)
    raw_text: str | None = Field(
        description="What is actually written for this value, including its unit, with '?' for unreadable characters. "
        "Describe corrections, e.g. '650 crossed out, 600 written'. null when not_shown."
    )

    @model_validator(mode="before")
    @classmethod
    def unit_defaults_to_none(cls, data: Any) -> Any:
        return default_missing(data, unit=None)


class TextReading(BaseModel):
    text: str | None = Field(description="The text as written, e.g. 'toughened' or 'polished edges'. null when not_shown.")
    status: ReadingStatus = Field(description=STATUS_HELP)


class Hole(BaseModel):
    diameter_mm: Reading
    x_mm: Reading = Field(
        description="Distance from the panel's left edge to the hole centre, only if dimensioned on the drawing."
    )
    y_mm: Reading = Field(
        description="Distance from the panel's bottom edge to the hole centre, only if dimensioned on the drawing."
    )
    position_description: str | None = Field(
        description="Where the hole is drawn, in words, e.g. 'upper half, near the left edge'."
    )


class Notch(BaseModel):
    kind: NotchKind
    width_mm: Reading = Field(description="Horizontal size of the notch or offcut as written.")
    depth_mm: Reading = Field(description="Vertical size of the notch or offcut as written.")
    position: str | None = Field(description="Corner or edge where it is drawn, e.g. 'top-right corner'.")


class Panel(BaseModel):
    panel_id: str = Field(
        description="Label written on the drawing, e.g. 'P1'. If unlabelled, P1, P2... left to right, top to bottom."
    )
    item: str | None = Field(
        description="Name of the item in items this panel belongs to, e.g. 'sliding window'. null when items is empty."
    )
    width_mm: Reading
    height_mm: Reading
    qty: Reading
    thickness_mm: Reading
    glass_type: TextReading
    holes: list[Hole] = Field(description="One entry per hole drawn on this panel.")
    notches: list[Notch] = Field(description="Notches, offcuts or cutouts on this panel.")
    edge_work: TextReading = Field(description="Edge work or grooves, e.g. 'polished edges all round'.")
    notes: str | None = Field(description="Anything else about this panel, including which general notes were applied.")
    confidence: Confidence
    confidence_reason: str

    @model_validator(mode="before")
    @classmethod
    def item_defaults_to_none(cls, data: Any) -> Any:
        return default_missing(data, item=None)


class Item(BaseModel):
    name: str = Field(description="What the item is called on the drawing, e.g. 'doors' or 'sliding window'.")
    overall_width_mm: Reading
    overall_height_mm: Reading


class DrawingExtraction(BaseModel):
    drawing_unit: LengthUnit | None = Field(
        description="Unit stated for the whole drawing in a note such as 'ALL DIMENSIONS IN MM'. null if none."
    )
    items: list[Item] = Field(
        description="Only when the sheet shows more than one separate item (e.g. a pair of doors and a window): "
        "one entry each with its overall size. Empty for a single item."
    )
    overall_width_mm: Reading = Field(description="Overall width of a single-item drawing. not_shown when items is used.")
    overall_height_mm: Reading = Field(description="Overall height of a single-item drawing. not_shown when items is used.")
    stated_hole_count: Reading = Field(
        description="Total number of holes stated in a note, e.g. '6NO.' or '2 holes'. not_shown if no count is written."
    )
    panels: list[Panel]
    general_notes: list[str] = Field(description="Notes that apply to the whole drawing, copied as written.")
    unreadable_items: list[str] = Field(description="Everything on the drawing that could not be read.")

    @model_validator(mode="before")
    @classmethod
    def sheet_defaults(cls, data: Any) -> Any:
        return default_missing(data, drawing_unit=None, items=[])