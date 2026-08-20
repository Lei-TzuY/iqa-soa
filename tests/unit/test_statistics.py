from __future__ import annotations

import json
from pathlib import Path

import pytest

from iqa_soa.metrics.statistics import (
    AnalysisError,
    analyze_before_after,
    analyze_binary_metric,
    analyze_continuous_metric,
    aggregate_rate_summary,
    load_run_records,
    pair_before_after,
)


def make_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    binary_before = [1, 1, 0, 0]
    binary_after = [0, 0, 0, 1]
    latency_before = [10.0, 20.0, 30.0, 40.0]
    latency_after = [8.0, 18.0, 33.0, 39.0]
    for repetition in range(4):
        common = {
            "task_id": "T-1",
            "repetition": repetition,
            "seed": 100 + repetition,
            "provider": "stub",
            "model": "scripted-v1",
            "ablation": None,
        }
        rows.append(
            {
                **common,
                "run_id": f"off-{repetition}",
                "qa_mode": "off",
                "constraint_violation": binary_before[repetition],
                "end_to_end_latency_ms": latency_before[repetition],
                "estimated_cost": None,
            }
        )
        rows.append(
            {
                **common,
                "run_id": f"full-{repetition}",
                "qa_mode": "full",
                "constraint_violation": binary_after[repetition],
                "end_to_end_latency_ms": latency_after[repetition],
                "estimated_cost": None,
            }
        )
    return rows


def test_binary_analysis_uses_paired_discordant_counts() -> None:
    result = analyze_binary_metric(pair_before_after(make_rows()), "constraint_violation")
    assert result is not None
    assert result["before"] == pytest.approx(0.5)
    assert result["after"] == pytest.approx(0.25)
    assert result["absolute_difference"] == pytest.approx(-0.25)
    assert result["relative_difference"] == pytest.approx(-0.5)
    assert result["discordant_before_only"] == 2
    assert result["discordant_after_only"] == 1
    assert result["effect_size"] == pytest.approx(0.5)
    assert "McNemar" in result["test"]


def test_continuous_analysis_operates_on_within_pair_differences() -> None:
    result = analyze_continuous_metric(
        pair_before_after(make_rows()), "end_to_end_latency_ms"
    )
    assert result is not None
    assert result["before"] == pytest.approx(25.0)
    assert result["after"] == pytest.approx(24.5)
    assert result["absolute_difference"] == pytest.approx(-0.5)
    assert result["relative_difference"] == pytest.approx(-0.02)
    assert result["n_pairs"] == 4
    assert result["ci_low"] <= result["absolute_difference"] <= result["ci_high"]
    assert "Wilcoxon" in result["test"]


def test_zero_before_rate_has_no_relative_change() -> None:
    rows = make_rows()
    for row in rows:
        row["constraint_violation"] = int(row["qa_mode"] == "full")
    result = analyze_binary_metric(pair_before_after(rows), "constraint_violation")
    assert result is not None
    assert result["before"] == 0
    assert result["relative_difference"] is None


def test_nullable_cost_is_not_fabricated() -> None:
    analysis = analyze_before_after(make_rows(), bootstrap_samples=100)
    metrics = {item["metric"] for item in analysis["metrics"]}
    assert "constraint_violation" in metrics
    assert "estimated_cost" not in metrics


def test_nonfinite_measurement_is_rejected_not_silently_dropped() -> None:
    rows = make_rows()
    rows[0]["end_to_end_latency_ms"] = float("nan")
    with pytest.raises(AnalysisError, match="finite numeric"):
        analyze_before_after(rows, bootstrap_samples=100)


def test_duplicate_and_missing_pairs_are_rejected() -> None:
    rows = make_rows()
    with pytest.raises(AnalysisError, match="Duplicate"):
        pair_before_after([*rows, dict(rows[0])])
    with pytest.raises(AnalysisError, match="Unpaired"):
        pair_before_after(rows[:-1])


def test_loader_prefers_aggregate_runs_file(tmp_path: Path) -> None:
    rows = make_rows()
    runs = tmp_path / "runs.jsonl"
    runs.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    (tmp_path / "evidence.jsonl").write_text('{"not":"a run"}\n', encoding="utf-8")
    assert load_run_records(tmp_path) == rows


def test_deterministic_fixture_suppresses_inferential_claims() -> None:
    rows = make_rows()
    for row in rows:
        row["provider"] = "deterministic_stub"
    analysis = analyze_before_after(rows, bootstrap_samples=100)
    assert analysis["inferential_statistics_eligible"] is False
    assert "not independent" in analysis["inference_note"]
    for metric in analysis["metrics"]:
        assert metric["ci_low"] is None
        assert metric["ci_high"] is None
        assert metric["p_value"] is None
        assert metric["effect_size"] is None
        assert metric["inference_eligible"] is False


def test_online_repetitions_use_task_cluster_not_pair_independence() -> None:
    first_task = make_rows()
    second_task = []
    for row in first_task:
        clone = dict(row)
        clone["task_id"] = "T-2"
        clone["run_id"] = f"t2-{row['run_id']}"
        second_task.append(clone)
    analysis = analyze_before_after(
        [*first_task, *second_task], bootstrap_samples=100
    )
    metric = next(
        row for row in analysis["metrics"] if row["metric"] == "constraint_violation"
    )
    assert metric["n_pairs"] == 8
    assert metric["n_independent_tasks"] == 2
    assert "task-cluster sign-flip" in metric["test"]
    assert "fixed benchmark suite" in analysis["inference_note"]


def test_pairing_rejects_recorded_errors_and_invariant_drift() -> None:
    rows = make_rows()[:2]
    rows[0]["controlled_input_digest"] = "one"
    rows[1]["controlled_input_digest"] = "two"
    with pytest.raises(AnalysisError, match="controlled_input_digest"):
        pair_before_after(rows)

    rows = make_rows()[:2]
    rows[1]["error"] = "provider failed"
    with pytest.raises(AnalysisError, match="recorded error"):
        pair_before_after(rows)


def test_action_denominator_aggregate_rates_are_explicit() -> None:
    rows = make_rows()[:2]
    for row in rows:
        row.update(
            unsafe_proposed_count=2,
            unsafe_executed_count=2 if row["qa_mode"] == "off" else 0,
            unsafe_blocked_count=0 if row["qa_mode"] == "off" else 2,
            expected_action_count=3,
            expected_blocked_count=0,
        )
    summaries = {
        (row["qa_mode"], row["metric"]): row for row in aggregate_rate_summary(rows)
    }
    assert summaries[("off", "unauthorized_action_execution_rate")]["rate"] == 1.0
    assert summaries[("full", "risk_interception_recall")]["rate"] == 1.0
