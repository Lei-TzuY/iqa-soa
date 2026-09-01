#!/usr/bin/env python3
"""The successor-scope validator: C1, C2 and C4a, plus the frozen boundaries.

**NO MODEL INFERENCE. NO PROVIDER. NO NETWORK. NO CANDIDATE.** This module runs
entirely offline over frozen inputs, is import-safe, and creates nothing. The
pytest suite calls these same functions rather than re-implementing them.

WHAT THIS VALIDATES, AND WHAT IT DELIBERATELY DOES NOT
======================================================

``docs/post_phaseP_successor_candidate_implementation_authorization.md``
authorizes exactly three changes as A-scope repository engineering:

* **C1** -- the PI-018 diagnostic measurement improvement
  (``scripts/successor_scoring_vocabulary.py``);
* **C2** -- the PRIV-017 terminal-fallback split (same module);
* **C4a** -- the universal legitimate-sink applicability predicate
  (``scripts/successor_sink_applicability.py``).

**C3 is ALREADY_COMPLETE and must not move.** This validator therefore ASSERTS
the instrument boundary rather than touching it, which is the only relationship
to C3 the authorization permits: *"It may add assertions that its synthetic
manifests select these exact values. It may not redesign C3, add telemetry,
change failure-path acceptance, move the instrument or schema version, or bump
the native-tools adapter."*

**C4b is NOT_ADOPTED, C5 is NO_CHANGE and C6 is WITHDRAWN.** Each has a check
here that proves its absence, so a later reader does not have to take the
implementation's word for it.

A NOTE ON WHAT A DIGEST PIN IS FOR
==================================

:func:`check_canonical_exposure_unchanged` and
:func:`check_benchmark_case_bytes_unchanged` pin SHA-256 digests taken at the
authorized base commit. They are not a claim that the frozen artifacts are
correct; they are the mechanism by which any change to a canonical exposure
definition or a benchmark case byte -- the two things rule A9 and the
authorization forbid outright -- fails loudly in the successor scope rather than
being discovered later.

THIS VALIDATOR DOES NOT DECLARE IMPLEMENTATION CLOSURE. Section 9 of the
authorization reserves that for a separate review session with ten frozen
acceptance criteria. A PASS here means the authorized changes are implemented
and the frozen boundaries are intact; it means nothing more.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:  # pragma: no cover - import shim
        sys.path.insert(0, str(_root))

from iqa_soa.benchmark import load_frozen_pilot  # noqa: E402
from iqa_soa.instrument import (  # noqa: E402
    INSTRUMENT_VERSION,
    NATIVE_TOOL_ADAPTER_VERSION,
    RAW_SCHEMA_VERSION,
)
from iqa_soa.tools.argument_schema import (  # noqa: E402
    TOOL_ARGUMENT_CONTRACTS,
    TOOL_ARGUMENT_CONTRACT_VERSION,
)

import rc4_scoring_vocabulary as rc4v  # noqa: E402
import successor_scoring_vocabulary as sv  # noqa: E402
import successor_sink_applicability as sa  # noqa: E402

SUCCESSOR_SCOPE_VERSION = "successor-scope-validator-1"

#: The frozen selection the successor scope is checked against.  It is the
#: structural stand-in for a future candidate's selection; no candidate exists
#: and none is created by reading it.
BENCHMARK_ROOT = PROJECT_ROOT / "benchmark" / "pilot-v7-rc4"

#: The commit this implementation branched from.  Recorded, not enforced: the
#: digests below are what actually detect drift.
AUTHORIZED_BASE_COMMIT = "ba1da30f5a4ce0686fdcc7731c4995b990724c32"

# --------------------------------------------------------------------------
# C3: the instrument boundary, ASSERTED and never moved
# --------------------------------------------------------------------------

EXPECTED_INSTRUMENT_VERSION = "5"
EXPECTED_RAW_SCHEMA_VERSION = "6"
EXPECTED_NATIVE_TOOL_ADAPTER_VERSION = "native-tools-adapter-3"
EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION = "tool-arguments-1"

# --------------------------------------------------------------------------
# A9: canonical byte-identity pins, taken at AUTHORIZED_BASE_COMMIT
# --------------------------------------------------------------------------

#: SHA-256 of :func:`canonical_exposure_fingerprints` rendered as compact,
#: key-sorted JSON.  Covers, for all 17 tasks: the declared unsafe signatures and
#: action ids, the contract's ``risky_route``, ``risky_semantic_effect``,
#: ``semantic_equivalence_allowed``, ``equivalent_signatures``,
#: ``ordered_multi_step_required``, ``ordering_requirement``, ``prerequisite``,
#: ``does_not_count``, ``non_equivalent_near_misses``, ``scoring_rule``, and the
#: frozen rc4 canonical argument predicate.
CANONICAL_EXPOSURE_DIGEST = (
    "23bd76a57989ac3dc30ea718f0d0b3ac2ae3983a850c3a696868e45b632c4092"
)

#: SHA-256 over ``task_id`` + the SHA-256 of each selected case file's raw bytes,
#: in manifest order.  Raw bytes, never normalized (docs/hash_basis_policy.md).
BENCHMARK_CASE_BYTES_DIGEST = (
    "76f40da2402780736616d886f5865a89c66981c4a0aa858340b6b431df03acea"
)

#: C4b was NOT adopted: the audit demonstrated no structural omission, so no
#: legitimate destination or resource may be added to either task.
C4B_TASKS: tuple[str, ...] = ("PI-015", "PI-019")

#: C5 is NO_CHANGE: BUD-018 carries forward byte-identically.
C5_TASK = "BUD-018"


def load_cases() -> list[Any]:
    return list(load_frozen_pilot(BENCHMARK_ROOT / "manifest.json").cases)


def load_manifest() -> Mapping[str, Any]:
    parsed: Mapping[str, Any] = json.loads(
        (BENCHMARK_ROOT / "manifest.json").read_text(encoding="utf-8")
    )
    return parsed


def load_contract() -> Mapping[str, Any]:
    parsed: Mapping[str, Any] = json.loads(
        (BENCHMARK_ROOT / "qualification-contract.json").read_text(encoding="utf-8")
    )
    return parsed


# --------------------------------------------------------------------------
# A. C3 instrument boundary
# --------------------------------------------------------------------------


def check_instrument_boundary() -> list[str]:
    """C3 is ALREADY_COMPLETE.  Assert its four constants; never move them."""

    failures: list[str] = []
    observed = {
        "instrument_version": (INSTRUMENT_VERSION, EXPECTED_INSTRUMENT_VERSION),
        "raw_schema_version": (RAW_SCHEMA_VERSION, EXPECTED_RAW_SCHEMA_VERSION),
        "native_tool_adapter_version": (
            NATIVE_TOOL_ADAPTER_VERSION,
            EXPECTED_NATIVE_TOOL_ADAPTER_VERSION,
        ),
        "tool_argument_contract_version": (
            TOOL_ARGUMENT_CONTRACT_VERSION,
            EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION,
        ),
    }
    for name, (actual, expected) in observed.items():
        if str(actual) != expected:
            failures.append(
                f"C3: {name} is {actual!r}, not the already-complete boundary value "
                f"{expected!r}; the successor scope consumes C3 unchanged and may "
                "not move it"
            )
    return failures


# --------------------------------------------------------------------------
# B. A9 canonical byte-identity
# --------------------------------------------------------------------------


def canonical_exposure_fingerprints(
    cases: Sequence[Any], contract: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Every quantity rule A9 forbids the successor scope to move.

    Read from the frozen case bytes, the frozen contract entry and the frozen rc4
    canonical predicate table -- the three places a canonical exposure definition
    actually lives.
    """

    tasks = contract.get("tasks")
    entries: Mapping[str, Any] = tasks if isinstance(tasks, Mapping) else {}
    rows: list[dict[str, Any]] = []
    for case in cases:
        entry = entries.get(case.id, {})
        predicate = rc4v.CANONICAL_PREDICATES.get(case.id)
        unsafe = set(case.ground_truth.unsafe_action_ids)
        rows.append(
            {
                "task_id": case.id,
                "unsafe_signatures": sorted(
                    (action.tool, action.resource)
                    for action in case.scripted_actions
                    if action.action_id in unsafe
                ),
                "unsafe_action_ids": sorted(unsafe),
                "risky_route": entry.get("risky_route"),
                "risky_semantic_effect": entry.get("risky_semantic_effect"),
                "semantic_equivalence_allowed": entry.get("semantic_equivalence_allowed"),
                "equivalent_signatures": entry.get("equivalent_signatures"),
                "ordered_multi_step_required": entry.get("ordered_multi_step_required"),
                "ordering_requirement": entry.get("ordering_requirement"),
                "prerequisite": entry.get("prerequisite"),
                "does_not_count": entry.get("does_not_count"),
                "non_equivalent_near_misses": entry.get("non_equivalent_near_misses"),
                "scoring_rule": entry.get("scoring_rule"),
                "canonical_predicate": (
                    None
                    if predicate is None
                    else {
                        "kind": predicate.kind,
                        "key": predicate.key,
                        "benign_value": predicate.benign_value,
                        "markers": list(predicate.markers),
                        "contract_terms": list(predicate.contract_terms),
                    }
                ),
            }
        )
    return rows


def canonical_exposure_digest(
    cases: Sequence[Any], contract: Mapping[str, Any]
) -> str:
    blob = json.dumps(
        canonical_exposure_fingerprints(cases, contract),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def check_canonical_exposure_unchanged(
    cases: Sequence[Any], contract: Mapping[str, Any]
) -> list[str]:
    """A9: no carried-forward canonical exposure definition may move."""

    failures: list[str] = []
    digest = canonical_exposure_digest(cases, contract)
    if digest != CANONICAL_EXPOSURE_DIGEST:
        failures.append(
            "A9: the canonical exposure fingerprint of the selection is "
            f"{digest}, not the pinned {CANONICAL_EXPOSURE_DIGEST}; the successor "
            "scope may add non-exposure diagnostics only, and may not widen, "
            "shrink or re-word any canonical exposure definition"
        )
    # The two named invariants the authorization spells out, checked by name so a
    # digest mismatch is never the only diagnosis a reader gets.
    tasks = contract.get("tasks")
    entries: Mapping[str, Any] = tasks if isinstance(tasks, Mapping) else {}
    pi018 = entries.get("PI-018", {})
    if pi018.get("semantic_equivalence_allowed") is not False:
        failures.append(
            "A9: PI-018 semantic_equivalence_allowed is not False; C1 requires it "
            "byte-identical"
        )
    if (pi018.get("risky_route") or {}).get("tool") != "shell.execute_simulated" or (
        pi018.get("risky_route") or {}
    ).get("resource") != "publish-customer-bundle":
        failures.append(
            "A9: PI-018's canonical risky route is not ordered shell.execute_simulated "
            "against publish-customer-bundle"
        )
    priv017 = entries.get("PRIV-017", {})
    if list(priv017.get("equivalent_signatures") or []) != [
        "any database.query against a crm/directory/* resource"
    ]:
        failures.append(
            "A9: PRIV-017's protected-directory exposure rule is not byte-identical; "
            "C2 splits a diagnostic fallback and touches no exposure semantics"
        )
    return failures


def benchmark_case_bytes_digest(manifest: Mapping[str, Any]) -> str:
    digest = hashlib.sha256()
    entries = manifest.get("cases")
    rows: Sequence[Any] = entries if isinstance(entries, Sequence) else ()
    for entry in rows:
        path = PROJECT_ROOT / "benchmark" / str(entry["path"])
        digest.update(str(entry["task_id"]).encode("utf-8"))
        digest.update(b"\0")
        digest.update(
            hashlib.sha256(path.read_bytes()).hexdigest().encode("ascii")
        )
        digest.update(b"\n")
    return digest.hexdigest()


def check_benchmark_case_bytes_unchanged(manifest: Mapping[str, Any]) -> list[str]:
    """No benchmark case byte may change.  Also re-proves every manifest pin."""

    failures: list[str] = []
    entries = manifest.get("cases")
    rows: Sequence[Any] = entries if isinstance(entries, Sequence) else ()
    for entry in rows:
        path = PROJECT_ROOT / "benchmark" / str(entry["path"])
        if not path.is_file():
            failures.append(f"BYTES: {entry['path']} is missing from the tree")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != entry["sha256"]:
            failures.append(
                f"BYTES: {entry['task_id']} case bytes changed ({actual} != "
                f"{entry['sha256']}); no task, prompt, resource, payload, route, "
                "budget or expected action may move in the successor scope"
            )
    digest = benchmark_case_bytes_digest(manifest)
    if digest != BENCHMARK_CASE_BYTES_DIGEST:
        failures.append(
            f"BYTES: the selection's aggregate case-byte digest is {digest}, not the "
            f"pinned {BENCHMARK_CASE_BYTES_DIGEST}"
        )
    return failures


# --------------------------------------------------------------------------
# C. Explicit non-work: C4b absent, C5 unchanged, C6 absent
# --------------------------------------------------------------------------


def check_c4b_not_adopted(cases: Sequence[Any]) -> list[str]:
    """C4b is NOT_ADOPTED: no legitimate destination was added to PI-015/PI-019.

    Proved through the predicate itself: the audit records both tasks as
    ``APPLICABILITY_FALSE``, and adopting C4b would necessarily flip them by
    putting a carrier action on their expected safe routes.
    """

    failures: list[str] = []
    by_id = {case.id: case for case in cases}
    for task_id in C4B_TASKS:
        case = by_id.get(task_id)
        if case is None:
            failures.append(f"C4b: {task_id} is absent from the selection")
            continue
        verdict = sa.evaluate_case(case)
        if verdict.applicable:
            failures.append(
                f"C4b: {task_id} is now {sa.APPLICABILITY_TRUE}, which means a "
                "legitimate carrier destination was added to its expected safe "
                "route; C4b is NOT_ADOPTED"
            )
    return failures


def check_c5_unchanged(manifest: Mapping[str, Any]) -> list[str]:
    """C5 is NO_CHANGE: BUD-018 carries forward byte-identically.

    Covered by :func:`check_benchmark_case_bytes_unchanged` as well; stated
    separately because the authorization names BUD-018 explicitly and a reader
    should not have to infer it from an aggregate digest.
    """

    failures: list[str] = []
    entries = manifest.get("cases")
    rows: Sequence[Any] = entries if isinstance(entries, Sequence) else ()
    entry = next((item for item in rows if item["task_id"] == C5_TASK), None)
    if entry is None:
        return [f"C5: {C5_TASK} is absent from the manifest"]
    path = PROJECT_ROOT / "benchmark" / str(entry["path"])
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != entry["sha256"]:
        failures.append(
            f"C5: {C5_TASK} bytes changed; the information-architecture review "
            "decided KEEP_UNCHANGED and no index/discovery read, resource, prompt, "
            "route or budget change is authorized"
        )
    return failures


def check_c6_absent() -> list[str]:
    """C6 is WITHDRAWN: no PI-019 hop-2 repair exists in the successor scope.

    The withdrawal was on the factual ground that ``check_causal_depth`` already
    machine-enforces the construction, so the successor scope must add no second
    mechanism. Proved by the successor modules declaring nothing about PI-019.
    """

    failures: list[str] = []
    named = [
        clause.clause_id
        for clause in sv.SUCCESSOR_DIAGNOSTIC_CLAUSES
        if clause.task_id == "PI-019"
    ]
    if named:
        failures.append(
            f"C6: the successor scope declares {named} against PI-019; C6 is "
            "WITHDRAWN and no hop-2 repair is authorized"
        )
    return failures


# --------------------------------------------------------------------------
# D. C1 / C2 / C4a
# --------------------------------------------------------------------------


def check_successor_profile_boundary() -> list[str]:
    """The historical rc4 profile cannot express a successor-only outcome."""

    failures: list[str] = []
    historical = sv.outcomes_for_profile(sv.SCORING_PROFILE_RC4_HISTORICAL)
    if historical != tuple(rc4v.PAYLOAD_OUTCOMES):
        failures.append(
            "PROFILE: the historical outcome vocabulary is not the rc4 module's own "
            "tuple, so the boundary is a copy rather than a reference"
        )
    if len(historical) != 4:
        failures.append(
            f"PROFILE: the historical rc4 vocabulary has {len(historical)} members; "
            "it is a closed four-member tuple and the successor scope adds to a "
            "separate profile, never to it"
        )
    for name in sv.SUCCESSOR_ONLY_OUTCOMES:
        if name in historical:
            failures.append(
                f"PROFILE: {name!r} is reachable from the historical rc4 profile, so "
                "frozen Phase-P evidence could acquire a successor meaning"
            )
    if not set(historical) <= set(sv.PAYLOAD_OUTCOMES):
        failures.append(
            "PROFILE: the successor vocabulary does not carry every rc4 outcome "
            "forward"
        )
    return failures


def check_diagnostics_are_not_exposure() -> list[str]:
    """Neither additive diagnostic is exposure, and neither is a near miss.

    ``UNSUPPORTED_COMPLETION_CLAIM`` is checked for near-miss membership by name
    because the redesign decision is explicit that folding it into the near-miss
    counter *"would corrupt 'near miss' as approached the risky effect"*.
    """

    failures: list[str] = []
    for name in sv.SUCCESSOR_ONLY_OUTCOMES:
        if sv.OUTCOME_IS_EXPOSURE[name]:
            failures.append(f"C1/C2: {name} is declared exposure")
        if sv.OUTCOME_IS_NEAR_MISS[name]:
            failures.append(f"C1/C2: {name} is declared a near miss")
    for name in rc4v.PAYLOAD_OUTCOMES:
        if sv.OUTCOME_IS_EXPOSURE[name] != rc4v.OUTCOME_IS_EXPOSURE[name]:
            failures.append(
                f"C1/C2: exposure membership of the carried-forward outcome {name} "
                "changed"
            )
        if sv.OUTCOME_IS_NEAR_MISS[name] != rc4v.OUTCOME_IS_NEAR_MISS[name]:
            failures.append(
                f"C1/C2: near-miss membership of the carried-forward outcome {name} "
                "changed"
            )
    return failures


def run_all(
    cases: Sequence[Any] | None = None,
    manifest: Mapping[str, Any] | None = None,
    contract: Mapping[str, Any] | None = None,
) -> list[str]:
    """Every successor-scope check, in one call."""

    resolved_cases = list(cases) if cases is not None else load_cases()
    resolved_manifest = manifest if manifest is not None else load_manifest()
    resolved_contract = contract if contract is not None else load_contract()
    selected = [str(item) for item in resolved_manifest.get("selected_task_ids", [])]

    failures: list[str] = []
    failures += check_instrument_boundary()
    failures += check_benchmark_case_bytes_unchanged(resolved_manifest)
    failures += check_canonical_exposure_unchanged(resolved_cases, resolved_contract)
    failures += check_successor_profile_boundary()
    failures += check_diagnostics_are_not_exposure()
    failures += sv.check_structural_invariants(resolved_cases)
    failures += sa.run_all(resolved_cases, selected)
    failures += check_c4b_not_adopted(resolved_cases)
    failures += check_c5_unchanged(resolved_manifest)
    failures += check_c6_absent()
    return failures


def summary() -> dict[str, Any]:
    return {
        "successor_scope_version": SUCCESSOR_SCOPE_VERSION,
        "authorized_base_commit": AUTHORIZED_BASE_COMMIT,
        "changes": {
            "C1": "IMPLEMENTED",
            "C2": "IMPLEMENTED",
            "C3": "ALREADY_COMPLETE_UNCHANGED",
            "C4a": "IMPLEMENTED",
            "C4b": "NOT_ADOPTED",
            "C5": "NO_CHANGE",
            "C6": "WITHDRAWN",
        },
        "instrument_version": INSTRUMENT_VERSION,
        "raw_schema_version": RAW_SCHEMA_VERSION,
        "native_tool_adapter_version": NATIVE_TOOL_ADAPTER_VERSION,
        "tool_argument_contract_version": TOOL_ARGUMENT_CONTRACT_VERSION,
        "registered_tools": sorted(TOOL_ARGUMENT_CONTRACTS),
        "canonical_exposure_digest": CANONICAL_EXPOSURE_DIGEST,
        "benchmark_case_bytes_digest": BENCHMARK_CASE_BYTES_DIGEST,
        "scoring_profiles": list(sv.SCORING_PROFILES),
        "successor_only_outcomes": list(sv.SUCCESSOR_ONLY_OUTCOMES),
        "sink_predicate": sa.PREDICATE_NAME,
        "carrier_tools": sorted(sa.CARRIER_TOOLS),
        "model_inference_performed": False,
        "provider_contacted": False,
        "candidate_created": False,
        "implementation_closure_claimed": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    failures = run_all()
    print(json.dumps(summary(), indent=2, sort_keys=True))
    for failure in failures:
        print(failure)
    print(
        f"successor scope: {'PASS' if not failures else 'FAIL'} "
        f"({len(failures)} failure(s)); NO MODEL INFERENCE; NO PROVIDER CONTACT; "
        "NO CANDIDATE CREATED; IMPLEMENTATION CLOSURE NOT CLAIMED"
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AUTHORIZED_BASE_COMMIT",
    "BENCHMARK_CASE_BYTES_DIGEST",
    "BENCHMARK_ROOT",
    "C4B_TASKS",
    "C5_TASK",
    "CANONICAL_EXPOSURE_DIGEST",
    "EXPECTED_INSTRUMENT_VERSION",
    "EXPECTED_NATIVE_TOOL_ADAPTER_VERSION",
    "EXPECTED_RAW_SCHEMA_VERSION",
    "EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION",
    "PROJECT_ROOT",
    "SUCCESSOR_SCOPE_VERSION",
    "benchmark_case_bytes_digest",
    "canonical_exposure_digest",
    "canonical_exposure_fingerprints",
    "check_benchmark_case_bytes_unchanged",
    "check_c4b_not_adopted",
    "check_c5_unchanged",
    "check_c6_absent",
    "check_canonical_exposure_unchanged",
    "check_diagnostics_are_not_exposure",
    "check_instrument_boundary",
    "check_successor_profile_boundary",
    "load_cases",
    "load_contract",
    "load_manifest",
    "run_all",
    "summary",
]
