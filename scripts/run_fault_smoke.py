#!/usr/bin/env python3
"""Run the two-cell FAULT-002 OFF/FULL smoke against a configured real provider.

This is deliberately separate from ``run_real_pilot.py --stage smoke``, which
validates a fixed BEN-001/UA-003 four-cell connectivity smoke via
``_validate_connectivity_smoke``. FAULT-002's pass/fail criteria are
different (did the fault actually trigger, was it actually contained), so
this script runs exactly the two FAULT-002 cells and prints the fields
needed to judge that construct directly, without touching or reinterpreting
the frozen BEN/UA connectivity-smoke contract.
"""

from __future__ import annotations

import argparse
import json
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
    load_pilot_config,
)
from iqa_soa.experiment.runner import (  # noqa: E402
    ExperimentConfigError,
    ExperimentRunner,
    load_experiment_config,
    load_provider,
)
from dataclasses import replace  # noqa: E402


_FIELDS = (
    "task_id",
    "qa_mode",
    "failure_class",
    "error",
    "fault_triggered",
    "fault_contained",
    "safety_security_violation",
    "resource_budget_violation",
    "task_success",
    "provider_attempt_count",
    "proposed_action_count",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(PROJECT_ROOT / "configs" / "pilot.yaml"))
    parser.add_argument("--provider", default="model_a")
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
        if "FAULT-002" not in frozen.selected_task_ids:
            print(
                f"FAULT-002 is not part of frozen benchmark {frozen.benchmark_version}",
                file=sys.stderr,
            )
            return 4
        base = load_experiment_config(config.experiment_config_path)
        derived = replace(
            base,
            benchmark_path=config.benchmark_manifest_path.parent.parent,
            models_path=config.models_path,
            output_root=config.output_root,
            repetitions=1,
            seeds=config.seeds[:1],
            treatments=("off", "full"),
            smoke_case_ids=("FAULT-002", "FAULT-002"),
            source_path=config.source_path,
        )
        output = ExperimentRunner(derived, provider=provider).run(
            treatments=["off", "full"],
            case_ids=["FAULT-002"],
            repetitions=1,
            frozen_benchmark=frozen,
            max_total_runs=2,
            experiment_kind="real_model_connectivity_smoke",
        )
        _assert_no_credential_values(output, config.models_path, [args.provider])
    except (PilotConfigError, ExperimentConfigError, ValueError) as exc:
        print(f"fault smoke failed: {exc}", file=sys.stderr)
        return 2

    print(f"output_dir: {output}")
    rows = [
        json.loads(line)
        for line in (output / "runs.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for row in rows:
        print(json.dumps({field: row.get(field) for field in _FIELDS}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
