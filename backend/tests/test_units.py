import pytest

from app.lpo import rows
from app.schema import Item, Reading
from app.units import normalize_units, parse_length
from app.validate import validate_drawing
from tests.factories import clear, drawing, hole, lpo_document, not_shown, panel


def written(value: float, unit: str | None, raw: str) -> Reading:
    return Reading(value=value, unit=unit, status="clear", raw_text=raw)


def sheet(*panels, **overrides):
    fields = {"overall_width_mm": not_shown(), "overall_height_mm": not_shown(), "stated_hole_count": not_shown()}
    fields.update(overrides)
    return drawing(list(panels), **fields)


@pytest.mark.parametrize(
    ("raw", "value", "unit", "fraction"),
    [
        ("2.95m", 2.95, "m", False),
        ("75cm", 75, "cm", False),
        ("4 feet", 4, "ft", False),
        ("3.5 ft", 3.5, "ft", False),
        ("107 7/8", 107.875, None, True),
        ("1/4", 0.25, None, True),
        ("7' 6\"", 90, "in", False),
        ("36 1/2 inches", 36.5, "in", True),
        ("1187 O/A", 1187, None, False),
        ("14MM UNIT", 14, "mm", False),
    ],
)
def test_parse_length_reads_number_unit_and_fractions(raw, value, unit, fraction):
    parsed = parse_length(raw)
    assert parsed is not None
    assert parsed.value == pytest.approx(value)
    assert (parsed.unit, parsed.fraction) == (unit, fraction)


@pytest.mark.parametrize("raw", [None, "", "650 crossed out, 600 written", "2 ft / 4 feet / 2 ft"])
def test_parse_length_gives_up_on_missing_or_several_numbers(raw):
    assert parse_length(raw) is None


@pytest.mark.parametrize(
    ("reading", "expected_mm"),
    [
        (written(2.95, "m", "2.95m"), 2950),
        (written(75, "cm", "75cm"), 750),
        (written(3.5, "ft", "3.5 feet"), 1067),
        (written(107.875, "in", "107 7/8\""), 2740),
        (written(900, "mm", "900mm"), 900),
        (written(900, None, "900"), 900),
    ],
)
def test_sizes_are_converted_to_whole_millimetres(reading, expected_mm):
    result = normalize_units(sheet(panel(width_mm=reading, height_mm=clear(1000))))
    width = result.panels[0].width_mm
    assert (width.value, width.unit, width.status) == (expected_mm, "mm", "clear")


def test_converted_values_keep_the_original_text_in_the_notes():
    result = normalize_units(sheet(panel(width_mm=written(75, "cm", "75cm"), height_mm=written(97, "cm", "97cm"))))
    assert result.panels[0].notes == "converted to mm from width '75cm', height '97cm'"


def test_unit_missing_from_the_reading_is_taken_from_its_raw_text():
    result = normalize_units(sheet(panel(width_mm=written(4, None, "4 feet"), height_mm=clear(1000))))
    assert result.panels[0].width_mm.value == 1219


def test_a_fraction_without_a_unit_is_assumed_inches_and_flagged():
    result = normalize_units(sheet(panel(width_mm=written(107.875, None, "107 7/8"), height_mm=clear(2000))))
    width = result.panels[0].width_mm
    assert (width.value, width.status) == (2740, "unclear")
    assert "inches assumed" in width.raw_text


def test_a_size_without_a_unit_follows_the_only_other_unit_on_the_sheet_and_is_flagged():
    result = normalize_units(sheet(panel(width_mm=written(4, "ft", "4 feet"), height_mm=written(7, None, "7"))))
    height = result.panels[0].height_mm
    assert (height.value, height.status) == (2134, "unclear")
    assert "feet assumed" in height.raw_text


def test_a_size_without_a_unit_on_a_mixed_sheet_is_flagged():
    result = normalize_units(
        sheet(panel(width_mm=written(2.95, "m", "2.95m"), height_mm=written(97, "cm", "97cm")),
              panel("P2", width_mm=written(75, None, "75"), height_mm=written(97, "cm", "97cm")))
    )
    assert result.panels[1].width_mm.status == "unclear"
    assert "mixes" in result.panels[1].width_mm.raw_text


def test_a_drawing_unit_note_applies_to_values_without_a_unit():
    result = normalize_units(
        sheet(panel(width_mm=written(36, None, "36"), height_mm=written(80, None, "80")), drawing_unit="in")
    )
    assert (result.panels[0].width_mm.value, result.panels[0].width_mm.status) == (914, "clear")


def test_hole_diameters_and_thickness_without_a_unit_stay_millimetres_on_a_feet_sheet():
    result = normalize_units(
        sheet(panel(width_mm=written(4, "ft", "4 feet"), height_mm=written(7, "ft", "7 feet"),
                    thickness_mm=written(10, None, "10"), holes=[hole(25)]))
    )
    converted = result.panels[0]
    assert (converted.thickness_mm.value, converted.thickness_mm.status) == (10, "clear")
    assert converted.holes[0].diameter_mm.value == 25


def test_a_value_already_converted_by_the_model_is_accepted_when_it_matches():
    result = normalize_units(sheet(panel(width_mm=written(2740, "mm", "107 7/8 in"), height_mm=clear(2000))))
    assert (result.panels[0].width_mm.value, result.panels[0].width_mm.status) == (2740, "clear")


def test_a_value_that_does_not_match_its_written_text_is_flagged():
    result = normalize_units(sheet(panel(width_mm=written(107.875, "mm", "107 7/8 in"), height_mm=clear(2000))))
    assert result.panels[0].width_mm.status == "unclear"
    assert "does not match" in result.panels[0].width_mm.raw_text


def test_normalizing_twice_changes_nothing():
    once = normalize_units(sheet(panel(width_mm=written(2.95, "m", "2.95m"), height_mm=written(2.4, "m", "2.4m"))))
    twice = normalize_units(once)
    assert twice.panels[0].width_mm == once.panels[0].width_mm


def test_converted_sizes_reach_the_lpo_rows_and_area():
    extraction = normalize_units(
        sheet(panel(width_mm=written(75, "cm", "75cm"), height_mm=written(97, "cm", "97cm")))
    )
    row = rows(lpo_document(extraction))[0]
    assert (row["Width (mm)"], row["Height (mm)"], row["Area (m²)"]) == (750, 970, 0.728)
    assert "75cm" in row["Notes"]


def items_sheet(door_width: float):
    return sheet(
        panel("P1", width=door_width, height=2100, item="doors"),
        panel("P2", width=door_width, height=2100, item="doors"),
        panel("P3", width=750, height=970, item="sliding window"),
        items=[
            Item(name="doors", overall_width_mm=clear(1800), overall_height_mm=clear(2100)),
            Item(name="sliding window", overall_width_mm=clear(750), overall_height_mm=clear(970)),
        ],
    )


def test_each_item_is_checked_against_its_own_overall_size():
    assert validate_drawing(items_sheet(900)).flags == []


def test_panels_that_do_not_add_up_to_their_item_are_flagged():
    result = validate_drawing(items_sheet(850))
    assert [flag.message for flag in result.drawing_flags] == [
        "doors: panel widths add up to 1700 mm but the overall width is 1800 mm"
    ]
    assert [line.area_m2 is None for line in result.lines] == [True, True, False]


def test_item_names_are_shown_in_the_notes():
    extraction = normalize_units(items_sheet(900))
    assert extraction.panels[2].notes == "Item: sliding window"
