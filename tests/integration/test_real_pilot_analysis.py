from __future__ import annotations

import csv
import json
from pathlib import Path

from iqa_soa.benchmark import load_frozen_pilot
from iqa_soa.experiment.runner import ExperimentRunner, load_experiment_config
from iqa_soa.metrics.pilot import analyze_real_pilot, load_real_pilot_records

from scripts.analyze_real_pilot import write_pilot_analysis
from scripts.generate_pilot_figures import generate_pilot_figures
from tests.integration.test_real_pilot_runner import SyntheticOnlineProvider


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _pilot_run(tmp_path: Path, model: str, *, repetitions: int = 2) -> Path:
    config = load_experiment_config(PROJECT_ROOT / "configs" / "experiment.yaml").with_overrides(
        output_root=tmp_path, repetitions=repetitions
    )
    frozen = load_frozen_pilot(PROJECT_ROOT / "benchmark" / "pilot-v1" / "manifest.json")
    return ExperimentRunner(config, provider=SyntheticOnlineProvider(model)).run(
        treatments=["off", "full"],
        repetitions=repetitions,
        frozen_benchmark=frozen,
        max_total_runs=300,
        experiment_kind="real_model_pilot",
    )


def test_real_pilot_analysis_validates_and_reports_two_models(tmp_path: Path) -> None:
    first = _pilot_run(tmp_path / "one", "synthetic-online-a")
    second = _pilot_run(tmp_path / "two", "synthetic-online-b")
    rows, validation = load_real_pilot_records([first, second])
    assert len(rows) == 96
    assert validation["models"] == 2
    assert validation["benchmark_version"] == "pilot-v1"
    analysis = analyze_real_pilot(
        [first, second], bootstrap_samples=100, seed=7
    )
    assert analysis["result_provenance"] == "real-model pilot"
    assert analysis["paired_analysis"]["n_pairs"] == 48
    assert len(analysis["per_model"]) == 2
    assert [row["metric"] for row in analysis["summary"]] == [
        "Safety/Security Violation Rate",
        "Resource Budget Violation Rate",
        "Constraint Violation Rate",
        "Unauthorized Action Rate",
        "Attack Success Rate",
        "Privacy Leakage Rate",
        "Task Success Rate",
        "False Rejection Rate",
        "Median Latency (ms)",
        "Mean Token Usage",
        "Estimated Cost",
        "Evidence Completeness",
    ]
    cost = next(row for row in analysis["summary"] if row["metric"] == "Estimated Cost")
    assert cost["qa_off"] is None and cost["qa_full"] is None


def test_real_pilot_tables_are_separate_and_provenance_labeled(tmp_path: Path) -> None:
    source = _pilot_run(tmp_path / "raw", "synthetic-online-a")
    analysis = analyze_real_pilot([source], bootstrap_samples=100, seed=11)
    paths = write_pilot_analysis(analysis, tmp_path / "derived", token="fixed")
    markdown = paths["markdown"].read_text(encoding="utf-8")
    assert "real-model pilot" in markdown
    assert "deterministic mechanism validation or final FSE evidence" in markdown
    assert "## Model: synthetic_online_contract / synthetic-online-a" in markdown
    with paths["csv"].open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 24
    assert {row["scope"] for row in rows} == {"all_models", "per_model"}


def test_real_pilot_figures_p1_through_p4_use_measured_rows(tmp_path: Path) -> None:
    config = load_experiment_config(PROJECT_ROOT / "configs" / "experiment.yaml").with_overrides(
        output_root=tmp_path / "raw", repetitions=2
    )
    frozen = load_frozen_pilot(PROJECT_ROOT / "benchmark" / "pilot-v1" / "manifest.json")
    source = ExperimentRunner(
        config,
        provider=SyntheticOnlineProvider("synthetic-online-figures", emit_scripted=True),
    ).run(
        treatments=["off", "full"],
        repetitions=2,
        frozen_benchmark=frozen,
        max_total_runs=300,
        experiment_kind="real_model_pilot",
    )
    outputs = generate_pilot_figures([source], tmp_path / "derived", token="fixed")
    assert len(outputs) == 8
    assert all(path.exists() and path.stat().st_size > 0 for path in outputs)
    names = {path.stem for path in outputs}
    assert names == {
        "figure-p1-safety",
        "figure-p2-tradeoff",
        "figure-p3-models",
        "figure-p4-categories",
    }
    provenance = tmp_path / "derived" / "figures" / "fixed" / "provenance.json"
    assert '"result_provenance": "real-model pilot"' in provenance.read_text(encoding="utf-8")


def test_analysis_preserves_and_labels_legacy_missing_resource_failures(tmp_path: Path) -> None:
    source = _pilot_run(tmp_path / "legacy", "synthetic-online-legacy", repetitions=5)
    run_path = source / "runs.jsonl"
    rows = [json.loads(line) for line in run_path.read_text(encoding="utf-8").splitlines()]
    historical_tasks = {"BEN-002", "PRIV-001", "PRIV-002", "UA-001"}
    selected = [
        row
        for row in rows
        if row["qa_mode"] == "off" and row["task_id"] in historical_tasks
    ]
    selected.extend(
        row
        for row in rows
        if row["qa_mode"] == "off"
        and row["task_id"] == "BUD-001"
        and row["repetition"] < 3
    )
    assert len(selected) == 23
    for row in selected:
        row["error"] = "sandbox file not found: model-invented-resource"
        row["failure_class"] = None
    run_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )

    loaded, validation = load_real_pilot_records([source])
    assert validation["failure_counts"] == {"invalid_resource": 23}
    assert validation["failure_classification_sources"] == {
        "legacy_inferred_from_error": 23
    }
    assert validation["historical_failure_taxonomy_inferred"] is True
    assert all(row["failure_class"] is None for row in loaded if row.get("error"))
    assert sum(
        row.get("analysis_failure_class") == "invalid_resource" for row in loaded
    ) == 23
    analysis = analyze_real_pilot([source], bootstrap_samples=100, seed=13)
    assert "legacy failure taxonomy inferred" in analysis["result_status"]
