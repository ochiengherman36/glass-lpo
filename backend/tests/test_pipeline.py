import json
from datetime import datetime

import pytest

from app import pipeline
from app.extract import ExtractionError
from app.lpo import COLUMNS
from tests.factories import FakeExtractor, drawing, panel, unclear

NOW = datetime(2026, 11, 25, 10, 0, 0)


def test_end_to_end_run_writes_every_output(skewed_page_bytes, tmp_path):
    extractor = FakeExtractor()

    result = pipeline.run(skewed_page_bytes, tmp_path, source_name="photo.jpg", extractor=extractor, now=NOW)

    assert result.document.lpo_no == "LPO-20261125-100000"
    for name in ("photo-original.jpg", "photo-enhanced.jpg", "LPO-20261125-100000.xlsx", "LPO-20261125-100000.pdf",
                 "result.json"):
        assert (tmp_path / name).is_file(), name


@pytest.mark.parametrize(
    ("source_name", "enhanced_name"),
    [("images 16.jpg", "images-16-enhanced.jpg"), ("sd42teinfr7f1.jpeg", "sd42teinfr7f1-enhanced.jpg"),
     ("../../x?.png", "x-enhanced.jpg"), (None, "upload-enhanced.jpg")],
)
def test_image_outputs_are_named_after_the_uploaded_photo(skewed_page_bytes, tmp_path, source_name, enhanced_name):
    result = pipeline.run(skewed_page_bytes, tmp_path, source_name=source_name, extractor=FakeExtractor(), now=NOW)

    assert result.enhancement.enhanced_path == tmp_path / enhanced_name
    assert result.to_dict()["files"]["enhanced"] == enhanced_name


def test_extractor_receives_the_resized_claude_copies(skewed_page_bytes, tmp_path):
    extractor = FakeExtractor()

    pipeline.run(skewed_page_bytes, tmp_path, extractor=extractor, now=NOW)

    enhanced_path, original_path = extractor.calls[0]
    assert enhanced_path.name == "claude_enhanced.jpg"
    assert original_path.name == "claude_original.jpg"


def test_result_json_has_everything_the_ui_and_evaluation_need(skewed_page_bytes, tmp_path):
    extraction = drawing([panel(height_mm=unclear("1?00"))])

    pipeline.run(skewed_page_bytes, tmp_path, source_name="photo.jpg", extractor=FakeExtractor(extraction), now=NOW)

    saved = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert saved["lpo_no"] == "LPO-20261125-100000"
    assert saved["source_name"] == "photo.jpg"
    assert saved["columns"] == list(COLUMNS)
    assert saved["panels"][0]["Height (mm)"] == "CHECK"
    assert saved["needs_check"] is True
    assert any("height unclear" in flag["message"] for flag in saved["flags"])
    assert saved["totals"]["area_complete"] is False
    assert saved["usage"]["model"] == "fake-model"
    assert saved["extraction"]["panels"][0]["height_mm"]["raw_text"] == "1?00"
    assert saved["steps_applied"]


def test_source_name_defaults_to_the_file_name(paper_photo_path, tmp_path):
    result = pipeline.run(paper_photo_path, tmp_path / "out", extractor=FakeExtractor(), now=NOW)

    assert result.document.source_name == "paper_photo.jpg"


def test_extraction_errors_propagate(skewed_page_bytes, tmp_path):
    extractor = FakeExtractor(error=ExtractionError("rate limit"))

    with pytest.raises(ExtractionError, match="rate limit"):
        pipeline.run(skewed_page_bytes, tmp_path, extractor=extractor, now=NOW)
