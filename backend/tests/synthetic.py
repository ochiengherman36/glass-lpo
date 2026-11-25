from pathlib import Path

import cv2
import numpy as np

PAPER = (245, 245, 245)
INK = (140, 40, 40)
TEST_DRAWINGS_DIR = Path(__file__).resolve().parents[2] / "test_drawings"


def draw_page(width: int, height: int) -> np.ndarray:
    page = np.full((height, width, 3), PAPER, np.uint8)
    for y in range(60, height, 40):
        cv2.line(page, (0, y), (width, y), (225, 215, 205), 1)
    left, top = width // 5, height // 4
    right, bottom = width - width // 5, height - height // 5
    cv2.rectangle(page, (left, top), (right, bottom), INK, 3)
    cv2.circle(page, (left + 80, (top + bottom) // 2), 10, INK, 2)
    cv2.circle(page, (right - 80, (top + bottom) // 2), 10, INK, 2)
    cv2.putText(page, "900 x 1200", (left, top - 40), cv2.FONT_HERSHEY_SIMPLEX, 1.4, INK, 3)
    cv2.putText(page, "P1", ((left + right) // 2 - 20, (top + bottom) // 2), cv2.FONT_HERSHEY_SIMPLEX, 1.2, INK, 3)
    cv2.putText(page, "900", ((left + right) // 2 - 30, bottom + 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, INK, 3)
    return page


def encode_jpeg(image: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    assert ok
    return encoded.tobytes()


def rotate(image: np.ndarray, degrees: float) -> np.ndarray:
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), degrees, 1.0)
    return cv2.warpAffine(image, matrix, (width, height), borderMode=cv2.BORDER_CONSTANT, borderValue=PAPER)
