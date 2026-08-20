from __future__ import annotations

import csv
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

from iqa_soa import __version__
from iqa_soa.experiment.replay import replay_experiment
from iqa_soa.agent import AgentProvider, DeterministicStubProvider
from iqa_soa.benchmark import load_benchmark_cases
from iqa_soa.experiment.runner import (
    ExperimentRunner,
    controlled_input_digest,
    load_experiment_config,
)
from iqa_soa.metrics.definitions import REQUIRED_RAW_FIELDS


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _config(tmp_path: Path):
    return load_experiment_config(PROJECT_ROOT / "configs" / "experiment.yaml").with_overrides(
        output_root=tmp_path, repetitions=1
    )


def _read_rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_paired_invariance_isolation_raw_schema_and_nonoverwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    runner = ExperimentRunner(config)
    first = runner.run(treatments=["off", "full"], case_ids=config.smoke_case_ids, repetitions=1)
    second = runner.run(treatments=["off", "full"], case_ids=config.smoke_case_ids, repetitions=1)
    assert first != second and first.exists() and second.exists()
    rows = _read_rows(first / "runs.jsonl")
    manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["software"]["artifact_version"] == __version__
    assert len(manifest["software"]["package_source_sha256"]) == 64
    assert manifest["status"] == "complete"
    assert manifest["record_count"] == manifest["expected_record_count"] == 8
    assert manifest["completed_at"]
    assert all(
        len(value) == 64 for value in manifest["input_digests"].values()
    )
    assert len(rows) == 8
    assert all(set(REQUIRED_RAW_FIELDS) <= set(row) for row in rows)
    assert all(row["error"] is None for row in rows)
    for task_id in config.smoke_case_ids:
        pair = [row for row in rows if row["task_id"] == task_id]
        assert len(pair) == 2
        assert len({row["seed"] for row in pair}) == 1
        assert len({row["controlled_input_digest"] for row in pair}) == 1
        assert len({row["initial_state_fingerprint"] for row in pair}) == 1
        assert len({row["proposed_action_digest"] for row in pair}) == 1
        assert {row["qa_mode"] for row in pair} == {"off", "full"}
        assert all(row["treatment_order"] == pair[0]["treatment_order"] for row in pair)

    with (first / "runs.csv").open(encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert len(csv_rows) == len(rows)
    assert tuple(csv_rows[0]) == REQUIRED_RAW_FIELDS


def test_smoke_behavioral_acceptance_and_evidence_paths(tmp_path: Path) -> None:
    config = _config(tmp_path)
    output = ExperimentRunner(config).run(
        treatments=["off", "full"], case_ids=config.smoke_case_ids, repetitions=1
    )
    rows = _read_rows(output / "runs.jsonl")
    benign = [row for row in rows if row["task_id"] == "BEN-001"]
    assert all(row["task_success"] is True for row in benign)
    assert all(row["false_rejection"] is False for row in benign)
    for task_id in ("UA-001", "PI-001", "BUD-001"):
        off = next(row for row in rows if row["task_id"] == task_id and row["qa_mode"] == "off")
        full = next(row for row in rows if row["task_id"] == task_id and row["qa_mode"] == "full")
        assert off["unsafe_action_executed"] is True
        assert full["unsafe_action_blocked"] is True
        assert full["unsafe_action_executed"] is False
    for row in rows:
        trace = output / str(row["trace_path"])
        assert trace.is_file()
        assert len(trace.read_text(encoding="utf-8").splitlines()) == row["completion_steps"]


def test_partial_is_exact_permission_budget_subset(tmp_path: Path) -> None:
    output = ExperimentRunner(_config(tmp_path)).run(
        treatments=["partial"], case_ids=["BEN-001"], repetitions=1
    )
    row = _read_rows(output / "runs.jsonl")[0]
    assert row["qa_mode"] == "partial"
    assert row["enabled_guards"] == {
        "injection": False,
        "permission": True,
        "privacy": False,
        "budget": True,
        "output_validation": False,
        "evidence": False,
    }
    assert row["evidence_complete"] is False


def test_controlled_input_digest_covers_constraints_and_ground_truth() -> None:
    case = load_benchmark_cases(PROJECT_ROOT / "benchmark", case_ids=["BEN-001"])[0]
    provider = DeterministicStubProvider()
    original = controlled_input_digest(case, provider, 1729)
    changed_budget = replace(
        case,
        budget=replace(case.budget, max_tool_calls=(case.budget.max_tool_calls or 0) + 1),
    )
    changed_truth = replace(
        case,
        ground_truth=replace(
            case.ground_truth,
            task_should_succeed=not case.ground_truth.task_should_succeed,
        ),
    )
    assert controlled_input_digest(changed_budget, provider, 1729) != original
    assert controlled_input_digest(changed_truth, provider, 1729) != original


def test_treatment_order_is_counterbalanced_within_a_complete_block(
    tmp_path: Path,
) -> None:
    output = ExperimentRunner(_config(tmp_path)).run(
        treatments=["off", "partial", "full"],
        case_ids=["BEN-001"],
        repetitions=3,
    )
    rows = _read_rows(output / "runs.jsonl")
    for mode in ("off", "partial", "full"):
        positions = {
            row["treatment_index"] for row in rows if row["qa_mode"] == mode
        }
        assert positions == {0, 1, 2}


class _NoActionProvider(AgentProvider):
    name = "no_action_test_provider"
    model = "none-v1"

    def generate_action(self, **_: object):
        return None


def test_zero_action_run_still_emits_lifecycle_evidence(tmp_path: Path) -> None:
    output = ExperimentRunner(
        _config(tmp_path), provider=_NoActionProvider()
    ).run(treatments=["full"], case_ids=["BEN-001"], repetitions=1)
    row = _read_rows(output / "runs.jsonl")[0]
    assert row["completion_steps"] == 0
    trace = output / str(row["trace_path"])
    events = _read_rows(trace)
    assert len(events) == 1
    assert events[0]["event_type"] == "run_terminal"
    assert events[0]["final_decision"] == "NO_ACTION"
    assert events[0]["qa_ium_compatible_fragment"] is True


def test_model_call_budget_is_a_treatment_not_an_all_arm_cap(tmp_path: Path) -> None:
    case_root = tmp_path / "benchmark"
    case_root.mkdir()
    source = PROJECT_ROOT / "benchmark" / "benign" / "BEN-001.yaml"
    case_text = source.read_text(encoding="utf-8").replace(
        "max_model_calls: 2", "max_model_calls: 0"
    )
    (case_root / "BEN-001.yaml").write_text(case_text, encoding="utf-8")
    config = replace(_config(tmp_path / "results"), benchmark_path=case_root)
    output = ExperimentRunner(config).run(
        treatments=["off", "full"], case_ids=["BEN-001"], repetitions=1
    )
    rows = _read_rows(output / "runs.jsonl")
    off = next(row for row in rows if row["qa_mode"] == "off")
    full = next(row for row in rows if row["qa_mode"] == "full")
    assert off["model_calls"] == 1
    assert off["budget_violation"] is True
    assert full["model_calls"] == 0
    assert full["budget_violation"] is False
    assert full["completion_steps"] == 0


def test_analysis_loader_rejects_manifest_count_drift(tmp_path: Path) -> None:
    from iqa_soa.metrics.statistics import AnalysisError, load_run_records

    output = ExperimentRunner(_config(tmp_path)).run(
        treatments=["off", "full"], case_ids=["BEN-001"], repetitions=1
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["record_count"] -= 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    import pytest

    with pytest.raises(AnalysisError, match="count mismatch"):
        load_run_records(output)


def test_replay_recomputes_unsafe_counts_in_configured_order(tmp_path: Path) -> None:
    config = _config(tmp_path)
    output = ExperimentRunner(config).run(
        treatments=["off", "full"], case_ids=["UA-001"], repetitions=1
    )
    report = replay_experiment(output, benchmark_path=config.benchmark_path, ordering="run_id")
    assert report["verified"] is True
    assert report["run_count"] == 2
    assert (output / "replay-run_id.json").is_file()

    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "replay.py"),
        str(output),
        "--config",
        str(PROJECT_ROOT / "configs" / "experiment.yaml"),
        "--ordering",
        "recorded",
    ]
    first = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
    assert first.returncode == 0
    second = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
    assert second.returncode == 2
    assert second.stderr.startswith("replay failed:")
    assert "Traceback" not in second.stderr
