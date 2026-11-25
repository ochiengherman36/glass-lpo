from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import pipeline
from app.config import AppSettings
from app.enhance import EnhancementError
from app.extract import ExtractionError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png"}
SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


def get_settings() -> AppSettings:
    return AppSettings.from_env()


def get_extractor() -> pipeline.Extractor:
    return pipeline.claude_extractor


def new_job_id() -> str:
    return f"{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:6]}"


def create_app() -> FastAPI:
    app = FastAPI(title="Glass Drawing to LPO", version="0.1.0")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/process")
    def process(
        file: Annotated[UploadFile, File()],
        settings: Annotated[AppSettings, Depends(get_settings)],
        extractor: Annotated[pipeline.Extractor, Depends(get_extractor)],
    ) -> dict[str, Any]:
        filename = file.filename or "upload"
        if Path(filename).suffix.lower() not in ALLOWED_SUFFIXES:
            raise HTTPException(status_code=400, detail="Upload a JPG or PNG photo of the drawing.")

        data = file.file.read(settings.max_upload_bytes + 1)
        if not data:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")
        if len(data) > settings.max_upload_bytes:
            limit_mb = settings.max_upload_bytes // (1024 * 1024)
            raise HTTPException(status_code=413, detail=f"The photo is larger than {limit_mb} MB.")

        job_id = new_job_id()
        out_dir = settings.output_dir / job_id
        try:
            result = pipeline.run(data, out_dir, source_name=filename, extractor=extractor)
        except EnhancementError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ExtractionError as exc:
            logger.warning("Extraction failed for job %s: %s", job_id, exc)
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        payload = result.to_dict()
        payload["job_id"] = job_id
        payload["urls"] = {name: f"/outputs/{job_id}/{path.name}" for name, path in result.files.items()}
        return payload

    @app.get("/outputs/{job_id}/{filename}")
    def download(
        job_id: str, filename: str, settings: Annotated[AppSettings, Depends(get_settings)]
    ) -> FileResponse:
        if not (SAFE_NAME.match(job_id) and SAFE_NAME.match(filename)) or ".." in job_id or ".." in filename:
            raise HTTPException(status_code=404, detail="File not found.")
        path = (settings.output_dir / job_id / filename).resolve()
        if not path.is_relative_to(settings.output_dir.resolve()) or not path.is_file():
            raise HTTPException(status_code=404, detail="File not found.")
        return FileResponse(path, filename=filename)

    static_dir = AppSettings.from_env().static_dir
    if (static_dir / "index.html").is_file():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")

    return app


app = create_app()
