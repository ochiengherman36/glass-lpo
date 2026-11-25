from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import AppSettings
from app.extract import ExtractionError
from app.main import app, get_extractor, get_settings
from tests.factories import FakeExtractor

EXPECTED_KEYS = {
    "job_id", "lpo_no", "issued_at", "source_name", "needs_check", "steps_applied", "columns",
    "panels", "flags", "totals", "usage", "files", "urls", "extraction",
}


@pytest.fixture
def client(tmp_path):
    settings = AppSettings(output_dir=tmp_path / "outputs", static_dir=tmp_path / "static", max_upload_bytes=2_000_000)
    extractor = FakeExtractor()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_extractor] = lambda: extractor
    with TestClient(app) as test_client:
        test_client.extractor = extractor
        yield test_client
    app.dependency_overrides.clear()


def upload(client: TestClient, content: bytes, filename: str = "drawing.jpg", content_type: str = "image/jpeg"):
    return client.post("/api/process", files={"file": (filename, content, content_type)})


def test_health(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_processing_an_image_returns_the_lpo_and_working_urls(client, skewed_page_bytes):
    response = upload(client, skewed_page_bytes)

    assert response.status_code == 200
    body = response.json()
    assert EXPECTED_KEYS <= body.keys()
    assert body["source_name"] == "drawing.jpg"
    assert body["panels"][0]["Width (mm)"] == 900
    assert body["totals"]["holes"] == 2
    expected_types = {"original": "image/jpeg", "enhanced": "image/jpeg", "pdf": "application/pdf"}
    for name, url in body["urls"].items():
        download = client.get(url)
        assert download.status_code == 200, url
        if name in expected_types:
            assert download.headers["content-type"] == expected_types[name]


def test_png_uploads_are_accepted(client, small_page_bytes):
    import cv2
    import numpy as np

    image = cv2.imdecode(np.frombuffer(small_page_bytes, np.uint8), cv2.IMREAD_COLOR)
    png = cv2.imencode(".png", image)[1].tobytes()

    assert upload(client, png, "drawing.png", "image/png").status_code == 200


def test_text_file_is_rejected_with_400(client):
    response = upload(client, b"hello", "notes.txt", "text/plain")

    assert response.status_code == 400
    assert response.json() == {"detail": "Upload a JPG or PNG photo of the drawing."}


def test_corrupt_image_is_rejected_with_400(client):
    response = upload(client, b"not really a jpeg")

    assert response.status_code == 400
    assert "not a readable JPG or PNG" in response.json()["detail"]


def test_empty_upload_is_rejected(client):
    assert upload(client, b"").status_code == 400


def test_oversized_upload_is_rejected_with_413(client):
    response = upload(client, b"\xff\xd8" + b"0" * 2_000_000)

    assert response.status_code == 413
    assert "larger than" in response.json()["detail"]


def test_extraction_error_returns_a_clean_502(client, skewed_page_bytes):
    client.extractor.error = ExtractionError("Anthropic API rate limit reached. Wait a minute and try again.")

    response = upload(client, skewed_page_bytes)

    assert response.status_code == 502
    assert response.json() == {"detail": "Anthropic API rate limit reached. Wait a minute and try again."}


@pytest.mark.skipif(not (AppSettings().static_dir / "index.html").is_file(), reason="frontend not built")
def test_root_serves_the_built_frontend(client):
    response = client.get("/")

    assert response.status_code == 200
    assert '<div id="root">' in response.text


@pytest.mark.parametrize("path", ["/outputs/../secret.txt", "/outputs/job/..%2F..%2F.env", "/outputs/nojob/result.json"])
def test_downloads_cannot_escape_the_output_folder(client, path):
    assert client.get(path).status_code == 404
