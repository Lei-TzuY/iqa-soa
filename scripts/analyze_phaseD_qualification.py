#!/usr/bin/env python3
"""Verify the recorded Phase-D artifacts against the frozen qualification plan.

This is a fail-closed verifier, not a report generator.  It reads only what the
instrument already wrote (the frozen plan and its hash, the inference-free
preflight record, the run manifests, the raw rows, and the evidence fragments)
and refuses any artifact set that does not satisfy every condition fixed in
``docs/phaseD_instrument_qualification_plan.md``.

It contacts no provider, runs no model, computes no statistic, and makes no
safety or utility claim.  It introduces no new qualification criterion: every
invariant enforced here is already stated in the frozen plan (sections 4, 5, 6
and 7) and was previously only printed, or only checked by a human reading
``preflight.json``.

Exit status is part of the contract:

    PASS          -> 0
    FAIL          -> 1
    INCONCLUSIVE  -> 3

A missing, unreadable, or incomplete artifact is a FAIL, never a pass and never
a traceback.

It also emits a Phase-D-only summary CSV carrying the full post-repair telemetry
column set, because the shared runner's stable CSV subset predates the
protocol-telemetry fields and the Phase-D report must show them per run.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from iqa_soa.instrument import (  # noqa: E402
    INSTRUMENT_VERSION,
    NATIVE_TOOL_ADAPTER_VERSION,
)
from iqa_soa.metrics.definitions import PILOT_RAW_FIELDS_V3  # noqa: E402


# ---------------------------------------------------------------------------
# Frozen expectations.  Each is fixed by the qualification plan, not by this
# script; changing one here would silently change what "PASS" means, so they are
# named constants rather than inline literals.
# ---------------------------------------------------------------------------

# Plan section 4: the exact execution matrix.
EXPECTED_ARMS: dict[str, tuple[str, str]] = {
    "A": ("mistral-small3.2:24b", "none"),
    "B": ("mistral-small3.2:24b", "trailing_user"),
    "C": ("qwen3.5:27b", "none"),
}
ARM_BY_MODEL_POLICY = {value: key for key, value in EXPECTED_ARMS.items()}
EXPECTED_SEEDS: tuple[int, ...] = (1729, 2718, 3141)
RUNS_PER_ARM = 3
EXPECTED_TOTAL_RUNS = RUNS_PER_ARM * len(EXPECTED_ARMS)
EXPECTED_EXPERIMENT_DIRS = len(EXPECTED_ARMS)

# Plan sections 4 and 5: recorded execution constraints.
EXPECTED_EXPERIMENT_KIND = "real_model_connectivity_smoke"
EXPECTED_TREATMENTS: tuple[str, ...] = ("off",)
EXPECTED_RETRY_LIMIT = 0

# Plan criterion H4: provenance that identifies the actual runtime in use.
REQUIRED_PROVENANCE_FIELDS: tuple[str, ...] = (
    "runtime",
    "runtime_version",
    "model_identifier",
    "model_digest",
    "template_sha256",
    "capabilities",
)

# Plan section 3: the diagnostic chain, in order.
CHAIN = ("public/start.txt", "public/middle.txt", "public/end.txt")

# Plan criterion H3: failure classes that indicate a protocol defect.
PROTOCOL_FAILURE_CLASSES = frozenset(
    {"invalid_tool_call", "invalid_json", "invalid_action_format", "multi_call_overflow"}
)

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_INCONCLUSIVE = 3

DERIVED_FIELDS = (
    "arm",
    "experiment_id",
    "depth",
    "depth_bucket",
    "chain_completed",
    "executed_resources",
    "input_token_trajectory",
    "output_token_trajectory",
    "contract_refresh_trajectory",
    "tool_call_count_trajectory",
    "finish_reason_trajectory",
    "attempt_outcome_trajectory",
    "phase_b_signature_present",
    "post_first_action_refresh_ok",
)


class ArtifactError(Exception):
    """An artifact is missing or unreadable.  Always a FAIL, never a crash."""


@dataclass(frozen=True, slots=True)
class RunAnalysis:
    """Derived, per-run view of one recorded diagnostic run."""

    arm: str
    seed: Any
    row: dict[str, Any]
    manifest: dict[str, Any]
    depth: int
    chain_completed: bool
    executed_resources: tuple[str, ...]
    input_tokens: tuple[Any, ...]
    output_tokens: tuple[Any, ...]
    refreshes: tuple[bool, ...]
    tool_call_counts: tuple[Any, ...]
    finish_reasons: tuple[Any, ...]
    outcomes: tuple[Any, ...]
    phase_b_signature_present: bool
    post_first_action_refresh_ok: bool

    @property
    def depth_bucket(self) -> str:
        return "3+" if self.depth >= 3 else str(self.depth)


@dataclass(slots=True)
class Verification:
    """The verifier's complete, machine-readable determination."""

    verdict: str = "FAIL"
    failures: list[str] = field(default_factory=list)
    criteria: dict[str, bool] = field(default_factory=dict)
    runs: list[RunAnalysis] = field(default_factory=list)
    f1: bool = False
    f2: bool = False
    multi_call_runs: int = 0

    @property
    def exit_code(self) -> int:
        if self.verdict == "PASS":
            return EXIT_PASS
        if self.verdict == "INCONCLUSIVE":
            return EXIT_INCONCLUSIVE
        return EXIT_FAIL

    def fail(self, criterion: str, message: str) -> None:
        self.criteria[criterion] = False
        if message not in self.failures:
            self.failures.append(message)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _read_json(path: Path, what: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ArtifactError(f"{what} is missing: {path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"{what} is unreadable: {path}: {exc}") from exc


def _sha256_file(path: Path, what: str) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError as exc:
        raise ArtifactError(f"{what} is missing: {path}") from exc
    except OSError as exc:
        raise ArtifactError(f"{what} is unreadable: {path}: {exc}") from exc


def load_experiments(root: Path) -> list[tuple[Path, dict[str, Any], list[dict[str, Any]]]]:
    """Return (directory, manifest, rows) per recorded experiment directory."""

    if not root.exists():
        raise ArtifactError(f"Phase-D artifact root is missing: {root}")
    experiments: list[tuple[Path, dict[str, Any], list[dict[str, Any]]]] = []
    for manifest_path in sorted(root.rglob("manifest.json")):
        experiment_dir = manifest_path.parent
        manifest = _read_json(manifest_path, "experiment manifest")
        if not isinstance(manifest, dict):
            raise ArtifactError(f"experiment manifest is not an object: {manifest_path}")
        jsonl = experiment_dir / str(manifest.get("raw_jsonl", "runs.jsonl"))
        if not jsonl.exists():
            raise ArtifactError(f"raw rows are missing: {jsonl}")
        rows: list[dict[str, Any]] = []
        try:
            lines = jsonl.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            raise ArtifactError(f"raw rows are unreadable: {jsonl}: {exc}") from exc
        for number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ArtifactError(f"raw row {number} is invalid JSON: {jsonl}") from exc
            if not isinstance(row, dict):
                raise ArtifactError(f"raw row {number} is not an object: {jsonl}")
            rows.append(row)
        experiments.append((experiment_dir, manifest, rows))
    if not experiments:
        raise ArtifactError(f"no Phase-D experiment directories were found under {root}")
    return experiments


def _gateway_events(experiment_dir: Path, row: dict[str, Any]) -> list[dict[str, Any]]:
    """Ordered gateway observations for this run, from its evidence fragment."""

    trace_path = row.get("trace_path")
    if not isinstance(trace_path, str) or not trace_path:
        raise ArtifactError(f"run {row.get('run_id')!r} records no evidence trace path")
    trace = experiment_dir / trace_path
    if not trace.exists():
        raise ArtifactError(f"evidence fragment is missing: {trace}")
    events: list[dict[str, Any]] = []
    try:
        lines = trace.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ArtifactError(f"evidence fragment is unreadable: {trace}: {exc}") from exc
    for line in lines:
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ArtifactError(f"evidence fragment has invalid JSON: {trace}") from exc
        if not isinstance(event, dict) or event.get("event_type") == "run_terminal":
            continue
        events.append(event)
    return events


def analyze_run(
    experiment_dir: Path, manifest: dict[str, Any], row: dict[str, Any]
) -> RunAnalysis:
    attempts = row.get("provider_attempts") or []
    if not isinstance(attempts, list) or any(
        not isinstance(attempt, dict) for attempt in attempts
    ):
        raise ArtifactError(f"run {row.get('run_id')!r} has malformed provider_attempts")
    events = _gateway_events(experiment_dir, row)
    executed = tuple(
        str(event.get("resource"))
        for event in events
        if event.get("executed") and event.get("success")
    )
    depth = len(executed)

    input_tokens = tuple(attempt.get("input_tokens") for attempt in attempts)
    refreshes = tuple(bool(attempt.get("tool_contract_refreshed")) for attempt in attempts)

    # Phase-B signature (plan 6.1): a later call carries strictly fewer input
    # tokens than an earlier call in the same run, despite the history having
    # grown.  Computed from the raw trajectory, independently of the runner's
    # telemetry flag, which the plan treats as corroboration only.
    known = [value for value in input_tokens if isinstance(value, int)]
    signature = any(
        later < earlier
        for index, earlier in enumerate(known)
        for later in known[index + 1 :]
    )

    # H1 shape: the first request carries no history and must not be refreshed;
    # every later request follows at least one executed action and must be.
    first_not_refreshed = not refreshes[0] if refreshes else True
    post_first_ok = first_not_refreshed and (all(refreshes[1:]) if depth > 0 else True)

    return RunAnalysis(
        arm=ARM_BY_MODEL_POLICY.get(
            (str(row.get("model")), str(row.get("tool_contract_policy"))), "?"
        ),
        seed=row.get("seed"),
        row=row,
        manifest=manifest,
        depth=depth,
        chain_completed=executed[: len(CHAIN)] == CHAIN,
        executed_resources=executed,
        input_tokens=input_tokens,
        output_tokens=tuple(attempt.get("output_tokens") for attempt in attempts),
        refreshes=refreshes,
        tool_call_counts=tuple(attempt.get("tool_call_count") for attempt in attempts),
        finish_reasons=tuple(attempt.get("finish_reason") for attempt in attempts),
        outcomes=tuple(attempt.get("outcome") for attempt in attempts),
        phase_b_signature_present=signature,
        post_first_action_refresh_ok=post_first_ok,
    )


# ---------------------------------------------------------------------------
# Frozen-boundary checks
# ---------------------------------------------------------------------------


def check_plan_boundary(
    result: Verification, *, plan: Path, plan_sha256: Path, preflight_path: Path
) -> dict[str, Any] | None:
    """Verify the frozen plan hash, the preflight record, and criterion H4."""

    result.criteria.setdefault("plan_boundary", True)
    result.criteria.setdefault("H4", True)

    computed = _sha256_file(plan, "qualification plan")
    try:
        declared = plan_sha256.read_text(encoding="utf-8").split()[0].strip().lower()
    except FileNotFoundError as exc:
        raise ArtifactError(f"frozen plan hash file is missing: {plan_sha256}") from exc
    except (OSError, UnicodeDecodeError, IndexError) as exc:
        raise ArtifactError(f"frozen plan hash file is unreadable: {plan_sha256}") from exc
    if computed != declared:
        result.fail(
            "plan_boundary",
            "plan boundary violated: qualification plan does not match its frozen "
            f"hash (computed={computed}, frozen={declared})",
        )

    preflight = _read_json(preflight_path, "preflight record")
    if not isinstance(preflight, dict):
        raise ArtifactError(f"preflight record is not an object: {preflight_path}")

    recorded_plan_hash = preflight.get("qualification_plan_sha256")
    if not isinstance(recorded_plan_hash, str) or recorded_plan_hash.lower() != computed:
        result.fail(
            "plan_boundary",
            "plan boundary violated: preflight qualification_plan_sha256 "
            f"({recorded_plan_hash!r}) does not match the plan on disk ({computed})",
        )
    if preflight.get("inference_performed") is not False:
        result.fail(
            "plan_boundary",
            "plan boundary violated: preflight must record inference_performed=false, "
            f"got {preflight.get('inference_performed')!r}",
        )
    if preflight.get("provenance_complete") is not True:
        result.fail(
            "H4",
            "H4 violated: preflight must record provenance_complete=true, got "
            f"{preflight.get('provenance_complete')!r}",
        )
    if preflight.get("instrument_version") != INSTRUMENT_VERSION:
        result.fail(
            "plan_boundary",
            "plan boundary violated: preflight instrument_version="
            f"{preflight.get('instrument_version')!r}, expected {INSTRUMENT_VERSION!r}",
        )
    if preflight.get("native_tool_adapter_version") != NATIVE_TOOL_ADAPTER_VERSION:
        result.fail(
            "plan_boundary",
            "plan boundary violated: preflight native_tool_adapter_version="
            f"{preflight.get('native_tool_adapter_version')!r}, expected "
            f"{NATIVE_TOOL_ADAPTER_VERSION!r}",
        )

    arms = preflight.get("arms")
    if not isinstance(arms, dict):
        result.fail("H4", "H4 violated: preflight records no per-arm provenance")
        return preflight
    for arm, (model, _policy) in sorted(EXPECTED_ARMS.items()):
        entry = arms.get(arm)
        if not isinstance(entry, dict):
            result.fail("H4", f"H4 violated: preflight has no provenance for arm {arm}")
            continue
        provenance = entry.get("runtime_provenance")
        if not isinstance(provenance, dict):
            result.fail(
                "H4", f"H4 violated: arm {arm} has no runtime_provenance block"
            )
            continue
        missing = [
            name
            for name in REQUIRED_PROVENANCE_FIELDS
            if provenance.get(name) in (None, "", [], {})
        ]
        if missing:
            result.fail(
                "H4",
                f"H4 violated: arm {arm} runtime provenance is incomplete: {missing}",
            )
        if provenance.get("probe_error") is not None:
            result.fail(
                "H4",
                f"H4 violated: arm {arm} provenance probe_error="
                f"{provenance.get('probe_error')!r}",
            )
        if provenance.get("model_identifier") != model:
            result.fail(
                "H4",
                f"H4 violated: arm {arm} provenance identifies model "
                f"{provenance.get('model_identifier')!r}, expected {model!r}",
            )
    return preflight


def check_matrix(
    result: Verification,
    experiments: list[tuple[Path, dict[str, Any], list[dict[str, Any]]]],
) -> None:
    """Enforce the frozen execution matrix and the recorded manifest constraints."""

    result.criteria.setdefault("matrix", True)
    result.criteria.setdefault("manifest", True)

    if len(experiments) != EXPECTED_EXPERIMENT_DIRS:
        result.fail(
            "matrix",
            "matrix violated: expected exactly "
            f"{EXPECTED_EXPERIMENT_DIRS} experiment directories, found "
            f"{len(experiments)} (an extra or rerun directory is not permitted)",
        )

    dir_arms: list[str] = []
    for experiment_dir, manifest, rows in experiments:
        name = experiment_dir.name
        provider = manifest.get("provider")
        provider = provider if isinstance(provider, dict) else {}
        arm = ARM_BY_MODEL_POLICY.get(
            (str(provider.get("model")), str(provider.get("tool_contract_policy"))), "?"
        )
        dir_arms.append(arm)
        if arm == "?":
            result.fail(
                "matrix",
                f"matrix violated: {name} declares an unknown arm "
                f"(model={provider.get('model')!r}, "
                f"policy={provider.get('tool_contract_policy')!r})",
            )

        if manifest.get("status") != "complete":
            result.fail(
                "manifest",
                f"manifest violated: {name} status={manifest.get('status')!r}, "
                "expected 'complete'",
            )
        record_count = manifest.get("record_count")
        expected_count = manifest.get("expected_record_count")
        if record_count != RUNS_PER_ARM or expected_count != RUNS_PER_ARM:
            result.fail(
                "manifest",
                f"manifest violated: {name} record_count={record_count!r} / "
                f"expected_record_count={expected_count!r}, both must be "
                f"{RUNS_PER_ARM}",
            )
        if len(rows) != RUNS_PER_ARM:
            result.fail(
                "manifest",
                f"manifest violated: {name} contains {len(rows)} raw rows, "
                f"expected {RUNS_PER_ARM}",
            )
        if manifest.get("infrastructure_retry_limit") != EXPECTED_RETRY_LIMIT:
            result.fail(
                "manifest",
                f"manifest violated: {name} infrastructure_retry_limit="
                f"{manifest.get('infrastructure_retry_limit')!r}, expected "
                f"{EXPECTED_RETRY_LIMIT}",
            )
        if manifest.get("experiment_kind") != EXPECTED_EXPERIMENT_KIND:
            result.fail(
                "manifest",
                f"manifest violated: {name} experiment_kind="
                f"{manifest.get('experiment_kind')!r}, expected "
                f"{EXPECTED_EXPERIMENT_KIND!r}",
            )
        treatments = manifest.get("treatments")
        if list(treatments or []) != list(EXPECTED_TREATMENTS):
            result.fail(
                "manifest",
                f"manifest violated: {name} treatments={treatments!r}, expected "
                f"{list(EXPECTED_TREATMENTS)!r}",
            )

    known_dir_arms = [arm for arm in dir_arms if arm != "?"]
    if len(set(known_dir_arms)) != len(known_dir_arms):
        result.fail(
            "matrix",
            "matrix violated: two experiment directories declare the same arm "
            "(a rerun of an arm is not permitted)",
        )

    total = len(result.runs)
    if total != EXPECTED_TOTAL_RUNS:
        result.fail(
            "matrix",
            f"matrix violated: expected exactly {EXPECTED_TOTAL_RUNS} recorded runs, "
            f"found {total}",
        )

    run_ids = [run.row.get("run_id") for run in result.runs]
    if len(set(run_ids)) != len(run_ids):
        result.fail("matrix", "matrix violated: duplicate run_id in the artifact set")

    by_arm: dict[str, list[RunAnalysis]] = {}
    for run in result.runs:
        by_arm.setdefault(run.arm, []).append(run)

    unknown = sorted(set(by_arm) - set(EXPECTED_ARMS))
    if unknown:
        result.fail(
            "matrix",
            f"matrix violated: unknown arm(s) present in recorded runs: {unknown}",
        )

    for arm, (model, policy) in sorted(EXPECTED_ARMS.items()):
        runs = by_arm.get(arm, [])
        if len(runs) != RUNS_PER_ARM:
            result.fail(
                "matrix",
                f"matrix violated: arm {arm} has {len(runs)} runs, expected "
                f"{RUNS_PER_ARM}",
            )
        seeds = sorted(run.seed for run in runs if isinstance(run.seed, int))
        if seeds != sorted(EXPECTED_SEEDS):
            result.fail(
                "matrix",
                f"matrix violated: arm {arm} seeds are {seeds}, expected exactly "
                f"{sorted(EXPECTED_SEEDS)} once each",
            )
        for run in runs:
            if str(run.row.get("model")) != model:
                result.fail(
                    "matrix",
                    f"matrix violated: arm {arm} run seed={run.seed} records model "
                    f"{run.row.get('model')!r}, expected {model!r}",
                )
            if str(run.row.get("tool_contract_policy")) != policy:
                result.fail(
                    "matrix",
                    f"matrix violated: arm {arm} run seed={run.seed} records "
                    f"tool_contract_policy {run.row.get('tool_contract_policy')!r}, "
                    f"expected {policy!r}",
                )


def check_run_criteria(result: Verification) -> None:
    """Enforce plan criteria H1, H2, H3, H5 and the byte-identical-input rule."""

    for criterion in ("H1", "H2", "H3", "H5", "input_identity"):
        result.criteria.setdefault(criterion, True)

    for run in result.runs:
        row = run.row
        label = f"arm {run.arm} seed={run.seed}"

        # H1: the repaired arm re-exposes the contract after the first action.
        if run.arm == "B" and not run.post_first_action_refresh_ok:
            result.fail(
                "H1",
                f"H1 violated: {label} refresh trajectory {list(run.refreshes)}",
            )

        # H2: unrepaired arms are never perturbed.
        if run.arm in {"A", "C"} and any(run.refreshes):
            result.fail(
                "H2", f"H2 violated: {label} recorded a tool-contract refresh"
            )

        # H3: no protocol-class failure, no unclassified failure, no lost proposal.
        failure_class = row.get("failure_class")
        if failure_class in PROTOCOL_FAILURE_CLASSES:
            result.fail(
                "H3", f"H3 violated: {label} failure_class={failure_class!r}"
            )
        if row.get("error") and not failure_class:
            result.fail("H3", f"H3 violated: {label} recorded an unclassified failure")
        if row.get("multi_call_overflow"):
            result.fail("H3", f"H3 violated: {label} reported multi-call overflow")
        if row.get("queued_action_count"):
            result.fail(
                "H3",
                f"H3 violated: {label} left {row.get('queued_action_count')!r} "
                "queued action(s) unaccounted for",
            )

        # H5: instrument identity on every row and every manifest.
        if row.get("instrument_version") != INSTRUMENT_VERSION:
            result.fail(
                "H5",
                f"H5 violated: {label} row instrument_version="
                f"{row.get('instrument_version')!r}",
            )
        if row.get("native_tool_adapter_version") != NATIVE_TOOL_ADAPTER_VERSION:
            result.fail(
                "H5",
                f"H5 violated: {label} row native_tool_adapter_version="
                f"{row.get('native_tool_adapter_version')!r}",
            )
        if run.manifest.get("instrument_version") != INSTRUMENT_VERSION:
            result.fail(
                "H5",
                "H5 violated: manifest instrument_version="
                f"{run.manifest.get('instrument_version')!r}",
            )
        if run.manifest.get("native_tool_adapter_version") != NATIVE_TOOL_ADAPTER_VERSION:
            result.fail(
                "H5",
                "H5 violated: manifest native_tool_adapter_version="
                f"{run.manifest.get('native_tool_adapter_version')!r}",
            )

    # Plan section 3: the diagnostic must be byte-identical across arms.
    prompts = {
        (run.row.get("system_prompt_sha256"), run.row.get("user_prompt_sha256"))
        for run in result.runs
    }
    states = {run.row.get("initial_state_fingerprint") for run in result.runs}
    if len(prompts) != 1 or len(states) != 1:
        result.fail(
            "input_identity",
            "diagnostic input was not byte-identical across arms: "
            f"{len(prompts)} distinct prompt digest pair(s), "
            f"{len(states)} distinct initial state(s)",
        )


def verify(
    *, root: Path, plan: Path, plan_sha256: Path, preflight: Path
) -> Verification:
    """Return the complete determination for one recorded Phase-D artifact set."""

    result = Verification()
    try:
        check_plan_boundary(
            result, plan=plan, plan_sha256=plan_sha256, preflight_path=preflight
        )
        experiments = load_experiments(root)
        for experiment_dir, manifest, rows in experiments:
            for row in rows:
                result.runs.append(analyze_run(experiment_dir, manifest, row))
        check_matrix(result, experiments)
        check_run_criteria(result)
    except ArtifactError as exc:
        result.fail("artifacts", f"artifact error: {exc}")
        result.verdict = "FAIL"
        return result

    by_arm: dict[str, list[RunAnalysis]] = {}
    for run in result.runs:
        by_arm.setdefault(run.arm, []).append(run)
    result.f1 = any(run.depth >= len(CHAIN) for run in by_arm.get("B", []))
    result.f2 = any(run.depth >= len(CHAIN) for run in by_arm.get("C", []))
    result.multi_call_runs = sum(
        1 for run in result.runs if run.row.get("provider_multi_tool_call")
    )

    if result.failures:
        result.verdict = "FAIL"
    elif result.f1 and result.f2:
        result.verdict = "PASS"
    else:
        result.verdict = "INCONCLUSIVE"
    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def write_summary_csv(result: Verification, out_path: Path) -> None:
    fieldnames = list(DERIVED_FIELDS) + [
        name for name in PILOT_RAW_FIELDS_V3 if name not in DERIVED_FIELDS
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for run in sorted(result.runs, key=lambda item: (item.arm, item.seed or 0)):
            merged: dict[str, Any] = {
                key: value for key, value in run.row.items() if not key.startswith("_")
            }
            merged.update(
                {
                    "arm": run.arm,
                    "depth": run.depth,
                    "depth_bucket": run.depth_bucket,
                    "chain_completed": run.chain_completed,
                    # Kept as a joined string, byte-identical to the recorded
                    # summary, so regenerating it can never rewrite evidence.
                    "executed_resources": " -> ".join(run.executed_resources)
                    or "(none)",
                    "input_token_trajectory": list(run.input_tokens),
                    "output_token_trajectory": list(run.output_tokens),
                    "contract_refresh_trajectory": list(run.refreshes),
                    "tool_call_count_trajectory": list(run.tool_call_counts),
                    "finish_reason_trajectory": list(run.finish_reasons),
                    "attempt_outcome_trajectory": list(run.outcomes),
                    "phase_b_signature_present": run.phase_b_signature_present,
                    "post_first_action_refresh_ok": run.post_first_action_refresh_ok,
                }
            )
            writer.writerow(
                {
                    key: (
                        json.dumps(merged.get(key), ensure_ascii=False)
                        if isinstance(merged.get(key), (list, dict))
                        else merged.get(key)
                    )
                    for key in fieldnames
                }
            )


def print_report(result: Verification) -> None:
    print(f"Phase-D runs recorded: {len(result.runs)}")
    by_arm: dict[str, list[RunAnalysis]] = {}
    for run in result.runs:
        by_arm.setdefault(run.arm, []).append(run)
    for arm in sorted(by_arm):
        print(f"  arm {arm}: {len(by_arm[arm])} runs")

    if result.runs:
        print("\n--- per-run ---")
    for run in sorted(result.runs, key=lambda item: (item.arm, item.seed or 0)):
        row = run.row
        print(
            f"arm={run.arm} seed={run.seed} model={row.get('model')} "
            f"policy={row.get('tool_contract_policy')} depth={run.depth_bucket} "
            f"chain={run.chain_completed} model_calls={row.get('model_calls')} "
            f"tool_calls={row.get('tool_calls')} "
            f"failure_class={row.get('failure_class')} "
            f"terminal_no_action={row.get('terminal_no_action')} "
            f"multi_tool={row.get('provider_multi_tool_call')} "
            f"max_tool_calls={row.get('provider_max_tool_calls')} "
            f"overflow={row.get('multi_call_overflow')} "
            f"regression_flag={row.get('tool_contract_regression_detected')}"
        )
        print(f"    executed: {' -> '.join(run.executed_resources) or '(none)'}")
        print(f"    input_tokens:   {list(run.input_tokens)}")
        print(f"    refreshed:      {list(run.refreshes)}")
        print(f"    tool_calls:     {list(run.tool_call_counts)}")
        print(f"    finish_reason:  {list(run.finish_reasons)}")
        print(f"    outcomes:       {list(run.outcomes)}")
        print(f"    phase_b_signature_present: {run.phase_b_signature_present}")

    def status(name: str) -> str:
        # A criterion that never ran must never read as PASS: an artifact error
        # short-circuits later checks, and printing PASS for them would be the
        # same fail-open behaviour this verifier exists to remove.
        if name not in result.criteria:
            return "NOT EVALUATED"
        return "PASS" if result.criteria[name] else "FAIL"

    if result.criteria.get("artifacts") is False:
        print("\nartifact set could not be read; later criteria were not evaluated")

    print("\n--- frozen criteria (all machine-enforced) ---")
    print(f"matrix (exactly 9 runs, 3 per arm, frozen seeds): {status('matrix')}")
    print(f"manifests (complete/3 rows/0 retries/kind/arm):   {status('manifest')}")
    print(f"plan boundary (hash, preflight, no inference):    {status('plan_boundary')}")
    print(f"H1 (arm B refreshes post-first-action):           {status('H1')}")
    print(f"H2 (arms A/C never refreshed):                    {status('H2')}")
    print(f"H3 (no protocol-class failure):                   {status('H3')}")
    print(f"H4 (runtime provenance identifies environment):   {status('H4')}")
    print(f"H5 (instrument identity on artifacts):            {status('H5')}")
    print(f"byte-identical diagnostic input across arms:      {status('input_identity')}")
    print(f"F1 (an arm-B run reached depth 3):                {'PASS' if result.f1 else 'NOT MET'}")
    print(f"F2 (an arm-C run reached depth 3):                {'PASS' if result.f2 else 'NOT MET'}")
    print(
        "multi-call turns naturally emitted:               "
        + (
            str(result.multi_call_runs)
            if result.multi_call_runs
            else "none (not naturally exercised in Phase D)"
        )
    )

    if result.failures:
        print("\nVIOLATIONS:")
        for item in result.failures:
            print(f"  - {item}")

    print(f"\nQUALIFICATION VERDICT: {result.verdict} (exit {result.exit_code})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    phase_d = PROJECT_ROOT / "results" / "phaseD-qualification"
    docs = PROJECT_ROOT / "docs"
    parser.add_argument("--root", default=str(phase_d / "raw"))
    parser.add_argument("--preflight", default=str(phase_d / "preflight.json"))
    parser.add_argument(
        "--plan", default=str(docs / "phaseD_instrument_qualification_plan.md")
    )
    parser.add_argument(
        "--plan-sha256",
        default=str(docs / "phaseD_instrument_qualification_plan.sha256"),
    )
    # Verification is read-only by default: writing a summary is opt-in, so a
    # verification run can never rewrite recorded Phase-D evidence.
    parser.add_argument("--out", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = verify(
        root=Path(args.root),
        plan=Path(args.plan),
        plan_sha256=Path(args.plan_sha256),
        preflight=Path(args.preflight),
    )
    print_report(result)
    if result.runs and args.out:
        write_summary_csv(result, Path(args.out))
        print(f"\nwrote {args.out}")
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
