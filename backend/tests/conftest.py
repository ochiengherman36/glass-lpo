from pathlib import Path

import cv2
import numpy as np
import pytest

from tests.synthetic import TEST_DRAWINGS_DIR, draw_page, encode_jpeg, rotate


@pytest.fixture
def paper_photo_path(tmp_path: Path) -> Path:
    page = draw_page(800, 1000)
    canvas = np.full((1500, 1300, 3), 50, np.uint8)
    source = np.array([[0, 0], [799, 0], [799, 999], [0, 999]], dtype=np.float32)
    target = np.array([[220, 180], [1050, 240], [1120, 1350], [150, 1290]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(source, target)
    cv2.warpPerspective(page, matrix, (1300, 1500), dst=canvas, borderMode=cv2.BORDER_TRANSPARENT)
    path = tmp_path / "paper_photo.jpg"
    path.write_bytes(encode_jpeg(canvas))
    return path


@pytest.fixture
def skewed_page_bytes() -> bytes:
    return encode_jpeg(rotate(draw_page(1200, 1600), 6.0))


@pytest.fixture
def small_page_bytes() -> bytes:
    return encode_jpeg(draw_page(450, 600))


@pytest.fixture
def real_drawing_paths() -> list[Path]:
    return sorted(TEST_DRAWINGS_DIR.glob("*/*.jp*g"))
