#!/usr/bin/env python3
"""Run exactly one Phase-I QA-OFF requalification arm (17 tasks x 3 seeds) per invocation.

Phase I is an ENGINEERING BENCHMARK REQUALIFICATION, not an experiment.  Its
only question is whether pilot-v7-rc2's intended safe paths, challenge routes,
multi-step causal prerequisites, resource modality, benign controls, deliberate
negative control and fault opportunity are actually REACHABLE under the two
qualified local real-model providers with QA OFF.  It estimates no QA
effectiveness, runs no FULL arm, and computes no treatment effect.

This driver deliberately runs ONE provider per invocation so that each arm
produces its own complete, non-overwriting experiment directory, and so that a
failure in one arm can never be silently retried or blended into another.

It invents no benchmark case, no treatment, and no metric.  It selects the
frozen pilot-v7-rc2 case set through the existing, already-validated
ExperimentRunner with the existing "off" treatment, and records
``experiment_kind=real_model_connectivity_smoke`` so these rows can never enter
pilot analysis: ``iqa_soa.metrics.pilot`` accepts only
``experiment_kind=real_model_pilot`` and refuses every other label at both the
manifest and the row level.  That refusal is the structural, machine-checked
non-pooling guarantee for Phase I, exactly as it was for Phase F.

Nothing under src/iqa_soa/ is modified, and the generic PilotConfig requirement
of treatments == [off, full] is neither weakened nor bypassed: this driver does
not use load_pilot_config at all.

Automatic infrastructure retries are fixed at zero, no run is repeated, and no
adaptive or replacement run is permitted.  Every attempt stays visible: a
provider failure remains a provider failure and a failed cell stays failed.

Before spending any inference this driver asserts, and refuses to run on any
mismatch:

* the frozen Phase-I plan matches its recorded SHA-256 sidecar;
* the experiment config admits exactly QA OFF and exactly the three frozen seeds;
* the benchmark is pilot-v7-rc2 with exactly its 17 hash-pinned tasks;
* the arm's model identity and tool-contract policy are the qualified values;
* the LIVE Ollama model digest for this arm equals the digest Phase F recorded,
  so the phase cannot silently run against a re-pulled or retagged model;
* the LIVE Ollama runtime version equals the version Phase F recorded.

The digest and runtime assertions are ENVIRONMENT_HOLD conditions.  This driver
never pulls, updates, retags or replaces a model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

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

# The two already-qualified Phase-C/D/F local providers, addressed by arm name
# so a mislabelled invocation cannot silently produce the wrong arm.
ARMS: dict[str, str] = {
    "qwen": "qwen_native_none",
    "mistral": "mistral_native_trailing_user",
}

# Arm identity is asserted from configuration, never assumed.  A mislabelled arm
# would invalidate the whole requalification.
EXPECTED_MODEL: dict[str, str] = {
    "qwen": "qwen3.5:27b",
    "mistral": "mistral-small3.2:24b",
}
EXPECTED_TOOL_CONTRACT_POLICY: dict[str, str] = {
    "qwen": "none",
    "mistral": "trailing_user",
}

# Reproducibility pins, transcribed from
# results/phaseF-qualification/phaseF-provenance.json.  A difference in either is
# an ENVIRONMENT_HOLD, never something this phase repairs.
EXPECTED_MODEL_DIGEST: dict[str, str] = {
    "qwen3.5:27b": "7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e",
    "mistral-small3.2:24b": "5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b",
}
EXPECTED_RUNTIME_VERSION = "0.32.13"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"

BENCHMARK_VERSION = "pilot-v7-rc2"
TREATMENT = "off"
SEEDS: tuple[int, ...] = (1729, 2718, 3141)
REPETITIONS = 3
TASK_COUNT = 17
RUNS_PER_ARM = TASK_COUNT * REPETITIONS  # 51; two arms give the frozen 102 cells
PLAN_RELATIVE = "docs/phaseI_rc2_real_model_requalification_plan.md"


def _sha256_file(path: Path) -> str:
    """Hash raw working-tree bytes; never normalize (docs/hash_basis_policy.md)."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frozen_plan_digest() -> tuple[str, str]:
    """Return (recorded, actual) SHA-256 for the frozen requalification plan."""

    plan = PROJECT_ROOT / PLAN_RELATIVE
    sidecar = plan.with_suffix(".sha256")
    recorded = sidecar.read_text(encoding="utf-8").split()[0].strip()
    return recorded, _sha256_file(plan)


def _ollama_get(path: str, timeout: float = 30.0) -> dict[str, object]:
    request = urllib.request.Request(f"{OLLAMA_BASE_URL}{path}", method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"unexpected payload from {path}")
    return payload


def probe_environment(model: str) -> tuple[str, str]:
    """Return (runtime_version, model_digest) from the live local runtime."""

    version = str(_ollama_get("/api/version").get("version") or "")
    tags = _ollama_get("/api/tags")
    entries = tags.get("models")
    digest = ""
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and entry.get("name") == model:
                digest = str(entry.get("digest") or "")
                break
    return version, digest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", required=True, choices=sorted(ARMS))
    parser.add_argument(
        "--config", default=str(PROJECT_ROOT / "configs" / "phaseI-qualification.yaml")
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
            "STOP: the Phase-I requalification plan does not match its frozen "
            f"sidecar digest (recorded={recorded_plan}, actual={actual_plan})",
            file=sys.stderr,
        )
        return 2

    config = load_experiment_config(args.config)
    if config.treatments != (TREATMENT,):
        print(
            f"STOP: Phase I admits exactly one treatment {TREATMENT!r}; config "
            f"declares {list(config.treatments)}",
            file=sys.stderr,
        )
        return 2
    if tuple(config.seeds) != SEEDS:
        print(f"STOP: Phase-I seeds must be exactly {list(SEEDS)}", file=sys.stderr)
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
    model = str(descriptor.get("model"))
    if model != EXPECTED_MODEL[args.arm]:
        print(
            f"STOP: arm {args.arm!r} expects model {EXPECTED_MODEL[args.arm]!r} but "
            f"slot {slot!r} declares {model!r}",
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
        print(
            f"STOP: arm {args.arm!r} must use the native_tools protocol", file=sys.stderr
        )
        return 2

    # 4. ENVIRONMENT_HOLD gate: the live runtime must be the model Phase F
    #    recorded.  Never repaired here, never pulled, never retagged.
    try:
        runtime_version, model_digest = probe_environment(model)
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ENVIRONMENT_HOLD: cannot probe the local runtime: {exc}", file=sys.stderr)
        return 5
    if model_digest != EXPECTED_MODEL_DIGEST[model]:
        print(
            f"ENVIRONMENT_HOLD: model {model!r} digest is {model_digest!r} but Phase F "
            f"recorded {EXPECTED_MODEL_DIGEST[model]!r}; Phase I does not pull, "
            "update, retag or replace a model",
            file=sys.stderr,
        )
        return 5
    if runtime_version != EXPECTED_RUNTIME_VERSION:
        print(
            f"ENVIRONMENT_HOLD: Ollama runtime version is {runtime_version!r} but "
            f"Phase F recorded {EXPECTED_RUNTIME_VERSION!r}; the committed "
            "experiment architecture does not permit unreviewed runtime drift",
            file=sys.stderr,
        )
        return 5

    # 5. Credential presence is checked by NAME only.  The value is never read
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
        f"Phase-I arm {args.arm}: slot={slot} model={model} "
        f"tool_contract_policy={policy} digest={model_digest} "
        f"runtime=ollama/{runtime_version} benchmark={frozen.benchmark_version} "
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

    # 6. Fail closed if an exact configured credential value reached an artifact.
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
