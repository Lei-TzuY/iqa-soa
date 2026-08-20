from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from iqa_soa.experiment.pilot import (
    PilotConfigError,
    load_pilot_config,
    preflight_pilot,
    run_real_pilot,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PILOT_CONFIG = PROJECT_ROOT / "configs" / "pilot.yaml"


def test_pilot_preflight_reports_exact_design_without_secret_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "MODEL_A_BASE_URL",
        "MODEL_A_API_KEY",
        "MODEL_A_NAME",
        "MODEL_B_BASE_URL",
        "MODEL_B_API_KEY",
        "MODEL_B_NAME",
    ):
        monkeypatch.delenv(name, raising=False)
    config = load_pilot_config(PILOT_CONFIG)
    report = preflight_pilot(config)
    assert (report.models, report.tasks, report.treatments, report.repetitions) == (
        2,
        12,
        2,
        5,
    )
    assert report.benchmark_version == "pilot-v5"
    assert report.expected_total_runs == 240
    assert report.max_total_runs == 300
    assert report.credentials_ready is False
    serialized = repr(report.provider_environment)
    assert "MODEL_A_API_KEY" in serialized
    assert "MODEL_B_API_KEY" in serialized


def test_pilot_refuses_missing_environment_before_creating_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in (
        "MODEL_A_BASE_URL",
        "MODEL_A_API_KEY",
        "MODEL_A_NAME",
    ):
        monkeypatch.delenv(name, raising=False)
    output = tmp_path / "raw"
    config = replace(load_pilot_config(PILOT_CONFIG), output_root=output)
    with pytest.raises(PilotConfigError, match="environment is incomplete"):
        run_real_pilot(config, provider_ids=["model_a"], stage="smoke")
    assert not output.exists()


def test_global_pilot_run_ceiling_is_checked_during_preflight() -> None:
    config = replace(load_pilot_config(PILOT_CONFIG), max_total_runs=239)
    with pytest.raises(PilotConfigError, match="ceiling exceeded"):
        preflight_pilot(config)
