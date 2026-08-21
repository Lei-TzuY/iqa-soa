#!/usr/bin/env python3
"""Run exactly one Phase-D qualification arm (3 diagnostic runs) against a real provider.

Phase D is an engineering instrument qualification, not an experiment.  This
driver deliberately runs ONE arm per invocation so that each arm produces its own
complete, non-overwriting experiment directory, and so that a failure in one arm
can never be silently retried or blended into another.

It invents no benchmark case, no treatment, and no metric: it selects the
Phase-D-only diagnostic case through the existing runner, with the existing
"off" treatment, and records ``experiment_kind=real_model_connectivity_smoke``
so these rows can never be mistaken for a real-model pilot.

Automatic infrastructure retries are fixed at zero and no run is repeated.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from iqa_soa.experiment.runner import (  # noqa: E402
    ExperimentConfigError,
    ExperimentRunner,
    load_experiment_config,
    load_provider,
)

ARMS = {
    "A": "mistral_none",
    "B": "mistral_trailing_user",
    "C": "qwen_none",
}
EXPECTED_POLICY = {
    "A": "none",
    "B": "trailing_user",
    "C": "none",
}
RUNS_PER_ARM = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", required=True, choices=sorted(ARMS))
    parser.add_argument(
        "--config", default=str(PROJECT_ROOT / "configs" / "phaseD-diagnostic.yaml")
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    slot = ARMS[args.arm]

    config = load_experiment_config(args.config)
    provider = load_provider(config.models_path, provider_name=slot)
    descriptor = provider.descriptor()

    # The arm's identity is asserted from configuration, never assumed: a
    # mislabelled arm would invalidate the whole qualification.
    policy = descriptor.get("tool_contract_policy")
    if policy != EXPECTED_POLICY[args.arm]:
        print(
            f"STOP: arm {args.arm} expects tool_contract_policy="
            f"{EXPECTED_POLICY[args.arm]!r} but slot {slot!r} declares {policy!r}",
            file=sys.stderr,
        )
        return 2
    if descriptor.get("protocol") != "native_tools":
        print(f"STOP: arm {args.arm} must use the native_tools protocol", file=sys.stderr)
        return 2

    credential_env = descriptor.get("api_key_env")
    if not os.environ.get(str(credential_env)):
        print(
            f"STOP: environment variable {credential_env!r} is unset; the provider "
            "path requires a credential value even when the local runtime ignores it",
            file=sys.stderr,
        )
        return 3

    print(
        f"Phase-D arm {args.arm}: slot={slot} model={descriptor.get('model')} "
        f"tool_contract_policy={policy} runs={RUNS_PER_ARM} "
        f"seeds={list(config.seeds[:RUNS_PER_ARM])}"
    )
    try:
        experiment_dir = ExperimentRunner(config, provider=provider).run(
            treatments=["off"],
            case_ids=["DIAG-001"],
            repetitions=RUNS_PER_ARM,
            max_total_runs=RUNS_PER_ARM,
            experiment_kind="real_model_connectivity_smoke",
            infrastructure_retry_limit=0,
        )
    except ExperimentConfigError as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 2
    print(f"arm={args.arm} experiment_dir={experiment_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
