#!/usr/bin/env python3
"""Validate and analyze one or more complete real-model pilot runs."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from iqa_soa.metrics.pilot import analyze_real_pilot  # noqa: E402
from iqa_soa.metrics.statistics import AnalysisError  # noqa: E402


def _display(value: Any) -> str:
    if value is None:
        return "null"
    return f"{value:.6g}" if isinstance(value, float) else str(value)


def write_pilot_analysis(
    analysis: Mapping[str, Any], output_root: Path, *, token: str | None = None
) -> dict[str, Path]:
    run_token = token or (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    )
    processed_dir = output_root / "processed" / run_token
    table_dir = output_root / "tables" / run_token
    processed_dir.mkdir(parents=True, exist_ok=False)
    table_dir.mkdir(parents=True, exist_ok=False)
    json_path = processed_dir / "real-model-before-after.json"
    csv_path = table_dir / "real-model-before-after.csv"
    markdown_path = table_dir / "real-model-before-after.md"
    payload = {
        **analysis,
        "generated_at": datetime.now(UTC).isoformat(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    fieldnames = (
        "scope",
        "provider",
        "model",
        "metric",
        "qa_off",
        "qa_full",
        "delta",
        "relative_delta",
        "qa_off_n",
        "qa_full_n",
        "summary_kind",
    )
    csv_rows: list[dict[str, Any]] = []
    for row in analysis["summary"]:
        csv_rows.append({"scope": "all_models", "provider": None, "model": None, **row})
    for model_result in analysis["per_model"]:
        for row in model_result["summary"]:
            csv_rows.append(
                {
                    "scope": "per_model",
                    "provider": model_result["provider"],
                    "model": model_result["model"],
                    **row,
                }
            )
    with csv_path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(csv_rows)
    lines = [
        "# Real-Model Pilot: QA OFF vs QA FULL",
        "",
        "Provenance: **real-model pilot**. These are descriptive pilot results, not deterministic mechanism validation or final FSE evidence.",
        "",
        f"Result status: {analysis['result_status']}.",
        "",
        str(analysis["inference_note"]),
        "",
        "## All models",
        "",
        "| Metric | QA OFF | QA FULL | Delta | OFF N | FULL N |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in analysis["summary"]:
        lines.append(
            f"| {row['metric']} | {_display(row['qa_off'])} | {_display(row['qa_full'])} | "
            f"{_display(row['delta'])} | {row['qa_off_n']} | {row['qa_full_n']} |"
        )
    for model_result in analysis["per_model"]:
        lines.extend(
            (
                "",
                f"## Model: {model_result['provider']} / {model_result['model']}",
                "",
                "| Metric | QA OFF | QA FULL | Delta | OFF N | FULL N |",
                "|---|---:|---:|---:|---:|---:|",
            )
        )
        for row in model_result["summary"]:
            lines.append(
                f"| {row['metric']} | {_display(row['qa_off'])} | {_display(row['qa_full'])} | "
                f"{_display(row['delta'])} | {row['qa_off_n']} | {row['qa_full_n']} |"
            )
    lines.extend(
        (
            "",
            "## Anomalies",
            "",
            "```json",
            json.dumps(analysis["anomalies"], ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
        )
    )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "markdown": markdown_path}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment_dirs", nargs="+", type=Path)
    parser.add_argument(
        "--output-root", type=Path, default=PROJECT_ROOT / "results" / "real-pilot"
    )
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        analysis = analyze_real_pilot(
            args.experiment_dirs,
            confidence=args.confidence,
            bootstrap_samples=args.bootstrap_samples,
            seed=args.seed,
        )
        paths = write_pilot_analysis(analysis, args.output_root)
    except (AnalysisError, FileExistsError, OSError, ValueError) as exc:
        print(f"real-pilot analysis failed: {exc}", file=sys.stderr)
        return 2
    print(f"analyzed {analysis['paired_analysis']['n_pairs']} real-model pairs")
    for label, path in paths.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
