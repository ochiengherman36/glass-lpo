from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

WORK_LONG_SIDE = 2000
CLAUDE_LONG_SIDE = 1568
MAX_UPSCALE = 2.0
MIN_PAPER_AREA_RATIO = 0.4
MAX_PAPER_AREA_RATIO = 0.97
MIN_DESKEW_DEGREES = 3.0
MAX_DESKEW_DEGREES = 10.0
MIN_SKEW_LINES = 3
SKEW_AGREEMENT_DEGREES = 1.0
MIN_AGREEING_FRACTION = 0.8
ALLOWED_FORMATS = {"JPEG", "PNG", "MPO"}
EXIF_ORIENTATION_TAG = 0x0112


class EnhancementError(ValueError):
    pass


@dataclass
class EnhanceResult:
    original_path: Path
    enhanced_path: Path
    claude_enhanced_path: Path
    claude_original_path: Path
    perspective_corrected: bool
    steps_applied: list[str] = field(default_factory=list)


def enhance_image(source: Path | str | bytes, out_dir: Path | str) -> EnhanceResult:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[str] = []

    original = load_image(source, steps)

    work = resize_long_side(original, WORK_LONG_SIDE, allow_upscale=False)
    if work.shape != original.shape:
        steps.append(f"resized to {WORK_LONG_SIDE} px long side")

    work, perspective_corrected = correct_perspective(work, steps)
    if not perspective_corrected:
        work = deskew(work, steps)

    gray = normalize_lighting(work, steps)
    gray = denoise_and_sharpen(gray, steps)
    gray = upscale_if_small(gray, steps)

    result = EnhanceResult(
        original_path=out_dir / "original.jpg",
        enhanced_path=out_dir / "enhanced.jpg",
        claude_enhanced_path=out_dir / "claude_enhanced.jpg",
        claude_original_path=out_dir / "claude_original.jpg",
        perspective_corrected=perspective_corrected,
        steps_applied=steps,
    )
    write_jpeg(result.original_path, original)
    write_jpeg(result.enhanced_path, gray)
    write_jpeg(result.claude_enhanced_path, resize_long_side(gray, CLAUDE_LONG_SIDE, allow_upscale=False))
    write_jpeg(result.claude_original_path, resize_long_side(original, CLAUDE_LONG_SIDE, allow_upscale=False))
    return result


def load_image(source: Path | str | bytes, steps: list[str]) -> np.ndarray:
    try:
        data = bytes(source) if isinstance(source, (bytes, bytearray)) else Path(source).read_bytes()
    except FileNotFoundError as exc:
        raise EnhancementError(f"Image file not found: {source}") from exc
    except OSError as exc:
        raise EnhancementError(f"Could not read image file: {source}") from exc

    try:
        with Image.open(io.BytesIO(data)) as pil:
            pil.load()
            image_format = pil.format
            orientation = pil.getexif().get(EXIF_ORIENTATION_TAG, 1)
            rgb = ImageOps.exif_transpose(pil).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise EnhancementError("The file is not a readable JPG or PNG image.") from exc

    if image_format not in ALLOWED_FORMATS:
        raise EnhancementError(f"Unsupported image format '{image_format}'. Upload a JPG or PNG photo.")
    if orientation not in (None, 1):
        steps.append("fixed EXIF orientation")
    return cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2BGR)


def resize_long_side(image: np.ndarray, target: int, allow_upscale: bool) -> np.ndarray:
    height, width = image.shape[:2]
    long_side = max(height, width)
    if long_side == target or (long_side < target and not allow_upscale):
        return image
    scale = target / long_side
    interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    size = (round(width * scale), round(height * scale))
    return cv2.resize(image, size, interpolation=interpolation)


def find_paper_quad(image: np.ndarray) -> np.ndarray | None:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=2)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    image_area = image.shape[0] * image.shape[1]
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue
        area_ratio = cv2.contourArea(approx) / image_area
        if MIN_PAPER_AREA_RATIO <= area_ratio <= MAX_PAPER_AREA_RATIO:
            return approx.reshape(4, 2).astype(np.float32)
    return None


def order_corners(points: np.ndarray) -> np.ndarray:
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1).ravel()
    top_left = points[np.argmin(sums)]
    bottom_right = points[np.argmax(sums)]
    top_right = points[np.argmin(diffs)]
    bottom_left = points[np.argmax(diffs)]
    return np.array([top_left, top_right, bottom_right, bottom_left], dtype=np.float32)


def correct_perspective(image: np.ndarray, steps: list[str]) -> tuple[np.ndarray, bool]:
    quad = find_paper_quad(image)
    if quad is None:
        steps.append("perspective: no paper edge found, skipped")
        return image, False

    tl, tr, br, bl = order_corners(quad)
    width = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
    height = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))
    target = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(np.array([tl, tr, br, bl]), target)
    steps.append("perspective corrected to the paper edges")
    return cv2.warpPerspective(image, matrix, (width, height)), True


def horizontal_line_angles(image: np.ndarray) -> list[float]:
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 30, 100)
    min_length = gray.shape[1] // 4
    lines = cv2.HoughLinesP(edges, 1, np.pi / 720, threshold=100, minLineLength=min_length, maxLineGap=20)
    if lines is None:
        return []
    angles = [float(np.degrees(np.arctan2(y2 - y1, x2 - x1))) for x1, y1, x2, y2 in lines.reshape(-1, 4)]
    return [angle for angle in angles if abs(angle) <= MAX_DESKEW_DEGREES]


def estimate_skew_angle(image: np.ndarray) -> float | None:
    angles = np.array(horizontal_line_angles(image))
    if len(angles) < MIN_SKEW_LINES:
        return None
    median = float(np.median(angles))
    agreeing = np.mean(np.abs(angles - median) <= SKEW_AGREEMENT_DEGREES)
    if agreeing < MIN_AGREEING_FRACTION:
        return None
    return median


def deskew(image: np.ndarray, steps: list[str]) -> np.ndarray:
    angle = estimate_skew_angle(image)
    if angle is None:
        steps.append("deskew: no consistent straight lines (curved page or too few lines), skipped")
        return image
    if abs(angle) < MIN_DESKEW_DEGREES:
        steps.append(f"deskew: page within {MIN_DESKEW_DEGREES:.0f} deg of straight ({angle:.1f} deg), left as is")
        return image

    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    steps.append(f"deskewed by {angle:.1f} deg")
    return cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def normalize_lighting(image: np.ndarray, steps: list[str]) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    background = cv2.medianBlur(cv2.dilate(gray, np.ones((7, 7), np.uint8)), 21)
    normalized = cv2.divide(gray, background, scale=255)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    steps.append("removed shadows and uneven lighting, boosted contrast (CLAHE)")
    return clahe.apply(normalized)


def denoise_and_sharpen(gray: np.ndarray, steps: list[str]) -> np.ndarray:
    denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
    blurred = cv2.GaussianBlur(denoised, (0, 0), sigmaX=1.5)
    steps.append("denoised and sharpened")
    return cv2.addWeighted(denoised, 1.5, blurred, -0.5, 0)


def upscale_if_small(gray: np.ndarray, steps: list[str]) -> np.ndarray:
    long_side = max(gray.shape[:2])
    if long_side >= WORK_LONG_SIDE:
        return gray
    scale = min(MAX_UPSCALE, WORK_LONG_SIDE / long_side)
    steps.append(f"upscaled x{scale:.2f}")
    return resize_long_side(gray, round(long_side * scale), allow_upscale=True)


def write_jpeg(path: Path, image: np.ndarray, quality: int = 95) -> None:
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise EnhancementError(f"Could not encode {path.name}")
    path.write_bytes(encoded.tobytes())