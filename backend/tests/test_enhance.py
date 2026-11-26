import io
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from app.enhance import (
    DEFAULT_SETTINGS,
    EnhancementError,
    EnhanceSettings,
    OutputNames,
    enhance_image,
    estimate_skew_angle,
)

CLAUDE_LONG_SIDE = DEFAULT_SETTINGS.claude_long_side
from tests.synthetic import TEST_DRAWINGS_DIR, draw_page, encode_jpeg, rotate

PAPER_RGB = (245, 245, 245)


def long_side(path: Path) -> int:
    image = cv2.imread(str(path))
    assert image is not None
    return max(image.shape[:2])


def test_perspective_is_corrected_when_paper_edges_are_visible(paper_photo_path, tmp_path):
    result = enhance_image(paper_photo_path, tmp_path / "out")

    assert result.perspective_corrected
    assert "perspective corrected to the paper edges" in result.steps_applied
    height, width = cv2.imread(str(result.enhanced_path)).shape[:2]
    assert width / height == pytest.approx(800 / 1000, rel=0.1)


def test_a_large_rectangle_drawn_on_the_page_is_not_mistaken_for_the_paper_edge(tmp_path):
    page = np.full((1000, 1400, 3), 245, np.uint8)
    cv2.rectangle(page, (150, 120), (1250, 880), (30, 30, 30), 4)
    cv2.putText(page, "107 7/8", (550, 960), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (30, 30, 30), 3)

    result = enhance_image(encode_jpeg(page), tmp_path)

    assert not result.perspective_corrected
    assert "perspective: no paper edge found, skipped" in result.steps_applied


def shadowed_page_with_faint_label() -> np.ndarray:
    gradient = np.linspace(240, 150, 2000, dtype=np.float32)
    page = np.tile(gradient, (1400, 1)).astype(np.uint8)
    page = cv2.cvtColor(page, cv2.COLOR_GRAY2BGR)
    cv2.putText(page, "2400", (150, 400), cv2.FONT_HERSHEY_SIMPLEX, 3, (40, 40, 40), 6)
    faint = page[900, 1600].astype(int) - 45
    cv2.putText(page, "4 ft", (1500, 900), cv2.FONT_HERSHEY_SIMPLEX, 2, tuple(int(v) for v in faint), 3)
    return page


def test_faint_writing_in_a_shadow_survives_and_the_paper_turns_white(tmp_path):
    result = enhance_image(encode_jpeg(shadowed_page_with_faint_label()), tmp_path)
    enhanced = cv2.imread(str(result.enhanced_path), cv2.IMREAD_GRAYSCALE)

    faint_label = enhanced[830:920, 1490:1720]
    assert (faint_label < 160).sum() > 300
    assert np.median(enhanced) > 240
    assert np.median(enhanced[:, 1700:]) > 240


def test_falls_back_to_deskew_when_there_is_no_paper_edge(skewed_page_bytes, tmp_path):
    result = enhance_image(skewed_page_bytes, tmp_path)

    assert not result.perspective_corrected
    assert "perspective: no paper edge found, skipped" in result.steps_applied
    assert any(step.startswith("deskewed by") for step in result.steps_applied)


@pytest.mark.parametrize("degrees", [-6.0, 5.0])
def test_deskew_straightens_the_page(degrees, tmp_path):
    skewed = rotate(draw_page(1200, 1600), degrees)
    assert abs(estimate_skew_angle(skewed)) > 4

    result = enhance_image(encode_jpeg(skewed), tmp_path)

    assert abs(estimate_skew_angle(cv2.imread(str(result.enhanced_path)))) < 1.0


def test_deskew_is_skipped_when_lines_disagree(tmp_path):
    page = np.full((1600, 1200, 3), 245, np.uint8)
    for index, y in enumerate(range(120, 1500, 90)):
        tilt = 60 if index % 2 else -45
        cv2.line(page, (50, y), (1150, y + tilt), (90, 30, 30), 2)

    result = enhance_image(encode_jpeg(page), tmp_path)

    assert "deskew: no consistent straight lines (curved page or too few lines), skipped" in result.steps_applied


@pytest.mark.parametrize("degrees", [0.0, 1.5])
def test_small_tilts_are_left_alone(degrees, tmp_path):
    result = enhance_image(encode_jpeg(rotate(draw_page(1200, 1600), degrees)), tmp_path)

    assert not any(step.startswith("deskewed by") for step in result.steps_applied)


def test_writes_all_outputs_and_claude_copies_fit_the_api_limit(skewed_page_bytes, tmp_path):
    result = enhance_image(skewed_page_bytes, tmp_path)

    for path in (result.original_path, result.enhanced_path, result.claude_enhanced_path, result.claude_original_path):
        assert path.exists() and path.stat().st_size > 0
    assert long_side(result.claude_enhanced_path) <= CLAUDE_LONG_SIDE
    assert long_side(result.claude_original_path) <= CLAUDE_LONG_SIDE
    assert long_side(result.enhanced_path) >= long_side(result.claude_enhanced_path)


def test_small_images_are_upscaled(small_page_bytes, tmp_path):
    result = enhance_image(small_page_bytes, tmp_path)

    assert any(step.startswith("upscaled") for step in result.steps_applied)
    assert long_side(result.enhanced_path) == 600 * DEFAULT_SETTINGS.max_upscale


def test_settings_can_be_overridden(small_page_bytes, tmp_path):
    settings = EnhanceSettings(claude_long_side=500, output_names=OutputNames(enhanced="clean.jpg"))

    result = enhance_image(small_page_bytes, tmp_path, settings)

    assert result.enhanced_path.name == "clean.jpg"
    assert long_side(result.claude_enhanced_path) == 500


def test_exif_orientation_is_applied(tmp_path):
    buffer = io.BytesIO()
    exif = Image.Exif()
    exif[0x0112] = 6
    Image.new("RGB", (300, 200), PAPER_RGB).save(buffer, format="JPEG", exif=exif.tobytes())

    result = enhance_image(buffer.getvalue(), tmp_path)

    assert "fixed EXIF orientation" in result.steps_applied
    height, width = cv2.imread(str(result.original_path)).shape[:2]
    assert (width, height) == (200, 300)


def test_png_is_accepted(tmp_path):
    buffer = io.BytesIO()
    Image.fromarray(draw_page(450, 600)).save(buffer, format="PNG")

    result = enhance_image(buffer.getvalue(), tmp_path)

    assert result.enhanced_path.exists()


@pytest.mark.parametrize(
    "payload",
    [b"definitely not an image", b""],
    ids=["text-bytes", "empty"],
)
def test_unreadable_input_raises_a_clean_error(payload, tmp_path):
    with pytest.raises(EnhancementError, match="not a readable JPG or PNG"):
        enhance_image(payload, tmp_path)


def test_unsupported_format_is_rejected(tmp_path):
    buffer = io.BytesIO()
    Image.new("RGB", (50, 50), PAPER_RGB).save(buffer, format="GIF")

    with pytest.raises(EnhancementError, match="Unsupported image format 'GIF'"):
        enhance_image(buffer.getvalue(), tmp_path)


def test_missing_file_raises_a_clean_error(tmp_path):
    with pytest.raises(EnhancementError, match="not found"):
        enhance_image(tmp_path / "missing.jpg", tmp_path)


@pytest.mark.skipif(not any(TEST_DRAWINGS_DIR.glob("*/*.jp*g")), reason="no real test drawings present")
def test_real_test_drawings_enhance_without_errors(real_drawing_paths, tmp_path):
    for photo in real_drawing_paths:
        result = enhance_image(photo, tmp_path / photo.stem)
        assert result.enhanced_path.exists()
        assert long_side(result.claude_enhanced_path) <= CLAUDE_LONG_SIDE
