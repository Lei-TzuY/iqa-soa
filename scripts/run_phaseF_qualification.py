#!/usr/bin/env python3
"""Run exactly one Phase-F QA-OFF qualification arm (17 tasks x 3 seeds) per invocation.

Phase F is an ENGINEERING BENCHMARK QUALIFICATION, not an experiment.  Its only
question is whether pilot-v7-rc1's intended safe paths, risky paths, multi-step
causal opportunities, benign controls and fault opportunity are actually
REACHABLE under real local models with QA OFF.  It estimates no QA
effectiveness, runs no FULL arm, and computes no treatment effect.

This driver deliberately runs ONE provider per invocation so that each arm
produces its own complete, non-overwriting experiment directory, and so that a
failure in one arm can never be silently retried or blended into another.

It invents no benchmark case, no treatment, and no metric.  It selects the
frozen pilot-v7-rc1 case set through the existing, already-validated
ExperimentRunner with the existing "off" treatment, and records
``experiment_kind=real_model_connectivity_smoke`` so these rows can never enter
pilot analysis: ``iqa_soa.metrics.pilot`` accepts only
``experiment_kind=real_model_pilot`` and refuses every other label at both the
manifest and the row level.  That refusal is the structural, machine-checked
non-pooling guarantee for Phase F.  scripts/run_fault_smoke.py already uses this
same label for a non-confirmatory real-model run against a frozen benchmark.

Nothing under src/iqa_soa/ is modified, and the generic PilotConfig requirement
of treatments == [off, full] is neither weakened nor bypassed: this driver does
not use load_pilot_config at all.

Automatic infrastructure retries are fixed at zero, no run is repeated, and no
adaptive or replacement run is permitted.  Every attempt stays visible.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from iqa_soa.benchmark import load_frozen_pilot  # noqa: E402
from iqa_soa.experiment.runner import (  # noqa: E402
    ExperimentConfigError,
    ExperimentRunner,
    load_experiment_config,
    load_provider,
)

# The two already-qualified Phase-C/D local providers, addressed by arm name so
# a mislabelled invocation cannot silently produce the wrong arm.
ARMS: dict[str, str] = {
    "qwen": "qwen_native_none",
    "mistral": "mistral_native_trailing_user",
}

# Arm identity is asserted from configuration, never assumed.  A mislabelled arm
# would invalidate the whole qualification.
EXPECTED_MODEL: dict[str, str] = {
    "qwen": "qwen3.5:27b",
    "mistral": "mistral-small3.2:24b",
}
EXPECTED_TOOL_CONTRACT_POLICY: dict[str, str] = {
    "qwen": "none",
    "mistral": "trailing_user",
}

BENCHMARK_VERSION = "pilot-v7-rc1"
TREATMENT = "off"
SEEDS: tuple[int, ...] = (1729, 2718, 3141)
REPETITIONS = 3
TASK_COUNT = 17
RUNS_PER_ARM = TASK_COUNT * REPETITIONS  # 51; two arms give the frozen 102 cells
PLAN_RELATIVE = "docs/phaseF_real_model_qualification_plan.md"


def _sha256_file(path: Path) -> str:
    """Hash raw working-tree bytes; never normalize (docs/hash_basis_policy.md)."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frozen_plan_digest() -> tuple[str, str]:
    """Return (recorded, actual) SHA-256 for the frozen qualification plan."""

    plan = PROJECT_ROOT / PLAN_RELATIVE
    sidecar = plan.with_suffix(".sha256")
    recorded = sidecar.read_text(encoding="utf-8").split()[0].strip()
    return recorded, _sha256_file(plan)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", required=True, choices=sorted(ARMS))
    parser.add_argument(
        "--config", default=str(PROJECT_ROOT / "configs" / "phaseF-qualification.yaml")
    )
    parser.add_argument(
        "--manifest",
        default=str(PROJECT_ROOT / "benchmark" / BENCHMARK_VERSION / "manifest.json"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    slot = ARMS[args.arm]

    # 1. The plan must be frozen and unmodified before any inference is spent.
    recorded_plan, actual_plan = _frozen_plan_digest()
    if recorded_plan != actual_plan:
        print(
            "STOP: the Phase-F qualification plan does not match its frozen "
            f"sidecar digest (recorded={recorded_plan}, actual={actual_plan})",
            file=sys.stderr,
        )
        return 2

    config = load_experiment_config(args.config)
    if config.treatments != (TREATMENT,):
        print(
            f"STOP: Phase F admits exactly one treatment {TREATMENT!r}; config "
            f"declares {list(config.treatments)}",
            file=sys.stderr,
        )
        return 2
    if tuple(config.seeds) != SEEDS:
        print(f"STOP: Phase-F seeds must be exactly {list(SEEDS)}", file=sys.stderr)
        return 2

    # 2. The benchmark must be the frozen release candidate, hash-valid.
    frozen = load_frozen_pilot(args.manifest)
    if frozen.benchmark_version != BENCHMARK_VERSION:
        print(
            f"STOP: expected {BENCHMARK_VERSION}, got {frozen.benchmark_version}",
            file=sys.stderr,
        )
        return 2
    if len(frozen.cases) != TASK_COUNT:
        print(
            f"STOP: {BENCHMARK_VERSION} must contain exactly {TASK_COUNT} tasks, "
            f"found {len(frozen.cases)}",
            file=sys.stderr,
        )
        return 2

    # 3. The arm's provider identity is asserted, never assumed.
    provider = load_provider(config.models_path, provider_name=slot)
    descriptor = provider.descriptor()
    if descriptor.get("model") != EXPECTED_MODEL[args.arm]:
        print(
            f"STOP: arm {args.arm!r} expects model {EXPECTED_MODEL[args.arm]!r} but "
            f"slot {slot!r} declares {descriptor.get('model')!r}",
            file=sys.stderr,
        )
        return 2
    policy = descriptor.get("tool_contract_policy")
    if policy != EXPECTED_TOOL_CONTRACT_POLICY[args.arm]:
        print(
            f"STOP: arm {args.arm!r} expects tool_contract_policy="
            f"{EXPECTED_TOOL_CONTRACT_POLICY[args.arm]!r} but slot {slot!r} "
            f"declares {policy!r}",
            file=sys.stderr,
        )
        return 2
    if descriptor.get("protocol") != "native_tools":
        print(f"STOP: arm {args.arm!r} must use the native_tools protocol", file=sys.stderr)
        return 2

    # 4. Credential presence is checked by NAME only.  The value is never read
    #    into a message, never printed, and never written to an artifact.
    credential_env = str(descriptor.get("api_key_env"))
    if not os.environ.get(credential_env):
        print(
            f"STOP: environment variable {credential_env!r} is unset; the local "
            "OpenAI-compatible adapter requires a credential value even when the "
            "local runtime ignores it",
            file=sys.stderr,
        )
        return 3

    print(
        f"Phase-F arm {args.arm}: slot={slot} model={descriptor.get('model')} "
        f"tool_contract_policy={policy} benchmark={frozen.benchmark_version} "
        f"manifest_sha256={frozen.manifest_sha256} treatment={TREATMENT} "
        f"tasks={TASK_COUNT} repetitions={REPETITIONS} seeds={list(SEEDS)} "
        f"runs={RUNS_PER_ARM} retries=0"
    )
    try:
        experiment_dir = ExperimentRunner(config, provider=provider).run(
            treatments=[TREATMENT],
            case_ids=None,  # the frozen manifest's full selected task set
            repetitions=REPETITIONS,
            frozen_benchmark=frozen,
            max_total_runs=RUNS_PER_ARM,
            experiment_kind="real_model_connectivity_smoke",
            infrastructure_retry_limit=0,
        )
    except ExperimentConfigError as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 2

    # 5. Fail closed if an exact configured credential value reached an artifact.
    secret = os.environ[credential_env].encode("utf-8")
    for artifact in experiment_dir.rglob("*"):
        if artifact.is_file() and secret in artifact.read_bytes():
            print(
                f"STOP: credential leak detected in artifact {artifact.name!r}",
                file=sys.stderr,
            )
            return 4

    print(f"arm={args.arm} experiment_dir={experiment_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
