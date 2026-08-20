from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from iqa_soa.agent.providers import AgentProvider, ProviderResponse
from iqa_soa.experiment.runner import ExperimentRunner, load_experiment_config
from iqa_soa.metrics.definitions import METRIC_BY_NAME, REQUIRED_RAW_FIELDS
from iqa_soa.types import Action


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _rows(tmp_path: Path, case_ids: list[str]) -> list[dict[str, object]]:
    config = load_experiment_config(PROJECT_ROOT / "configs" / "experiment.yaml").with_overrides(
        output_root=tmp_path, repetitions=1
    )
    output = ExperimentRunner(config).run(
        treatments=["off", "full"], case_ids=case_ids, repetitions=1
    )
    return [json.loads(line) for line in (output / "runs.jsonl").read_text(encoding="utf-8").splitlines()]


def test_metric_applicability_and_audit_completeness(tmp_path: Path) -> None:
    rows = _rows(tmp_path, ["BEN-001", "PRIV-001"])
    benign_off = next(row for row in rows if row["task_id"] == "BEN-001" and row["qa_mode"] == "off")
    benign_full = next(row for row in rows if row["task_id"] == "BEN-001" and row["qa_mode"] == "full")
    privacy_off = next(row for row in rows if row["task_id"] == "PRIV-001" and row["qa_mode"] == "off")
    assert benign_off["attack_success"] is None
    assert benign_off["privacy_leak"] is None
    assert benign_off["risk_interception"] is None
    assert benign_off["evidence_complete"] is False
    assert benign_off["evidence_completeness"] == 0.0
    assert benign_full["evidence_complete"] is True
    assert benign_full["evidence_completeness"] == 1.0
    assert privacy_off["privacy_leak"] is True


def test_safety_and_task_semantics_for_smoke_cases(tmp_path: Path) -> None:
    rows = _rows(tmp_path, ["UA-001", "PI-001", "BUD-001"])
    for task_id in ("UA-001", "PI-001", "BUD-001"):
        off = next(row for row in rows if row["task_id"] == task_id and row["qa_mode"] == "off")
        full = next(row for row in rows if row["task_id"] == task_id and row["qa_mode"] == "full")
        assert off["unsafe_action_proposed"] is True
        assert off["unsafe_action_executed"] is True
        assert off["constraint_violation"] is True
        assert off["task_success"] is False
        assert full["unsafe_action_blocked"] is True
        assert full["unsafe_action_executed"] is False
        assert full["risk_interception"] is True
        assert full["constraint_violation"] is False
        assert full["task_success"] is True


def test_raw_metric_contract_has_evidence_latency() -> None:
    assert "evidence_latency_ms" in REQUIRED_RAW_FIELDS
    assert METRIC_BY_NAME["evidence_latency_ms"].family == "performance"


def test_semantic_unsafe_effects_do_not_depend_on_model_action_ids(
    tmp_path: Path,
) -> None:
    class InventedIdProvider(AgentProvider):
        name = "synthetic_online_contract"
        model = "invented-ids"

        def generate_action(
            self,
            *,
            system_prompt: str,
            user_prompt: str,
            scripted_actions: Sequence[Action],
            step: int,
            seed: int,
            history: Sequence[Mapping[str, Any]] = (),
            canonical_resources: Sequence[str] = (),
        ) -> ProviderResponse | None:
            del system_prompt, user_prompt, seed, history, canonical_resources
            if step >= len(scripted_actions):
                return ProviderResponse(None, 1, 1, 0.0, '{"done":true}', self.model, outcome="no_action")
            original = scripted_actions[step]
            action = Action(
                action_id=f"invented-{step}",
                tool=original.tool,
                resource=original.resource,
                arguments=dict(original.arguments),
            )
            return ProviderResponse(action, 1, 1, 0.0, json.dumps(action.to_dict()), self.model)

    config = load_experiment_config(PROJECT_ROOT / "configs" / "experiment.yaml").with_overrides(
        output_root=tmp_path, repetitions=1
    )
    output = ExperimentRunner(config, provider=InventedIdProvider()).run(
        treatments=["off"], case_ids=["UA-001", "PI-001"], repetitions=1
    )
    rows = [json.loads(line) for line in (output / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert all(row["unsafe_action_proposed"] is True for row in rows)
    assert all(row["unsafe_action_executed"] is True for row in rows)
    assert all(row["constraint_violation"] is True for row in rows)
