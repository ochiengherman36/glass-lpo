from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app import pipeline
from app.config import AppSettings
from app.enhance import EnhancementError
from app.extract import ExtractionError


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Turn a photo of a glass drawing into an Excel file and a one-page PDF LPO.",
    )
    parser.add_argument("image", type=Path, help="JPG or PNG photo of the drawing")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Folder for the outputs (default: backend/outputs/<image name>)",
    )
    return parser.parse_args(argv)


def print_summary(result: pipeline.PipelineResult) -> None:
    drawing = result.drawing
    usage = result.extraction.usage
    print(f"LPO {result.document.lpo_no} from {result.document.source_name}")
    print(f"Enhancement: {'; '.join(result.enhancement.steps_applied)}")
    print(f"Model: {usage['model']} ({usage['input_tokens']} in / {usage['output_tokens']} out tokens)")
    print()
    for line in drawing.lines:
        status = "CHECK" if line.needs_check else "ok"
        area = f"{line.area_m2:.3f} m2" if line.area_m2 is not None else "area CHECK"
        print(
            f"  {line.line:>2}. {line.panel_id:<4} {line.width_mm} x {line.height_mm} mm  qty {line.qty}  "
            f"{area}  holes {line.hole_count}  {line.confidence:<6} {status}"
        )
    area_note = "" if drawing.area_complete else " (incomplete)"
    print(f"\nTotal area {drawing.total_area_m2:.3f} m2{area_note}, total holes {drawing.total_holes}")

    if drawing.flags:
        print(f"\nNeeds human check ({len(drawing.flags)}):")
        for flag in drawing.flags:
            print(f"  - {flag.message}")
    else:
        print("\nNeeds human check: none")

    print("\nFiles:")
    for path in result.files.values():
        print(f"  {path}")


def main(argv: list[str] | None = None, extractor: pipeline.Extractor = pipeline.claude_extractor) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args(argv)
    out_dir = args.out or AppSettings.from_env().output_dir / args.image.stem

    try:
        result = pipeline.run(args.image, out_dir, extractor=extractor)
    except (EnhancementError, ExtractionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
