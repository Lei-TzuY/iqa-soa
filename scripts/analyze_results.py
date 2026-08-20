#!/usr/bin/env python3
"""Analyze immutable IQA-SOA run records using the paired study design."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from iqa_soa.metrics.statistics import (  # noqa: E402
    AnalysisError,
    analyze_before_after,
    load_run_records,
    raw_source_digests,
)


def artifact_directory(source: Path, kind: str) -> Path:
    """Map results/raw/<experiment> to results/<kind>/<experiment>."""

    location = source.resolve()
    source_dir = location if location.is_dir() else location.parent
    cursor = source_dir
    while cursor != cursor.parent:
        if cursor.name == "raw":
            relative = source_dir.relative_to(cursor)
            experiment = relative.parts[0] if relative.parts else "analysis"
            return cursor.parent / kind / experiment
        cursor = cursor.parent
    return source_dir / kind


def _display(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def write_analysis(
    analysis: dict[str, Any], source: Path, *, token: str | None = None
) -> dict[str, Path]:
    """Write new analysis artifacts without replacing any earlier analysis."""

    run_token = token or (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    )
    processed = artifact_directory(source, "processed")
    tables = artifact_directory(source, "tables")
    processed.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    json_path = processed / f"before_after-{run_token}.json"
    csv_path = tables / f"before_after-{run_token}.csv"
    markdown_path = tables / f"before_after-{run_token}.md"
    targets = (json_path, csv_path, markdown_path)
    if any(path.exists() for path in targets):
        raise FileExistsError(f"Refusing to overwrite analysis token {run_token}")

    source_digests = raw_source_digests(source)
    payload = {
        **analysis,
        "generated_at": datetime.now(UTC).isoformat(),
        "raw_source": str(source.resolve()),
        "raw_source_digests": source_digests,
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    fieldnames = (
        "metric",
        "kind",
        "n_pairs",
        "before",
        "after",
        "absolute_difference",
        "relative_difference",
        "ci_low",
        "ci_high",
        "effect_size_name",
        "effect_size",
        "test",
        "statistic",
        "p_value",
        "n_independent_tasks",
    )
    with csv_path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(analysis["metrics"])

    lines = [
        "# Paired IQA-SOA Before/After Analysis",
        "",
        f"Pairs: {analysis['n_pairs']}. Delta is After (FULL) minus Before (OFF).",
        f"Raw records SHA-256: `{source_digests['raw_records_sha256']}`.",
        "",
        "| Metric | Applicable pairs | Independent tasks | Before | After | Delta | 95% task-cluster bootstrap CI | Effect | p-value |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    if analysis.get("inference_note"):
        lines[4:4] = [f"Inference note: {analysis['inference_note']}", ""]
    for row in analysis["metrics"]:
        ci = f"[{_display(row['ci_low'])}, {_display(row['ci_high'])}]"
        effect = (
            f"{row['effect_size_name']}: {_display(row['effect_size'])}"
            if row.get("effect_size") is not None
            else (
                str(row["effect_size_name"])
                if str(row.get("effect_size_name", "")).startswith("not estimated")
                else f"{row['effect_size_name']}: null"
            )
        )
        lines.append(
            "| "
            + " | ".join(
                (
                    str(row["metric"]),
                    _display(row.get("n_pairs")),
                    _display(row.get("n_independent_tasks")),
                    _display(row["before"]),
                    _display(row["after"]),
                    _display(row["absolute_difference"]),
                    ci,
                    effect,
                    _display(row["p_value"]),
                )
            )
            + " |"
        )
    lines.extend(
        (
            "",
            "For eligible online-provider data, intervals resample task clusters and "
            "p-values use task-level sign-flip randomization; deterministic-fixture "
            "inference is suppressed. A p-value is descriptive evidence, not a "
            "substitute for effect size or study design.",
            "",
            "## Action-denominator aggregate rates",
            "",
            "| Treatment | Metric | Numerator | Denominator | Rate |",
            "|---|---|---:|---:|---:|",
        )
    )
    for row in analysis.get("aggregate_rates", []):
        lines.append(
            "| "
            + " | ".join(
                (
                    str(row["qa_mode"]),
                    str(row["metric"]),
                    str(row["numerator"]),
                    str(row["denominator"]),
                    _display(row["rate"]),
                )
            )
            + " |"
        )
    lines.append("")
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "markdown": markdown_path}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Produce paired QA-OFF versus QA-FULL statistical tables."
    )
    parser.add_argument("experiment_dir", type=Path, help="Experiment directory or runs file")
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        records = load_run_records(args.experiment_dir)
        analysis = analyze_before_after(
            records,
            confidence=args.confidence,
            bootstrap_samples=args.bootstrap_samples,
            seed=args.seed,
        )
        paths = write_analysis(analysis, args.experiment_dir)
    except (AnalysisError, FileExistsError, ValueError) as exc:
        print(f"analysis failed: {exc}", file=sys.stderr)
        return 2
    print(f"analyzed {analysis['n_pairs']} paired observations")
    for label, path in paths.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
