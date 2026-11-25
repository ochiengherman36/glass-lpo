"""Compare pipeline results with hand-written ground truth.

Usage (from the repo root):
    python scripts/evaluate.py                 # every folder in test_drawings/
    python scripts/evaluate.py test_drawings/hard

Each drawing folder needs a ground-truth-*.json and an output/result.json written by the CLI.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DRAWINGS_DIR = REPO_ROOT / "test_drawings"
RESULT_PATH = Path("output") / "result.json"
REPORT_NAME = "EVALUATION.md"
TOLERANCE_MM = 0.5

CORRECT = "correct"
CHECKED_RIGHT = "checked, right value"
FLAGGED_WRONG = "flagged, wrong or missing"
WRONG_UNFLAGGED = "WRONG, NOT FLAGGED"
OUTCOMES = (CORRECT, CHECKED_RIGHT, FLAGGED_WRONG, WRONG_UNFLAGGED)


@dataclass
class FieldScore:
    panel_id: str
    field: str
    expected: Any
    got: Any
    flagged: bool
    outcome: str


def same_number(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= TOLERANCE_MM


def words(text: str | None) -> set[str]:
    return {word.strip(".,;:()").lower() for word in (text or "").split() if word.strip(".,;:()")}


def same_text(expected: str | None, got: str | None) -> bool:
    if not expected:
        return not got
    return bool(got) and words(expected) <= words(got)


def same_multiset(expected: list, got: list) -> bool:
    return Counter(expected) == Counter(got)


def outcome(match: bool, flagged: bool) -> str:
    if match:
        return CHECKED_RIGHT if flagged else CORRECT
    return FLAGGED_WRONG if flagged else WRONG_UNFLAGGED


def is_check(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("CHECK")


def reading(value: dict | None) -> float | None:
    return value.get("value") if value else None


def text_reading(value: dict | None) -> str | None:
    return value.get("text") if value else None


def none_last(pair: tuple) -> tuple:
    return tuple(float("inf") if value is None else value for value in pair)


def round_all(values: list[float | None]) -> list[float | None]:
    return [None if value is None else round(float(value), 1) for value in values]


FLAG_FIELDS = {
    "width_mm": {"width"},
    "height_mm": {"height"},
    "qty": {"qty"},
    "thickness_mm": {"thickness"},
    "glass_type": {"glass_type"},
    "edge_work": {"edge_work"},
    "hole_count": {"holes"},
    "hole_diameters": {"holes"},
    "hole_positions": {"hole_positions"},
    "notches": {"notches"},
}


def final_number(row: dict, column: str, extracted_reading: dict | None) -> float | None:
    value = row.get(column)
    if isinstance(value, (int, float)):
        return value
    return reading(extracted_reading)


def score_panel(expected: dict, extracted: dict | None, row: dict | None, flags: list[dict]) -> list[FieldScore]:
    panel_id = expected["panel_id"]
    if extracted is None or row is None:
        return [FieldScore(panel_id, "panel", "present", "missing", False, WRONG_UNFLAGGED)]

    scores: list[FieldScore] = []
    flagged_fields = {flag["field"] for flag in flags if (flag.get("panel_id") or "").upper() == panel_id.upper()}

    def add(field: str, exp: Any, got: Any, match: bool, column: str) -> None:
        flagged = is_check(row.get(column)) or bool(FLAG_FIELDS[field] & flagged_fields)
        result = CORRECT if match and exp is None else outcome(match, flagged)
        scores.append(FieldScore(panel_id, field, exp, got, flagged, result))

    for field, column in (("width_mm", "Width (mm)"), ("height_mm", "Height (mm)"), ("qty", "Qty"),
                          ("thickness_mm", "Thickness (mm)")):
        got = final_number(row, column, extracted.get(field))
        add(field, expected.get(field), got, same_number(expected.get(field), got), column)

    got_type = text_reading(extracted.get("glass_type"))
    add("glass_type", expected.get("glass_type"), got_type, same_text(expected.get("glass_type"), got_type), "Glass type")

    got_edge = text_reading(extracted.get("edge_work"))
    add("edge_work", expected.get("edge_work"), got_edge, same_text(expected.get("edge_work"), got_edge),
        "Grooves/edge work")

    expected_holes = expected.get("holes", [])
    got_holes = extracted.get("holes", [])
    add("hole_count", len(expected_holes), len(got_holes), len(expected_holes) == len(got_holes),
        "Hole diameters (mm)")

    expected_diameters = round_all([hole["diameter_mm"] for hole in expected_holes])
    got_diameters = round_all([reading(hole.get("diameter_mm")) for hole in got_holes])
    add("hole_diameters", expected_diameters, got_diameters, same_multiset(expected_diameters, got_diameters),
        "Hole diameters (mm)")

    if any(hole.get("x_mm") is not None for hole in expected_holes):
        expected_positions = sorted(((hole["x_mm"], hole["y_mm"]) for hole in expected_holes), key=none_last)
        got_positions = sorted(
            ((reading(hole.get("x_mm")), reading(hole.get("y_mm"))) for hole in got_holes), key=none_last
        )
        match = len(expected_positions) == len(got_positions) and all(
            same_number(ex, gx) and same_number(ey, gy)
            for (ex, ey), (gx, gy) in zip(expected_positions, got_positions, strict=True)
        )
        add("hole_positions", expected_positions, got_positions, match, "Hole positions")

    expected_notches = sorted(((n["width_mm"], n["depth_mm"]) for n in expected.get("notches", [])), key=none_last)
    got_notches = sorted(
        ((reading(n.get("width_mm")), reading(n.get("depth_mm"))) for n in extracted.get("notches", [])),
        key=none_last,
    )
    notch_match = len(expected_notches) == len(got_notches) and all(
        same_number(ew, gw) and same_number(ed, gd)
        for (ew, ed), (gw, gd) in zip(expected_notches, got_notches, strict=True)
    )
    add("notches", expected_notches, got_notches, notch_match, "Notches/offcuts")
    return scores


def score_overall(expected: dict, extraction: dict, flags: list[dict]) -> list[FieldScore]:
    scores = []
    for field, key in (("overall_width_mm", "width_mm"), ("overall_height_mm", "height_mm")):
        exp = expected.get("overall", {}).get(key)
        got = reading(extraction.get(field))
        label = "overall width" if key == "width_mm" else "overall height"
        flagged = any(label in flag["message"].lower() for flag in flags)
        scores.append(FieldScore("drawing", field, exp, got, flagged, outcome(same_number(exp, got), flagged)))
    return scores


def evaluate_folder(folder: Path) -> tuple[list[FieldScore], dict, dict] | None:
    truth_files = sorted(folder.glob("ground-truth-*.json"))
    result_file = folder / RESULT_PATH
    if not truth_files or not result_file.is_file():
        return None

    truth = json.loads(truth_files[0].read_text(encoding="utf-8"))
    result = json.loads(result_file.read_text(encoding="utf-8"))
    extraction = result["extraction"]
    extracted_by_id = {panel["panel_id"].upper(): panel for panel in extraction["panels"]}
    rows_by_id = {str(row["Panel ID"]).upper(): row for row in result["panels"]}

    scores = score_overall(truth, extraction, result["flags"])
    for panel in truth["panels"]:
        key = panel["panel_id"].upper()
        scores += score_panel(panel, extracted_by_id.get(key), rows_by_id.get(key), result["flags"])

    expected_ids = {panel["panel_id"].upper() for panel in truth["panels"]}
    for extra in sorted(set(extracted_by_id) - expected_ids):
        flagged = rows_by_id.get(extra, {}).get("Needs check (Y/N)") == "Y"
        scores.append(FieldScore(extra, "panel", "absent", "extra panel", flagged, outcome(False, flagged)))
    return scores, truth, result


def summary(scores: list[FieldScore]) -> Counter:
    return Counter(score.outcome for score in scores)


def accuracy_line(counts: Counter) -> str:
    total = sum(counts.values())
    right = counts[CORRECT] + counts[CHECKED_RIGHT]
    return (
        f"{right}/{total} fields right ({100 * right / total:.0f}%), "
        f"{counts[CORRECT]} without a flag; "
        f"{counts[CHECKED_RIGHT]} flagged but right; "
        f"{counts[FLAGGED_WRONG]} flagged and wrong/missing; "
        f"**{counts[WRONG_UNFLAGGED]} wrong and NOT flagged**"
    )


def fmt(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return "-" if value is None or value == [] else str(value)


def report(folder: Path, scores: list[FieldScore], truth: dict, result: dict) -> str:
    lines = [f"## {folder.name} ({truth.get('drawing_id', '')})", "", accuracy_line(summary(scores)), ""]
    usage = result.get("usage", {})
    lines.append(
        f"Model `{usage.get('model')}`, {usage.get('input_tokens')} input / {usage.get('output_tokens')} output tokens. "
        f"LPO `{result['lpo_no']}`."
    )
    lines += ["", "| Panel | Field | Expected | Got | Flagged | Outcome |", "|---|---|---|---|---|---|"]
    for score in scores:
        if score.outcome == CORRECT:
            continue
        lines.append(
            f"| {score.panel_id} | {score.field} | {fmt(score.expected)} | {fmt(score.got)} | "
            f"{'yes' if score.flagged else 'no'} | {score.outcome} |"
        )
    if all(score.outcome == CORRECT for score in scores):
        lines.append("| - | - | - | - | - | every field correct |")

    lines += ["", "Expected flags (ground truth):"]
    lines += [f"- {flag}" for flag in truth.get("expected_flags", [])] or ["- none"]
    lines += ["", "System flags:"]
    lines += [f"- {flag['message']}" for flag in result.get("flags", [])] or ["- none"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folders", nargs="*", type=Path, help="Drawing folders (default: all in test_drawings/)")
    args = parser.parse_args(argv)
    folders = args.folders or sorted(path for path in DEFAULT_DRAWINGS_DIR.iterdir() if path.is_dir())

    sections, totals = [], Counter()
    for folder in folders:
        evaluated = evaluate_folder(folder)
        if evaluated is None:
            print(f"Skipping {folder}: needs ground-truth-*.json and {RESULT_PATH}", file=sys.stderr)
            continue
        scores, truth, result = evaluated
        totals += summary(scores)
        sections.append(report(folder, scores, truth, result))

    if not sections:
        print("Nothing to evaluate.", file=sys.stderr)
        return 1

    text = "# Accuracy against ground truth\n\n" + f"**All drawings:** {accuracy_line(totals)}\n\n" + "\n".join(sections)
    (DEFAULT_DRAWINGS_DIR / REPORT_NAME).write_text(text, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())