#!/usr/bin/env python3
"""Generate non-overwriting Figures P1-P4 from validated real-model pilot rows."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence
from uuid import uuid4

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
import numpy as np  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from iqa_soa.metrics.pilot import analyze_real_pilot, load_real_pilot_records  # noqa: E402
from iqa_soa.metrics.statistics import AnalysisError  # noqa: E402


def _save(fig: Figure, stem: Path) -> list[Path]:
    outputs = [stem.with_suffix(".png"), stem.with_suffix(".pdf")]
    for output in outputs:
        if output.exists():
            raise FileExistsError(f"refusing to overwrite pilot figure {output}")
    fig.tight_layout()
    fig.savefig(outputs[0], dpi=180, bbox_inches="tight")
    fig.savefig(outputs[1], bbox_inches="tight")
    plt.close(fig)
    return outputs


def _summary_map(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {str(row["metric"]): row for row in rows}


def _required_value(row: Mapping[str, Any], field: str, metric: str) -> float:
    value = row.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AnalysisError(f"pilot figure lacks {metric} {field}")
    number = float(value)
    if not math.isfinite(number):
        raise AnalysisError(f"pilot figure has nonfinite {metric} {field}")
    return number


def figure_p1(analysis: Mapping[str, Any], output: Path) -> list[Path]:
    summary = _summary_map(analysis["summary"])
    metrics = (
        "Safety/Security Violation Rate",
        "Unauthorized Action Rate",
        "Attack Success Rate",
        "Privacy Leakage Rate",
    )
    before = [_required_value(summary[item], "qa_off", item) for item in metrics]
    after = [_required_value(summary[item], "qa_full", item) for item in metrics]
    x = np.arange(len(metrics))
    fig, ax = plt.subplots(figsize=(10, 5.5))
    width = 0.36
    ax.bar(x - width / 2, before, width, label="QA OFF")
    ax.bar(x + width / 2, after, width, label="QA FULL")
    ax.set_xticks(x, ["Safety/security\nviolation", "Unauthorized\nexecution", "Attack\nsuccess", "Privacy\nleakage"])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Rate")
    ax.set_title("P1. Real-Model Pilot Safety: Before vs After")
    ax.legend()
    return _save(fig, output / "figure-p1-safety")


def figure_p2(analysis: Mapping[str, Any], output: Path) -> list[Path]:
    summary = _summary_map(analysis["summary"])
    specifications = (
        ("Task Success Rate", "Rate"),
        ("False Rejection Rate", "Rate"),
        ("Median Latency (ms)", "Milliseconds"),
        ("Mean Token Usage", "Tokens"),
    )
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for ax, (metric, ylabel) in zip(axes.flat, specifications, strict=True):
        row = summary[metric]
        values = [
            _required_value(row, "qa_off", metric),
            _required_value(row, "qa_full", metric),
        ]
        ax.bar(["QA OFF", "QA FULL"], values, color=["#6b7280", "#2563eb"])
        ax.set_title(metric)
        ax.set_ylabel(ylabel)
        if ylabel == "Rate":
            ax.set_ylim(0, 1.05)
    fig.suptitle("P2. Real-Model Pilot Utility / Overhead Trade-off")
    return _save(fig, output / "figure-p2-tradeoff")


def figure_p3(analysis: Mapping[str, Any], output: Path) -> list[Path]:
    model_results = analysis["per_model"]
    if not model_results:
        raise AnalysisError("P3 requires at least one real model")
    metrics = (
        "Safety/Security Violation Rate",
        "Unauthorized Action Rate",
        "Task Success Rate",
    )
    labels = [str(item["model"]) for item in model_results]
    x = np.arange(len(labels))
    width = 0.24
    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 2.2), 5.5))
    for index, metric in enumerate(metrics):
        deltas = [
            _required_value(_summary_map(item["summary"])[metric], "delta", metric)
            for item in model_results
        ]
        ax.bar(x + (index - 1) * width, deltas, width, label=metric)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x, labels, rotation=15, ha="right")
    ax.set_ylabel("QA FULL minus QA OFF")
    ax.set_title("P3. Treatment Effect by Real Model")
    ax.legend(fontsize=8)
    return _save(fig, output / "figure-p3-models")


def figure_p4(rows: Sequence[Mapping[str, Any]], output: Path) -> list[Path]:
    categories = sorted({str(row["category"]) for row in rows})
    required = {
        "benign",
        "prompt_injection",
        "unauthorized_action",
        "privacy",
        "knowledge_poisoning",
        "budget",
        "fault_injection",
    }
    if set(categories) != required:
        raise AnalysisError("P4 requires all seven frozen pilot categories")
    before: list[float] = []
    after: list[float] = []
    for category in categories:
        for mode, destination in (("off", before), ("full", after)):
            values = [
                float(bool(row["safety_security_violation"]))
                for row in rows
                if row["category"] == category and row["qa_mode"] == mode
            ]
            if not values:
                raise AnalysisError(f"P4 lacks {mode} data for {category}")
            destination.append(sum(values) / len(values))
    x = np.arange(len(categories))
    width = 0.36
    fig, ax = plt.subplots(figsize=(12, 5.8))
    ax.bar(x - width / 2, before, width, label="QA OFF")
    ax.bar(x + width / 2, after, width, label="QA FULL")
    ax.set_xticks(x, [item.replace("_", "\n") for item in categories])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Safety/Security Violation Rate")
    ax.set_title("P4. Real-Model Pilot Safety/Security Category Breakdown")
    ax.legend()
    return _save(fig, output / "figure-p4-categories")


def generate_pilot_figures(
    sources: Sequence[Path], output_root: Path, *, token: str | None = None
) -> list[Path]:
    rows, validation = load_real_pilot_records(sources)
    analysis = analyze_real_pilot(sources)
    run_token = token or (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    )
    output = output_root / "figures" / run_token
    output.mkdir(parents=True, exist_ok=False)
    provenance = {
        "result_provenance": "real-model pilot",
        "result_status": "descriptive pilot result",
        "generated_at": datetime.now(UTC).isoformat(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "validation": validation,
    }
    (output / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    outputs: list[Path] = []
    outputs += figure_p1(analysis, output)
    outputs += figure_p2(analysis, output)
    outputs += figure_p3(analysis, output)
    outputs += figure_p4(rows, output)
    return outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment_dirs", nargs="+", type=Path)
    parser.add_argument(
        "--output-root", type=Path, default=PROJECT_ROOT / "results" / "real-pilot"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        outputs = generate_pilot_figures(args.experiment_dirs, args.output_root)
    except (AnalysisError, FileExistsError, OSError, ValueError) as exc:
        print(f"real-pilot figure generation failed: {exc}", file=sys.stderr)
        return 2
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
