from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anthropic

from app.config import ExtractionSettings
from app.schema import DrawingExtraction

logger = logging.getLogger(__name__)

FALLBACK_BETA = "server-side-fallback-2026-07-01"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

SYSTEM_PROMPT = """\
You read hand-drawn glass fabrication drawings photographed on a phone and transcribe them into \
structured data for a glass processor's order (LPO). A misread dimension means glass is cut that \
cannot be used, so honesty matters more than completeness.

Rules:
1. Transcribe only what is written. Never calculate, estimate, measure from the sketch or infer a \
number that is not written. Do not derive a panel width by subtracting from the overall width, and \
do not estimate a hole position from where the circle is drawn. The only arithmetic allowed is the \
hole-position conversion in rule 6.
2. For every value set status:
   - clear: written and unambiguous.
   - unclear: written but smudged, ambiguous (5 or 6, 1 or 7), corrected or partly unreadable. Set \
value to null unless one reading is clearly intended. For a crossed-out correction use the final \
written value, keep status unclear and describe the correction in raw_text.
   - not_shown: not written anywhere on the drawing. value is null.
   raw_text is what you actually see, with '?' for unreadable characters.
3. A note that explicitly covers all or several panels (for example 'ALL PANELS H=2100', \
'QTY 1 EACH', '8MM TOUGHENED', 'Ø25 TYP') is written information: apply it to every panel it \
covers and mention the note in that panel's notes. Likewise, a single height dimension drawn beside \
one row of side-by-side panels is the height of every panel in that row, and a single width \
dimension beside one column of stacked panels is the width of every panel in that column: apply it \
to each of those panels and say so in their notes.
4. Units are millimetres unless the drawing says otherwise. 'Ø25', 'Q25' or 'O25' next to a \
circle means a hole of 25 mm diameter.
5. One record per glass panel. Use the panel labels written on the drawing. If panels are \
unlabelled, name them P1, P2... left to right, top to bottom, and say so in notes.
6. One hole entry per circle drawn. x_mm is the distance from the panel's left edge to the hole \
centre and y_mm the distance from the panel's bottom edge. Fill them only from written dimensions. \
If a hole is dimensioned from the right or top edge, or by a chain of written dimensions such as \
'150 | 600 | 150', add or subtract those written numbers to get the distance from the left or bottom \
edge, and put the dimensions you used in raw_text (e.g. '900 - 150 from right edge'). If no written \
dimension locates the hole, use not_shown and describe where it is drawn in position_description.
7. Record each notch, offcut or cutout with its size as written and the corner or edge where it \
is drawn, as a short phrase such as 'top-left corner'.
8. Panel confidence: high when every written value is clear; medium when a secondary value \
(thickness, glass type, edge work, hole position) is unclear; low when width, height, quantity or \
a hole diameter is unclear or missing. Explain why in confidence_reason.
9. unreadable_items is only for marks that are written on the drawing but cannot be read. Do not \
list values that are simply not on the drawing (status not_shown already records those), and do \
not repeat a value you already marked unclear on a panel.
10. Stains, rings, smudges and scribbles are not holes, notches or dimensions: ignore them. Copy \
handwritten notes that are not about the glass itself (for example delivery or contact notes) into \
general_notes.
"""

USER_INSTRUCTIONS = """\
Both images show the same glass drawing: the first is cleaned up, the second is the original \
photo. Use whichever is clearer for each value. If they seem to disagree, mark the value unclear. \
Extract every panel following the rules."""


class ExtractionError(RuntimeError):
    pass


@dataclass
class ExtractionResult:
    drawing: DrawingExtraction
    model: str
    input_tokens: int
    output_tokens: int
    fallback_used: bool

    @property
    def usage(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "fallback_used": self.fallback_used,
        }


def media_type(data: bytes) -> str:
    return "image/png" if data.startswith(PNG_SIGNATURE) else "image/jpeg"


def image_block(data: bytes) -> dict[str, Any]:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type(data),
            "data": base64.standard_b64encode(data).decode("ascii"),
        },
    }


def build_messages(enhanced: bytes, original: bytes) -> list[dict[str, Any]]:
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Image 1 (cleaned up):"},
                image_block(enhanced),
                {"type": "text", "text": "Image 2 (original photo):"},
                image_block(original),
                {"type": "text", "text": USER_INSTRUCTIONS},
            ],
        }
    ]


def build_request(enhanced: bytes, original: bytes, settings: ExtractionSettings) -> dict[str, Any]:
    request: dict[str, Any] = {
        "model": settings.model,
        "max_tokens": settings.max_tokens,
        "system": SYSTEM_PROMPT,
        "messages": build_messages(enhanced, original),
        "output_format": DrawingExtraction,
        "output_config": {"effort": settings.effort},
    }
    if settings.use_fallbacks:
        request["betas"] = [FALLBACK_BETA]
        request["fallbacks"] = "default"
    return request


def extract_drawing(
    enhanced_image: Path | bytes,
    original_image: Path | bytes,
    client: Any | None = None,
    settings: ExtractionSettings | None = None,
) -> ExtractionResult:
    settings = settings or ExtractionSettings.from_env()
    enhanced = read_bytes(enhanced_image)
    original = read_bytes(original_image)
    client = client or anthropic.Anthropic()

    try:
        response = client.beta.messages.parse(**build_request(enhanced, original, settings))
    except anthropic.AuthenticationError as exc:
        raise ExtractionError("Anthropic API key is missing or invalid. Set ANTHROPIC_API_KEY in backend/.env.") from exc
    except anthropic.RateLimitError as exc:
        raise ExtractionError("Anthropic API rate limit reached. Wait a minute and try again.") from exc
    except anthropic.APIConnectionError as exc:
        raise ExtractionError("Could not reach the Anthropic API. Check the internet connection.") from exc
    except anthropic.APIStatusError as exc:
        raise ExtractionError(f"Anthropic API error {exc.status_code}: {exc.message}") from exc
    except anthropic.AnthropicError as exc:
        raise ExtractionError(f"Anthropic client error: {exc}") from exc

    return parse_response(response)


def parse_response(response: Any) -> ExtractionResult:
    if response.stop_reason == "max_tokens":
        raise ExtractionError("Claude's answer was truncated (max_tokens reached). Increase ANTHROPIC_MAX_TOKENS.")
    if response.stop_reason == "refusal":
        details = getattr(response, "stop_details", None)
        category = getattr(details, "category", None) or "unspecified"
        raise ExtractionError(f"Claude declined to read this drawing (refusal category: {category}).")

    drawing = getattr(response, "parsed_output", None)
    if drawing is None:
        raise ExtractionError(f"Claude returned no structured output (stop_reason: {response.stop_reason}).")

    usage = response.usage
    iterations = getattr(usage, "iterations", None) or []
    result = ExtractionResult(
        drawing=drawing,
        model=response.model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        fallback_used=any(getattr(item, "type", None) == "fallback_message" for item in iterations),
    )
    logger.info(
        "Extraction done: model=%s input_tokens=%d output_tokens=%d fallback_used=%s panels=%d",
        result.model,
        result.input_tokens,
        result.output_tokens,
        result.fallback_used,
        len(drawing.panels),
    )
    return result


def read_bytes(source: Path | bytes) -> bytes:
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    try:
        return Path(source).read_bytes()
    except OSError as exc:
        raise ExtractionError(f"Could not read image for extraction: {source}") from exc
