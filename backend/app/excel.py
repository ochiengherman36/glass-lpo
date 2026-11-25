from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.lpo import COLUMNS, LpoDocument, is_check, rows


@dataclass(frozen=True)
class ExcelSettings:
    sheet_title: str = "LPO"
    check_fill: str = "FFFF00"
    header_fill: str = "D9D9D9"
    area_format: str = "0.000"
    min_column_width: int = 8
    max_column_width: int = 60


DEFAULT_EXCEL_SETTINGS = ExcelSettings()


def write_excel(document: LpoDocument, path: Path | str, settings: ExcelSettings = DEFAULT_EXCEL_SETTINGS) -> Path:
    path = Path(path)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = settings.sheet_title

    sheet.append(list(COLUMNS))
    for row in rows(document):
        sheet.append([row[column] for column in COLUMNS])

    style_sheet(sheet, settings)
    workbook.save(path)
    return path


def style_sheet(sheet, settings: ExcelSettings) -> None:
    header_fill = PatternFill("solid", fgColor=settings.header_fill)
    check_fill = PatternFill("solid", fgColor=settings.check_fill)
    area_column = COLUMNS.index("Area (m²)") + 1
    needs_check_column = COLUMNS.index("Needs check (Y/N)") + 1

    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)

    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if is_check(cell.value) or (cell.column == needs_check_column and cell.value == "Y"):
                cell.fill = check_fill
            if cell.column == area_column and isinstance(cell.value, float):
                cell.number_format = settings.area_format

    for index, column in enumerate(COLUMNS, start=1):
        values = [str(cell.value) for cell in sheet[get_column_letter(index)] if cell.value is not None]
        longest = max((len(value) for value in values), default=len(column))
        width = min(max(longest + 2, settings.min_column_width), settings.max_column_width)
        sheet.column_dimensions[get_column_letter(index)].width = width

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions