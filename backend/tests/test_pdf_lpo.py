from pypdf import PdfReader

from app.pdf_lpo import write_pdf
from tests.factories import drawing, hole, lpo_document, many_panels, not_shown, panel, unclear


def read_pdf(path) -> tuple[int, str]:
    reader = PdfReader(path)
    text = " ".join(page.extract_text() for page in reader.pages)
    return len(reader.pages), " ".join(text.split())


def normalized(text: str) -> str:
    return " ".join(text.split())


def three_panels_with_flags():
    return drawing(
        [
            panel("P1", 500, 2100, holes=[hole(), hole()]),
            panel("P2", 400, 2100, thickness_mm=not_shown()),
            panel("P3", 600, 2100, width_mm=unclear("6?0")),
        ],
        overall_width_mm=not_shown(),
        overall_height_mm=not_shown(),
        stated_hole_count=not_shown(),
    )


def test_three_panels_fit_on_one_page_with_every_flag(tmp_path):
    document = lpo_document(three_panels_with_flags())

    pages, text = read_pdf(write_pdf(document, tmp_path / "lpo.pdf"))

    assert pages == 1
    assert "LPO-20261125-143005" in text
    assert "25 Nov 2026" in text
    assert "Needs human check (2)" in text
    for flag in document.drawing.flags:
        assert normalized(flag.message) in text


def test_forty_panels_still_fit_on_one_page(tmp_path):
    document = lpo_document(many_panels(40))

    pages, text = read_pdf(write_pdf(document, tmp_path / "lpo.pdf"))

    assert pages == 1
    assert "P40" in text
    assert "Total area: 42.000 m²" in text


def test_many_flags_are_summarised_but_stay_on_one_page(tmp_path):
    document = lpo_document(many_panels(40, width_mm=unclear("?00")))

    pages, text = read_pdf(write_pdf(document, tmp_path / "lpo.pdf"))

    assert pages == 1
    assert "Needs human check (40)" in text
    assert "more items: see the Notes column in the Excel file" in text


def test_clean_drawing_says_nothing_needs_checking(tmp_path):
    pages, text = read_pdf(write_pdf(lpo_document(), tmp_path / "lpo.pdf"))

    assert pages == 1
    assert "Needs human check: none" in text
    assert "Total area: 1.080 m²" in text
    assert "Total holes: 2" in text


def test_totals_say_when_area_is_incomplete(tmp_path):
    pages, text = read_pdf(write_pdf(lpo_document(three_panels_with_flags()), tmp_path / "lpo.pdf"))

    assert "Total area: 1.890 m² (excludes 1 line marked CHECK)" in text


def test_check_is_never_split_across_lines(tmp_path):
    every_field_unclear = panel(
        width_mm=unclear("?"), height_mm=unclear("?"), qty=unclear("?"), thickness_mm=unclear("?"), holes=[hole()]
    )
    document = lpo_document(drawing([every_field_unclear], stated_hole_count=not_shown()))

    _, text = read_pdf(write_pdf(document, tmp_path / "lpo.pdf"))

    assert "CHEC K" not in text
    assert "CHECK" in text


def test_no_prices_on_the_lpo(tmp_path):
    _, text = read_pdf(write_pdf(lpo_document(), tmp_path / "lpo.pdf"))

    assert "KES" not in text
    assert "Prices are not included" in text
