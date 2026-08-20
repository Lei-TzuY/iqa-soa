from __future__ import annotations

import json
from pathlib import Path

from iqa_soa.experiment.ablation import load_ablation_treatments
from iqa_soa.experiment.runner import ExperimentRunner, load_experiment_config


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_every_required_ablation_has_an_observable_case(tmp_path: Path) -> None:
    config = load_experiment_config(PROJECT_ROOT / "configs" / "experiment.yaml").with_overrides(
        output_root=tmp_path, repetitions=1
    )
    output = ExperimentRunner(config).run(
        treatments=load_ablation_treatments(config.ablations_path), repetitions=1
    )
    rows = [json.loads(line) for line in (output / "runs.jsonl").read_text(encoding="utf-8").splitlines()]

    checks = {
        "injection": lambda row: row["task_id"] == "PI-001" and row["attack_success"] is True,
        "permission": lambda row: row["task_id"] == "UA-001" and row["unsafe_action_executed"] is True,
        "privacy": lambda row: row["task_id"] == "PRIV-001" and row["privacy_leak"] is True,
        "budget": lambda row: row["task_id"] == "BUD-001" and row["budget_violation"] is True,
        "output_validation": lambda row: row["task_id"] == "FAULT-001" and row["fault_contained"] is False,
        "evidence": lambda row: row["task_id"] == "BEN-001" and row["evidence_complete"] is False,
    }
    for guard, observable in checks.items():
        assert any(row["ablation"] == guard and observable(row) for row in rows), guard

    full_fault = next(
        row for row in rows if row["task_id"] == "FAULT-001" and row["qa_mode"] == "full"
    )
    assert full_fault["fault_contained"] is True
    assert full_fault["unsafe_action_executed"] is False
