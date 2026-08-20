#!/usr/bin/env python3
"""Run a targeted subset of the existing ablation matrix against a real provider.

Unlike ``run_ablation.py`` (which always runs the complete FULL plus every
full-minus-one treatment over the whole benchmark with the configured
default provider), this script runs an explicitly named subset of
already-defined treatments over an explicitly named subset of frozen pilot
cases, with a specific real provider. It invents no new treatment and no
new benchmark case; it only selects among what already exists.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from iqa_soa.benchmark import load_frozen_pilot  # noqa: E402
from iqa_soa.experiment.pilot import (  # noqa: E402
    PilotConfigError,
    _assert_no_credential_values,
    inspect_provider_environment,
)
from iqa_soa.experiment.runner import (  # noqa: E402
    ExperimentConfigError,
    ExperimentRunner,
    load_experiment_config,
    load_provider,
)
from iqa_soa.experiment.treatments import load_ablation_treatments  # noqa: E402
from iqa_soa.experiment.pilot import load_pilot_config  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(PROJECT_ROOT / "configs" / "pilot.yaml"))
    parser.add_argument("--provider", required=True)
    parser.add_argument("--cases", nargs="+", required=True)
    parser.add_argument("--treatments", nargs="+", required=True)
    parser.add_argument("--repetitions", type=int, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_pilot_config(args.config)
        environment = inspect_provider_environment(config.models_path, [args.provider])
        missing = environment[args.provider].get("missing", [])
        if missing:
            print(f"provider {args.provider} environment incomplete: {missing}", file=sys.stderr)
            return 3
        provider = load_provider(config.models_path, provider_name=args.provider)
        frozen = load_frozen_pilot(config.benchmark_manifest_path)
        missing_cases = set(args.cases) - set(frozen.selected_task_ids)
        if missing_cases:
            print(f"cases absent from frozen benchmark: {sorted(missing_cases)}", file=sys.stderr)
            return 4
        all_ablation_treatments = {
            t.name: t for t in load_ablation_treatments(PROJECT_ROOT / "configs" / "ablations.yaml")
        }
        missing_treatments = set(args.treatments) - set(all_ablation_treatments)
        if missing_treatments:
            print(f"unknown treatments: {sorted(missing_treatments)}", file=sys.stderr)
            return 5
        selected_treatments = [all_ablation_treatments[name] for name in args.treatments]

        base = load_experiment_config(config.experiment_config_path)
        derived = replace(
            base,
            benchmark_path=config.benchmark_manifest_path.parent.parent,
            models_path=config.models_path,
            output_root=config.output_root,
            repetitions=args.repetitions,
            seeds=config.seeds[: args.repetitions],
            treatments=tuple(args.treatments),
            smoke_case_ids=tuple(args.cases[:2]) if len(args.cases) >= 2 else config.smoke_case_ids,
            source_path=config.source_path,
        )
        expected = len(args.cases) * len(selected_treatments) * args.repetitions
        output = ExperimentRunner(derived, provider=provider).run(
            treatments=selected_treatments,
            case_ids=args.cases,
            repetitions=args.repetitions,
            frozen_benchmark=frozen,
            max_total_runs=expected,
            experiment_kind="real_model_ablation_smoke",
        )
        _assert_no_credential_values(output, config.models_path, [args.provider])
    except (PilotConfigError, ExperimentConfigError, ValueError) as exc:
        print(f"targeted ablation run failed: {exc}", file=sys.stderr)
        return 2

    print(f"output_dir: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
