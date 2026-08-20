from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

from iqa_soa.agent.providers import AgentProvider, ProviderResponse
from iqa_soa.benchmark import load_frozen_pilot
from iqa_soa.experiment.runner import (
    ExperimentConfigError,
    ExperimentRunner,
    load_experiment_config,
)
from iqa_soa.experiment.pilot import PilotConfigError, _validate_connectivity_smoke
from iqa_soa.experiment.treatments import load_ablation_treatments
from iqa_soa.metrics.definitions import PILOT_RAW_FIELDS
from iqa_soa.types import Action


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class SyntheticOnlineProvider(AgentProvider):
    name = "synthetic_online_contract"

    def __init__(
        self, model: str = "synthetic-online-v1", *, emit_scripted: bool = False
    ) -> None:
        self.model = model
        self.emit_scripted = emit_scripted

    def descriptor(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "model": self.model,
            "temperature": 0.2,
            "top_p": 1.0,
            "max_output_tokens": 128,
            "supports_seed": True,
        }

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
        del system_prompt, user_prompt, history, canonical_resources
        action = (
            scripted_actions[step]
            if self.emit_scripted and step < len(scripted_actions)
            else None
        )
        return ProviderResponse(
            action=action,
            input_tokens=3,
            output_tokens=1,
            latency_ms=0.1,
            raw_response=(
                json.dumps(action.to_dict(), sort_keys=True)
                if action is not None
                else '{"done":true}'
            ),
            model=self.model,
            outcome="action" if action is not None else "no_action",
            request_id=f"req-{seed}-{step}",
            client_request_id=f"client-{seed}-{step}",
            response_id=f"response-{seed}-{step}",
            effective_model=self.model,
            finish_reason="stop",
            protocol="native_tools",
            effective_seed=seed,
            original_action_id=action.action_id if action is not None else None,
            canonical_action_id=action.action_id if action is not None else None,
        )


def test_frozen_real_pilot_contract_writes_schema_and_exact_pairs(tmp_path: Path) -> None:
    config = load_experiment_config(PROJECT_ROOT / "configs" / "experiment.yaml").with_overrides(
        output_root=tmp_path, repetitions=1
    )
    frozen = load_frozen_pilot(PROJECT_ROOT / "benchmark" / "pilot-v1" / "manifest.json")
    output = ExperimentRunner(config, provider=SyntheticOnlineProvider()).run(
        treatments=["off", "full"],
        case_ids=["BEN-001", "UA-001"],
        repetitions=1,
        frozen_benchmark=frozen,
        max_total_runs=4,
        experiment_kind="real_model_connectivity_smoke",
    )
    rows = [json.loads(line) for line in (output / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 4
    assert all(set(PILOT_RAW_FIELDS) <= set(row) for row in rows)
    assert all(row["benchmark_version"] == "pilot-v1" for row in rows)
    assert all(row["experiment_kind"] == "real_model_connectivity_smoke" for row in rows)
    assert all(row["provider_attempt_count"] == 1 for row in rows)
    assert all(row["no_action"] is True for row in rows)
    for task_id in ("BEN-001", "UA-001"):
        task_rows = [row for row in rows if row["task_id"] == task_id]
        assert len({row["pair_id"] for row in task_rows}) == 1
        assert len({row["controlled_input_digest"] for row in task_rows}) == 1
    with (output / "runs.csv").open(encoding="utf-8", newline="") as handle:
        assert tuple(next(csv.reader(handle))) == PILOT_RAW_FIELDS
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 2
    assert manifest["raw_schema_version"] == 2
    assert manifest["record_count"] == manifest["expected_record_count"] == 4
    assert manifest["input_digests"]["benchmark_manifest_sha256"] == frozen.manifest_sha256


def test_run_ceiling_refuses_before_result_directory_creation(tmp_path: Path) -> None:
    config = load_experiment_config(PROJECT_ROOT / "configs" / "experiment.yaml").with_overrides(
        output_root=tmp_path, repetitions=1
    )
    frozen = load_frozen_pilot(PROJECT_ROOT / "benchmark" / "pilot-v1" / "manifest.json")
    with pytest.raises(ExperimentConfigError, match="ceiling exceeded"):
        ExperimentRunner(config, provider=SyntheticOnlineProvider()).run(
            treatments=["off", "full"],
            case_ids=["BEN-001", "UA-001"],
            repetitions=1,
            frozen_benchmark=frozen,
            max_total_runs=3,
            experiment_kind="real_model_connectivity_smoke",
        )
    assert not any(tmp_path.iterdir())


def test_connectivity_smoke_gate_requires_real_actions_and_interception(
    tmp_path: Path,
) -> None:
    config = load_experiment_config(PROJECT_ROOT / "configs" / "experiment.yaml").with_overrides(
        output_root=tmp_path / "passing", repetitions=1
    )
    frozen = load_frozen_pilot(PROJECT_ROOT / "benchmark" / "pilot-v2" / "manifest.json")
    provider = SyntheticOnlineProvider("synthetic-online-smoke", emit_scripted=True)
    output = ExperimentRunner(config, provider=provider).run(
        treatments=["off", "full"],
        case_ids=["BEN-001", "UA-003"],
        repetitions=1,
        frozen_benchmark=frozen,
        max_total_runs=4,
        experiment_kind="real_model_connectivity_smoke",
    )
    _validate_connectivity_smoke(output, frozen, provider.name, provider.model)

    failing_provider = SyntheticOnlineProvider("synthetic-online-no-action")
    failing = ExperimentRunner(
        config.with_overrides(output_root=tmp_path / "failing"),
        provider=failing_provider,
    ).run(
        treatments=["off", "full"],
        case_ids=["BEN-001", "UA-003"],
        repetitions=1,
        frozen_benchmark=frozen,
        max_total_runs=4,
        experiment_kind="real_model_connectivity_smoke",
    )
    with pytest.raises(PilotConfigError, match="failure"):
        _validate_connectivity_smoke(
            failing, frozen, failing_provider.name, failing_provider.model
        )


def test_frozen_real_provider_contract_remains_ablation_compatible(
    tmp_path: Path,
) -> None:
    config = load_experiment_config(PROJECT_ROOT / "configs" / "experiment.yaml").with_overrides(
        output_root=tmp_path, repetitions=1
    )
    frozen = load_frozen_pilot(PROJECT_ROOT / "benchmark" / "pilot-v2" / "manifest.json")
    treatments = load_ablation_treatments(PROJECT_ROOT / "configs" / "ablations.yaml")
    output = ExperimentRunner(
        config,
        provider=SyntheticOnlineProvider("synthetic-online-ablation", emit_scripted=True),
    ).run(
        treatments=treatments,
        case_ids=["UA-003"],
        repetitions=1,
        frozen_benchmark=frozen,
        max_total_runs=7,
        experiment_kind="real_model_ablation_smoke",
    )

    rows = [
        json.loads(line)
        for line in (output / "runs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 7
    observed_treatments = {
        "full" if row["ablation"] is None else f"full_minus_{row['ablation']}"
        for row in rows
    }
    assert observed_treatments == {item.name for item in treatments}
    assert all(row["experiment_kind"] == "real_model_ablation_smoke" for row in rows)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete"
    assert manifest["record_count"] == manifest["expected_record_count"] == 7
