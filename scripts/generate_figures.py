#!/usr/bin/env python3
"""Generate publication-oriented figures strictly from measured run records."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import uuid
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from iqa_soa.metrics.statistics import (  # noqa: E402
    AnalysisError,
    load_run_records,
    pair_before_after,
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
REQUIRED_CATEGORIES = (
    "prompt_injection",
    "unauthorized_action",
    "privacy",
    "knowledge_poisoning",
    "budget",
    "fault_injection",
)
REQUIRED_ABLATIONS = frozenset(
    {"injection", "permission", "privacy", "budget", "output_validation", "evidence"}
)


def _unablated(row: Mapping[str, Any]) -> bool:
    return row.get("ablation") in (None, "", "none", "None", "FULL", "full")


def _numeric(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return float(value)
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise AnalysisError(f"malformed numeric measurement: {value!r}") from exc
    if not math.isfinite(number):
        raise AnalysisError(f"non-finite numeric measurement: {value!r}")
    return number


def _mean(
    rows: Iterable[Mapping[str, Any]], metric: str, *, mode: str | None = None
) -> float | None:
    values = [
        value
        for row in rows
        if (mode is None or str(row.get("qa_mode", "")).lower() == mode)
        if (value := _numeric(row.get(metric))) is not None
    ]
    return float(np.mean(values)) if values else None


def _rate(
    rows: Iterable[Mapping[str, Any]],
    numerator: str,
    denominator: str,
    *,
    mode: str,
) -> tuple[float | None, int]:
    selected = [
        row for row in rows if str(row.get("qa_mode", "")).lower() == mode
    ]
    numerator_total = sum(_numeric(row.get(numerator)) or 0.0 for row in selected)
    denominator_total = sum(_numeric(row.get(denominator)) or 0.0 for row in selected)
    if denominator_total <= 0:
        return None, 0
    return numerator_total / denominator_total, int(denominator_total)


def _require_modes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered = [row for row in rows if _unablated(row)]
    modes = {str(row.get("qa_mode", "")).lower() for row in filtered}
    missing = {"off", "full"} - modes
    if missing:
        raise AnalysisError(
            "Figures A, B, and D require unablated OFF and FULL measurements; missing "
            + ", ".join(sorted(missing))
        )
    # Reuse the analyzer's exact pair, error, and controlled-input integrity
    # checks; figures must never average mismatched treatment arms.
    pairs = pair_before_after(filtered)
    flattened: list[dict[str, Any]] = []
    for pair in pairs:
        flattened.extend((dict(pair.before), dict(pair.after)))
    return flattened


def _save(fig: plt.Figure, stem: Path, title: str, source: str) -> list[Path]:
    png = stem.with_suffix(".png")
    pdf = stem.with_suffix(".pdf")
    metadata = {
        "Title": title,
        "Author": "IQA-SOA FSE artifact",
        "Subject": f"Generated from measured records: {source}",
        "Keywords": "IQA-SOA, runtime quality assurance, empirical software engineering",
    }
    if "deterministic fixture; descriptive artifact validation only" in source:
        fig.text(
            0.5,
            0.005,
            "Deterministic fixture — descriptive artifact validation only",
            ha="center",
            va="bottom",
            fontsize=8,
            color="#555555",
        )
    fig.savefig(png, dpi=300, bbox_inches="tight", metadata={"Description": metadata["Subject"]})
    fig.savefig(pdf, bbox_inches="tight", metadata=metadata)
    plt.close(fig)
    return [png, pdf]


def figure_a(rows: list[dict[str, Any]], output: Path, source: str) -> list[Path]:
    usable: list[tuple[str, float, float, str]] = []
    for metric, label in (
        ("constraint_violation", "constraint\nviolation"),
        ("attack_success", "attack\nsuccess"),
        ("privacy_leak", "privacy\nleak"),
    ):
        before = _mean(rows, metric, mode="off")
        after = _mean(rows, metric, mode="full")
        if before is not None and after is not None:
            off_n = sum(
                row.get(metric) not in (None, "")
                for row in rows
                if str(row.get("qa_mode", "")).lower() == "off"
            )
            full_n = sum(
                row.get(metric) not in (None, "")
                for row in rows
                if str(row.get("qa_mode", "")).lower() == "full"
            )
            n_label = f"n={off_n} pairs" if off_n == full_n else f"n={off_n}/{full_n}"
            usable.append((label, before, after, n_label))
    off_ua, off_ua_n = _rate(
        rows, "unsafe_executed_count", "unsafe_proposed_count", mode="off"
    )
    full_ua, full_ua_n = _rate(
        rows, "unsafe_executed_count", "unsafe_proposed_count", mode="full"
    )
    if off_ua is not None and full_ua is not None:
        n_label = (
            f"n={off_ua_n} actions"
            if off_ua_n == full_ua_n
            else f"n={off_ua_n}/{full_ua_n} actions"
        )
        usable.insert(
            1,
            ("unauthorized\naction execution", off_ua, full_ua, n_label),
        )
    if not usable:
        raise AnalysisError("Figure A has no measured safety metrics")
    labels = [f"{item[0]}\n({item[3]})" for item in usable]
    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(x - width / 2, [item[1] for item in usable], width, label="Before: QA OFF")
    ax.bar(x + width / 2, [item[2] for item in usable], width, label="After: IQA-SOA FULL")
    ax.set_ylabel("Observed rate")
    ax.set_title("A. Before vs After Safety Outcomes")
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 1.05)
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    return _save(fig, output / "figure-a-safety", "Before vs After Safety", source)


def figure_b(rows: list[dict[str, Any]], output: Path, source: str) -> list[Path]:
    panels = (
        ("constraint_violation", "Constraint violation", "lower is better"),
        ("task_success", "Task success", "higher is better"),
        ("false_rejection", "False rejection", "lower is better"),
        ("end_to_end_latency_ms", "End-to-end latency (ms)", "lower is better"),
        ("estimated_cost", "Estimated cost", "lower is better"),
    )
    fig, axes = plt.subplots(1, len(panels), figsize=(14, 4.5))
    required_measured: set[str] = set()
    for ax, (metric, label, direction) in zip(axes, panels, strict=True):
        before = _mean(rows, metric, mode="off")
        after = _mean(rows, metric, mode="full")
        off_n = sum(
            row.get(metric) not in (None, "")
            for row in rows
            if str(row.get("qa_mode", "")).lower() == "off"
        )
        full_n = sum(
            row.get(metric) not in (None, "")
            for row in rows
            if str(row.get("qa_mode", "")).lower() == "full"
        )
        n_text = f"n={off_n} pairs" if off_n == full_n else f"n={off_n}/{full_n}"
        ax.set_title(f"{label}\n({n_text})", fontsize=10)
        if before is None or after is None:
            ax.text(0.5, 0.5, "not measured", ha="center", va="center", transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            if metric in {
                "constraint_violation",
                "task_success",
                "false_rejection",
                "end_to_end_latency_ms",
            }:
                required_measured.add(metric)
            ax.bar([0, 1], [before, after], color=["#7f8c8d", "#2471a3"])
            ax.set_xticks([0, 1], ["OFF", "FULL"])
            ax.grid(axis="y", alpha=0.2)
        ax.set_xlabel(direction, fontsize=8)
    if required_measured != {
        "constraint_violation",
        "task_success",
        "false_rejection",
        "end_to_end_latency_ms",
    }:
        plt.close(fig)
        raise AnalysisError(
            "Figure B requires measured safety, task-success, false-rejection, and latency data"
        )
    fig.suptitle("B. Safety–Utility–Overhead Trade-off")
    fig.tight_layout()
    return _save(fig, output / "figure-b-tradeoff", "Quality Trade-off", source)


def figure_c(rows: list[dict[str, Any]], output: Path, source: str) -> list[Path]:
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("error") not in (None, ""):
            raise AnalysisError("Figure C refuses ablation rows with recorded errors")
        variant = row.get("ablation")
        if variant in (None, "", "none", "None"):
            # The ablation runner records the unmodified baseline as qa_mode=full
            # with a null ablation field.  Normalize that real runner shape here;
            # unrelated null rows must not silently become an ablation baseline.
            if str(row.get("qa_mode", "")).lower() != "full":
                continue
            label = "FULL"
        else:
            label = f"FULL - {str(variant).replace('_', ' ').title()} Guard"
        by_variant.setdefault(label, []).append(row)
    observed_ablations = {
        str(row.get("ablation"))
        for row in rows
        if row.get("ablation") not in (None, "", "none", "None")
    }
    if observed_ablations != REQUIRED_ABLATIONS or "FULL" not in by_variant:
        raise AnalysisError(
            "Figure C requires a FULL baseline and exactly all six measured "
            "ablation variants"
        )
    key_fields = ("task_id", "repetition", "seed", "provider", "model")

    def indexed(group: list[dict[str, Any]]) -> dict[tuple[Any, ...], dict[str, Any]]:
        result: dict[tuple[Any, ...], dict[str, Any]] = {}
        for row in group:
            key = tuple(row.get(field) for field in key_fields)
            if None in key or key in result:
                raise AnalysisError(f"Figure C has invalid/duplicate design key {key!r}")
            result[key] = row
        return result

    baseline = indexed(by_variant["FULL"])
    for label, group in by_variant.items():
        if label == "FULL":
            continue
        comparison = indexed(group)
        if set(comparison) != set(baseline):
            raise AnalysisError(f"Figure C variant {label} is not aligned with FULL")
        for key, full_row in baseline.items():
            variant_row = comparison[key]
            for field in ("controlled_input_digest", "initial_state_fingerprint"):
                if not full_row.get(field) or full_row.get(field) != variant_row.get(field):
                    raise AnalysisError(
                        f"Figure C {field} differs for {label}, design key {key!r}"
                    )
            if str(full_row.get("provider")) == "deterministic_stub" and (
                not full_row.get("proposed_action_digest")
                or full_row.get("proposed_action_digest")
                != variant_row.get("proposed_action_digest")
            ):
                raise AnalysisError(
                    f"Figure C proposal digest differs for {label}, design key {key!r}"
                )
    names = sorted(by_variant, key=lambda name: (name.lower() != "full", name))
    violation = [_mean(by_variant[name], "constraint_violation") for name in names]
    success = [_mean(by_variant[name], "task_success") for name in names]
    evidence = [_mean(by_variant[name], "evidence_completeness") for name in names]
    if any(value is None for value in violation + success + evidence):
        raise AnalysisError(
            "Figure C ablation rows lack constraint-violation, task-success, "
            "or evidence-completeness data"
        )
    x = np.arange(len(names))
    width = 0.26
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width, violation, width, label="Constraint violation")
    ax.bar(x, success, width, label="Task success")
    ax.bar(x + width, evidence, width, label="Evidence completeness")
    ax.set_xticks(
        x,
        [f"{name.replace('FULL - ', '− ')}\n(n={len(by_variant[name])})" for name in names],
        rotation=25,
        ha="right",
    )
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Observed mean (0–1)")
    ax.set_title("C. Data-driven Guard Ablation")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    return _save(fig, output / "figure-c-ablation", "Guard Ablation", source)


def figure_d(rows: list[dict[str, Any]], output: Path, source: str) -> list[Path]:
    present = {str(row.get("category")) for row in rows}
    missing = [category for category in REQUIRED_CATEGORIES if category not in present]
    if missing:
        raise AnalysisError(
            "Figure D requires all configured categories; missing " + ", ".join(missing)
        )
    off_values: list[float] = []
    full_values: list[float] = []
    for category in REQUIRED_CATEGORIES:
        category_rows = [row for row in rows if row.get("category") == category]
        before = _mean(category_rows, "constraint_violation", mode="off")
        after = _mean(category_rows, "constraint_violation", mode="full")
        if before is None or after is None:
            raise AnalysisError(f"Figure D lacks constraint-violation data for {category}")
        off_values.append(before)
        full_values.append(after)
    y = np.arange(len(REQUIRED_CATEGORIES))
    height = 0.36
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(y + height / 2, off_values, height, label="QA OFF")
    ax.barh(y - height / 2, full_values, height, label="IQA-SOA FULL")
    ax.set_yticks(y, [item.replace("_", " ") for item in REQUIRED_CATEGORIES])
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Constraint-violation run proportion")
    ax.set_title("D. Category Breakdown")
    ax.legend(frameon=False)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    return _save(fig, output / "figure-d-categories", "Category Breakdown", source)


def generate_all(
    before_source: Path, ablation_source: Path, *, token: str | None = None
) -> list[Path]:
    before_rows = _require_modes(load_run_records(before_source))
    ablation_rows = load_run_records(ablation_source)
    deterministic_fixture_only = all(
        str(row.get("provider", "")) == "deterministic_stub"
        for row in (*before_rows, *ablation_rows)
    )
    run_token = token or (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    )
    base = artifact_directory(before_source, "figures") / run_token
    if base.exists():
        raise FileExistsError(f"Refusing to overwrite figure set {base}")
    base.mkdir(parents=True)
    provenance = json.dumps(
        {
            "before_after_source": str(before_source.resolve()),
            "ablation_source": str(ablation_source.resolve()),
            "before_after_source_digests": raw_source_digests(before_source),
            "ablation_source_digests": raw_source_digests(ablation_source),
            "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "generated_at": datetime.now(UTC).isoformat(),
            "data_status": (
                "deterministic fixture; descriptive artifact validation only"
                if deterministic_fixture_only
                else "measured provider run"
            ),
        },
        sort_keys=True,
    )
    outputs = []
    outputs += figure_a(before_rows, base, provenance)
    outputs += figure_b(before_rows, base, provenance)
    outputs += figure_c(ablation_rows, base, provenance)
    outputs += figure_d(before_rows, base, provenance)
    (base / "provenance.json").write_text(provenance + "\n", encoding="utf-8")
    return outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Figures A–D from real run records.")
    parser.add_argument("experiment_dir", type=Path, help="Before/after experiment directory")
    parser.add_argument(
        "--ablation-dir",
        type=Path,
        required=True,
        help="Ablation experiment directory containing FULL and removal variants",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        outputs = generate_all(args.experiment_dir, args.ablation_dir)
    except (AnalysisError, FileExistsError, ValueError) as exc:
        print(f"figure generation failed: {exc}", file=sys.stderr)
        return 2
    print(f"generated {len(outputs)} files from measured data")
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
