from datetime import datetime

from app.lpo import generate_lpo_number, rows
from tests.factories import clear, drawing, hole, lpo_document, panel, unclear


def test_lpo_number_uses_date_and_time():
    assert generate_lpo_number(datetime(2026, 11, 25, 9, 5, 7)) == "LPO-20261125-090507"


def test_clean_row_has_numbers_for_the_erp():
    row = rows(lpo_document())[0]

    assert row["Width (mm)"] == 900
    assert isinstance(row["Width (mm)"], int)
    assert row["Area (m²)"] == 1.08
    assert row["Hole diameters (mm)"] == "25, 25"
    assert row["Hole positions"] == "x150 y600; x750 y600"
    assert row["Confidence"] == "High"
    assert row["Needs check (Y/N)"] == "N"
    assert row["Notes"] == ""


def test_checked_values_show_check_with_the_best_reading():
    extraction = drawing([panel(width_mm=unclear("650 crossed out, 600 written", 600), holes=[hole(), hole()])])

    row = rows(lpo_document(extraction))[0]

    assert row["Width (mm)"] == "CHECK (600?)"
    assert row["Area (m²)"] == "CHECK"
    assert row["Needs check (Y/N)"] == "Y"
    assert "width unclear (raw: '650 crossed out, 600 written')" in row["Notes"]


def test_unreadable_value_shows_plain_check():
    extraction = drawing([panel(thickness_mm=unclear("1?"), holes=[hole(), hole()])])

    row = rows(lpo_document(extraction))[0]

    assert row["Thickness (mm)"] == "CHECK"
    assert row["Width (mm)"] == 900


def test_undimensioned_hole_positions_are_written_once():
    row = rows(lpo_document(drawing([panel(holes=[hole(), hole()])])))[0]

    assert row["Hole positions"] == "not dimensioned"


def test_notes_keep_the_panel_notes_and_add_flags():
    extraction = drawing([panel(notes="from note: 8MM TOUGHENED", qty=clear(1), thickness_mm=clear(7),
                                holes=[hole(), hole()])])

    row = rows(lpo_document(extraction))[0]

    assert row["Notes"].startswith("from note: 8MM TOUGHENED; thickness 7 mm is not a standard")
