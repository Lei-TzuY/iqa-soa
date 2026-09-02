#!/usr/bin/env python3
"""Strict, fail-closed validation of the frozen post-Phase-P candidate.

**NO MODEL INFERENCE. NO PROVIDER. NO NETWORK. NO SEED. NO PHASE-P EVIDENCE.**

WHAT THIS VALIDATOR IS FOR
==========================

:mod:`successor_candidate_freeze` decides whether a candidate MAY be frozen.
This module decides whether what is on disk STILL IS that candidate. The two are
deliberately separate: a freeze that could only be checked by the code that
produced it would prove nothing about the artifacts a later reader finds.

Every check here fails CLOSED. Absence is a failure, an unreadable file is a
failure, an unexpected file is a failure, and a value the validator does not
recognise is a failure rather than a value it skips. Nothing is waived,
normalized or reclassified to make a gate pass.

WHAT IT REFUSES
===============

The freeze brief's section 15 list, in order: identifier mismatch; a candidate
marked qualified; provider eligibility prematurely realized; model inference,
qualification execution or confirmatory execution enabled; benchmark digest or
task-byte mutation; canonical exposure digest mutation; C1, C2 or C3 drift; C4a
incomplete; C4b adopted; C5 modified; C6 reintroduced; historical rc4
contamination or retrospective entry; incomplete task coverage; carrier
derivation mismatch; an incomplete sink register or change ledger; an
unauthorized benchmark or model-visible ledger item; the descriptive audit
promoted to a gate; any forecast of a task's behaviour; a missing provenance or
digest binding; nondeterminism outside the approved normalization; an overly
broad normalization policy; and a missing freeze-critical artifact.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:  # pragma: no cover - import shim
        sys.path.insert(0, str(_root))

from iqa_soa.instrument import (  # noqa: E402
    INSTRUMENT_VERSION,
    NATIVE_TOOL_ADAPTER_VERSION,
    RAW_SCHEMA_VERSION,
)
from iqa_soa.tools.argument_schema import TOOL_ARGUMENT_CONTRACT_VERSION  # noqa: E402

import rc4_scoring_vocabulary as rc4v  # noqa: E402
import successor_candidate_freeze as fz  # noqa: E402
import successor_candidate_naming as naming  # noqa: E402
import successor_scoring_vocabulary as sv  # noqa: E402
import successor_sink_applicability as sa  # noqa: E402
import validate_pilot_v7_rc4 as rc4_validator  # noqa: E402
import validate_successor_scope as scope  # noqa: E402

CANDIDATE_VALIDATOR_VERSION = "successor-candidate-freeze-validator-1"

#: A state that would mean the candidate had been qualified.  None may appear.
FORBIDDEN_CANDIDATE_STATES: tuple[str, ...] = (
    "QUALIFIED",
    "PROVIDER_QUALIFIED",
    "MODEL_QUALIFIED",
    "REAL_QUALIFICATION_PASS",
    "CONFIRMATORY_PASS",
    "PASS",
)

#: Flags that must be false in every artifact that carries an authorization block.
UNREALIZED_FLAGS: tuple[str, ...] = (
    "provider_selected",
    "provider_contacted",
    "real_qualification_authorized",
    "model_inference_authorized",
    "qualification_execution_authorized",
    "confirmatory_execution_authorized",
    "randomization_realized",
    "registration_performed",
    "production_seed_realized",
    "freeze_is_execution_authorization",
)


def candidate_root(root: Path | str | None = None) -> Path:
    base = Path(root) if root is not None else PROJECT_ROOT
    return base / "candidates" / naming.candidate_identifier()


def load_artifacts(root: Path | str | None = None) -> tuple[dict[str, Any], list[str]]:
    """Read every freeze-critical artifact, failing closed on absence or garbage."""

    namespace = candidate_root(root)
    failures: list[str] = []
    artifacts: dict[str, Any] = {}
    if not namespace.is_dir():
        return {}, [
            f"ARTIFACTS: the candidate namespace {namespace} does not exist, so "
            "there is no frozen candidate to validate"
        ]
    for name in fz.FREEZE_CRITICAL_ARTIFACTS:
        path = namespace / name
        if not path.is_file():
            failures.append(
                f"ARTIFACTS: the freeze-critical artifact {name} is missing from "
                f"{namespace}"
            )
            continue
        try:
            artifacts[name] = json.loads(path.read_bytes().decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as error:
            failures.append(f"ARTIFACTS: {name} is not readable canonical JSON: {error}")
    present = {item.name for item in namespace.iterdir() if item.is_file()}
    for extra in sorted(present - set(fz.FREEZE_CRITICAL_ARTIFACTS)):
        failures.append(
            f"ARTIFACTS: {extra} is present in the candidate namespace but is not a "
            "declared freeze-critical artifact; an unexpected artifact in a frozen "
            "namespace fails closed"
        )
    for extra in sorted(
        item.name for item in namespace.iterdir() if not item.is_file()
    ):
        failures.append(
            f"ARTIFACTS: {extra} is a directory inside the candidate namespace, "
            "which holds files only"
        )
    return artifacts, failures


# --------------------------------------------------------------------------
# Identity, status and authorization
# --------------------------------------------------------------------------


def check_identifier(artifacts: Mapping[str, Any]) -> list[str]:
    """Every artifact must name the same identifier, and it must be THE one."""

    failures: list[str] = []
    expected = naming.candidate_identifier()
    failures.extend(naming.run_all())
    for name, document in sorted(artifacts.items()):
        actual = document.get("candidate_identifier")
        if actual != expected:
            failures.append(
                f"IDENTITY: {name} names the candidate {actual!r}, not the "
                f"policy-derived {expected!r}"
            )
    record = artifacts.get(fz.ARTIFACT_FREEZE, {})
    if record.get("candidate_namespace") != naming.candidate_namespace():
        failures.append(
            "IDENTITY: the freeze record's namespace is not the policy-derived "
            f"{naming.candidate_namespace()!r}"
        )
    manifest = artifacts.get(fz.ARTIFACT_MANIFEST, {})
    policy = manifest.get("naming_policy", {})
    if policy.get("identifiers_assigned") != 1:
        failures.append(
            "IDENTITY: the naming policy does not record exactly one assigned "
            "identifier"
        )
    if policy.get("neutrality_failures") or policy.get("determinism_failures"):
        failures.append(
            "IDENTITY: the recorded naming policy carries neutrality or determinism "
            "failures"
        )
    return failures


def check_status_and_authorization(artifacts: Mapping[str, Any]) -> list[str]:
    """No artifact may claim qualification, eligibility or execution authority."""

    failures: list[str] = []
    for name, document in sorted(artifacts.items()):
        block = document.get("authorization")
        if isinstance(block, Mapping):
            failures.extend(
                f"{name}: {failure}"
                for failure in fz.check_authorization_block(block)
            )
        text = json.dumps(document, sort_keys=True, ensure_ascii=False)
        for key in ("candidate_status", "qualification_status"):
            value = document.get(key)
            if value is not None and value in FORBIDDEN_CANDIDATE_STATES:
                failures.append(
                    f"STATUS: {name} carries {key}={value!r}, which claims a "
                    "qualification the freeze does not confer"
                )
        if '"conclusion": "PROVIDER_QUALIFIED"' in text:
            failures.append(f"STATUS: {name} concludes PROVIDER_QUALIFIED")
    record = artifacts.get(fz.ARTIFACT_FREEZE, {})
    if record.get("candidate_status") != fz.CANDIDATE_STATUS:
        failures.append(
            "STATUS: the freeze record's candidate_status is "
            f"{record.get('candidate_status')!r}, not {fz.CANDIDATE_STATUS!r}"
        )
    if record.get("freeze_is_execution_authorization") is not False:
        failures.append(
            "STATUS: the freeze record does not state that freeze is not execution "
            "authorization"
        )
    readiness = artifacts.get(fz.ARTIFACT_READINESS, {})
    conclusion = readiness.get("conclusion")
    if conclusion != fz.READINESS_CONCLUSION_PASS:
        failures.append(
            f"STATUS: the readiness report concludes {conclusion!r}, not "
            f"{fz.READINESS_CONCLUSION_PASS!r}"
        )
    forbidden = readiness.get("conclusions_this_report_may_never_reach", {})
    for name in fz.FORBIDDEN_READINESS_CONCLUSIONS:
        if forbidden.get(name) is not False:
            failures.append(
                f"STATUS: the readiness report does not explicitly refuse the "
                f"conclusion {name}"
            )
        if conclusion == name:
            failures.append(
                f"STATUS: the readiness report reaches the forbidden conclusion "
                f"{name}"
            )
    return failures


# --------------------------------------------------------------------------
# The scientific invariants, recomputed rather than read
# --------------------------------------------------------------------------


def check_scientific_digests(artifacts: Mapping[str, Any]) -> list[str]:
    """Recompute both digests from the frozen inputs and compare to the bindings."""

    failures: list[str] = []
    cases = scope.load_cases()
    manifest = scope.load_manifest()
    contract = scope.load_contract()
    failures.extend(scope.check_benchmark_case_bytes_unchanged(manifest))
    failures.extend(scope.check_canonical_exposure_unchanged(cases, contract))

    benchmark = scope.benchmark_case_bytes_digest(manifest)
    exposure = scope.canonical_exposure_digest(cases, contract)
    bound_benchmark = {
        fz.ARTIFACT_MANIFEST: artifacts.get(fz.ARTIFACT_MANIFEST, {})
        .get("benchmark_selection", {})
        .get("benchmark_case_bytes_digest"),
        fz.ARTIFACT_CONTRACT: artifacts.get(fz.ARTIFACT_CONTRACT, {})
        .get("task_selection", {})
        .get("benchmark_case_bytes_digest"),
        fz.ARTIFACT_PROVENANCE: artifacts.get(fz.ARTIFACT_PROVENANCE, {})
        .get("scientific_digests", {})
        .get("benchmark_case_bytes_digest"),
        fz.ARTIFACT_FREEZE: artifacts.get(fz.ARTIFACT_FREEZE, {})
        .get("scientific_digests", {})
        .get("benchmark_case_bytes_digest"),
    }
    for name, value in sorted(bound_benchmark.items()):
        if value != benchmark:
            failures.append(
                f"DIGEST: {name} binds the benchmark case-byte digest {value!r}, "
                f"but recomputation from the frozen case files yields {benchmark!r}"
            )
    bound_exposure = {
        fz.ARTIFACT_MANIFEST: artifacts.get(fz.ARTIFACT_MANIFEST, {})
        .get("canonical_exposure", {})
        .get("digest"),
        fz.ARTIFACT_CONTRACT: artifacts.get(fz.ARTIFACT_CONTRACT, {})
        .get("canonical_exposure", {})
        .get("digest"),
        fz.ARTIFACT_PROVENANCE: artifacts.get(fz.ARTIFACT_PROVENANCE, {})
        .get("scientific_digests", {})
        .get("canonical_exposure_digest"),
        fz.ARTIFACT_FREEZE: artifacts.get(fz.ARTIFACT_FREEZE, {})
        .get("scientific_digests", {})
        .get("canonical_exposure_digest"),
    }
    for name, value in sorted(bound_exposure.items()):
        if value != exposure:
            failures.append(
                f"DIGEST: {name} binds the canonical exposure digest {value!r}, but "
                f"recomputation from the frozen contract yields {exposure!r}"
            )

    bound_cases = (
        artifacts.get(fz.ARTIFACT_MANIFEST, {})
        .get("benchmark_selection", {})
        .get("case_sha256", {})
    )
    live_cases = {
        str(entry["task_id"]): str(entry["sha256"])
        for entry in manifest.get("cases", [])
    }
    if bound_cases != live_cases:
        failures.append(
            "DIGEST: the candidate manifest's per-task case digests differ from the "
            "frozen benchmark manifest, so a task byte or a pin has moved"
        )
    return failures


def check_instrument_binding(artifacts: Mapping[str, Any]) -> list[str]:
    """C3 must not drift, in the live constants or in any artifact that binds them."""

    failures = list(scope.check_instrument_boundary())
    expected = {
        "instrument_version": INSTRUMENT_VERSION,
        "raw_schema_version": RAW_SCHEMA_VERSION,
        "native_tool_adapter_version": NATIVE_TOOL_ADAPTER_VERSION,
        "tool_argument_contract_version": TOOL_ARGUMENT_CONTRACT_VERSION,
    }
    for name in (
        fz.ARTIFACT_MANIFEST,
        fz.ARTIFACT_CONTRACT,
        fz.ARTIFACT_PROVENANCE,
        fz.ARTIFACT_FREEZE,
    ):
        block = artifacts.get(name, {}).get("instrument")
        if not isinstance(block, Mapping):
            failures.append(f"C3: {name} binds no instrument block")
            continue
        for key, value in sorted(expected.items()):
            if block.get(key) != value:
                failures.append(
                    f"C3: {name} binds {key}={block.get(key)!r}, not the frozen "
                    f"{value!r}"
                )
        if block.get("cross_instrument_pooling_permitted") is not False:
            failures.append(
                f"C3: {name} does not forbid cross-instrument pooling"
            )
    return failures


def check_change_dispositions(artifacts: Mapping[str, Any]) -> list[str]:
    """C1, C2, C4a implemented; C3 unchanged; C4b, C6 absent; C5 unmodified."""

    cases = scope.load_cases()
    manifest = scope.load_manifest()
    failures: list[str] = []
    failures.extend(scope.check_successor_profile_boundary())
    failures.extend(scope.check_diagnostics_are_not_exposure())
    failures.extend(scope.check_c4b_not_adopted(cases))
    failures.extend(scope.check_c5_unchanged(manifest))
    failures.extend(scope.check_c6_absent())
    failures.extend(sv.check_structural_invariants(cases))

    ledger = artifacts.get(fz.ARTIFACT_LEDGER, {})
    failures.extend(fz.check_change_ledger(ledger))

    record = artifacts.get(fz.ARTIFACT_FREEZE, {}).get("change_dispositions", {})
    expected = {
        "C1": "IMPLEMENTED",
        "C2": "IMPLEMENTED",
        "C3": "ALREADY_COMPLETE",
        "C4a": "IMPLEMENTED",
        "C4b": "NOT_ADOPTED",
        "C5": "NO_CHANGE",
        "C6": "WITHDRAWN",
    }
    for change, disposition in sorted(expected.items()):
        entry = record.get(change)
        if not isinstance(entry, Mapping):
            failures.append(f"LEDGER: the freeze record binds no disposition for {change}")
            continue
        if entry.get("disposition") != disposition:
            failures.append(
                f"LEDGER: the freeze record binds {change}="
                f"{entry.get('disposition')!r}, not the frozen {disposition!r}"
            )
    if record.get("C3", {}).get("status") != "UNCHANGED":
        failures.append("C3: the freeze record does not bind C3 as UNCHANGED")

    contract = artifacts.get(fz.ARTIFACT_CONTRACT, {})
    c1 = contract.get("c1_semantics", {})
    if c1.get("adds") != sv.PAYLOAD_UNSUPPORTED_COMPLETION_CLAIM:
        failures.append("C1: the contract does not bind the C1 diagnostic class")
    if c1.get("is_exposure") is not False or c1.get("is_near_miss") is not False:
        failures.append(
            "C1: the contract records the C1 diagnostic as exposure or a near miss"
        )
    c2 = contract.get("c2_semantics", {})
    if c2.get("adds") != sv.PAYLOAD_NONCANONICAL_RESOURCE_SELECTION:
        failures.append("C2: the contract does not bind the C2 diagnostic class")
    if c2.get("is_exposure") is not False or c2.get("is_near_miss") is not False:
        failures.append(
            "C2: the contract records the C2 diagnostic as exposure or a near miss"
        )
    return failures


def check_historical_isolation(artifacts: Mapping[str, Any]) -> list[str]:
    """The historical profile must be closed, and unable to hold a new meaning."""

    failures: list[str] = []
    if len(rc4v.PAYLOAD_OUTCOMES) != 4:
        failures.append(
            "RC4: the historical payload vocabulary is no longer a closed "
            f"four-member tuple ({len(rc4v.PAYLOAD_OUTCOMES)} members)"
        )
    for outcome in sv.SUCCESSOR_ONLY_OUTCOMES:
        if outcome in rc4v.PAYLOAD_OUTCOMES:
            failures.append(
                f"RC4: the successor-only outcome {outcome} is reachable from the "
                "historical profile, so retrospective entry is possible"
            )
        if outcome in rc4v.OUTCOME_IS_EXPOSURE or outcome in rc4v.OUTCOME_IS_NEAR_MISS:
            failures.append(
                f"RC4: the historical profile carries a membership entry for the "
                f"successor-only outcome {outcome}"
            )
    historical = sv.outcomes_for_profile(sv.SCORING_PROFILE_RC4_HISTORICAL)
    if tuple(historical) != tuple(rc4v.PAYLOAD_OUTCOMES):
        failures.append(
            "RC4: the historical profile's outcomes are a copy rather than the "
            "frozen tuple itself"
        )
    for name in (fz.ARTIFACT_MANIFEST, fz.ARTIFACT_CONTRACT, fz.ARTIFACT_FREEZE):
        document = artifacts.get(name, {})
        blob = json.dumps(document, sort_keys=True, ensure_ascii=False)
        if "IMPOSSIBLE" not in blob:
            failures.append(
                f"RC4: {name} does not record retrospective entry into the "
                "historical profile as IMPOSSIBLE"
            )
    predecessor = artifacts.get(fz.ARTIFACT_FREEZE, {}).get("predecessor", {})
    for key, value in (
        ("qualification_status", "UNQUALIFIED"),
        ("verdict", "HOLD"),
        ("terminal_status", "SCHEDULE_COMPLETE_VERDICT_HOLD"),
        ("ben003_cell_status", "MODEL_PROTOCOL_INVALID"),
        ("ben003_matrix_status", "MATRIX_INVALID"),
        ("ben003_forensic_attribution", "MODEL_PROTOCOL_FAILURE"),
    ):
        if predecessor.get(key) != value:
            failures.append(
                f"RC4: the freeze record binds predecessor {key}="
                f"{predecessor.get(key)!r}, not the permanent {value!r}"
            )
    for key in (
        "this_candidate_continues_the_predecessor",
        "this_candidate_replaces_the_predecessor",
        "this_candidate_repairs_the_predecessor",
        "this_candidate_rehabilitates_the_predecessor",
        "historical_evidence_read",
    ):
        if predecessor.get(key) is not False:
            failures.append(f"RC4: the freeze record does not deny {key}")
    for key in (
        "historical_rows_rerun",
        "historical_rows_rescored",
        "historical_rows_reclassified",
    ):
        if predecessor.get(key) != 0:
            failures.append(f"RC4: the freeze record records a nonzero {key}")
    return failures


def check_task_coverage(artifacts: Mapping[str, Any]) -> list[str]:
    """Seventeen tasks, the same seventeen, in every artifact that lists them."""

    cases = scope.load_cases()
    manifest = scope.load_manifest()
    expected = [str(item) for item in manifest.get("selected_task_ids", [])]
    failures: list[str] = []
    if len(cases) != 17 or len(expected) != 17:
        failures.append(
            f"COVERAGE: the frozen selection holds {len(cases)} cases and "
            f"{len(expected)} manifest ids; the candidate is bound to exactly 17"
        )
    selection = (
        artifacts.get(fz.ARTIFACT_MANIFEST, {})
        .get("benchmark_selection", {})
        .get("selected_task_ids")
    )
    if sorted(selection or []) != sorted(expected):
        failures.append(
            "COVERAGE: the candidate manifest's selection is not the frozen "
            "seventeen-task selection"
        )
    contract_ids = (
        artifacts.get(fz.ARTIFACT_CONTRACT, {}).get("task_selection", {}).get("task_ids")
    )
    if sorted(contract_ids or []) != sorted(expected):
        failures.append(
            "COVERAGE: the qualification contract's task selection is not the "
            "frozen seventeen-task selection"
        )
    register = artifacts.get(fz.ARTIFACT_SINKS, {}).get("register", {})
    verdicts = register.get("verdicts")
    rows: Sequence[Any] = verdicts if isinstance(verdicts, Sequence) else ()
    if sorted(str(row.get("task_id")) for row in rows) != sorted(expected):
        failures.append(
            "COVERAGE: the sink applicability register does not record a decision "
            "for every task in the selection"
        )
    audit_rows = artifacts.get(fz.ARTIFACT_AUDIT, {}).get("audit")
    audit_entries: Sequence[Any] = audit_rows if isinstance(audit_rows, Sequence) else ()
    if sorted(str(row.get("task_id")) for row in audit_entries) != sorted(expected):
        failures.append(
            "COVERAGE: the resource-selection audit does not cover every task in "
            "the selection"
        )
    return failures


def check_sink_register(artifacts: Mapping[str, Any]) -> list[str]:
    """C4a: the derivation, the coverage and the regression pin, all recomputed."""

    cases = scope.load_cases()
    manifest = scope.load_manifest()
    selected = [str(item) for item in manifest.get("selected_task_ids", [])]
    failures = list(sa.run_all(cases, selected))

    document = artifacts.get(fz.ARTIFACT_SINKS, {})
    derivation = document.get("carrier_derivation", {})
    if sorted(derivation.get("derived_carrier_tools") or []) != sorted(sa.CARRIER_TOOLS):
        failures.append(
            "SINKS: the register's derived carrier tools differ from the live "
            "derivation from the published tool argument contract"
        )
    if derivation.get("derived_from") != TOOL_ARGUMENT_CONTRACT_VERSION:
        failures.append(
            "SINKS: the register does not derive the carrier class from "
            f"{TOOL_ARGUMENT_CONTRACT_VERSION}"
        )
    if derivation.get("derivation_matches_pin") is not True:
        failures.append(
            "SINKS: the derived carrier class no longer matches its regression pin"
        )
    expected_pairs = {
        task_id: [list(pair)] for task_id, pair in rc4_validator.REQUIRED_SINKS.items()
    }
    actual_pairs = document.get("applicable_sink_pairs") or {}
    normalized = {
        str(key): [list(pair) for pair in value]
        for key, value in actual_pairs.items()
    }
    if normalized != expected_pairs:
        failures.append(
            "SINKS: the applicable set is not exactly the frozen regression pin "
            f"{sorted(expected_pairs)}"
        )
    pin = document.get("required_sinks_regression_pin", {})
    if pin.get("role") != "REGRESSION_ONLY" or pin.get("is_the_primary_predicate") is not False:
        failures.append(
            "SINKS: REQUIRED_SINKS is not recorded as a regression pin only"
        )
    register = document.get("register", {})
    if register.get("tasks_evaluated") != len(cases):
        failures.append(
            f"SINKS: the register evaluated {register.get('tasks_evaluated')!r} "
            f"tasks, not the {len(cases)} in the selection"
        )
    if register.get("emission_screen_is_a_gate") is not False:
        failures.append("SINKS: the emission vocabulary screen is recorded as a gate")
    true_ids = set(register.get("applicability_true") or [])
    false_ids = set(register.get("applicability_false") or [])
    if true_ids & false_ids:
        failures.append("SINKS: a task is recorded as both applicable and inapplicable")
    if len(true_ids | false_ids) != len(cases):
        failures.append(
            "SINKS: the register does not record a TRUE or FALSE decision for every "
            "task"
        )
    return failures


def check_descriptive_audit(artifacts: Mapping[str, Any]) -> list[str]:
    """The audit must remain descriptive and must gate nothing."""

    document = artifacts.get(fz.ARTIFACT_AUDIT, {})
    failures = list(fz.check_descriptive_audit(document))
    readiness = artifacts.get(fz.ARTIFACT_READINESS, {})
    gates = readiness.get("gates")
    rows: Sequence[Any] = gates if isinstance(gates, Sequence) else ()
    for row in rows:
        name = str(row.get("gate", ""))
        if "RESOURCE_SELECTION" in name and name != "DESCRIPTIVE_AUDIT_IS_NOT_A_GATE":
            failures.append(
                f"AUDIT: {name} makes the descriptive resource-selection audit a "
                "gate"
            )
    failures.extend(sa.check_emission_screen_is_not_a_gate(scope.load_cases()))
    return failures


def check_no_forecast(artifacts: Mapping[str, Any]) -> list[str]:
    """No candidate artifact may state a forecast of any task's behaviour."""

    failures: list[str] = []
    for name, document in sorted(artifacts.items()):
        failures.extend(
            f"FORECAST: {name}: {hit}"
            for hit in fz.check_no_predicted_exposure(document)
        )
    contract = artifacts.get(fz.ARTIFACT_CONTRACT, {}).get("prohibited_content", {})
    if contract.get("realized_model_outcome_count") != 0:
        failures.append(
            "FORECAST: the qualification contract records a realized model outcome"
        )
    if contract.get("per_task_exposure_forecast_stated") is not False:
        failures.append(
            "FORECAST: the qualification contract does not deny stating a per-task "
            "forecast"
        )
    return failures


# --------------------------------------------------------------------------
# Provenance, digests and determinism
# --------------------------------------------------------------------------

#: Every binding the provenance register must carry.  A missing one fails closed.
REQUIRED_PROVENANCE_KEYS: tuple[str, ...] = (
    "candidate_identifier",
    "candidate_namespace",
    "source_commit",
    "historical_scientific_baseline_commit",
    "naming_policy_id",
    "naming_components",
    "normalization_policy",
    "authorization",
    "instrument",
    "scientific_digests",
    "scoring_profile_identity",
    "generation_code",
    "measurement_code",
    "historical_code",
    "instrument_tree_digest",
    "change_dispositions",
    "randomization",
    "boundary",
)


def check_provenance(artifacts: Mapping[str, Any]) -> list[str]:
    """Every provenance binding must be present, and the code digests must match."""

    failures: list[str] = []
    document = artifacts.get(fz.ARTIFACT_PROVENANCE, {})
    for key in REQUIRED_PROVENANCE_KEYS:
        if key not in document:
            failures.append(f"PROVENANCE: the register is missing the binding {key!r}")
    if document.get("source_commit") != fz.SOURCE_COMMIT:
        failures.append(
            f"PROVENANCE: the register binds the source commit "
            f"{document.get('source_commit')!r}, not {fz.SOURCE_COMMIT!r}"
        )
    for group, names in (
        ("generation_code", fz.GENERATION_CODE_FILES),
        ("measurement_code", fz.MEASUREMENT_CODE_FILES),
        ("historical_code", fz.HISTORICAL_CODE_FILES),
    ):
        bound = document.get(group)
        if not isinstance(bound, Mapping):
            failures.append(f"PROVENANCE: {group} binds no code identities")
            continue
        try:
            live = fz.file_digests(names)
        except FileNotFoundError as error:
            failures.append(f"PROVENANCE: {error}")
            continue
        if dict(bound) != live:
            for name in sorted(set(live) | set(bound)):
                if bound.get(name) != live.get(name):
                    failures.append(
                        f"PROVENANCE: {group} binds {name}={bound.get(name)!r}, but "
                        f"the file now digests to {live.get(name)!r}"
                    )
    randomization = document.get("randomization", {})
    for key in ("seeds_derived", "random_bits_realized"):
        if randomization.get(key) != 0:
            failures.append(
                f"PROVENANCE: the register records {key}={randomization.get(key)!r}; "
                "a freeze realizes no seed and no random bit"
            )
    boundary = document.get("boundary", {})
    for key in (
        "provider_contacted",
        "network_call_made",
        "endpoint_configured",
        "api_key_read",
        "model_inference_performed",
        "phase_p_evidence_read",
    ):
        if boundary.get(key) is not False:
            failures.append(f"PROVENANCE: the register does not deny {key}")
    return failures


def check_digest_manifest(
    artifacts: Mapping[str, Any], root: Path | str | None = None
) -> list[str]:
    """Recompute every bound digest from the files on disk."""

    failures: list[str] = []
    namespace = candidate_root(root)
    document = artifacts.get(fz.ARTIFACT_DIGESTS, {})
    covered = document.get("covered_artifacts")
    rows: Sequence[Any] = covered if isinstance(covered, Sequence) else ()
    if document.get("digest_algorithm") != fz.DIGEST_ALGORITHM:
        failures.append("DIGEST: the manifest does not declare the sha256 basis")
    if not str(document.get("digest_basis", "")).strip():
        failures.append("DIGEST: the manifest states no exact digest basis")
    if document.get("self_digested") is not False:
        failures.append("DIGEST: the manifest claims to digest itself")
    if document.get("digests_the_freeze_record") is not False:
        failures.append(
            "DIGEST: the manifest claims to digest the freeze record, which would "
            "make the architecture cyclic"
        )
    bound = {str(row.get("artifact")): str(row.get("sha256")) for row in rows}
    if sorted(bound) != sorted(fz.CONTENT_ARTIFACTS):
        failures.append(
            "DIGEST: the manifest does not cover exactly the tier-0 content "
            f"artifacts; it covers {sorted(bound)}"
        )
    for name, expected in sorted(bound.items()):
        path = namespace / name
        if not path.is_file():
            failures.append(f"DIGEST: the bound artifact {name} is missing from disk")
            continue
        actual = fz.digest_of_path(path)
        if actual != expected:
            failures.append(
                f"DIGEST: {name} digests to {actual}, but the manifest binds "
                f"{expected}; a bound artifact has been mutated"
            )
    record = artifacts.get(fz.ARTIFACT_FREEZE, {})
    manifest_path = namespace / fz.ARTIFACT_DIGESTS
    if manifest_path.is_file():
        actual_manifest = fz.digest_of_path(manifest_path)
        if record.get("digest_manifest_sha256") != actual_manifest:
            failures.append(
                "DIGEST: the freeze record binds a digest manifest hash of "
                f"{record.get('digest_manifest_sha256')!r}, but the manifest on "
                f"disk digests to {actual_manifest}"
            )
    critical = record.get("critical_digests")
    if not isinstance(critical, Mapping):
        failures.append("DIGEST: the freeze record binds no critical digests")
    else:
        expected_names = set(fz.CONTENT_ARTIFACTS) | {fz.ARTIFACT_DIGESTS}
        if set(critical) != expected_names:
            failures.append(
                "DIGEST: the freeze record's critical digests do not cover exactly "
                "the tier-0 artifacts and the digest manifest"
            )
        for name, expected in sorted(critical.items()):
            path = namespace / str(name)
            if not path.is_file():
                failures.append(
                    f"DIGEST: the freeze record binds {name}, which is missing from "
                    "disk"
                )
                continue
            actual = fz.digest_of_path(path)
            if actual != expected:
                failures.append(
                    f"DIGEST: the freeze record binds {name}={expected}, but the "
                    f"file digests to {actual}"
                )
    return failures


def check_determinism_policy(artifacts: Mapping[str, Any]) -> list[str]:
    """The normalization must be closed, exact, and empirically justified."""

    failures: list[str] = []
    readiness = artifacts.get(fz.ARTIFACT_READINESS, {})
    determinism = readiness.get("determinism", {})
    if determinism.get("independent_generations", 0) < 2:
        failures.append(
            "DETERMINISM: fewer than two independent generations were compared, so "
            "determinism is asserted rather than demonstrated"
        )
    if determinism.get("unregistered_differing_leaf_paths"):
        failures.append(
            "DETERMINISM: raw generations differ at leaves outside the closed "
            f"registry: {determinism.get('unregistered_differing_leaf_paths')}"
        )
    if determinism.get("normalized_generations_identical") is not True:
        failures.append(
            "DETERMINISM: the normalized generations are not byte-identical"
        )
    if determinism.get("failures"):
        failures.append(
            f"DETERMINISM: the freeze recorded {determinism.get('failures')}"
        )
    registered = set(determinism.get("registered_leaf_paths") or [])
    policy_registered = {leaf.path for leaf in fz.NORMALIZED_LEAF_PATHS}
    if registered != policy_registered:
        failures.append(
            "DETERMINISM: the recorded registry differs from the live normalization "
            "policy"
        )
    observed = set(determinism.get("raw_differing_leaf_paths") or [])
    if not observed <= policy_registered:
        failures.append(
            "DETERMINISM: an observed raw difference is outside the registry"
        )

    for name in (fz.ARTIFACT_PROVENANCE, fz.ARTIFACT_READINESS, fz.ARTIFACT_FREEZE):
        policy = artifacts.get(name, {}).get("normalization_policy")
        if not isinstance(policy, Mapping):
            failures.append(f"DETERMINISM: {name} binds no normalization policy")
            continue
        if policy.get("policy_id") != fz.NORMALIZATION_POLICY_VERSION:
            failures.append(
                f"DETERMINISM: {name} binds the normalization policy "
                f"{policy.get('policy_id')!r}, not "
                f"{fz.NORMALIZATION_POLICY_VERSION!r}"
            )
        if policy.get("canonical_replacement") != fz.EPHEMERAL_RUN_ROOT_SENTINEL:
            failures.append(
                f"DETERMINISM: {name} binds the replacement "
                f"{policy.get('canonical_replacement')!r}, not the exact sentinel "
                f"{fz.EPHEMERAL_RUN_ROOT_SENTINEL!r}"
            )
        leaves = policy.get("registered_leaves")
        entries: Sequence[Any] = leaves if isinstance(leaves, Sequence) else ()
        if {str(row.get("leaf_path")) for row in entries} != policy_registered:
            failures.append(
                f"DETERMINISM: {name}'s registered leaves are not the closed "
                "registry"
            )
        for row in entries:
            if row.get("canonical_replacement") != fz.EPHEMERAL_RUN_ROOT_SENTINEL:
                failures.append(
                    f"DETERMINISM: {name} registers {row.get('leaf_path')!r} with a "
                    "non-canonical replacement"
                )
            if row.get("demonstrated_to_vary_across_independent_generations") is not True:
                failures.append(
                    f"DETERMINISM: {name} registers {row.get('leaf_path')!r} without "
                    "an empirical demonstration that it varies"
                )
            if not str(row.get("reason", "")).strip():
                failures.append(
                    f"DETERMINISM: {name} registers {row.get('leaf_path')!r} with no "
                    "stated reason"
                )
        rules = policy.get("rules", {})
        for rule, required in (
            ("exact_leaf_paths_only", True),
            ("arbitrary_paths_stripped", False),
            ("arbitrary_timestamps_stripped", False),
            ("arbitrary_strings_normalized", False),
            ("unknown_fields_ignored", False),
            ("value_matching_used", False),
            ("unknown_nondeterminism_fails_closed", True),
            ("scope_may_be_widened_silently", False),
        ):
            if rules.get(rule) is not required:
                failures.append(
                    f"DETERMINISM: {name} binds the normalization rule {rule}="
                    f"{rules.get(rule)!r}, not {required!r}; the policy would be "
                    "broader than the one that was approved"
                )
    evidence = readiness.get("offline_capability_evidence", {})
    if isinstance(evidence, Mapping):
        failures.extend(fz.check_normalization_structure(evidence))
        for leaf in fz.NORMALIZED_LEAF_PATHS:
            values = dict(fz.leaf_values(evidence))
            if values.get(leaf.path) != fz.EPHEMERAL_RUN_ROOT_SENTINEL:
                failures.append(
                    f"DETERMINISM: the embedded evidence leaf {leaf.path} is "
                    f"{values.get(leaf.path)!r}, not the canonical sentinel"
                )
    return failures


def check_baseline_declaration() -> list[str]:
    """The declared baseline difference table must match what git actually reports.

    Runs git. Absence of git, or a failed invocation, is a failure: a ledger that
    cannot be checked against reality is not a checked ledger.
    """

    try:
        completed = subprocess.run(
            [
                "git",
                "diff",
                "--name-status",
                fz.HISTORICAL_SCIENTIFIC_BASELINE_COMMIT,
                fz.SOURCE_COMMIT,
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:  # pragma: no cover - git is present in this repository
        return [f"BASELINE: git could not be invoked to check the declaration: {error}"]
    if completed.returncode != 0:
        return [
            "BASELINE: git could not diff the historical scientific baseline against "
            f"the source commit: {completed.stderr.strip()}"
        ]
    actual = tuple(
        (parts[0], parts[1])
        for parts in (line.split("\t") for line in completed.stdout.splitlines() if line)
        if len(parts) >= 2
    )
    failures: list[str] = []
    declared = set(fz.BASELINE_TRACKED_DIFFERENCES)
    observed = set(actual)
    for row in sorted(observed - declared):
        failures.append(
            f"BASELINE: {row[1]} ({row[0]}) differs from the historical scientific "
            "baseline but is not classified in the change ledger"
        )
    for row in sorted(declared - observed):
        failures.append(
            f"BASELINE: the change ledger classifies {row[1]} ({row[0]}), which is "
            "not a difference from the historical scientific baseline"
        )
    for _, path in actual:
        if any(path.startswith(prefix) for prefix in fz.MODEL_VISIBLE_PATH_PREFIXES):
            failures.append(
                f"BASELINE: {path} is a model-visible surface that differs from the "
                "historical scientific baseline"
            )
        if fz.classify_difference(path) == "UNCLASSIFIED":
            failures.append(
                f"BASELINE: {path} cannot be classified by the ledger's rule"
            )
    return failures


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


def run_all(
    root: Path | str | None = None, check_baseline: bool = True
) -> list[str]:
    """Every candidate-freeze check, in one call.  Fails closed throughout."""

    artifacts, failures = load_artifacts(root)
    if not artifacts:
        return failures
    failures = list(failures)
    failures += check_identifier(artifacts)
    failures += check_status_and_authorization(artifacts)
    failures += check_scientific_digests(artifacts)
    failures += check_instrument_binding(artifacts)
    failures += check_change_dispositions(artifacts)
    failures += check_historical_isolation(artifacts)
    failures += check_task_coverage(artifacts)
    failures += check_sink_register(artifacts)
    failures += check_descriptive_audit(artifacts)
    failures += check_no_forecast(artifacts)
    failures += check_provenance(artifacts)
    failures += check_digest_manifest(artifacts, root)
    failures += check_determinism_policy(artifacts)
    if check_baseline:
        failures += check_baseline_declaration()
    return failures


def summary(root: Path | str | None = None) -> dict[str, Any]:
    artifacts, _ = load_artifacts(root)
    record = artifacts.get(fz.ARTIFACT_FREEZE, {})
    return {
        "validator_version": CANDIDATE_VALIDATOR_VERSION,
        "candidate_identifier": naming.candidate_identifier(),
        "candidate_namespace": naming.candidate_namespace(),
        "candidate_status": record.get("candidate_status"),
        "source_commit": fz.SOURCE_COMMIT,
        "artifacts_found": sorted(artifacts),
        "instrument_version": INSTRUMENT_VERSION,
        "raw_schema_version": RAW_SCHEMA_VERSION,
        "native_tool_adapter_version": NATIVE_TOOL_ADAPTER_VERSION,
        "tool_argument_contract_version": TOOL_ARGUMENT_CONTRACT_VERSION,
        "provider_eligibility": fz.PROVIDER_ELIGIBILITY,
        "model_inference_authorized": False,
        "qualification_execution_authorized": False,
        "confirmatory_execution_authorized": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=None, help="Repository root to validate.")
    parser.add_argument(
        "--skip-baseline",
        action="store_true",
        help="Skip the git-backed baseline-declaration cross-check.",
    )
    args = parser.parse_args(argv)
    failures = run_all(args.root, check_baseline=not args.skip_baseline)
    print(json.dumps(summary(args.root), indent=2, sort_keys=True))
    for failure in failures:
        print(failure)
    print(
        f"candidate freeze validation: {'PASS' if not failures else 'FAIL'} "
        f"({len(failures)} failure(s)); NO MODEL INFERENCE; NO PROVIDER CONTACT; "
        "NOT YET QUALIFIED; NO EXECUTION AUTHORIZED"
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CANDIDATE_VALIDATOR_VERSION",
    "FORBIDDEN_CANDIDATE_STATES",
    "PROJECT_ROOT",
    "REQUIRED_PROVENANCE_KEYS",
    "UNREALIZED_FLAGS",
    "candidate_root",
    "check_baseline_declaration",
    "check_change_dispositions",
    "check_descriptive_audit",
    "check_determinism_policy",
    "check_digest_manifest",
    "check_historical_isolation",
    "check_identifier",
    "check_instrument_binding",
    "check_no_forecast",
    "check_provenance",
    "check_scientific_digests",
    "check_sink_register",
    "check_status_and_authorization",
    "check_task_coverage",
    "load_artifacts",
    "run_all",
    "summary",
]
