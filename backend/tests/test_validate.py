from __future__ import annotations

import pytest

from app.schema import Notch, TextReading
from app.validate import ValidationRules, validate_drawing
from tests.factories import clear, drawing, hole, not_shown, notch, panel, unclear


def messages(result) -> list[str]:
    return [flag.message for flag in result.flags]


def only_line(result):
    assert len(result.lines) == 1
    return result.lines[0]


def test_clean_drawing_has_no_flags():
    result = validate_drawing(drawing())

    line = only_line(result)
    assert result.flags == []
    assert not result.needs_check
    assert not line.needs_check
    assert line.confidence == "high"
    assert line.area_m2 == pytest.approx(1.08)
    assert line.hole_count == 2
    assert line.hole_positions == ["x150 y600", "x750 y600"]


def test_unclear_width_becomes_check_and_needs_check():
    result = validate_drawing(drawing([panel(width_mm=unclear("9?0"))], stated_hole_count=not_shown()))

    line = only_line(result)
    assert "width" in line.check_fields
    assert line.needs_check
    assert "P1: width unclear (raw: '9?0')" in messages(result)
    assert line.area_m2 is None
    assert line.confidence == "low"


def test_unclear_width_keeps_the_best_reading_for_the_checker():
    result = validate_drawing(drawing([panel(width_mm=unclear("650 crossed out, 600 written", 600))]))

    line = only_line(result)
    assert line.width_mm == 600
    assert "width" in line.check_fields
    assert line.area_m2 is None


def test_missing_width_is_flagged_as_not_written():
    result = validate_drawing(drawing([panel(width_mm=not_shown())], overall_width_mm=not_shown()))

    assert "P1: width not written on drawing" in messages(result)


@pytest.mark.parametrize(("overall", "flagged"), [(900, False), (905, False), (950, True)])
def test_panel_widths_must_add_up_to_the_overall_width(overall, flagged):
    panels = [panel("P1", 500, 2100), panel("P2", 400, 2100)]
    result = validate_drawing(
        drawing(panels, overall_width_mm=clear(overall), overall_height_mm=clear(2100), stated_hole_count=not_shown())
    )

    sum_flags = [m for m in messages(result) if "add up to" in m]
    assert bool(sum_flags) is flagged
    if flagged:
        assert sum_flags == ["Panel widths add up to 900 mm but the overall width is 950 mm"]
        assert all("width" in line.check_fields for line in result.lines)
        assert all(line.confidence == "low" for line in result.lines)


def test_stacked_panels_are_not_flagged_for_widths():
    panels = [panel("P1", 900, 600), panel("P2", 900, 600)]
    result = validate_drawing(
        drawing(panels, overall_width_mm=clear(900), overall_height_mm=clear(1200), stated_hole_count=not_shown())
    )

    assert result.flags == []


def test_panel_heights_must_add_up_when_stacked():
    panels = [panel("P1", 900, 600), panel("P2", 900, 700)]
    result = validate_drawing(
        drawing(panels, overall_width_mm=clear(900), overall_height_mm=clear(1200), stated_hole_count=not_shown())
    )

    assert "Panel heights add up to 1300 mm but the overall height is 1200 mm" in messages(result)


@pytest.mark.parametrize(("width", "flagged"), [(50, False), (3300, False), (40, True), (4000, True)])
def test_panel_size_must_be_within_range(width, flagged):
    result = validate_drawing(drawing([panel(width=width)], overall_width_mm=not_shown(), stated_hole_count=not_shown()))

    range_flags = [m for m in messages(result) if "outside the 50-3300 mm range" in m]
    assert bool(range_flags) is flagged


def test_standard_thickness_passes():
    result = validate_drawing(drawing([panel(thickness_mm=clear(12), holes=[hole(), hole()])]))

    assert result.flags == []


def test_non_standard_thickness_is_flagged():
    result = validate_drawing(drawing([panel(thickness_mm=clear(7), holes=[hole(), hole()])]))

    line = only_line(result)
    assert "P1: thickness 7 mm is not a standard glass thickness (4, 5, 6, 8, 10, 12, 15, 19)" in messages(result)
    assert "thickness" in line.check_fields
    assert line.confidence == "medium"


def test_missing_thickness_and_glass_type_are_check():
    result = validate_drawing(
        drawing([panel(thickness_mm=not_shown(), glass_type=TextReading(text=None, status="not_shown"))])
    )

    line = only_line(result)
    assert {"thickness", "glass_type"} <= line.check_fields
    assert "P1: thickness not written on drawing" in messages(result)
    assert "P1: glass type not written on drawing" in messages(result)
    assert line.area_m2 == pytest.approx(1.08)


def test_missing_edge_work_is_not_flagged():
    result = validate_drawing(drawing([panel(edge_work=TextReading(text=None, status="not_shown"), holes=[hole(), hole()])]))

    assert result.flags == []


def test_hole_that_does_not_fit_the_panel_is_flagged():
    result = validate_drawing(
        drawing([panel(width=60, height=1200, holes=[hole(80)])], overall_width_mm=clear(60), stated_hole_count=not_shown())
    )

    assert "P1: hole 1 diameter 80 mm does not fit in a 60 x 1200 mm panel" in messages(result)


def test_hole_that_fits_is_not_flagged():
    result = validate_drawing(drawing([panel(holes=[hole(25), hole(25)])]))

    assert result.flags == []


@pytest.mark.parametrize("diameter", [3, 150])
def test_hole_diameter_outside_range_is_flagged(diameter):
    result = validate_drawing(drawing([panel(holes=[hole(diameter), hole()])]))

    assert f"P1: hole 1 diameter {diameter} mm is outside the 5-100 mm range" in messages(result)


def test_unclear_hole_diameter_is_check():
    unclear_hole = hole()
    unclear_hole = unclear_hole.model_copy(update={"diameter_mm": unclear("2?")})
    result = validate_drawing(drawing([panel(holes=[unclear_hole, hole()])]))

    line = only_line(result)
    assert "holes" in line.check_fields
    assert "P1: hole 1 diameter unclear (raw: '2?')" in messages(result)
    assert line.confidence == "low"


def test_hole_outside_the_panel_is_flagged():
    result = validate_drawing(drawing([panel(holes=[hole(x=950, y=600), hole(x=750, y=600)])]))

    assert "P1: hole 1 centre (x950, y600) is outside the 900 x 1200 mm panel" in messages(result)


def test_undimensioned_hole_positions_are_not_flagged():
    result = validate_drawing(drawing([panel(holes=[hole(), hole()])]))

    assert result.flags == []
    assert only_line(result).hole_positions == ["not dimensioned", "not dimensioned"]


def test_missing_qty_is_assumed_one_and_flagged():
    result = validate_drawing(drawing([panel(qty=not_shown(), holes=[hole(), hole()])]))

    line = only_line(result)
    assert line.qty == 1
    assert line.needs_check
    assert "P1: quantity not written, assumed 1" in messages(result)
    assert line.area_m2 == pytest.approx(1.08)
    assert line.confidence == "medium"


def test_unclear_qty_is_check_and_blocks_area():
    result = validate_drawing(drawing([panel(qty=unclear("?"), holes=[hole(), hole()])]))

    line = only_line(result)
    assert "qty" in line.check_fields
    assert line.area_m2 is None


def test_area_uses_quantity():
    result = validate_drawing(
        drawing([panel(width=500, height=2100, qty=clear(2))], overall_width_mm=not_shown(),
                overall_height_mm=not_shown(), stated_hole_count=not_shown())
    )

    assert only_line(result).area_m2 == pytest.approx(2.1)


def test_notch_larger_than_panel_is_flagged():
    big = notch(width=1000, depth=50)
    result = validate_drawing(drawing([panel(notches=[big], holes=[hole(), hole()])]))

    assert "P1: offcut 1 (1000 x 50 mm) is larger than the 900 x 1200 mm panel" in messages(result)


def test_notch_that_fits_is_described():
    result = validate_drawing(drawing([panel(notches=[notch()], holes=[hole(), hole()])]))

    assert result.flags == []
    assert only_line(result).notches == ["offcut 50 x 50 mm, top-right corner"]


def test_long_notch_positions_are_shortened_for_the_lpo():
    wordy = notch(100, 50, "top-left corner of P3 (against the P2/P3 boundary line); the leader points to it")
    result = validate_drawing(drawing([panel(notches=[wordy], holes=[hole(), hole()])]))

    assert only_line(result).notches == ["offcut 100 x 50 mm, top-left corner of P3"]


def test_unclear_notch_size_is_check():
    bad = Notch(kind="notch", width_mm=unclear("1?0"), depth_mm=clear(50), position="top-left corner")
    result = validate_drawing(drawing([panel(notches=[bad], holes=[hole(), hole()])]))

    line = only_line(result)
    assert "notches" in line.check_fields
    assert "P1: notch 1 width unclear (raw: '1?0')" in messages(result)


def test_stated_hole_count_must_match_holes_drawn():
    result = validate_drawing(drawing([panel(holes=[hole()])], stated_hole_count=clear(2)))

    assert "Note says 2 holes but 1 is drawn" in messages(result)


@pytest.mark.parametrize(
    ("model_confidence", "overrides", "expected"),
    [
        ("high", {}, "high"),
        ("medium", {}, "medium"),
        ("high", {"thickness_mm": clear(7)}, "medium"),
        ("high", {"height_mm": unclear("1?00")}, "low"),
        ("low", {}, "low"),
    ],
    ids=["clean", "model-medium", "minor-flag", "critical-flag", "model-low"],
)
def test_confidence_is_the_lower_of_rules_and_model(model_confidence, overrides, expected):
    test_panel = panel(confidence=model_confidence, holes=[hole(), hole()], **overrides)

    result = validate_drawing(drawing([test_panel]))

    assert only_line(result).confidence == expected


def test_unreadable_items_become_drawing_flags():
    result = validate_drawing(drawing(unreadable_items=["note under the drawing"]))

    assert "Unreadable on drawing: note under the drawing" in messages(result)
    assert result.needs_check


def test_drawing_without_panels_is_flagged():
    result = validate_drawing(drawing([], stated_hole_count=not_shown()))

    assert "No glass panels found on the drawing" in messages(result)


def test_totals_cover_all_lines():
    panels = [
        panel("P1", 500, 2100, qty=clear(2), holes=[hole(), hole()]),
        panel("P2", 400, 2100, holes=[hole()]),
    ]
    result = validate_drawing(
        drawing(panels, overall_width_mm=not_shown(), overall_height_mm=not_shown(), stated_hole_count=not_shown())
    )

    assert result.total_area_m2 == pytest.approx(2.1 + 0.84)
    assert result.total_holes == 5
    assert result.area_complete


def test_total_area_is_marked_incomplete_when_a_line_has_no_area():
    panels = [panel("P1", 500, 2100), panel("P2", 400, 2100, height_mm=unclear("2?00"))]
    result = validate_drawing(
        drawing(panels, overall_width_mm=clear(900), overall_height_mm=clear(2100), stated_hole_count=not_shown())
    )

    assert result.total_area_m2 == pytest.approx(1.05)
    assert not result.area_complete


def test_rules_can_be_overridden():
    rules = ValidationRules(sum_tolerance_mm=60)
    panels = [panel("P1", 500, 2100), panel("P2", 400, 2100)]
    extraction = drawing(panels, overall_width_mm=clear(950), overall_height_mm=clear(2100), stated_hole_count=not_shown())

    assert validate_drawing(extraction, rules).flags == []
