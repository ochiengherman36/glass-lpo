from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm as MM
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, Frame, KeepInFrame, Paragraph, Spacer, Table, TableStyle

from app.lpo import LpoDocument, is_check, rows

PDF_COLUMNS: tuple[tuple[str, str, float], ...] = (
    ("#", "Line", 2.5),
    ("Panel", "Panel ID", 5),
    ("W (mm)", "Width (mm)", 6.5),
    ("H (mm)", "Height (mm)", 6.5),
    ("Qty", "Qty", 6.5),
    ("Thk (mm)", "Thickness (mm)", 6),
    ("Glass type", "Glass type", 7.5),
    ("Area (m²)", "Area (m²)", 6),
    ("Holes", "Hole count", 5),
    ("Hole Ø (mm)", "Hole diameters (mm)", 7),
    ("Hole positions", "Hole positions", 9),
    ("Notches / offcuts", "Notches/offcuts", 11),
    ("Edge work", "Grooves/edge work", 9),
    ("Conf.", "Confidence", 6),
    ("Check", "Needs check (Y/N)", 5),
)
AREA_COLUMN = "Area (m²)"


@dataclass(frozen=True)
class PdfSettings:
    title: str = "Local Purchase Order (LPO) - Draft"
    font_sizes: tuple[float, ...] = (9, 8, 7, 6, 5.5, 5, 4.5)
    max_flags_at_smallest_font: int = 30
    margin_mm: float = 12
    font: str = "Helvetica"
    bold_font: str = "Helvetica-Bold"
    check_color: str = "#FFF176"
    header_color: str = "#E0E0E0"
    flag_box_color: str = "#C62828"
    flag_box_background: str = "#FFF5F5"
    date_format: str = "%d %b %Y, %H:%M"


DEFAULT_PDF_SETTINGS = PdfSettings()


class Styles:
    def __init__(self, size: float, settings: PdfSettings) -> None:
        leading = size * 1.25
        self.cell = ParagraphStyle("cell", fontName=settings.font, fontSize=size, leading=leading)
        self.cell_bold = ParagraphStyle("cell_bold", parent=self.cell, fontName=settings.bold_font)
        self.body = ParagraphStyle("body", parent=self.cell, fontSize=size + 1, leading=(size + 1) * 1.3)
        self.title = ParagraphStyle("title", fontName=settings.bold_font, fontSize=size + 6, leading=(size + 6) * 1.2)
        self.box_title = ParagraphStyle(
            "box_title", fontName=settings.bold_font, fontSize=size + 2, leading=(size + 2) * 1.3,
            textColor=colors.HexColor(settings.flag_box_color),
        )


def write_pdf(document: LpoDocument, path: Path | str, settings: PdfSettings = DEFAULT_PDF_SETTINGS) -> Path:
    path = Path(path)
    page_width, page_height = landscape(A4)
    margin = settings.margin_mm * MM
    width, height = page_width - 2 * margin, page_height - 2 * margin
    flags = [flag.message for flag in document.drawing.flags]

    story = None
    for size in settings.font_sizes:
        candidate = build_story(document, flags, 0, size, width, settings)
        if fits(candidate, width, height):
            story = candidate
            break
    if story is None:
        shown = flags[: settings.max_flags_at_smallest_font]
        story = build_story(document, shown, len(flags) - len(shown), settings.font_sizes[-1], width, settings)

    canvas = Canvas(str(path), pagesize=(page_width, page_height))
    canvas.setTitle(f"{document.lpo_no} - {settings.title}")
    frame = Frame(margin, margin, width, height, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    frame.addFromList([KeepInFrame(width, height, story, mode="shrink")], canvas)
    canvas.showPage()
    canvas.save()
    return path


def fits(story: list[Flowable], width: float, height: float) -> bool:
    return sum(flowable.wrap(width, height)[1] for flowable in story) <= height


def build_story(
    document: LpoDocument, flags: list[str], hidden_flags: int, size: float, width: float, settings: PdfSettings
) -> list[Flowable]:
    styles = Styles(size, settings)
    gap = size * 1.2
    return [
        header(document, styles, width, settings),
        Spacer(0, gap),
        items_table(document, styles, width, settings),
        Spacer(0, gap),
        Paragraph(totals_text(document), styles.body),
        Spacer(0, gap),
        check_box(flags, hidden_flags, styles, width, settings),
        Spacer(0, gap / 2),
        Paragraph(
            "Draft generated automatically from a photo of a hand drawing. Verify every CHECK item against "
            "the original drawing before cutting. Prices are not included.",
            styles.cell,
        ),
    ]


def header(document: LpoDocument, styles: Styles, width: float, settings: PdfSettings) -> Table:
    left = [
        Paragraph(escape(settings.title), styles.title),
        Paragraph(f"Source drawing: {escape(document.source_name)}", styles.body),
    ]
    right = [
        Paragraph(f"<b>LPO No:</b> {escape(document.lpo_no)}", styles.body),
        Paragraph(f"<b>Date:</b> {document.issued_at.strftime(settings.date_format)}", styles.body),
    ]
    table = Table([[left, right]], colWidths=[width * 0.65, width * 0.35])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    return table


def display(value: Any, column: str) -> str:
    if value is None:
        return ""
    if column == AREA_COLUMN and isinstance(value, (int, float)):
        return f"{value:.3f}"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def items_table(document: LpoDocument, styles: Styles, width: float, settings: PdfSettings) -> Table:
    data: list[list[Paragraph]] = [[Paragraph(escape(label), styles.cell_bold) for label, _, _ in PDF_COLUMNS]]
    check_cells: list[tuple[int, int]] = []

    for row_index, row in enumerate(rows(document), start=1):
        cells = []
        for column_index, (_, column, _) in enumerate(PDF_COLUMNS):
            value = row[column]
            if is_check(value) or (column == "Needs check (Y/N)" and value == "Y"):
                check_cells.append((column_index, row_index))
            cells.append(Paragraph(escape(display(value, column)), styles.cell))
        data.append(cells)

    total_weight = sum(weight for _, _, weight in PDF_COLUMNS)
    column_widths = [width * weight / total_weight for _, _, weight in PDF_COLUMNS]
    table = Table(data, colWidths=column_widths, repeatRows=1)
    commands: list[tuple] = [
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(settings.header_color)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]
    commands += [("BACKGROUND", cell, cell, colors.HexColor(settings.check_color)) for cell in check_cells]
    table.setStyle(TableStyle(commands))
    return table


def totals_text(document: LpoDocument) -> str:
    drawing = document.drawing
    pieces = sum(line.qty or 1 for line in drawing.lines)
    area = f"{drawing.total_area_m2:.3f} m²"
    if drawing.lines and all(line.area_m2 is None for line in drawing.lines):
        area = "not available until the CHECK sizes are confirmed"
    elif not drawing.area_complete:
        missing = sum(1 for line in drawing.lines if line.area_m2 is None)
        area += f" (excludes {missing} line{'s' if missing != 1 else ''} marked CHECK)"
    return (
        f"<b>Lines:</b> {len(drawing.lines)} &nbsp;&nbsp; <b>Pieces:</b> {pieces} &nbsp;&nbsp; "
        f"<b>Total area:</b> {area} &nbsp;&nbsp; <b>Total holes:</b> {drawing.total_holes}"
    )


def check_box(
    flags: list[str], hidden_flags: int, styles: Styles, width: float, settings: PdfSettings
) -> Table:
    total = len(flags) + hidden_flags
    if total == 0:
        content = [
            Paragraph("Needs human check: none", styles.box_title),
            Paragraph("All values were read clearly and passed the checks.", styles.body),
        ]
    else:
        content = [Paragraph(f"Needs human check ({total})", styles.box_title)]
        content += [Paragraph(f"&bull; {escape(message)}", styles.body) for message in flags]
        if hidden_flags:
            content.append(
                Paragraph(
                    f"&bull; ... and {hidden_flags} more item{'s' if hidden_flags != 1 else ''}: "
                    "see the Notes column in the Excel file.",
                    styles.body,
                )
            )

    box = Table([[content]], colWidths=[width])
    box.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor(settings.flag_box_color)),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(settings.flag_box_background)),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return box
