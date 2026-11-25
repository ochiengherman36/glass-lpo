from openpyxl import load_workbook

from app.excel import write_excel
from app.lpo import COLUMNS
from tests.factories import drawing, hole, lpo_document, many_panels, panel, unclear

BRIEF_COLUMNS = [
    "LPO No", "Line", "Panel ID", "Width (mm)", "Height (mm)", "Qty", "Thickness (mm)", "Glass type",
    "Area (m²)", "Hole count", "Hole diameters (mm)", "Hole positions", "Notches/offcuts",
    "Grooves/edge work", "Notes", "Confidence", "Needs check (Y/N)",
]


def load_sheet(path):
    return load_workbook(path).active


def column(sheet, name: str) -> list:
    index = COLUMNS.index(name) + 1
    return [sheet.cell(row=row, column=index) for row in range(2, sheet.max_row + 1)]


def is_yellow(cell) -> bool:
    return cell.fill.fill_type == "solid" and cell.fill.fgColor.rgb.endswith("FFFF00")


def test_header_matches_the_brief_exactly(tmp_path):
    sheet = load_sheet(write_excel(lpo_document(), tmp_path / "lpo.xlsx"))

    assert [cell.value for cell in sheet[1]] == BRIEF_COLUMNS
    assert sheet.freeze_panes == "A2"


def test_one_row_per_panel_with_the_lpo_number(tmp_path):
    sheet = load_sheet(write_excel(lpo_document(many_panels(5)), tmp_path / "lpo.xlsx"))

    assert sheet.max_row == 6
    assert {cell.value for cell in column(sheet, "LPO No")} == {"LPO-20261125-143005"}
    assert [cell.value for cell in column(sheet, "Line")] == [1, 2, 3, 4, 5]


def test_check_cells_are_yellow_and_clean_cells_are_not(tmp_path):
    extraction = drawing([panel(height_mm=unclear("1?00"), holes=[hole(), hole()])])

    sheet = load_sheet(write_excel(lpo_document(extraction), tmp_path / "lpo.xlsx"))

    height = column(sheet, "Height (mm)")[0]
    width = column(sheet, "Width (mm)")[0]
    assert height.value == "CHECK"
    assert is_yellow(height)
    assert width.value == 900
    assert not is_yellow(width)
    assert is_yellow(column(sheet, "Area (m²)")[0])


def test_needs_check_is_y_or_n(tmp_path):
    extraction = drawing([panel("P1", holes=[hole()]), panel("P2", width_mm=unclear("?"), holes=[hole()])])

    sheet = load_sheet(write_excel(lpo_document(extraction), tmp_path / "lpo.xlsx"))

    assert [cell.value for cell in column(sheet, "Needs check (Y/N)")] == ["N", "Y"]


def test_numbers_stay_numeric_for_erp_import(tmp_path):
    sheet = load_sheet(write_excel(lpo_document(), tmp_path / "lpo.xlsx"))

    assert column(sheet, "Width (mm)")[0].value == 900
    assert column(sheet, "Area (m²)")[0].value == 1.08
    assert column(sheet, "Area (m²)")[0].number_format == "0.000"
    assert column(sheet, "Hole count")[0].value == 2
