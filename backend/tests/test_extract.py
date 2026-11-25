from __future__ import annotations

import base64
import os
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx
import pytest

from app.config import ExtractionSettings
from app.extract import FALLBACK_BETA, ExtractionError, build_request, extract_drawing
from app.schema import DrawingExtraction
from tests.factories import drawing
from tests.synthetic import TEST_DRAWINGS_DIR

JPEG_BYTES = b"\xff\xd8\xff\xe0fake-jpeg"
PNG_BYTES = b"\x89PNG\r\n\x1a\nfake-png"
SETTINGS = ExtractionSettings(model="claude-test-model", effort="high", max_tokens=1234, use_fallbacks=True)
API_REQUEST = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def make_response(**overrides: Any) -> SimpleNamespace:
    fields: dict[str, Any] = {
        "stop_reason": "end_turn",
        "stop_details": None,
        "parsed_output": drawing(),
        "model": "claude-test-model",
        "usage": SimpleNamespace(input_tokens=4100, output_tokens=2300, iterations=None),
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


class FakeClient:
    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.requests: list[dict[str, Any]] = []
        self._response = response if response is not None else make_response()
        self._error = error
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self._parse))

    def _parse(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._response


def status_error(error_class: type[anthropic.APIStatusError], status: int) -> anthropic.APIStatusError:
    response = httpx.Response(status, request=API_REQUEST, json={"error": {"message": "boom"}})
    return error_class("boom", response=response, body=None)


def test_returns_the_parsed_drawing_and_usage():
    client = FakeClient()

    result = extract_drawing(JPEG_BYTES, JPEG_BYTES, client=client, settings=SETTINGS)

    assert isinstance(result.drawing, DrawingExtraction)
    assert result.drawing.panels[0].width_mm.value == 900
    assert result.usage == {
        "model": "claude-test-model",
        "input_tokens": 4100,
        "output_tokens": 2300,
        "fallback_used": False,
    }


def test_request_sends_both_images_with_the_configured_model():
    client = FakeClient()

    extract_drawing(JPEG_BYTES, PNG_BYTES, client=client, settings=SETTINGS)

    request = client.requests[0]
    content = request["messages"][0]["content"]
    images = [block for block in content if block["type"] == "image"]
    assert request["model"] == "claude-test-model"
    assert request["max_tokens"] == 1234
    assert request["output_format"] is DrawingExtraction
    assert request["output_config"] == {"effort": "high"}
    assert "temperature" not in request
    assert [image["source"]["media_type"] for image in images] == ["image/jpeg", "image/png"]
    assert base64.standard_b64decode(images[0]["source"]["data"]) == JPEG_BYTES
    assert content[-1]["type"] == "text"


def test_fallbacks_are_sent_only_when_enabled():
    with_fallbacks = build_request(JPEG_BYTES, JPEG_BYTES, SETTINGS)
    without_fallbacks = build_request(JPEG_BYTES, JPEG_BYTES, ExtractionSettings(use_fallbacks=False))

    assert with_fallbacks["betas"] == [FALLBACK_BETA]
    assert with_fallbacks["fallbacks"] == "default"
    assert "betas" not in without_fallbacks and "fallbacks" not in without_fallbacks


def test_reports_when_a_fallback_model_served_the_request():
    usage = SimpleNamespace(input_tokens=1, output_tokens=1, iterations=[SimpleNamespace(type="fallback_message")])
    client = FakeClient(make_response(usage=usage, model="claude-fallback-model"))

    result = extract_drawing(JPEG_BYTES, JPEG_BYTES, client=client, settings=SETTINGS)

    assert result.fallback_used
    assert result.model == "claude-fallback-model"


def test_truncated_answer_raises():
    client = FakeClient(make_response(stop_reason="max_tokens", parsed_output=None))

    with pytest.raises(ExtractionError, match="truncated"):
        extract_drawing(JPEG_BYTES, JPEG_BYTES, client=client, settings=SETTINGS)


def test_refusal_raises_with_the_category():
    response = make_response(
        stop_reason="refusal",
        stop_details=SimpleNamespace(category="general_harms", explanation="declined"),
        parsed_output=None,
    )

    with pytest.raises(ExtractionError, match="declined.*general_harms"):
        extract_drawing(JPEG_BYTES, JPEG_BYTES, client=FakeClient(response), settings=SETTINGS)


def test_missing_structured_output_raises():
    client = FakeClient(make_response(parsed_output=None))

    with pytest.raises(ExtractionError, match="no structured output"):
        extract_drawing(JPEG_BYTES, JPEG_BYTES, client=client, settings=SETTINGS)


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (status_error(anthropic.AuthenticationError, 401), "API key is missing or invalid"),
        (status_error(anthropic.RateLimitError, 429), "rate limit"),
        (status_error(anthropic.InternalServerError, 500), "Anthropic API error 500"),
        (anthropic.APIConnectionError(request=API_REQUEST), "Could not reach the Anthropic API"),
    ],
    ids=["auth", "rate-limit", "server-error", "connection"],
)
def test_api_errors_become_clean_extraction_errors(error, message):
    with pytest.raises(ExtractionError, match=message):
        extract_drawing(JPEG_BYTES, JPEG_BYTES, client=FakeClient(error=error), settings=SETTINGS)


def test_unreadable_image_path_raises(tmp_path):
    with pytest.raises(ExtractionError, match="Could not read image"):
        extract_drawing(tmp_path / "missing.jpg", JPEG_BYTES, client=FakeClient(), settings=SETTINGS)


def test_settings_read_model_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-from-env")
    monkeypatch.setenv("ANTHROPIC_USE_FALLBACKS", "false")

    settings = ExtractionSettings.from_env()

    assert settings.model == "claude-from-env"
    assert settings.use_fallbacks is False


def test_empty_env_values_fall_back_to_defaults(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "")
    monkeypatch.delenv("ANTHROPIC_EFFORT", raising=False)

    settings = ExtractionSettings.from_env()

    assert settings.model == "claude-opus-5-5"
    assert settings.effort == "high"


@pytest.mark.live
@pytest.mark.skipif(os.getenv("RUN_LIVE") != "1", reason="set RUN_LIVE=1 to call the real Claude API")
def test_live_extraction_on_the_simple_drawing(tmp_path):
    from app.enhance import enhance_image

    enhanced = enhance_image(TEST_DRAWINGS_DIR / "simple" / "simple.jpeg", tmp_path)

    result = extract_drawing(enhanced.claude_enhanced_path, enhanced.claude_original_path)

    panel = result.drawing.panels[0]
    assert len(result.drawing.panels) == 1
    assert panel.width_mm.value == 900
    assert panel.height_mm.value == 1200
    assert len(panel.holes) == 2
