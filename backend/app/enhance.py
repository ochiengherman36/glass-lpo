from __future__ import annotations

import io
import re
from dataclasses import dataclass, field, replace
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED_FORMATS = frozenset({"JPEG", "PNG", "MPO"})
EXIF_ORIENTATION_TAG = 0x0112


@dataclass(frozen=True)
class OutputNames:
    original: str = "original.jpg"
    enhanced: str = "enhanced.jpg"
    claude_enhanced: str = "claude_enhanced.jpg"
    claude_original: str = "claude_original.jpg"

    def for_source(self, source_name: str | None) -> OutputNames:
        stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(source_name or "").stem).strip("-.")
        if not stem:
            return self
        return replace(self, original=f"{stem}-{self.original}", enhanced=f"{stem}-{self.enhanced}")


@dataclass(frozen=True)
class EnhanceSettings:
    work_long_side: int = 2000
    claude_long_side: int = 1568
    max_upscale: float = 3.0
    jpeg_quality: int = 95

    edge_blur_kernel: int = 5
    paper_canny_low: int = 50
    paper_canny_high: int = 150
    paper_edge_dilate_kernel: int = 3
    paper_edge_dilate_iterations: int = 2
    paper_candidate_contours: int = 5
    paper_poly_epsilon: float = 0.02
    min_paper_area_ratio: float = 0.4
    max_paper_area_ratio: float = 0.97
    paper_border_band_fraction: float = 0.03
    min_paper_border_contrast: float = 30.0

    line_canny_low: int = 30
    line_canny_high: int = 100
    line_min_length_fraction: float = 0.25
    line_hough_threshold: int = 100
    line_hough_angle_step_degrees: float = 0.25
    line_max_gap: int = 20
    min_deskew_degrees: float = 3.0
    max_deskew_degrees: float = 10.0
    min_skew_lines: int = 3
    skew_agreement_degrees: float = 1.0
    min_agreeing_fraction: float = 0.8

    background_dilate_fraction: float = 0.008
    min_background_dilate_kernel: int = 7
    background_median_fraction: float = 0.02
    min_background_median_kernel: int = 15
    ink_percentile: float = 1.0
    paper_white_fraction: float = 0.92
    ink_gamma: float = 1.3

    denoise_strength: float = 6.0
    denoise_template_window: int = 7
    denoise_search_window: int = 21
    sharpen_sigma: float = 1.2
    sharpen_amount: float = 0.35

    output_names: OutputNames = field(default_factory=OutputNames)


DEFAULT_SETTINGS = EnhanceSettings()


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


def enhance_image(
    source: Path | str | bytes,
    out_dir: Path | str,
    settings: EnhanceSettings = DEFAULT_SETTINGS,
) -> EnhanceResult:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[str] = []

    original = load_image(source, steps)

    work = resize_long_side(original, settings.work_long_side, allow_upscale=False)
    if work.shape != original.shape:
        steps.append(f"resized to {settings.work_long_side} px long side")

    work, perspective_corrected = correct_perspective(work, steps, settings)
    if not perspective_corrected:
        work = deskew(work, steps, settings)

    gray = upscale_if_small(to_gray(work), steps, settings)
    gray = normalize_lighting(gray, steps, settings)
    gray = denoise_and_sharpen(gray, steps, settings)

    names = settings.output_names
    result = EnhanceResult(
        original_path=out_dir / names.original,
        enhanced_path=out_dir / names.enhanced,
        claude_enhanced_path=out_dir / names.claude_enhanced,
        claude_original_path=out_dir / names.claude_original,
        perspective_corrected=perspective_corrected,
        steps_applied=steps,
    )
    claude_enhanced = resize_long_side(gray, settings.claude_long_side, allow_upscale=False)
    claude_original = resize_long_side(original, settings.claude_long_side, allow_upscale=False)
    write_jpeg(result.original_path, original, settings.jpeg_quality)
    write_jpeg(result.enhanced_path, gray, settings.jpeg_quality)
    write_jpeg(result.claude_enhanced_path, claude_enhanced, settings.jpeg_quality)
    write_jpeg(result.claude_original_path, claude_original, settings.jpeg_quality)
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


def to_gray(image: np.ndarray) -> np.ndarray:
    return image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def blurred_edges(gray: np.ndarray, low: int, high: int, settings: EnhanceSettings) -> np.ndarray:
    kernel = (settings.edge_blur_kernel, settings.edge_blur_kernel)
    return cv2.Canny(cv2.GaussianBlur(gray, kernel, 0), low, high)


def find_paper_quad(image: np.ndarray, settings: EnhanceSettings = DEFAULT_SETTINGS) -> np.ndarray | None:
    edges = blurred_edges(to_gray(image), settings.paper_canny_low, settings.paper_canny_high, settings)
    dilate_kernel = np.ones((settings.paper_edge_dilate_kernel,) * 2, np.uint8)
    edges = cv2.dilate(edges, dilate_kernel, iterations=settings.paper_edge_dilate_iterations)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    image_area = image.shape[0] * image.shape[1]
    largest = sorted(contours, key=cv2.contourArea, reverse=True)[: settings.paper_candidate_contours]
    for contour in largest:
        epsilon = settings.paper_poly_epsilon * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue
        area_ratio = cv2.contourArea(approx) / image_area
        if not settings.min_paper_area_ratio <= area_ratio <= settings.max_paper_area_ratio:
            continue
        if stands_out_from_background(to_gray(image), approx, settings):
            return approx.reshape(4, 2).astype(np.float32)
    return None


def stands_out_from_background(gray: np.ndarray, quad: np.ndarray, settings: EnhanceSettings = DEFAULT_SETTINGS) -> bool:
    inside = np.zeros(gray.shape, np.uint8)
    cv2.fillPoly(inside, [quad.reshape(-1, 2).astype(np.int32)], 255)
    band = max(3, int(min(gray.shape) * settings.paper_border_band_fraction))
    grown = cv2.dilate(inside, np.ones((band, band), np.uint8))
    outside = cv2.subtract(grown, inside)
    if not outside.any():
        return True
    contrast = float(np.median(gray[inside > 0])) - float(np.median(gray[outside > 0]))
    return contrast >= settings.min_paper_border_contrast


def order_corners(points: np.ndarray) -> np.ndarray:
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1).ravel()
    top_left = points[np.argmin(sums)]
    bottom_right = points[np.argmax(sums)]
    top_right = points[np.argmin(diffs)]
    bottom_left = points[np.argmax(diffs)]
    return np.array([top_left, top_right, bottom_right, bottom_left], dtype=np.float32)


def correct_perspective(
    image: np.ndarray, steps: list[str], settings: EnhanceSettings = DEFAULT_SETTINGS
) -> tuple[np.ndarray, bool]:
    quad = find_paper_quad(image, settings)
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


def horizontal_line_angles(image: np.ndarray, settings: EnhanceSettings = DEFAULT_SETTINGS) -> list[float]:
    gray = to_gray(image)
    edges = blurred_edges(gray, settings.line_canny_low, settings.line_canny_high, settings)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.radians(settings.line_hough_angle_step_degrees),
        threshold=settings.line_hough_threshold,
        minLineLength=int(gray.shape[1] * settings.line_min_length_fraction),
        maxLineGap=settings.line_max_gap,
    )
    if lines is None:
        return []
    angles = [float(np.degrees(np.arctan2(y2 - y1, x2 - x1))) for x1, y1, x2, y2 in lines.reshape(-1, 4)]
    return [angle for angle in angles if abs(angle) <= settings.max_deskew_degrees]


def estimate_skew_angle(image: np.ndarray, settings: EnhanceSettings = DEFAULT_SETTINGS) -> float | None:
    angles = np.array(horizontal_line_angles(image, settings))
    if len(angles) < settings.min_skew_lines:
        return None
    median = float(np.median(angles))
    agreeing = np.mean(np.abs(angles - median) <= settings.skew_agreement_degrees)
    if agreeing < settings.min_agreeing_fraction:
        return None
    return median


def deskew(image: np.ndarray, steps: list[str], settings: EnhanceSettings = DEFAULT_SETTINGS) -> np.ndarray:
    angle = estimate_skew_angle(image, settings)
    if angle is None:
        steps.append("deskew: no consistent straight lines (curved page or too few lines), skipped")
        return image
    if abs(angle) < settings.min_deskew_degrees:
        steps.append(
            f"deskew: page within {settings.min_deskew_degrees:.0f} deg of straight ({angle:.1f} deg), left as is"
        )
        return image

    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    steps.append(f"deskewed by {angle:.1f} deg")
    return cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def normalize_lighting(
    image: np.ndarray, steps: list[str], settings: EnhanceSettings = DEFAULT_SETTINGS
) -> np.ndarray:
    gray = to_gray(image)
    long_side = max(gray.shape[:2])
    dilate_size = odd_kernel(long_side * settings.background_dilate_fraction, settings.min_background_dilate_kernel)
    median_size = odd_kernel(long_side * settings.background_median_fraction, settings.min_background_median_kernel)
    background = cv2.medianBlur(cv2.dilate(gray, np.ones((dilate_size, dilate_size), np.uint8)), median_size)
    normalized = cv2.divide(gray, background, scale=255).astype(np.float32)

    ink = float(np.percentile(normalized, settings.ink_percentile))
    paper = float(np.median(normalized)) * settings.paper_white_fraction
    stretched = np.clip((normalized - ink) / max(1.0, paper - ink), 0.0, 1.0)
    steps.append("removed shadows and uneven lighting, whitened the paper and darkened the ink")
    return (stretched**settings.ink_gamma * 255).astype(np.uint8)


def odd_kernel(size: float, minimum: int) -> int:
    return max(minimum, int(size)) | 1


def denoise_and_sharpen(
    gray: np.ndarray, steps: list[str], settings: EnhanceSettings = DEFAULT_SETTINGS
) -> np.ndarray:
    denoised = cv2.fastNlMeansDenoising(
        gray,
        None,
        h=settings.denoise_strength,
        templateWindowSize=settings.denoise_template_window,
        searchWindowSize=settings.denoise_search_window,
    )
    blurred = cv2.GaussianBlur(denoised, (0, 0), sigmaX=settings.sharpen_sigma)
    steps.append("denoised and sharpened")
    return cv2.addWeighted(denoised, 1 + settings.sharpen_amount, blurred, -settings.sharpen_amount, 0)


def upscale_if_small(
    gray: np.ndarray, steps: list[str], settings: EnhanceSettings = DEFAULT_SETTINGS
) -> np.ndarray:
    long_side = max(gray.shape[:2])
    if long_side >= settings.work_long_side:
        return gray
    scale = min(settings.max_upscale, settings.work_long_side / long_side)
    steps.append(f"upscaled x{scale:.2f}")
    return resize_long_side(gray, round(long_side * scale), allow_upscale=True)


def write_jpeg(path: Path, image: np.ndarray, quality: int) -> None:
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise EnhancementError(f"Could not encode {path.name}")
    path.write_bytes(encoded.tobytes())
