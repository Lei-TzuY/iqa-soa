"""Controlled paired and ablation experiment orchestration."""

from iqa_soa.experiment.pilot import (
    PilotConfig,
    PilotConfigError,
    load_pilot_config,
    preflight_pilot,
    run_real_pilot,
)
from iqa_soa.experiment.runner import ExperimentRunner, load_experiment_config
from iqa_soa.experiment.treatments import Treatment, treatment_for

__all__ = [
    "ExperimentRunner",
    "PilotConfig",
    "PilotConfigError",
    "Treatment",
    "load_experiment_config",
    "load_pilot_config",
    "preflight_pilot",
    "run_real_pilot",
    "treatment_for",
]
