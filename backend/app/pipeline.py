from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.enhance import EnhanceResult, enhance_image
from app.excel import write_excel
from app.extract import ExtractionResult, extract_drawing
from app.lpo import COLUMNS, LpoDocument, generate_lpo_number, rows
from app.pdf_lpo import write_pdf
from app.schema import DrawingExtraction
from app.validate import ValidatedDrawing, validate_drawing

logger = logging.getLogger(__name__)

Extractor = Callable[[Path, Path], ExtractionResult]
RESULT_FILE = "result.json"


def claude_extractor(enhanced_path: Path, original_path: Path) -> ExtractionResult:
    return extract_drawing(enhanced_path, original_path)


def replay_extractor(result_path: Path | str) -> Extractor:
    saved = json.loads(Path(result_path).read_text(encoding="utf-8"))
    usage = saved.get("usage", {})
    result = ExtractionResult(
        drawing=DrawingExtraction.model_validate(saved["extraction"]),
        model=usage.get("model", "replay"),
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        fallback_used=usage.get("fallback_used", False),
    )

    def extractor(enhanced_path: Path, original_path: Path) -> ExtractionResult:
        return result

    return extractor


@dataclass
class PipelineResult:
    document: LpoDocument
    enhancement: EnhanceResult
    extraction: ExtractionResult
    excel_path: Path
    pdf_path: Path
    result_path: Path

    @property
    def drawing(self) -> ValidatedDrawing:
        return self.document.drawing

    @property
    def files(self) -> dict[str, Path]:
        return {
            "original": self.enhancement.original_path,
            "enhanced": self.enhancement.enhanced_path,
            "xlsx": self.excel_path,
            "pdf": self.pdf_path,
            "json": self.result_path,
        }

    def to_dict(self) -> dict[str, Any]:
        drawing = self.drawing
        return {
            "lpo_no": self.document.lpo_no,
            "issued_at": self.document.issued_at.isoformat(timespec="seconds"),
            "source_name": self.document.source_name,
            "needs_check": drawing.needs_check,
            "steps_applied": self.enhancement.steps_applied,
            "columns": list(COLUMNS),
            "panels": rows(self.document),
            "flags": [
                {"panel_id": flag.panel_id, "field": flag.field, "message": flag.message, "severity": flag.severity}
                for flag in drawing.flags
            ],
            "totals": {
                "lines": len(drawing.lines),
                "pieces": sum(line.qty or 1 for line in drawing.lines),
                "area_m2": drawing.total_area_m2,
                "area_complete": drawing.area_complete,
                "holes": drawing.total_holes,
            },
            "usage": self.extraction.usage,
            "files": {name: path.name for name, path in self.files.items()},
            "extraction": self.extraction.drawing.model_dump(mode="json"),
        }


def run(
    image: Path | bytes,
    out_dir: Path | str,
    source_name: str | None = None,
    extractor: Extractor = claude_extractor,
    now: datetime | None = None,
) -> PipelineResult:
    out_dir = Path(out_dir)
    issued_at = now or datetime.now()
    source_name = source_name or (Path(image).name if isinstance(image, (str, Path)) else "upload")

    enhancement = enhance_image(image, out_dir)
    extraction = extractor(enhancement.claude_enhanced_path, enhancement.claude_original_path)

    lpo_no = generate_lpo_number(issued_at)
    document = LpoDocument(
        lpo_no=lpo_no,
        issued_at=issued_at,
        source_name=source_name,
        drawing=validate_drawing(extraction.drawing),
    )
    result = PipelineResult(
        document=document,
        enhancement=enhancement,
        extraction=extraction,
        excel_path=write_excel(document, out_dir / f"{lpo_no}.xlsx"),
        pdf_path=write_pdf(document, out_dir / f"{lpo_no}.pdf"),
        result_path=out_dir / RESULT_FILE,
    )
    result.result_path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Pipeline done: %s, %d panels, %d flags", lpo_no, len(document.drawing.lines), len(document.drawing.flags))
    return result
