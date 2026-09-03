#!/usr/bin/env python3
"""The successor real-model qualification DRIVER: EXECUTABLE BUT LOCKED.

**THIS DRIVER STILL CANNOT EXECUTE ANYTHING, AND THAT IS THE POINT.**

Everything an authorized successor qualification would do is implemented here,
reviewed here and tested here -- the runtime-evidence gate, the frozen 102-cell
schedule, the immediate pre-inference environment check, the write-once
persistence, the no-retry orchestration and the post-run analyzer that produces
the frozen verdict.  What is NOT here is an authorization.
:data:`successor_qualification_protocol.QUALIFICATION_EXECUTION_AUTHORIZED` is
``False``, and while it is, no path in this file can contact a provider, resolve
a credential, open a socket, spend a token or create the results namespace.

Provider OBJECTS are constructed on one offline path, and only there:
:func:`capture_stratum_runtime_snapshot` needs a provider descriptor to compute a
``RuntimeSnapshotV1``.  Constructing one reads
``configs/successor-models.yaml``, opens no socket and sends no prompt, which is
what lets the offline suite exercise the REAL capture rather than a stand-in.
Contact is the gated act, not construction, and the two are kept distinct here on
purpose.

The previous revision stopped at ``PREFLIGHT_STOP`` with the message *"a runtime
preflight ... is not implemented here because capturing it requires provider
contact, which no record has yet authorized"*.  That statement is now false:
``docs/post_phaseP_successor_runtime_preflight_contact_authorization.md``
authorized exactly that contact, it happened once, and its evidence is committed
at ``results/prospective-candidate-i5-m1-b76f40da2-runtime-preflight/``.  The
gap the message described is the gap this revision closes.  Closing it is not
authorizing execution; it is making the execution boundary a reviewed artifact
BEFORE anyone is in a position to cross it, which is the same reason the driver
existed at all.

    EXECUTABLE: every step after the authorization is written, wired and tested.
    LOCKED:     the authorization is False, and it is checked first, every time.

THE ORDER OF THE LOCKS IS THE POINT
===================================

``--preflight`` and ``--analyze`` are offline and always available.
``--execute-real-model`` is refused, and refused in a specific order:

1. :func:`~successor_qualification_protocol.require_execution_authorization`
   FIRST.  While ``QUALIFICATION_EXECUTION_AUTHORIZED`` is ``False`` a caller
   who supplies BOTH the flag and the environment gate still gets a refusal, and
   gets it before either is read.  A human record is the authorization; the
   gates are only how an already-granted authorization is exercised.
2. Only then the two human gates, then the offline preflight, then the canonical
   runtime evidence, then the credential name, then the namespace absence, then
   the fresh pre-inference environment check, then -- and only then -- a cell.

Written the other way round, a green environment would look like consent.  It is
not consent, and this driver never lets it read as consent.

THE CAPABILITY, NOT THE CALLER, IS THE GATE
===========================================

Stating a rule in :func:`main` is not enforcing it.  The authority to contact a
runtime or spend inference travels as a :class:`SuccessorExecutionAuthorization`
object.  :func:`grant_execution_authorization` is the only thing that mints one;
it calls the protocol's authorization check FIRST and therefore cannot mint one
today at all.  :func:`probe_ollama_metadata` and :func:`make_cell_executor` --
the only two functions in this file that can reach a live runtime or spend a
token -- each REQUIRE one and re-verify it, per call and per cell.

    NO HUMAN RECORD -> NO CAPABILITY
    NO CAPABILITY   -> NO PROVIDER, NO PROBE, NO INFERENCE, NO NAMESPACE

The offline regression suite drives everything beyond the gate through
:func:`execute_offline_bound_run`, which requires an injected probe and an
injected cell executor, has no real-model default to fall back to, refuses the
real primitives by identity, and refuses to write the frozen successor namespace
at all.  The two paths are disjoint by construction rather than by convention.

WHAT THE RUNTIME EVIDENCE IS, AND IS NOT
========================================

The committed preflight evidence is IMMUTABLE OBSERVED EVIDENCE.  This driver
reads it, validates every ``RuntimeSnapshotV1`` self-digest by reconstruction,
and binds the capture commit -- and it rewrites no timestamp, no self-digest and
no provenance field.  It is a PRIOR observation, so it is never accepted as a
substitute for a FRESH one: :func:`environment_preflight` re-verifies the live
runtime version and both model digests, and freshly captures one
``RuntimeSnapshotV1`` per stratum through the repository-owned capture callable,
before the first cell.  ``captured_at`` and ``self_digest`` naturally differ
between the two; ``runtime_identity_digest`` must not.  Any disagreement, or any
missing observation, is an ``ENVIRONMENT_HOLD`` with zero cells executed.

WHAT THIS DRIVER DOES NOT DO
============================

* It does not retry.  ``INFRASTRUCTURE_RETRY_LIMIT`` is fixed at ``0``.  A
  provider or model failure is a RECORDED OUTCOME, never a reason to rerun.
* It does not resume, merge, overwrite, repair or deduplicate.  Persistence is
  write-once BY ABSENCE: the entire results namespace must not exist, and a
  second invocation is refused before any provider object is constructed.
* It does not touch ``results/phaseP-rc4-qualification`` or any earlier lineage
  namespace, or any ``FSE-*`` clarification directory.  Phase P remains
  permanently UNQUALIFIED / HOLD and no Phase-P row is read, reused, rescored or
  reinterpreted.
* It does not perform confirmatory registration, confirmatory randomization or
  confirmatory execution, and it cannot: every constant that would authorize one
  is ``False`` and :func:`check_confirmatory_remains_impossible` proves it.
* It invents no scientific schedule and no threshold.  The schedule is the
  frozen 17 x 2 x 3, QA OFF only; the verdict rule is the committed one, reused
  from the frozen qualification analyzer rather than restated.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field, replace
import functools
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Iterator, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
SRC_ROOT = PROJECT_ROOT / "src"
for _root in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import qualification_harness_v2 as harness  # noqa: E402
import successor_eligibility_preflight as eligibility  # noqa: E402
import successor_qualification_protocol as protocol  # noqa: E402
import successor_scoring_vocabulary as successor_vocabulary  # noqa: E402
from iqa_soa.experiment.confirmatory_registration import (  # noqa: E402
    RetryPolicyV1,
    RuntimeSnapshotV1,
)
from iqa_soa.metrics.definitions import (  # noqa: E402
    PILOT_RAW_FIELDS_V6,
    provider_failure_attempt_violations,
)

DRIVER_VERSION = "successor-qualification-driver-1"
ANALYZER_VERSION = "successor-qualification-analyzer-1"


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


class SuccessorExecutionRefused(protocol.SuccessorProtocolError):
    """A real-model execution was requested without the capability that permits one."""


class RuntimeEvidenceInvalid(protocol.SuccessorProtocolError):
    """The committed runtime-preflight evidence is absent, malformed or tampered.

    A subclass of the protocol error so every caller that already refuses a
    protocol error refuses this too.  It is raised BEFORE any provider object
    exists: unusable prior evidence is a stop, never something to regenerate.
    """


# --------------------------------------------------------------------------
# 0. The committed runtime-preflight evidence -- IMMUTABLE OBSERVED EVIDENCE
# --------------------------------------------------------------------------

#: Where the one authorized runtime preflight wrote what it observed.  This
#: driver READS it and never writes it; the namespace is not the qualification
#: namespace precisely so a pre-execution capture can never be read later as
#: evidence that a qualification began.
RUNTIME_EVIDENCE_NAMESPACE = f"results/{protocol.CANDIDATE_IDENTIFIER}-runtime-preflight"
RUNTIME_EVIDENCE_REPORT_NAME = "runtime-preflight-report.json"
RUNTIME_EVIDENCE_RECORD_KIND = "runtime_preflight_report"
RUNTIME_EVIDENCE_SCHEMA_VERSION = "successor-runtime-preflight-evidence-1"
RUNTIME_SNAPSHOT_RECORD_KIND = "RuntimeSnapshotV1"
RUNTIME_SNAPSHOT_CAPTURE_KIND = "PRE_EXECUTION_PROVENANCE"

#: The repository-owned capture callable the evidence was produced by, and the
#: one this driver calls again for the fresh capture.  Named as a string so the
#: two can be compared without importing the module twice.
CAPTURE_CALLABLE = "iqa_soa.experiment.confirmatory.capture_runtime_snapshot_v1"

#: The canonical main commit the capture ran at, and the commit its authorizing
#: record was written at.  Both are recorded in the evidence and both are
#: required, so evidence carried in from a different history is refused.
RUNTIME_EVIDENCE_CAPTURE_COMMIT = "9f7a8b578b6f8d5de96e12e6725d9f3b8bcec51a"
RUNTIME_EVIDENCE_AUTHORIZATION_COMMIT = "469b0c5916ae74f098da8ab2a45955297a04120b"

RUNTIME_EVIDENCE_AUTHORIZATION_RECORD = (
    "docs/post_phaseP_successor_runtime_preflight_contact_authorization.md"
)
RUNTIME_EVIDENCE_AUTHORIZATION_VERSION = (
    "successor-runtime-preflight-contact-authorization-1"
)

#: The provider slot each frozen arm occupies, and the artifact its snapshot
#: lives in.  Slot order follows :data:`successor_qualification_protocol.ARM_ORDER`.
ARM_SLOT: Mapping[str, str] = dict(protocol.ARM_PROVIDER_SLOT)
SLOT_ARM: Mapping[str, str] = {slot: arm for arm, slot in ARM_SLOT.items()}


def runtime_snapshot_artifact_name(provider_slot: str) -> str:
    """The evidence artifact one stratum's captured snapshot lives in."""

    return f"runtime-snapshot-{provider_slot}.json"


#: THE CANONICAL RUNTIME IDENTITY OF EACH FROZEN STRATUM.
#:
#: These are the ``runtime_identity_digest`` values the authorized preflight
#: OBSERVED.  They are restated here so that a tampered evidence file cannot
#: quietly redefine what "the canonical identity" means -- the file must agree
#: with these, and these must agree with the file.  Neither alone is trusted.
#:
#: The identity digest is a pure function of the frozen provider configuration,
#: the frozen ``ExperimentConfig``, the package source, the prompt template, the
#: adapter version and the host fingerprint.  It contains no timestamp and no
#: self-digest, which is exactly why a FRESH capture can be required to equal it
#: while ``captured_at`` and ``self_digest`` legitimately differ.
CANONICAL_RUNTIME_IDENTITY: Mapping[str, str] = {
    "qwen_native_none": (
        "3c49ab568c75b07b8c640cd4862003725b4552948cdba594ddd753af4911d30b"
    ),
    "mistral_native_trailing_user": (
        "5ff8e0922b589522682b3e2d9efd3b55b0e014221011669247d421996d742e48"
    ),
}

#: The observed self-digests and capture timestamps.  Recorded so the evidence's
#: OWN immutability is checkable, and NEVER as something a fresh capture must
#: reproduce: a fresh capture that reproduced ``captured_at`` would be a replay,
#: not an observation.
CANONICAL_RUNTIME_SELF_DIGEST: Mapping[str, str] = {
    "qwen_native_none": (
        "5f2ff4e2eaf6852ca87b861e1e93d0d179b5df0956f7f5760d27e37fa89b1d2c"
    ),
    "mistral_native_trailing_user": (
        "b2c3ea571ad71a7bf02650079e41b6ed5068be85de30b903284dffbffd97161b"
    ),
}
CANONICAL_RUNTIME_CAPTURED_AT: Mapping[str, str] = {
    "qwen_native_none": "2026-09-03T09:53:38Z",
    "mistral_native_trailing_user": "2026-09-03T09:53:38Z",
}

#: The number of keys a RuntimeSnapshotV1 artifact carries.  Closed in both
#: directions by the frozen schema; restated so a nineteen- or twenty-one-key
#: look-alike is refused rather than partially validated.
RUNTIME_SNAPSHOT_KEY_COUNT = 20

#: Execution-boundary facts the evidence must assert about ITSELF.  Every one is
#: ``False``: the preflight observed a runtime, and did nothing else.
REQUIRED_EVIDENCE_BOUNDARY: Mapping[str, bool] = {
    "BENCHMARK_PROMPT_SENT": False,
    "CANDIDATE_REFROZEN": False,
    "CONFIRMATORY_EXECUTION_AUTHORIZED": False,
    "CONFIRMATORY_EXECUTION_PERFORMED": False,
    "MODEL_INFERENCE_AUTHORIZED": False,
    "MODEL_INFERENCE_PERFORMED": False,
    "PRODUCTION_RANDOMIZATION_AUTHORIZED": False,
    "QUALIFICATION_EXECUTION_AUTHORIZED": False,
    "QUALIFICATION_EXECUTION_PERFORMED": False,
    "RANDOMIZATION_REALIZED": False,
    "REPAIR_PERFORMED": False,
}


@dataclass(frozen=True, slots=True)
class CanonicalRuntimeEvidence:
    """The validated committed preflight evidence, as read.  Never as written."""

    report: Mapping[str, Any]
    report_sha256: str
    snapshots: Mapping[str, Mapping[str, Any]]
    identity: Mapping[str, str]
    self_digest: Mapping[str, str]
    captured_at: Mapping[str, str]
    capture_commit: str

    def provenance(self) -> dict[str, Any]:
        """What a run manifest records about the evidence it was gated on."""

        return {
            "evidence_namespace": RUNTIME_EVIDENCE_NAMESPACE,
            "report": f"{RUNTIME_EVIDENCE_NAMESPACE}/{RUNTIME_EVIDENCE_REPORT_NAME}",
            "report_sha256": self.report_sha256,
            "capture_commit": self.capture_commit,
            "authorization_record": RUNTIME_EVIDENCE_AUTHORIZATION_RECORD,
            "authorization_version": RUNTIME_EVIDENCE_AUTHORIZATION_VERSION,
            "capture_callable": CAPTURE_CALLABLE,
            "canonical_runtime_identity": dict(self.identity),
            "canonical_self_digest": dict(self.self_digest),
            "canonical_captured_at": dict(self.captured_at),
            "evidence_rewritten": False,
        }


def _read_json_object(path: Path, description: str) -> Mapping[str, Any]:
    if not path.is_file():
        raise RuntimeEvidenceInvalid(
            f"RUNTIME_EVIDENCE_MISSING: {description} is absent at {path}. The "
            "successor qualification is gated on the committed preflight "
            "evidence; absent evidence is a stop, never something to recapture."
        )
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeEvidenceInvalid(
            f"RUNTIME_EVIDENCE_UNREADABLE: {description} at {path}: {error}"
        ) from error
    if not isinstance(loaded, Mapping):
        raise RuntimeEvidenceInvalid(
            f"RUNTIME_EVIDENCE_UNREADABLE: {description} is not a JSON object"
        )
    return loaded


def _reconstruct_snapshot(payload: Mapping[str, Any], *, label: str) -> RuntimeSnapshotV1:
    """Rebuild a ``RuntimeSnapshotV1`` from a persisted artifact, or refuse it.

    Both digests are DERIVED in ``RuntimeSnapshotV1.__post_init__`` and are never
    accepted as free-standing input, so reconstructing the object from the
    persisted invariant fields and comparing the two digests is an independent
    recomputation rather than a restatement of what the file claims.
    """

    retry = payload.get("retry_policy")
    if not isinstance(retry, Mapping):
        raise RuntimeEvidenceInvalid(
            f"RUNTIME_EVIDENCE_TAMPERED: {label} carries no retry_policy object"
        )
    retryable = retry.get("retryable_error_classes")
    if not isinstance(retryable, Sequence) or isinstance(retryable, (str, bytes)):
        raise RuntimeEvidenceInvalid(
            f"RUNTIME_EVIDENCE_TAMPERED: {label} retry_policy."
            "retryable_error_classes is not a list"
        )
    try:
        return RuntimeSnapshotV1(
            provider_name=payload["provider_name"],
            model=payload["model"],
            endpoint=payload["endpoint"],
            provider_config_digest=payload["provider_config_digest"],
            provider_parameters_digest=payload["provider_parameters_digest"],
            timeout_seconds=payload["timeout_seconds"],
            retry_policy=RetryPolicyV1(
                max_attempts=retry["max_attempts"],
                backoff_kind=retry["backoff_kind"],
                initial_delay_seconds=retry["initial_delay_seconds"],
                max_delay_seconds=retry["max_delay_seconds"],
                retryable_error_classes=tuple(retryable),
            ),
            tool_contract_policy=payload["tool_contract_policy"],
            native_tool_adapter_version=payload["native_tool_adapter_version"],
            package_source_sha256=payload["package_source_sha256"],
            python_version=payload["python_version"],
            artifact_version=payload["artifact_version"],
            prompt_digest=payload["prompt_digest"],
            experiment_config_digest=payload["experiment_config_digest"],
            models_config_digest=payload["models_config_digest"],
            environment_fingerprint=payload["environment_fingerprint"],
            captured_at=payload["captured_at"],
        )
    except Exception as error:  # noqa: BLE001 - every malformation is one refusal
        raise RuntimeEvidenceInvalid(
            f"RUNTIME_EVIDENCE_TAMPERED: {label} does not reconstruct as a "
            f"RuntimeSnapshotV1: {type(error).__name__}: {error}"
        ) from error


def _validate_snapshot_artifact(
    artifact: Mapping[str, Any], *, provider_slot: str
) -> tuple[Mapping[str, Any], RuntimeSnapshotV1]:
    """Validate one committed snapshot artifact end to end, or refuse it."""

    label = runtime_snapshot_artifact_name(provider_slot)
    arm = SLOT_ARM[provider_slot]
    expected_model = protocol.EXPECTED_MODEL[arm]

    for key, expected in (
        ("record_kind", RUNTIME_SNAPSHOT_RECORD_KIND),
        ("capture_kind", RUNTIME_SNAPSHOT_CAPTURE_KIND),
        ("capture_callable", CAPTURE_CALLABLE),
        ("candidate_identifier", protocol.CANDIDATE_IDENTIFIER),
        ("provider_slot", provider_slot),
        ("model", expected_model),
    ):
        if artifact.get(key) != expected:
            raise RuntimeEvidenceInvalid(
                f"RUNTIME_EVIDENCE_TAMPERED: {label} declares {key}="
                f"{artifact.get(key)!r}, the frozen expectation is {expected!r}"
            )

    payload = artifact.get("snapshot")
    if not isinstance(payload, Mapping):
        raise RuntimeEvidenceInvalid(
            f"RUNTIME_EVIDENCE_TAMPERED: {label} carries no snapshot object"
        )
    if len(payload) != RUNTIME_SNAPSHOT_KEY_COUNT:
        raise RuntimeEvidenceInvalid(
            f"RUNTIME_EVIDENCE_TAMPERED: {label} carries a {len(payload)}-key "
            f"snapshot; RuntimeSnapshotV1 is closed at {RUNTIME_SNAPSHOT_KEY_COUNT}"
        )

    snapshot = _reconstruct_snapshot(payload, label=label)

    # THE SELF-DIGEST VALIDATION.  Recomputed, then compared three ways: against
    # what the artifact recorded, against what this module pins, and -- for the
    # identity -- against what a later FRESH capture will have to reproduce.
    if payload.get("schema_version") != snapshot.schema_version:
        raise RuntimeEvidenceInvalid(
            f"RUNTIME_EVIDENCE_TAMPERED: {label} schema_version is "
            f"{payload.get('schema_version')!r}, not {snapshot.schema_version!r}"
        )
    if payload.get("runtime_identity_digest") != snapshot.runtime_identity_digest:
        raise RuntimeEvidenceInvalid(
            f"RUNTIME_EVIDENCE_TAMPERED: {label} records runtime_identity_digest "
            f"{payload.get('runtime_identity_digest')!r}, its own invariant fields "
            f"hash to {snapshot.runtime_identity_digest}"
        )
    if payload.get("self_digest") != snapshot.self_digest:
        raise RuntimeEvidenceInvalid(
            f"RUNTIME_EVIDENCE_TAMPERED: {label} records self_digest "
            f"{payload.get('self_digest')!r}, its own canonical payload hashes to "
            f"{snapshot.self_digest}"
        )
    if snapshot.runtime_identity_digest != CANONICAL_RUNTIME_IDENTITY[provider_slot]:
        raise RuntimeEvidenceInvalid(
            f"RUNTIME_EVIDENCE_TAMPERED: {label} presents runtime identity "
            f"{snapshot.runtime_identity_digest}, the canonical preflight identity "
            f"is {CANONICAL_RUNTIME_IDENTITY[provider_slot]}"
        )
    if snapshot.self_digest != CANONICAL_RUNTIME_SELF_DIGEST[provider_slot]:
        raise RuntimeEvidenceInvalid(
            f"RUNTIME_EVIDENCE_TAMPERED: {label} presents self digest "
            f"{snapshot.self_digest}, the committed observation is "
            f"{CANONICAL_RUNTIME_SELF_DIGEST[provider_slot]}"
        )
    if snapshot.captured_at != CANONICAL_RUNTIME_CAPTURED_AT[provider_slot]:
        raise RuntimeEvidenceInvalid(
            f"RUNTIME_EVIDENCE_TAMPERED: {label} presents captured_at "
            f"{snapshot.captured_at!r}, the committed observation is "
            f"{CANONICAL_RUNTIME_CAPTURED_AT[provider_slot]!r}"
        )
    if snapshot.tool_contract_policy != protocol.EXPECTED_TOOL_CONTRACT_POLICY[arm]:
        raise RuntimeEvidenceInvalid(
            f"RUNTIME_EVIDENCE_TAMPERED: {label} presents tool_contract_policy "
            f"{snapshot.tool_contract_policy!r}, the frozen pin is "
            f"{protocol.EXPECTED_TOOL_CONTRACT_POLICY[arm]!r}"
        )
    if snapshot.native_tool_adapter_version != (
        protocol.EXPECTED_NATIVE_TOOL_ADAPTER_VERSION
    ):
        raise RuntimeEvidenceInvalid(
            f"RUNTIME_EVIDENCE_TAMPERED: {label} presents adapter "
            f"{snapshot.native_tool_adapter_version!r}, the frozen pin is "
            f"{protocol.EXPECTED_NATIVE_TOOL_ADAPTER_VERSION!r}"
        )
    if snapshot.endpoint != protocol.EXPECTED_ENDPOINT:
        raise RuntimeEvidenceInvalid(
            f"RUNTIME_EVIDENCE_TAMPERED: {label} presents endpoint "
            f"{snapshot.endpoint!r}, the frozen pin is {protocol.EXPECTED_ENDPOINT!r}"
        )
    return payload, snapshot


def _validate_report(report: Mapping[str, Any]) -> None:
    """Every claim the preflight report makes about the act it recorded."""

    for key, expected in (
        ("record_kind", RUNTIME_EVIDENCE_RECORD_KIND),
        ("schema_version", RUNTIME_EVIDENCE_SCHEMA_VERSION),
        ("candidate_identifier", protocol.CANDIDATE_IDENTIFIER),
        ("candidate_status_at_entry", protocol.CANDIDATE_STATUS_AT_ENTRY),
        ("candidate_qualification_status", protocol.CANDIDATE_QUALIFICATION_STATUS),
        ("canonical_main_commit", RUNTIME_EVIDENCE_CAPTURE_COMMIT),
        (
            "authorization_canonical_main_commit",
            RUNTIME_EVIDENCE_AUTHORIZATION_COMMIT,
        ),
        ("authorization_record", RUNTIME_EVIDENCE_AUTHORIZATION_RECORD),
        ("authorization_version", RUNTIME_EVIDENCE_AUTHORIZATION_VERSION),
        ("benchmark_version", protocol.BENCHMARK_VERSION),
        ("benchmark_case_bytes_digest", protocol.BENCHMARK_CASE_BYTES_DIGEST),
        ("canonical_exposure_digest", protocol.CANONICAL_EXPOSURE_DIGEST),
        ("experiment_config", protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE),
        ("models_config", protocol.CANONICAL_MODELS_RELATIVE),
        ("qualification_results_namespace", protocol.RESULTS_NAMESPACE),
        ("qualification_results_namespace_exists", False),
    ):
        if report.get(key) != expected:
            raise RuntimeEvidenceInvalid(
                f"RUNTIME_EVIDENCE_TAMPERED: the preflight report declares {key}="
                f"{report.get(key)!r}, the frozen expectation is {expected!r}"
            )

    boundary = report.get("execution_boundary")
    if not isinstance(boundary, Mapping):
        raise RuntimeEvidenceInvalid(
            "RUNTIME_EVIDENCE_TAMPERED: the preflight report records no "
            "execution_boundary block"
        )
    for name, expected_flag in REQUIRED_EVIDENCE_BOUNDARY.items():
        if boundary.get(name) is not expected_flag:
            raise RuntimeEvidenceInvalid(
                f"RUNTIME_EVIDENCE_TAMPERED: the preflight report records "
                f"{name}={boundary.get(name)!r}; the capture performed and "
                f"authorized nothing beyond a metadata observation"
            )

    contact = report.get("metadata_contact")
    if not isinstance(contact, Mapping):
        raise RuntimeEvidenceInvalid(
            "RUNTIME_EVIDENCE_TAMPERED: the preflight report records no "
            "metadata_contact block"
        )
    if contact.get("live_runtime_version") != protocol.EXPECTED_RUNTIME_VERSION:
        raise RuntimeEvidenceInvalid(
            "RUNTIME_EVIDENCE_TAMPERED: the preflight observed runtime "
            f"{contact.get('live_runtime_version')!r}, the frozen pin is "
            f"{protocol.EXPECTED_RUNTIME_VERSION!r}"
        )
    if contact.get("runtime_version_comparison") != protocol.RUNTIME_VERSION_COMPARISON:
        raise RuntimeEvidenceInvalid(
            "RUNTIME_EVIDENCE_TAMPERED: the preflight softened the runtime version "
            "comparison"
        )
    if contact.get("request_body_sent") is not False:
        raise RuntimeEvidenceInvalid(
            "RUNTIME_EVIDENCE_TAMPERED: the preflight records a request body"
        )
    if contact.get("credential_transmitted") is not False:
        raise RuntimeEvidenceInvalid(
            "RUNTIME_EVIDENCE_TAMPERED: the preflight records a transmitted credential"
        )
    if contact.get("fail_closed_conditions_triggered"):
        raise RuntimeEvidenceInvalid(
            "RUNTIME_EVIDENCE_TAMPERED: the preflight recorded fail-closed "
            f"conditions {contact.get('fail_closed_conditions_triggered')!r}; a held "
            "preflight is not evidence that the environment agreed"
        )
    live = contact.get("live_model_identities")
    if not isinstance(live, Mapping) or dict(live) != dict(
        protocol.EXPECTED_MODEL_DIGEST
    ):
        raise RuntimeEvidenceInvalid(
            "RUNTIME_EVIDENCE_TAMPERED: the preflight's observed model identities "
            "are not the two prospectively frozen digests"
        )

    boundary_history = report.get("historical_boundary")
    if not isinstance(boundary_history, Mapping):
        raise RuntimeEvidenceInvalid(
            "RUNTIME_EVIDENCE_TAMPERED: the preflight report records no "
            "historical_boundary block"
        )
    if boundary_history.get("phase_p_evidence_touched") is not False:
        raise RuntimeEvidenceInvalid(
            "RUNTIME_EVIDENCE_TAMPERED: the preflight claims Phase-P evidence was "
            "touched"
        )
    if boundary_history.get("historical_row_access_authorized") is not False:
        raise RuntimeEvidenceInvalid(
            "RUNTIME_EVIDENCE_TAMPERED: the preflight claims historical row access"
        )

    capture = report.get("capture")
    if not isinstance(capture, Mapping):
        raise RuntimeEvidenceInvalid(
            "RUNTIME_EVIDENCE_TAMPERED: the preflight report records no capture block"
        )
    if capture.get("capture_callable") != CAPTURE_CALLABLE:
        raise RuntimeEvidenceInvalid(
            "RUNTIME_EVIDENCE_TAMPERED: the capture names callable "
            f"{capture.get('capture_callable')!r}, the repository-owned capture is "
            f"{CAPTURE_CALLABLE!r}"
        )
    for name in ("timestamp_synthesized", "identity_copied_into_snapshot",
                 "snapshot_manually_instantiated", "field_override_supplied"):
        if capture.get(name) is not False:
            raise RuntimeEvidenceInvalid(
                f"RUNTIME_EVIDENCE_TAMPERED: the capture records {name}="
                f"{capture.get(name)!r}; a synthesized snapshot is not an observation"
            )
    strata = capture.get("capture_strata")
    if [tuple(item) for item in (strata or [])] != [
        tuple(item) for item in protocol.PROPOSED_STRATA
    ]:
        raise RuntimeEvidenceInvalid(
            "RUNTIME_EVIDENCE_TAMPERED: the capture covers "
            f"{strata!r}, the frozen strata are "
            f"{[list(item) for item in protocol.PROPOSED_STRATA]}"
        )


def load_runtime_evidence(namespace: Path | str | None = None) -> CanonicalRuntimeEvidence:
    """Load and fully validate the committed preflight evidence, or refuse it.

    Nothing here writes.  Nothing here recaptures.  Absent, malformed, tampered
    or disagreeing evidence raises :class:`RuntimeEvidenceInvalid`, which the
    driver turns into a stop with zero cells executed -- because prior evidence
    the driver cannot validate is exactly the situation in which continuing
    would be measuring under an unverified instrument.
    """

    root = (
        PROJECT_ROOT / RUNTIME_EVIDENCE_NAMESPACE
        if namespace is None
        else Path(namespace)
    )
    report_path = root / RUNTIME_EVIDENCE_REPORT_NAME
    report = _read_json_object(report_path, "the runtime preflight report")
    _validate_report(report)

    capture = report["capture"]
    recorded = capture.get("snapshots")
    if not isinstance(recorded, Mapping) or set(recorded) != set(ARM_SLOT.values()):
        raise RuntimeEvidenceInvalid(
            "RUNTIME_EVIDENCE_TAMPERED: the capture records snapshots for "
            f"{sorted(recorded) if isinstance(recorded, Mapping) else recorded!r}, "
            f"the frozen strata are {sorted(ARM_SLOT.values())}"
        )

    snapshots: dict[str, Mapping[str, Any]] = {}
    identity: dict[str, str] = {}
    self_digest: dict[str, str] = {}
    captured_at: dict[str, str] = {}
    for arm in protocol.ARM_ORDER:
        slot = ARM_SLOT[arm]
        name = runtime_snapshot_artifact_name(slot)
        artifact = _read_json_object(root / name, f"the {slot} runtime snapshot")
        payload, snapshot = _validate_snapshot_artifact(artifact, provider_slot=slot)

        summary = recorded[slot]
        if not isinstance(summary, Mapping):
            raise RuntimeEvidenceInvalid(
                f"RUNTIME_EVIDENCE_TAMPERED: the capture summary for {slot} is not "
                "an object"
            )
        for key, expected in (
            ("artifact", name),
            ("model", protocol.EXPECTED_MODEL[arm]),
            ("runtime_identity_digest", snapshot.runtime_identity_digest),
            ("self_digest", snapshot.self_digest),
            ("captured_at", snapshot.captured_at),
            ("field_count", RUNTIME_SNAPSHOT_KEY_COUNT),
            ("self_digest_validated", True),
        ):
            if summary.get(key) != expected:
                raise RuntimeEvidenceInvalid(
                    f"RUNTIME_EVIDENCE_TAMPERED: the capture summary for {slot} "
                    f"records {key}={summary.get(key)!r}, the artifact presents "
                    f"{expected!r}"
                )
        snapshots[slot] = payload
        identity[slot] = snapshot.runtime_identity_digest
        self_digest[slot] = snapshot.self_digest
        captured_at[slot] = snapshot.captured_at

    return CanonicalRuntimeEvidence(
        report=report,
        report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
        snapshots=snapshots,
        identity=identity,
        self_digest=self_digest,
        captured_at=captured_at,
        capture_commit=str(report["canonical_main_commit"]),
    )


def check_runtime_evidence(namespace: Path | str | None = None) -> list[str]:
    """The runtime-evidence gate as an offline check.  Empty means PASS."""

    try:
        load_runtime_evidence(namespace)
    except RuntimeEvidenceInvalid as error:
        return [str(error)]
    return []


# --------------------------------------------------------------------------
# 1. The capability.  It is what execution costs, and it cannot be bought today.
# --------------------------------------------------------------------------

_GRANT_TOKEN: object = object()

#: The attribute the real cell executor carries.  The offline seam refuses a
#: callable that has it, so "this is the real executor" is a checkable property
#: of the object rather than a claim about the caller.
REAL_EXECUTOR_MARKER = "successor_real_model_executor"


def human_gate_refusal(*, execute_flag: bool, env: Mapping[str, str]) -> str | None:
    """The exercise-gate refusal, or ``None`` when BOTH gates are open.

    THESE ARE EXERCISE GATES, NOT AUTHORIZATION.  Both being open means only
    that a human at this console asked for the run; it does not mean a human
    record permits one.  :func:`grant_execution_authorization` checks the
    authorization BEFORE it looks at either of them, which is why an open
    environment can never read as consent.
    """

    reasons: list[str] = []
    if not execute_flag:
        reasons.append(
            f"GATE_CLOSED: {protocol.HUMAN_GATE_FLAG} was not supplied"
        )
    if env.get(protocol.HUMAN_GATE_ENV) != protocol.HUMAN_GATE_VALUE:
        reasons.append(
            f"GATE_CLOSED: {protocol.HUMAN_GATE_ENV} must be exactly "
            f"{protocol.HUMAN_GATE_VALUE!r}"
        )
    return "\n".join(reasons) if reasons else None


def _process_gate_refusal() -> str | None:
    """Evaluate both exercise gates against THIS PROCESS, never against arguments."""

    return human_gate_refusal(
        execute_flag=protocol.HUMAN_GATE_FLAG in sys.argv[1:], env=os.environ
    )


@dataclass(frozen=True, slots=True)
class SuccessorExecutionAuthorization:
    """Proof that a real successor execution is permitted.  Unobtainable today.

    The constructor demands the module-private token BY IDENTITY, so the object
    cannot be forged by passing ``True``; and it re-derives the whole decision
    rather than trusting whoever built it.  The order inside is the order that
    matters: :func:`successor_qualification_protocol.require_execution_authorization`
    runs FIRST, so while the governing record withholds qualification execution
    this class raises before it has looked at a flag or an environment variable.
    """

    granted: bool = field(default=False)

    def __init__(self, token: object) -> None:
        if token is not _GRANT_TOKEN:
            raise SuccessorExecutionRefused(
                "SuccessorExecutionAuthorization cannot be constructed directly; "
                "grant_execution_authorization() is the only thing that mints one, "
                "and it mints one only after a human record authorizes execution."
            )
        protocol.require_execution_authorization()
        refusal = _process_gate_refusal()  # pragma: no cover - unreachable today
        if refusal is not None:  # pragma: no cover - unreachable today
            raise SuccessorExecutionRefused(refusal)
        object.__setattr__(self, "granted", True)  # pragma: no cover


def grant_execution_authorization() -> SuccessorExecutionAuthorization:
    """Mint the capability, or refuse.  Today it always refuses.

    It reads ``sys.argv`` and ``os.environ`` itself and takes no argument, so
    nothing a caller passes can influence what it decides.
    """

    return SuccessorExecutionAuthorization(_GRANT_TOKEN)


def require_execution_authorization(authorization: object) -> None:
    """Re-prove a capability at the moment it is used, never on trust.

    Re-evaluated at every real primitive and at every cell: a hundred and two
    cells are a long time, and a grant minted under one process state must not
    survive into a state that no longer authorizes anything.
    """

    if not isinstance(authorization, SuccessorExecutionAuthorization):
        raise SuccessorExecutionRefused(
            "REAL_EXECUTION_REFUSED: a SuccessorExecutionAuthorization is required. "
            "Real-model execution is reachable only through "
            "execute_authorized_real_run(), which requires a capability that "
            "grant_execution_authorization() cannot mint while "
            f"{protocol.AUTHORIZATION_RECORD_RELATIVE} withholds qualification "
            "execution."
        )
    protocol.require_execution_authorization()
    refusal = _process_gate_refusal()  # pragma: no cover - unreachable today
    if refusal is not None:  # pragma: no cover - unreachable today
        raise SuccessorExecutionRefused(refusal)


def _names_a_real_seam(candidate: Any) -> str | None:
    """Whether *candidate* is, or wraps, a primitive that can reach the runtime."""

    seen: set[int] = set()
    current = candidate
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if current is probe_ollama_metadata:
            return "probe_ollama_metadata"
        if current is _REAL_CELL_EXECUTOR_FACTORY:
            return "make_cell_executor"
        if getattr(current, REAL_EXECUTOR_MARKER, False):
            return "an executor built by make_cell_executor"
        current = getattr(current, "func", None) or getattr(current, "__wrapped__", None)
    return None


def check_confirmatory_remains_impossible() -> list[str]:
    """Confirmatory registration, randomization and execution stay out of reach.

    Stated as a check rather than as prose because "this driver does not do X" is
    a claim, and a claim that no test can fail is not a control.
    """

    failures: list[str] = []
    for name in (
        "CONFIRMATORY_EXECUTION_AUTHORIZED",
        "AUTHORIZES_CONFIRMATORY_EXECUTION",
        "RANDOMIZATION_REALIZATION_AUTHORIZED",
        "STAGE_C_FINAL_REGISTRATION_AUTHORIZED",
    ):
        if getattr(protocol, name) is not False:
            failures.append(
                f"CONFIRMATORY_BOUNDARY: successor_qualification_protocol.{name} is "
                f"{getattr(protocol, name)!r}; this driver performs no confirmatory "
                "registration, randomization or execution and must never be able to"
            )
    for treatment in protocol.OUT_OF_SCOPE_TREATMENTS:
        if treatment in protocol.EXPECTED_TREATMENTS:
            failures.append(
                f"CONFIRMATORY_BOUNDARY: {treatment!r} is an out-of-scope treatment "
                "and is present in the executed treatment set"
            )
    if list(protocol.EXPECTED_TREATMENTS) != [protocol.QA_MODE]:
        failures.append(
            f"CONFIRMATORY_BOUNDARY: the executed treatment set is "
            f"{list(protocol.EXPECTED_TREATMENTS)}, the frozen qualification "
            f"treatment is exactly [{protocol.QA_MODE!r}]"
        )
    return failures


# --------------------------------------------------------------------------
# 2. The row contract: what a successor row must carry to be a measurement
# --------------------------------------------------------------------------

#: The experiment kind, carried forward from the qualification lineage.  It is
#: one of the four values ``ExperimentRunner`` accepts and is not invented here.
EXPERIMENT_KIND = "real_model_connectivity_smoke"

#: The two identity fields the DRIVER stamps, because the canonical runner emits
#: neither and both are frozen inputs rather than runtime observations.  Every
#: other bound identity field comes from the runner, so the binding check is a
#: real check and not a tautology.
DRIVER_STAMPED_IDENTITY_FIELDS: tuple[str, ...] = ("model_digest", "run_key")

#: Fields TRANSPORTED from the cell's own persisted ``manifest.json`` because the
#: runner records them there rather than on the row.  Copying a constant instead
#: would make the disclosure precondition a tautology.
MANIFEST_TRANSPORTED_FIELDS: tuple[str, ...] = (
    "raw_schema_version",
    "tool_argument_contract_version",
    "tool_argument_contract_digest",
)

DRIVER_STAMPED_SCHEDULE_FIELDS: tuple[str, ...] = (
    "schedule_index",
    "arm",
    "cell_key",
    "cell_experiment_dir",
)

#: Identity fields an evidence event carries that must agree with the row it is
#: filed under, carried forward from the instrument unchanged.
TRACE_IDENTITY_FIELDS: tuple[str, ...] = ("task_id", "run_id", "qa_mode")

RUN_MANIFEST_CLASSIFICATION_FIELDS: tuple[str, ...] = (
    "cell",
    "index",
    "failure_class",
    "disposition",
)

#: THE PATH CONTRACT, binding on the driver and on the analyzer alike.
CELL_EXPERIMENT_DIR_CONTRACT = (
    "row['cell_experiment_dir'] is the ExperimentRunner experiment directory "
    "expressed RELATIVE TO THE SUCCESSOR OUTPUT ROOT, as a POSIX path. The "
    "analyzer resolves a cell's evidence trace as "
    "<output_root>/<cell_experiment_dir>/<row['trace_path']> and never any "
    "other way. A row that declares no experiment directory, declares no trace, "
    "or whose resolved trace is absent or unreadable is LOST EVIDENCE and is a "
    "blocking INSTRUMENT_DEFECT -- never an empty proposal list."
)

#: Row fields whose recorded value must equal the frozen successor pin.  A
#: missing key or a ``None`` is a mismatch, never agreement: an unstamped row
#: cannot be proved to have been produced under the frozen instrument.
ROW_CONTRACT_PINS: Mapping[str, Any] = {
    "instrument_version": protocol.EXPECTED_INSTRUMENT_VERSION,
    "raw_schema_version": protocol.EXPECTED_RAW_SCHEMA_VERSION,
    "native_tool_adapter_version": protocol.EXPECTED_NATIVE_TOOL_ADAPTER_VERSION,
    "tool_argument_contract_version": (
        protocol.EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION
    ),
    "tool_argument_contract_digest": protocol.EXPECTED_TOOL_ARGUMENT_CONTRACT_DIGEST,
    "benchmark_version": protocol.BENCHMARK_VERSION,
    "experiment_kind": EXPERIMENT_KIND,
}

#: Every field a completed successor row must carry.  One contract, written by
#: the driver and read by the analyzer.
SUCCESSOR_ROW_FIELDS: tuple[str, ...] = tuple(
    dict.fromkeys(
        (
            *PILOT_RAW_FIELDS_V6,
            *harness.REQUIRED_IDENTITY_FIELDS,
            *harness.REQUIRED_RC4_ROW_FIELDS,
            *DRIVER_STAMPED_SCHEDULE_FIELDS,
            *MANIFEST_TRANSPORTED_FIELDS,
        )
    )
)


def contract_drift(row: Mapping[str, Any], cell: Any | None = None) -> list[str]:
    """Every frozen contract pin the row fails to carry, or carries differently.

    The successor instrument is 5 / raw schema 6 / ``native-tools-adapter-3`` /
    ``tool-arguments-1``.  An instrument-4 / schema-5 row is refused here, which
    is the machine-enforced half of "never emit an instrument-4/schema-5
    successor row" and of the ban on cross-instrument pooling.
    """

    mismatches: list[str] = []
    for field_name, expected in sorted(ROW_CONTRACT_PINS.items()):
        if field_name not in row or row.get(field_name) is None:
            mismatches.append(
                f"{field_name} is missing from the returned row; the frozen "
                f"successor pin is {expected!r} and absence is never agreement"
            )
            continue
        actual = row[field_name]
        if field_name == "raw_schema_version":
            try:
                actual = int(actual)
            except (TypeError, ValueError):
                mismatches.append(f"raw_schema_version {actual!r} is not an integer")
                continue
        if actual != expected:
            mismatches.append(
                f"{field_name} is {actual!r}, the frozen successor pin is {expected!r}"
            )
    if cell is not None:
        expected_policy = protocol.EXPECTED_TOOL_CONTRACT_POLICY.get(str(cell.arm), "")
        actual_policy = row.get("tool_contract_policy")
        if actual_policy is None:
            mismatches.append(
                "tool_contract_policy is missing from the returned row; arm "
                f"{cell.arm!r} is frozen against {expected_policy!r}"
            )
        elif str(actual_policy) != expected_policy:
            mismatches.append(
                f"tool_contract_policy is {actual_policy!r} for arm {cell.arm!r}, "
                f"the frozen successor pin is {expected_policy!r}"
            )
    return mismatches


def provider_attempt_defects(row: Mapping[str, Any]) -> list[str]:
    """Every C3 provider-attempt telemetry defect on one row.

    Delegated to ``iqa_soa.metrics.definitions.provider_failure_attempt_violations``
    -- the repository-owned schema-6 contract -- rather than restated, so the
    driver cannot accept an attempt shape the instrument rejects, or vice versa.
    """

    attempts = row.get("provider_attempts")
    if attempts is None:
        return ["provider_attempts is missing from the row"]
    if not isinstance(attempts, Sequence) or isinstance(attempts, (str, bytes)):
        return [f"provider_attempts is {type(attempts).__name__}, not a list"]
    count = row.get("provider_attempt_count")
    if count is None or int(count) != len(attempts):
        return [
            f"provider_attempt_count is {count!r} but provider_attempts carries "
            f"{len(attempts)} entr{'y' if len(attempts) == 1 else 'ies'}"
        ]
    defects: list[str] = []
    for position, attempt in enumerate(attempts):
        if not isinstance(attempt, Mapping):
            defects.append(f"provider_attempts[{position}] is not an object")
            continue
        defects.extend(
            f"provider_attempts[{position}]: {item}"
            for item in provider_failure_attempt_violations(
                attempt, raw_schema_version=protocol.EXPECTED_RAW_SCHEMA_VERSION
            )
        )
    return defects


#: Bound once, at import, so :func:`classify_row` cannot recurse into itself when
#: the module global is rebound for the duration of a ``record`` call.
_RC4_CLASSIFY_ROW_DETAILED = harness.classify_row_detailed


def classify_row_detailed(
    row: Mapping[str, Any],
    cell: Any | None = None,
    *,
    scripted_faults: Mapping[str, Sequence[Any]] | None = None,
) -> tuple[str, str, dict[str, Any]]:
    """Classify one successor cell: contract drift FIRST, then the frozen rules.

    The drift check runs ahead of every scientific branch because a row produced
    by an instrument that is not the frozen one is not a measurement of the
    frozen experiment, and scoring it would turn drift into a finding about a
    model.
    """

    drift = contract_drift(row, cell)
    if drift:
        return (
            harness.FROZEN_ARTIFACT_MISMATCH,
            harness.IMMEDIATE_STOP,
            {
                "events": [],
                "decided_by": None,
                "reasons": [
                    "the row was not produced under the frozen successor "
                    "instrument, adapter and argument contract",
                    *drift,
                ],
            },
        )
    telemetry = provider_attempt_defects(row)
    if telemetry:
        return (
            harness.INSTRUMENT_DEFECT,
            harness.IMMEDIATE_STOP,
            {
                "events": [],
                "decided_by": None,
                "reasons": [
                    "the row does not carry the C3 provider-attempt telemetry raw "
                    "schema 6 requires",
                    *telemetry,
                ],
            },
        )
    return _RC4_CLASSIFY_ROW_DETAILED(row, cell, scripted_faults=scripted_faults)


def classify_row(
    row: Mapping[str, Any],
    cell: Any | None = None,
    *,
    scripted_faults: Mapping[str, Sequence[Any]] | None = None,
) -> tuple[str, str]:
    """``(failure_class, disposition)`` for one successor cell."""

    return classify_row_detailed(row, cell, scripted_faults=scripted_faults)[:2]


class StopController(harness.StopController):
    """The frozen stop controller, driving the successor classifier.

    Subclassed rather than copied: the schedule-order rules, the duplicate-cell
    and index checks, the identity binding, the hold accounting and the partial
    manifest are the frozen Phase-K semantics and are inherited unchanged.  Only
    the classification call is substituted, and only for the duration of one
    ``record``, so a frozen caller importing the harness directly is unaffected.
    There is still no retry, no replacement and no resume.
    """

    def record(self, cell: Any, row: Mapping[str, Any]) -> str:
        original = harness.classify_row
        harness.classify_row = classify_row
        try:
            return str(super().record(cell, row))
        finally:
            harness.classify_row = original


# --------------------------------------------------------------------------
# 3. The frozen schedule: 17 tasks x 2 arms x 3 seeds, QA OFF, and nothing else
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LoadedBenchmark:
    """The frozen 17-task selection and the fault declarations read from it."""

    manifest_sha256: str
    task_ids: tuple[str, ...]
    scripted_faults: Mapping[str, tuple[Any, ...]]


def load_benchmark(manifest_path: Path | str | None = None) -> LoadedBenchmark:
    """Load the frozen benchmark and refuse anything that is not it.

    The manifest is proven canonical by PATH, by the digest the frozen-input
    record accepted, and by the loader's own independent hash of the bytes it
    parsed -- before a single task id is taken from it.  ``benchmark_version``
    and a 17-case count are structural checks only: a copy with the tasks
    reordered would pass both while being a different experiment.
    """

    from iqa_soa.benchmark import load_frozen_pilot  # noqa: PLC0415 - import shim

    path = protocol.require_canonical_input(
        protocol.CANONICAL_MANIFEST_RELATIVE, manifest_path
    )
    frozen_pilot = load_frozen_pilot(path)
    accepted = protocol.accepted_frozen_digest(protocol.CANONICAL_MANIFEST_RELATIVE)
    if frozen_pilot.manifest_sha256 != accepted:
        raise protocol.NoncanonicalInput(
            f"FROZEN_ARTIFACT_MISMATCH: the loaded "
            f"{protocol.CANONICAL_MANIFEST_RELATIVE} hashes to "
            f"{frozen_pilot.manifest_sha256}, the successor freeze accepted {accepted}"
        )
    if frozen_pilot.benchmark_version != protocol.BENCHMARK_VERSION:
        raise protocol.SuccessorProtocolError(
            f"expected {protocol.BENCHMARK_VERSION}, got "
            f"{frozen_pilot.benchmark_version}"
        )
    if len(frozen_pilot.cases) != protocol.TASK_COUNT:
        raise protocol.SuccessorProtocolError(
            f"{protocol.BENCHMARK_VERSION} must contain exactly "
            f"{protocol.TASK_COUNT} tasks, found {len(frozen_pilot.cases)}"
        )
    return LoadedBenchmark(
        manifest_sha256=frozen_pilot.manifest_sha256,
        task_ids=tuple(frozen_pilot.selected_task_ids),
        scripted_faults=harness.scripted_faults_from_cases(list(frozen_pilot.cases)),
    )


def build_arms() -> tuple[Any, ...]:
    """The two frozen arms, in frozen order, each carrying its model identity."""

    return tuple(
        harness.ArmSpec(
            arm=arm,
            model=protocol.EXPECTED_MODEL[arm],
            model_digest=protocol.EXPECTED_MODEL_DIGEST[protocol.EXPECTED_MODEL[arm]],
        )
        for arm in protocol.ARM_ORDER
    )


def build_successor_schedule(benchmark: LoadedBenchmark) -> list[Any]:
    """The frozen arm-major / task-major / seed-minor 102-cell schedule.

    Arm order is :data:`successor_qualification_protocol.ARM_ORDER`; task order is
    the frozen manifest's own ``selected_task_ids`` order; seed order is the
    prospectively derived triple in its derived order.  The schedule is therefore
    a pure function of frozen bytes -- nothing about it is chosen here.

    QA OFF is the only treatment, and the schedule carries no treatment axis at
    all, so there is no place for a second one to appear.
    """

    schedule = harness.build_schedule(
        build_arms(),
        benchmark.task_ids,
        protocol.SEEDS,
        qa_mode=protocol.QA_MODE,
        benchmark_manifest_sha256=benchmark.manifest_sha256,
    )
    if len(schedule) != protocol.PLANNED_CELLS:
        raise protocol.SuccessorProtocolError(
            f"the frozen schedule must be exactly {protocol.PLANNED_CELLS} cells, "
            f"built {len(schedule)}"
        )
    keys = [cell.run_key for cell in schedule]
    if len(set(keys)) != len(keys):
        raise protocol.SuccessorProtocolError(
            "run_key is not unique across the frozen successor schedule"
        )
    return list(schedule)


# ``build_phase_p_schedule`` is the name the frozen analyzer resolves; the
# successor adapter binds this function to it.  Aliased rather than renamed so
# the successor schedule builder keeps its own honest name here.
def cell_slug(cell: Any) -> str:
    """A stable, filesystem-safe directory name for one cell's raw evidence."""

    return f"{cell.index:03d}-{cell.arm}-{cell.task_id}-{cell.seed}"


def schedule_digest(schedule: Sequence[Any]) -> str:
    """A single digest over the whole frozen schedule, for the run manifest."""

    material = "\n".join(
        "|".join(
            [
                str(cell.index),
                cell.arm,
                cell.task_id,
                str(cell.seed),
                cell.model,
                cell.model_digest,
                cell.qa_mode,
                cell.benchmark_manifest_sha256,
                cell.run_key,
            ]
        )
        for cell in schedule
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def cells_root(output_root: Path) -> Path:
    """The directory that holds every cell's own experiment directory."""

    return Path(output_root).joinpath(*protocol.CELLS_SUBDIR)


def cell_evidence_root(output_root: Path, cell: Any) -> Path:
    """The ONLY directory a given frozen cell's evidence may live beneath."""

    return cells_root(output_root) / cell_slug(cell)


def cell_experiment_dir_value(experiment_dir: Path, output_root: Path) -> str:
    """Serialize an experiment directory under :data:`CELL_EXPERIMENT_DIR_CONTRACT`."""

    try:
        relative = Path(experiment_dir).resolve().relative_to(Path(output_root).resolve())
    except ValueError as error:
        raise protocol.SuccessorProtocolError(
            f"the cell experiment directory {experiment_dir} is not beneath the "
            f"successor output root {output_root}; {CELL_EXPERIMENT_DIR_CONTRACT}"
        ) from error
    return relative.as_posix()


def _is_absolute_anywhere(value: str) -> bool:
    from pathlib import PurePosixPath, PureWindowsPath  # noqa: PLC0415

    return PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()


def contained_child(
    base: Path, value: str, *, label: str, must_be_dir: bool = False
) -> tuple[Path | None, str]:
    """Resolve ``value`` strictly beneath ``base``, or say why it is refused.

    Refuses, in order: an empty value, an absolute path in either platform
    flavour, any ``..`` component, and anything whose CANONICAL resolution does
    not sit strictly beneath the canonical ``base``.  Containment is checked on
    resolved paths -- so a symlink pointing out of the tree is refused too -- and
    BEFORE the target is read, never by joining and then testing ``is_file()``.
    """

    text = str(value).strip()
    if not text:
        return None, f"{label} is empty"
    if _is_absolute_anywhere(text):
        return None, f"{label} {value!r} is an absolute path; it must be relative"
    if any(part == ".." for part in Path(text.replace("\\", "/")).parts):
        return None, f"{label} {value!r} traverses with '..'"
    resolved = (Path(base) / text).resolve()
    anchor = Path(base).resolve()
    if resolved == anchor or anchor not in resolved.parents:
        return None, (
            f"{label} {value!r} resolves to {resolved}, which is not strictly "
            f"beneath {anchor}"
        )
    if must_be_dir and not resolved.is_dir():
        return None, f"{label} {value!r} is not an existing directory"
    return resolved, ""


# --------------------------------------------------------------------------
# 4. Provider construction and the immediate pre-inference environment check
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RuntimeMetadata:
    """What a metadata-only probe observed about one model.

    ``model_present`` is carried separately from ``model_digest`` so that "the
    runtime does not have this model" and "the runtime has it under a different
    digest" stay two distinguishable environment holds rather than one.
    """

    runtime_version: str
    model_present: bool
    model_digest: str


#: ``(model) -> RuntimeMetadata``.  :func:`probe_ollama_metadata` deliberately
#: does NOT have this shape -- it additionally requires a keyword-only
#: capability -- so it cannot be handed anywhere a bare probe is expected and
#: silently work.  The real path binds the capability into it first.
MetadataProbe = Callable[[str], RuntimeMetadata]

#: ``(provider_slot) -> RuntimeSnapshotV1``.  The fresh capture seam.
SnapshotCapture = Callable[[str], Any]

#: ``(cell) -> raw row``.
CellExecutor = Callable[[Any], Mapping[str, Any]]

#: ``(config_path, manifest_path, output_root) -> CellExecutor``.  The run loop is
#: handed a FACTORY rather than an optional executor, so there is no ``None`` for
#: it to resolve into a real-model default.
CellExecutorFactory = Callable[[Path, Path, Path], CellExecutor]

OLLAMA_METADATA_ORIGIN = "http://127.0.0.1:11434"
OLLAMA_VERSION_PATH = "/api/version"
OLLAMA_TAGS_PATH = "/api/tags"


def _ollama_get(url: str, *, timeout: float = 10.0) -> Mapping[str, Any]:
    """One bodiless, headerless GET against the local runtime.  REAL CONTACT."""

    request = urllib.request.Request(url, method="GET")  # noqa: S310 - fixed loopback
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise protocol.EnvironmentHold(
            f"ENVIRONMENT_HOLD: {url} did not return a JSON object"
        )
    return payload


def probe_ollama_metadata(
    model: str, *, authorization: SuccessorExecutionAuthorization
) -> RuntimeMetadata:
    """Observe the live runtime version and one model's digest.  REQUIRES the capability.

    Metadata only: ``GET /api/version`` and ``GET /api/tags``, no credential, no
    header, no body, and no inference of any kind.  It is still gated, because
    reaching the runtime at all is contact, and contact is what the governing
    record withholds.
    """

    require_execution_authorization(authorization)
    version_payload = _ollama_get(f"{OLLAMA_METADATA_ORIGIN}{OLLAMA_VERSION_PATH}")
    tags_payload = _ollama_get(f"{OLLAMA_METADATA_ORIGIN}{OLLAMA_TAGS_PATH}")
    version = version_payload.get("version")
    entries = tags_payload.get("models")
    digest = ""
    present = False
    if isinstance(entries, Sequence) and not isinstance(entries, (str, bytes)):
        for entry in entries:
            if isinstance(entry, Mapping) and entry.get("name") == model:
                present = True
                raw = str(entry.get("digest") or "")
                digest = raw.split(":", 1)[-1] if ":" in raw else raw
                break
    return RuntimeMetadata(
        runtime_version=version if type(version) is str else "",
        model_present=present,
        model_digest=digest,
    )


#: The real probe, bound once at import so :func:`_names_a_real_seam` can
#: recognise it through a wrapper.  The control is that the function validates
#: the capability itself; this is a convenience on top of that.
_REAL_METADATA_PROBE = probe_ollama_metadata


def load_successor_provider(provider_slot: str) -> Any:
    """Build one frozen provider from the SUCCESSOR configuration and nothing else.

    ``configs/successor-models.yaml`` and ``configs/successor-qualification.yaml``
    are the only configurations read.  Every historical phase configuration is
    refused by name in
    :data:`successor_qualification_protocol.FORBIDDEN_RUNTIME_CONFIGS`, and none
    is loaded here: a historical provider configuration can never satisfy a
    successor precondition, however identical its settings look.
    """

    from iqa_soa.experiment.runner import load_experiment_config, load_provider  # noqa: PLC0415

    if provider_slot not in SLOT_ARM:
        raise protocol.SuccessorProtocolError(
            f"{provider_slot!r} is not one of the two frozen provider slots "
            f"{sorted(SLOT_ARM)}"
        )
    config_path = protocol.require_canonical_input(
        protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE
    )
    config = load_experiment_config(config_path)
    models_path = Path(config.models_path).resolve()
    canonical_models = (PROJECT_ROOT / protocol.CANONICAL_MODELS_RELATIVE).resolve()
    if models_path != canonical_models:
        raise protocol.NoncanonicalInput(
            f"PROTOCOL_DEVIATION: the successor ExperimentConfig resolves its model "
            f"configuration to {models_path}; the frozen one is {canonical_models}"
        )
    return load_provider(models_path, provider_name=provider_slot)


def capture_stratum_runtime_snapshot(provider_slot: str) -> Any:
    """Freshly capture one ``RuntimeSnapshotV1`` through the repository-owned callable.

    NO CONTACT.  ``capture_runtime_snapshot_v1`` reads the frozen configuration,
    the provider descriptor and the package source; it opens no socket and sends
    no prompt.  It is therefore reachable without the capability, and the offline
    suite exercises the REAL capture rather than a stand-in -- which is what
    makes "a fresh capture reproduces the canonical identity" a proved property
    of this repository instead of a promise about a future one.

    The snapshot is never manually instantiated and no field is overridden here:
    the digests are derived inside ``RuntimeSnapshotV1`` from what the capture
    observed, which is the only reason comparing them to the canonical identity
    means anything.
    """

    from iqa_soa.experiment.confirmatory import (  # noqa: PLC0415
        capture_runtime_snapshot_v1,
    )
    from iqa_soa.experiment.runner import load_experiment_config  # noqa: PLC0415

    config = load_experiment_config(
        protocol.require_canonical_input(
            protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE
        )
    )
    provider = load_successor_provider(provider_slot)
    return capture_runtime_snapshot_v1(config=config, provider=provider)


def environment_preflight(
    *,
    evidence: CanonicalRuntimeEvidence,
    probe: MetadataProbe,
    capture: SnapshotCapture,
) -> tuple[list[str], dict[str, Any]]:
    """THE IMMEDIATE PRE-INFERENCE CHECK.  Both arms, before either runs a cell.

    In order, per stratum:

    1. the live runtime version, by EXACT string equality against ``0.32.13``;
    2. the live model digest, against the prospectively frozen pin;
    3. the tool contract policy and the protocol, against their pins; and
    4. a FRESH ``RuntimeSnapshotV1``, whose ``runtime_identity_digest`` must
       equal the canonical preflight identity.  ``captured_at`` and
       ``self_digest`` differ, and are required to differ in nothing.

    A prior observation is never accepted in place of a fresh one, and a MISSING
    observation is a mismatch: "the preflight did not look" must never read as
    "the preflight found agreement".  Any disagreement returns failures, and the
    caller stops with ``ENVIRONMENT_HOLD`` and ZERO cells executed.  Nothing here
    pulls, updates, retags or replaces a model, installs or repins a runtime, or
    rewrites a frozen input.
    """

    failures: list[str] = []
    observations: dict[str, Any] = {
        "runtime_version_comparison": protocol.RUNTIME_VERSION_COMPARISON,
        "expected_runtime_version": protocol.EXPECTED_RUNTIME_VERSION,
        "canonical_runtime_identity": dict(evidence.identity),
        "fresh_capture_callable": CAPTURE_CALLABLE,
        "strata": {},
    }

    for arm in protocol.ARM_ORDER:
        slot = ARM_SLOT[arm]
        model = protocol.EXPECTED_MODEL[arm]
        entry: dict[str, Any] = {"arm": arm, "model": model, "provider_slot": slot}
        observations["strata"][slot] = entry

        try:
            metadata = probe(model)
        except Exception as error:  # noqa: BLE001 - an unobserved runtime is a hold
            failures.append(
                f"ENVIRONMENT_HOLD: the {arm!r} metadata probe failed "
                f"({type(error).__name__}: {error}); an unobserved runtime fact is "
                "never treated as a matching one"
            )
            continue
        entry["live_runtime_version"] = metadata.runtime_version
        entry["model_present"] = metadata.model_present
        entry["live_model_digest"] = metadata.model_digest
        if not metadata.model_present:
            failures.append(
                f"ENVIRONMENT_HOLD: the live runtime does not present model "
                f"{model!r}. The successor protocol never pulls, downloads, "
                "updates, retags or replaces a model."
            )
            continue
        try:
            protocol.verify_runtime_identity(
                arm=arm,
                observed={
                    "model": model,
                    "model_digest": metadata.model_digest,
                    "runtime_version": metadata.runtime_version,
                    "tool_contract_policy": (
                        protocol.EXPECTED_TOOL_CONTRACT_POLICY[arm]
                    ),
                    "protocol": protocol.EXPECTED_PROTOCOL,
                },
            )
        except protocol.EnvironmentHold as hold:
            failures.append(str(hold))
            continue

        try:
            snapshot = capture(slot)
        except Exception as error:  # noqa: BLE001 - a failed capture is a hold
            failures.append(
                f"ENVIRONMENT_HOLD: the fresh {slot} RuntimeSnapshotV1 capture "
                f"failed ({type(error).__name__}: {error}); a stratum with no fresh "
                "runtime provenance never executes a cell"
            )
            continue

        fresh_identity = getattr(snapshot, "runtime_identity_digest", None)
        fresh_self = getattr(snapshot, "self_digest", None)
        fresh_at = getattr(snapshot, "captured_at", None)
        if not isinstance(fresh_identity, str) or not fresh_identity:
            failures.append(
                f"ENVIRONMENT_HOLD: the fresh {slot} capture produced no "
                "runtime_identity_digest"
            )
            continue
        entry["fresh_runtime_identity_digest"] = fresh_identity
        entry["fresh_self_digest"] = fresh_self
        entry["fresh_captured_at"] = fresh_at
        entry["canonical_runtime_identity_digest"] = evidence.identity[slot]
        expected_identity = evidence.identity[slot]
        if fresh_identity != expected_identity:
            failures.append(
                f"ENVIRONMENT_HOLD: the fresh {slot} RuntimeSnapshotV1 presents "
                f"runtime identity {fresh_identity}, the canonical preflight "
                f"identity is {expected_identity}. The successor protocol never "
                "repins a runtime identity to whatever the environment happens to "
                f"present; the resolution is {protocol.RUNTIME_VERSION_RESOLUTION}."
            )
            continue
        entry["runtime_identity_match"] = True

    observations["environment_hold"] = bool(failures)
    return failures, observations


# --------------------------------------------------------------------------
# 5. Persistence: write-once BY ABSENCE
# --------------------------------------------------------------------------


def check_output_namespace(output_root: Path) -> list[str]:
    """The entire results namespace must be ABSENT before anything executes.

    Not "the raw record must be absent" -- the whole namespace.  Write-once by
    absence is the strongest form of the no-resume, no-merge, no-overwrite,
    no-repair-after-outcome rule the frozen persistence policy states, and it is
    checked BEFORE any provider object exists so a second invocation costs zero
    contact and zero inference.
    """

    root = Path(output_root)
    if not root.exists():
        return []
    try:
        contents = sorted(item.name for item in root.iterdir())
    except OSError:  # pragma: no cover - unreadable directory is still a stop
        contents = []
    return [
        f"PROTOCOL_DEVIATION: {root} already exists (containing {contents}). The "
        "successor qualification is written exactly once, to a namespace that must "
        "not already exist. There is no overwrite mode, no resume mode, no merge "
        "mode and no repair-after-outcome path; a second execution is refused, and "
        "an interrupted run's partial state is read, never continued."
    ]


def _append_row(path: Path, row: Mapping[str, Any]) -> None:
    """Append one raw row immediately.  Never rewrite, never deduplicate."""

    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def stamp_frozen_identity(row: Mapping[str, Any], cell: Any) -> dict[str, Any]:
    """Add the two frozen-input identity fields and the schedule bookkeeping.

    ``model_digest`` and ``run_key`` are the only identity fields stamped here,
    and both come from the FROZEN CELL rather than from the run.  A row that
    already carries a conflicting value KEEPS ITS OWN VALUE -- ``setdefault`` is
    what makes that true -- so a runner that someday emits these fields cannot be
    silently overwritten into agreement and the binding check still sees the
    disagreement.
    """

    stamped = dict(row)
    stamped.setdefault("model_digest", cell.model_digest)
    stamped.setdefault("run_key", cell.run_key)
    stamped["schedule_index"] = cell.index
    stamped["arm"] = cell.arm
    stamped["cell_key"] = cell.key
    stamped.setdefault("cell_experiment_dir", "")
    return stamped


def lost_cell_row(cell: Any, detail: str) -> dict[str, Any]:
    """The record for a cell whose execution raised before producing a row.

    There is no row to transport, so the identity comes from the frozen cell by
    necessity, and the row carries none of the instrument pins a real row would.
    :func:`classify_row_detailed` therefore stops the run at this cell -- as
    ``FROZEN_ARTIFACT_MISMATCH`` because the drift check runs first, and as
    ``INSTRUMENT_DEFECT`` on ``provider_attempt_count == 0`` if it did not.  Both
    are ``IMMEDIATE_STOP`` and both say the same thing: no attempt was preserved,
    this cell's evidence is lost, and continuing would measure with a broken
    instrument.

    The exception text is preserved verbatim rather than summarized, and the row
    is still appended -- a failed cell is a RECORDED OUTCOME, never a retry.
    """

    return {
        "task_id": cell.task_id,
        "seed": cell.seed,
        "model": cell.model,
        "model_digest": cell.model_digest,
        "qa_mode": cell.qa_mode,
        "benchmark_manifest_sha256": cell.benchmark_manifest_sha256,
        "run_key": cell.run_key,
        "schedule_index": cell.index,
        "arm": cell.arm,
        "cell_key": cell.key,
        "cell_experiment_dir": "",
        "provider_attempt_count": 0,
        "provider_attempts": [],
        "error": detail,
        "cell_execution_raised": True,
    }


# --------------------------------------------------------------------------
# 6. The real cell executor -- the only thing here that spends inference
# --------------------------------------------------------------------------


def _row_from_cell_directory(experiment_dir: Path) -> dict[str, Any]:
    """The single raw row the runner wrote for this cell."""

    raw_path = experiment_dir / protocol.RAW_RECORD_NAME
    lines = [
        line
        for line in raw_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(lines) != 1:
        raise protocol.SuccessorProtocolError(
            f"one cell must produce exactly one raw row; {raw_path} carries "
            f"{len(lines)}"
        )
    loaded = json.loads(lines[0])
    if not isinstance(loaded, Mapping):  # pragma: no cover - defensive
        raise protocol.SuccessorProtocolError(f"{raw_path} row is not an object")
    return dict(loaded)


def _manifest_observations(experiment_dir: Path) -> dict[str, Any]:
    """The fields the runner records in its manifest rather than on the row."""

    observations: dict[str, Any] = {}
    manifest_path = experiment_dir / "manifest.json"
    if not manifest_path.is_file():
        return observations
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, Mapping):  # pragma: no cover - defensive
        return observations
    observations["raw_schema_version"] = manifest.get("raw_schema_version")
    descriptor = manifest.get("provider")
    if isinstance(descriptor, Mapping):
        for name in ("tool_argument_contract_version", "tool_argument_contract_digest"):
            observations[name] = descriptor.get(name)
    return observations


def make_cell_executor(
    *,
    authorization: SuccessorExecutionAuthorization,
    config_path: Path,
    manifest_path: Path,
    output_root: Path,
) -> CellExecutor:
    """Build the real, runner-backed executor for one frozen cell.  REQUIRES the capability.

    This function constructs the real providers, so it is a real primitive and
    gates ITSELF -- being called only from an authorized path was never a
    control.  The capability is validated here once, and AGAIN before every
    single cell, so a run whose authorization lapses mid-schedule stops rather
    than finishing.

    The canonical ``ExperimentRunner.run`` owns its own case x repetition loop and
    derives the seed as ``config.seeds[repetition]``, so a per-cell driver must
    give it a per-cell configuration: one seed, one repetition, the single QA-OFF
    treatment, and this cell's own directory beneath ``<output_root>/raw/cells/``.
    No cell can therefore overwrite, blend into or resume another.  Nothing else
    about the run is altered: the provider, the policy, the ablations, the step
    budget and the frozen benchmark are the frozen ones, and
    ``infrastructure_retry_limit`` is the protocol's fixed ``0``.
    """

    require_execution_authorization(authorization)

    from iqa_soa.benchmark import load_frozen_pilot  # noqa: PLC0415
    from iqa_soa.experiment.runner import (  # noqa: PLC0415
        ExperimentRunner,
        load_experiment_config,
    )

    frozen_pilot = load_frozen_pilot(manifest_path)
    base_config = load_experiment_config(config_path)
    providers: Mapping[str, Any] = {
        arm: load_successor_provider(ARM_SLOT[arm]) for arm in protocol.ARM_ORDER
    }
    root = cells_root(output_root)

    def execute(cell: Any) -> Mapping[str, Any]:
        # RE-PROVED PER CELL.  Not decoration: this is the only thing standing
        # between a captured executor and 102 cells of inference if the process
        # state changes after the factory ran.
        require_execution_authorization(authorization)
        cell_root = root / cell_slug(cell)
        config = replace(
            base_config,
            output_root=cell_root,
            treatments=(protocol.QA_MODE,),
            repetitions=1,
            seeds=(cell.seed,),
        )
        started = time.perf_counter()
        experiment_dir = ExperimentRunner(config, provider=providers[cell.arm]).run(
            treatments=[protocol.QA_MODE],
            case_ids=[cell.task_id],
            repetitions=1,
            frozen_benchmark=frozen_pilot,
            max_total_runs=1,
            experiment_kind=EXPERIMENT_KIND,
            infrastructure_retry_limit=protocol.INFRASTRUCTURE_RETRY_LIMIT,
        )
        row = _row_from_cell_directory(experiment_dir)
        row["cell_elapsed_ms"] = (time.perf_counter() - started) * 1000.0
        row.update(_manifest_observations(experiment_dir))
        stored = cell_experiment_dir_value(experiment_dir, output_root)
        # Producer-side half of the containment contract: the analyzer binds every
        # evidence pointer to its frozen cell, and asserting the same thing here
        # means a producer regression fails at the cell that caused it.
        resolved, reason = contained_child(
            Path(output_root), stored, label="cell_experiment_dir", must_be_dir=True
        )
        evidence_root = cell_evidence_root(Path(output_root), cell).resolve()
        if resolved is None or evidence_root not in resolved.parents:
            raise protocol.SuccessorProtocolError(
                f"cell {cell.key} produced an evidence pointer that is not beneath "
                f"its own evidence root {evidence_root}: {reason or stored}"
            )
        row["cell_experiment_dir"] = stored
        return row

    setattr(execute, REAL_EXECUTOR_MARKER, True)
    return execute


_REAL_CELL_EXECUTOR_FACTORY = make_cell_executor


# --------------------------------------------------------------------------
# 7. The run
# --------------------------------------------------------------------------


def run_frozen_schedule(
    *,
    schedule: Sequence[Any],
    scripted_faults: Mapping[str, Sequence[Any]],
    execute_cell: CellExecutor,
    raw_path: Path,
    partial_manifest_path: Path,
) -> Any:
    """Drive the frozen schedule under machine-enforced stop semantics.

    :meth:`StopController.cells` is the ONLY source of the next cell and it
    terminates the instant a stop is armed, so an immediate-stop condition cannot
    be stepped past and arm 2 cannot start after arm 1 stopped.

    The partial manifest is written in a ``finally``, so an INTERRUPTION -- a
    ``KeyboardInterrupt``, a killed process that still unwinds, an exception from
    the controller itself -- leaves the frozen fail-closed partial state on disk
    rather than an unexplained directory.  The exception is then re-raised: an
    interrupted run is not a completed one, and nothing here converts it into a
    resumable one.
    """

    controller = StopController(schedule, scripted_faults=scripted_faults)
    try:
        for cell in controller.cells():
            try:
                row = execute_cell(cell)
            except Exception as exc:  # noqa: BLE001 - preserved, never swallowed
                row = lost_cell_row(cell, f"{type(exc).__name__}: {exc}")
            stamped = stamp_frozen_identity(row, cell)
            # Persist BEFORE classifying, so a classifier crash can never erase
            # the observed row and an invalidated cell keeps its raw evidence.
            _append_row(raw_path, stamped)
            failure_class = controller.record(cell, stamped)
            print(
                f"cell {cell.index:03d}/{len(schedule)} {cell.key} -> {failure_class}",
                flush=True,
            )
    finally:
        controller.write_partial_manifest(partial_manifest_path)
    return controller.result()


def _describe_path(path: Path) -> dict[str, Any]:
    """One input's ACTUAL identity: where it is, and what its bytes hash to."""

    resolved = Path(path).resolve()
    try:
        relative: str | None = resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        relative = None
    try:
        digest: str | None = hashlib.sha256(resolved.read_bytes()).hexdigest()
    except OSError:
        digest = None
    return {
        "path": str(resolved),
        "repository_relative_path": relative,
        "sha256": digest,
    }


#: The binding a run manifest's ``execution_inputs`` block declares.  Named once
#: so the driver that WRITES it and the analyzer that RECOMPUTES it cannot drift
#: into two literals that silently never match.
EXECUTION_INPUT_BINDING = "CANONICAL_PATH_AND_FROZEN_SHA256"

EXECUTION_INPUT_BINDINGS: Mapping[str, str] = {
    "config": protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE,
    "models": protocol.CANONICAL_MODELS_RELATIVE,
    "benchmark_manifest": protocol.CANONICAL_MANIFEST_RELATIVE,
}


def describe_execution_inputs(
    *,
    config_path: Path,
    models_path: Path,
    manifest_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    """The provenance of what this run ACTUALLY read and wrote.

    Every digest here is computed from the bytes at the path this invocation
    used, so a run manifest can never report a canonical digest over
    noncanonical inputs.  ``official_successor_execution`` is true only when
    EVERY input is canonical AND the output root is the frozen namespace -- the
    single field a reader needs in order to know whether a directory is an
    official successor qualification or a harness exercise.
    """

    described = {
        "config": _describe_path(config_path),
        "models": _describe_path(models_path),
        "benchmark_manifest": _describe_path(manifest_path),
    }
    for name, entry in described.items():
        relative = EXECUTION_INPUT_BINDINGS[name]
        try:
            accepted: str | None = protocol.accepted_frozen_digest(relative)
        except protocol.SuccessorProtocolError:
            accepted = None
        entry["canonical_repository_relative_path"] = relative
        entry["frozen_sha256"] = accepted
        entry["is_canonical"] = bool(
            entry["repository_relative_path"] == relative
            and accepted is not None
            and entry["sha256"] == accepted
        )
    resolved_root = Path(output_root).resolve()
    namespace_is_canonical = protocol.is_canonical_results_root(resolved_root)
    return {
        **described,
        "output_root": str(resolved_root),
        "canonical_results_namespace": protocol.RESULTS_NAMESPACE,
        "output_root_is_canonical_namespace": namespace_is_canonical,
        "binding": EXECUTION_INPUT_BINDING,
        "official_successor_execution": bool(
            namespace_is_canonical
            and all(entry["is_canonical"] for entry in described.values())
        ),
    }


def _write_run_manifest(
    path: Path,
    *,
    result: Any,
    summary: Mapping[str, Any],
    schedule: Sequence[Any],
    frozen_inputs: Mapping[str, Any] | None,
    runtime_evidence: Mapping[str, Any],
    runtime_observations: Mapping[str, Any],
    execution_inputs: Mapping[str, Any],
) -> None:
    payload = {
        "record_kind": "successor_run_manifest",
        "driver_version": DRIVER_VERSION,
        "candidate_identifier": protocol.CANDIDATE_IDENTIFIER,
        "candidate_status_at_entry": protocol.CANDIDATE_STATUS_AT_ENTRY,
        "benchmark_version": protocol.BENCHMARK_VERSION,
        "protocol": dict(summary),
        "schedule_digest": schedule_digest(schedule),
        "frozen_inputs": dict(frozen_inputs or {}),
        # THE INPUTS THIS RUN ACTUALLY READ, hashed from their own bytes.
        "execution_inputs": dict(execution_inputs),
        # THE EVIDENCE THIS RUN WAS GATED ON, and the FRESH observation that had
        # to agree with it before the first cell.
        "runtime_preflight_evidence": dict(runtime_evidence),
        "runtime_environment_observations": dict(runtime_observations),
        "terminal_status": result.terminal_status,
        "exit_code": result.exit_code,
        "planned_cells": result.planned,
        "executed_cells": result.executed,
        "invalidated_cells": list(result.invalidated_cells),
        "hold_reasons": list(result.hold_reasons),
        "stop_cell": result.stop_cell,
        "stop_failure_class": result.stop_failure_class,
        "stop_reason": result.stop_reason,
        "stop_detail": list(result.stop_detail),
        "cells_not_started": list(result.not_started),
        # THE STOPCONTROLLER LEDGER, persisted verbatim rather than regenerated,
        # so the analyzer's independent reclassification has something real to
        # disagree with.
        "classifications": [dict(item) for item in result.classifications],
        "infrastructure_retry_limit": protocol.INFRASTRUCTURE_RETRY_LIMIT,
        "cells_retried": 0,
        "cells_replaced": 0,
        "cells_resumed": 0,
        "confirmatory_execution_performed": False,
        "randomization_realized": False,
        "note": (
            "Every provider attempt is preserved. No cell was retried, replaced, "
            "repaired, resumed or rerun, and no raw trace was deleted."
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _refuse_unauthorized_real_seams(
    *, output_root: Path, probe: Any, make_executor: Any
) -> None:
    """The OFFLINE-MODE refusals, enforced in the core so every caller meets them.

    None of these is the primary control -- :func:`probe_ollama_metadata` and
    :func:`make_cell_executor` validate the capability themselves, so a real
    primitive that got this far would raise when CALLED, having contacted
    nothing.  What these add is refusal one step earlier, at the moment the seam
    is handed in, with a message that says which seam and why.
    """

    if probe is None or make_executor is None:
        raise protocol.SuccessorProtocolError(
            "OFFLINE_SEAM_MISUSE: an unauthorized successor run requires BOTH an "
            "injected metadata probe and an injected cell executor. There is no "
            "real-model default and none is ever acquired; real-model execution is "
            "reachable only through execute_authorized_real_run()."
        )
    if not callable(probe) or not callable(make_executor):
        raise protocol.SuccessorProtocolError(
            "OFFLINE_SEAM_MISUSE: the injected probe and the injected cell executor "
            "must both be callables"
        )
    for label, candidate in (("probe", probe), ("cell executor", make_executor)):
        named = _names_a_real_seam(candidate)
        if named is not None:
            raise protocol.SuccessorProtocolError(
                f"OFFLINE_SEAM_MISUSE: the injected {label} is {named}, which "
                "contacts the live local runtime or spends real inference. An "
                "unauthorized successor run refuses it -- including through a "
                "functools.partial or a functools.wraps wrapper. Real-model "
                "execution is reachable only through execute_authorized_real_run()."
            )
    if protocol.is_canonical_results_root(output_root):
        raise protocol.SuccessorProtocolError(
            f"OFFLINE_SEAM_MISUSE: {protocol.RESULTS_NAMESPACE} is the namespace an "
            "OFFICIAL successor execution writes. An unauthorized run never writes "
            "it, so synthetic evidence can never occupy the one directory an "
            "official successor qualification analysis is allowed to read."
        )


def _drive_bound_run(
    *,
    authorization: SuccessorExecutionAuthorization | None,
    config_path: Path,
    manifest_path: Path,
    output_root: Path,
    env: Mapping[str, str],
    probe: MetadataProbe,
    capture: SnapshotCapture,
    make_executor: CellExecutorFactory,
) -> int:
    """Drive the frozen schedule against ALREADY-BOUND scientific inputs.

    ``authorization`` selects the MODE, and the mode is enforced here rather than
    by whichever function called.

    **Not ``None``: REAL MODE.**  The grant is validated here, and again inside
    every real primitive the run reaches -- the probe for each arm,
    :func:`make_cell_executor` once, and each of the 102 cells it runs.

    **``None``: OFFLINE MODE.**  Both injections are REQUIRED, neither may be or
    wrap a real primitive, and the frozen namespace may not be written.

    The order below is the protocol's order and never any other: authorization,
    canonical inputs, offline preflight, canonical runtime evidence, schedule,
    configuration, namespace ABSENCE, credential name, fresh environment check,
    then cells.
    """

    if authorization is not None:
        require_execution_authorization(authorization)
    else:
        _refuse_unauthorized_real_seams(
            output_root=output_root, probe=probe, make_executor=make_executor
        )

    # ---- 1. The execution config, bound here as well as by the entry point. --
    try:
        config_path = protocol.require_canonical_input(
            protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE, config_path
        )
    except protocol.SuccessorProtocolError as exc:
        print(f"IMMEDIATE_STOP: {exc}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP

    # ---- 2. Offline preflight, still before any provider contact. ----
    failures = [*protocol.offline_preflight(), *check_confirmatory_remains_impossible()]
    if failures:
        for failure in failures:
            print(f"IMMEDIATE_STOP: {failure}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP

    # ---- 3. THE CANONICAL RUNTIME EVIDENCE. Read, validated, never rewritten. -
    try:
        evidence = load_runtime_evidence()
    except RuntimeEvidenceInvalid as exc:
        print(f"IMMEDIATE_STOP: {exc}", file=sys.stderr)
        print(
            "RUNTIME_EVIDENCE_STOP: 0 cells executed, no results namespace created. "
            "The committed preflight evidence is immutable; it is never regenerated "
            "to make a run possible.",
            file=sys.stderr,
        )
        return protocol.EXIT_PREFLIGHT_STOP

    # ---- 4. The frozen schedule and the provenance-truth check. ----
    try:
        benchmark = load_benchmark(manifest_path)
        schedule = build_successor_schedule(benchmark)
        summary = protocol_summary(benchmark, schedule)
    except protocol.SuccessorProtocolError as exc:
        print(f"IMMEDIATE_STOP: FROZEN_ARTIFACT_MISMATCH: {exc}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP
    except Exception as exc:  # noqa: BLE001 - a malformed frozen input is a stop
        print(f"IMMEDIATE_STOP: FROZEN_ARTIFACT_MISMATCH: {exc}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP

    # ---- 5. Configuration assertion. Local reads only, contacts nothing. ----
    config_failures = check_experiment_configuration(config_path)
    if config_failures:
        for failure in config_failures:
            print(f"IMMEDIATE_STOP: {failure}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP

    # ---- 6. NAMESPACE ABSENCE. Refused before the runtime is even probed. ----
    namespace_failures = check_output_namespace(output_root)
    if namespace_failures:
        for failure in namespace_failures:
            print(f"IMMEDIATE_STOP: {failure}", file=sys.stderr)
        return protocol.EXIT_SCHEDULE_STOPPED

    # ---- 7. Credential presence, by NAME only.  The value is never read. ----
    if not env.get(protocol.CREDENTIAL_ENV):
        print(
            f"CREDENTIAL_STOP: environment variable {protocol.CREDENTIAL_ENV!r} is "
            "unset; the local OpenAI-compatible adapter requires a credential value "
            "even when the local runtime ignores it. The value is never read into a "
            "message, never printed and never written to an artifact.",
            file=sys.stderr,
        )
        return protocol.EXIT_CREDENTIAL_STOP

    # ---- 8. THE IMMEDIATE PRE-INFERENCE ENVIRONMENT CHECK. ----
    environment_failures, runtime_observations = environment_preflight(
        evidence=evidence, probe=probe, capture=capture
    )
    if environment_failures:
        for failure in environment_failures:
            print(failure, file=sys.stderr)
        print(
            "ENVIRONMENT_HOLD: 0 cells executed, no results namespace created. The "
            "successor qualification never pulls, downloads, updates, retags, "
            "repairs or substitutes a model, and never repins a runtime.",
            file=sys.stderr,
        )
        return protocol.EXIT_ENVIRONMENT_HOLD

    # ---- 9. The frozen schedule, owned by the stop controller. ----
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=False)
    raw_path = output_root / protocol.RAW_RECORD_NAME
    raw_path.touch()

    print(
        f"successor QA-OFF qualification: candidate={protocol.CANDIDATE_IDENTIFIER} "
        f"benchmark={protocol.BENCHMARK_VERSION} "
        f"manifest_sha256={benchmark.manifest_sha256} treatment={protocol.QA_MODE} "
        f"arms={list(protocol.ARM_ORDER)} tasks={protocol.TASK_COUNT} "
        f"seeds={list(protocol.SEEDS)} cells={len(schedule)} "
        f"instrument={protocol.EXPECTED_INSTRUMENT_VERSION} "
        f"raw_schema={protocol.EXPECTED_RAW_SCHEMA_VERSION} "
        f"arguments={protocol.EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION} "
        f"adapter={protocol.EXPECTED_NATIVE_TOOL_ADAPTER_VERSION} retries=0"
    )

    executor = make_executor(config_path, manifest_path, output_root)
    result = run_frozen_schedule(
        schedule=schedule,
        scripted_faults=benchmark.scripted_faults,
        execute_cell=executor,
        raw_path=raw_path,
        partial_manifest_path=output_root / protocol.PARTIAL_MANIFEST_NAME,
    )

    from iqa_soa.experiment.runner import load_experiment_config  # noqa: PLC0415

    _write_run_manifest(
        output_root / protocol.RUN_MANIFEST_NAME,
        result=result,
        summary=summary,
        schedule=schedule,
        frozen_inputs=protocol.load_frozen_inputs(),
        runtime_evidence=evidence.provenance(),
        runtime_observations=runtime_observations,
        execution_inputs=describe_execution_inputs(
            config_path=config_path,
            models_path=Path(load_experiment_config(config_path).models_path),
            manifest_path=manifest_path,
            output_root=output_root,
        ),
    )

    if result.stopped:
        print(
            f"HOLD_POST_FREEZE_DEFECT: stopped at {result.stop_cell} "
            f"({result.stop_failure_class}); {result.executed}/{result.planned} cells "
            f"executed, {len(result.not_started)} never started. There is no "
            "resumption path and no replacement path.",
            file=sys.stderr,
        )
    print(
        f"terminal_status={result.terminal_status} executed={result.executed}/"
        f"{result.planned} invalidated={len(result.invalidated_cells)} "
        f"holds={len(result.hold_reasons)}"
    )
    exit_code: int = result.exit_code
    return exit_code


def check_experiment_configuration(config_path: Path) -> list[str]:
    """The successor ExperimentConfig resolves to the frozen successor execution.

    A local read.  It contacts nothing and it loads no historical phase
    configuration: :data:`successor_qualification_protocol.FORBIDDEN_RUNTIME_CONFIGS`
    names every one this driver refuses at runtime, and this function proves the
    config it was given resolves to none of them.
    """

    from iqa_soa.experiment.runner import (  # noqa: PLC0415
        ExperimentConfigError,
        load_experiment_config,
    )

    failures: list[str] = list(protocol.check_experiment_config())
    try:
        config = load_experiment_config(config_path)
    except ExperimentConfigError as error:
        return [*failures, f"FROZEN_ARTIFACT_MISMATCH: {error}"]

    models_path = Path(config.models_path).resolve()
    for forbidden in protocol.FORBIDDEN_RUNTIME_CONFIGS:
        if models_path == (PROJECT_ROOT / forbidden).resolve():
            failures.append(
                f"PROTOCOL_DEVIATION: the run resolves its provider configuration to "
                f"{forbidden}; a historical phase configuration can never satisfy a "
                "successor precondition"
            )
    if models_path != (PROJECT_ROOT / protocol.CANONICAL_MODELS_RELATIVE).resolve():
        failures.append(
            f"PROTOCOL_DEVIATION: the run resolves its provider configuration to "
            f"{models_path}; the frozen successor configuration is "
            f"{protocol.CANONICAL_MODELS_RELATIVE}"
        )
    if list(config.treatments) != [protocol.QA_MODE]:
        failures.append(
            f"PROTOCOL_DEVIATION: the treatment set is {list(config.treatments)}; "
            f"the frozen qualification treatment is exactly [{protocol.QA_MODE!r}]"
        )
    if config.shuffle_treatments:
        failures.append(
            "PROTOCOL_DEVIATION: shuffle_treatments is true; no production "
            "randomization is authorized and none is realized"
        )
    if list(config.seeds) != list(protocol.SEEDS):
        failures.append(
            "PROTOCOL_DEVIATION: the config seeds are not the prospectively derived "
            "successor triple"
        )
    return failures


def protocol_summary(benchmark: LoadedBenchmark, schedule: Sequence[Any]) -> dict[str, Any]:
    """What this run is about to execute, stated as data before it executes."""

    return {
        **protocol.protocol_summary(),
        "driver_version": DRIVER_VERSION,
        "experiment_kind": EXPERIMENT_KIND,
        "benchmark_manifest_sha256": benchmark.manifest_sha256,
        "task_order": list(benchmark.task_ids),
        "arm_order": list(protocol.ARM_ORDER),
        "seed_order": list(protocol.SEEDS),
        "schedule_order": "ARM_MAJOR_TASK_MAJOR_SEED_MINOR",
        "planned_cells": len(schedule),
        "schedule_digest": schedule_digest(schedule),
        "treatments": list(protocol.EXPECTED_TREATMENTS),
        "row_fields": list(SUCCESSOR_ROW_FIELDS),
        "row_contract_pins": dict(ROW_CONTRACT_PINS),
        "cell_experiment_dir_contract": CELL_EXPERIMENT_DIR_CONTRACT,
        "execution_input_binding": EXECUTION_INPUT_BINDING,
        "runtime_evidence_namespace": RUNTIME_EVIDENCE_NAMESPACE,
        "runtime_evidence_capture_commit": RUNTIME_EVIDENCE_CAPTURE_COMMIT,
    }


def execute_authorized_real_run(
    *, authorization: SuccessorExecutionAuthorization
) -> int:
    """THE ONLY REAL-MODEL-CAPABLE PATH.  It requires the capability, and nothing else.

    It takes no config, no manifest and no output root, because there is nothing
    about an official successor qualification for a caller to choose: it binds
    the frozen ``ExperimentConfig``, the frozen benchmark manifest and the frozen
    results namespace itself, by canonical path AND by the SHA-256 the
    frozen-input record accepted.  It takes no probe, no capture and no executor
    either: it SELECTS them, which is exactly the authority the capability
    confers and the reason nothing else here may do it.

    An unauthorized call RAISES rather than returning an exit code, because no
    run happened and an exit code is a result.
    """

    require_execution_authorization(authorization)

    try:  # pragma: no cover - unreachable while execution is unauthorized
        config_path = protocol.require_canonical_input(
            protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE
        )
        manifest_path = protocol.require_canonical_input(
            protocol.CANONICAL_MANIFEST_RELATIVE
        )
        output_root = protocol.require_canonical_results_root()
    except protocol.SuccessorProtocolError as exc:  # pragma: no cover
        print(f"IMMEDIATE_STOP: {exc}", file=sys.stderr)
        print(
            "NONCANONICAL_SUCCESSOR_EXECUTION: refused. 0 metadata probes, 0 cells "
            "executed, no results namespace created.",
            file=sys.stderr,
        )
        return protocol.EXIT_PREFLIGHT_STOP

    return _drive_bound_run(  # pragma: no cover - unreachable today
        authorization=authorization,
        config_path=config_path,
        manifest_path=manifest_path,
        output_root=output_root,
        env=os.environ,
        probe=functools.partial(probe_ollama_metadata, authorization=authorization),
        capture=capture_stratum_runtime_snapshot,
        make_executor=lambda config, manifest, root: make_cell_executor(
            authorization=authorization,
            config_path=config,
            manifest_path=manifest,
            output_root=root,
        ),
    )


def execute_offline_bound_run(
    *,
    config_path: Path,
    manifest_path: Path,
    output_root: Path,
    env: Mapping[str, str],
    probe: MetadataProbe,
    capture: SnapshotCapture,
    execute_cell: CellExecutor,
) -> int:
    """THE OFFLINE SEAM.  It needs no authorization because it cannot execute a model.

    The offline regression suite has to drive everything beyond the gate -- the
    runtime-evidence gate, the environment check, the stop controller, the raw
    record, the partial manifest, the run manifest -- without a provider.  This
    function is structurally incapable of a real run, and says so in behaviour
    rather than in prose:

    * ``probe``, ``capture`` and ``execute_cell`` are REQUIRED, so there is no
      default for a missing argument to resolve into;
    * :func:`probe_ollama_metadata` is refused BY IDENTITY;
    * an executor built by :func:`make_cell_executor` is refused by its marker;
    * the frozen successor namespace is refused outright, so nothing this seam
      writes can be -- or be mistaken for -- an official successor run.
    """

    _refuse_unauthorized_real_seams(
        output_root=output_root, probe=probe, make_executor=execute_cell
    )
    return _drive_bound_run(
        authorization=None,
        config_path=config_path,
        manifest_path=manifest_path,
        output_root=output_root,
        env=env,
        probe=probe,
        capture=capture,
        make_executor=lambda _config, _manifest, _root: execute_cell,
    )


# --------------------------------------------------------------------------
# 8. The post-run analyzer -- the COMMITTED decision rule, reused not restated
# --------------------------------------------------------------------------

#: The successor verdict vocabulary.  Deliberately NOT the Phase-P strings: a
#: successor verdict is about this candidate and must never be confusable with
#: the Phase-P HOLD, which stands permanently and is not revisited here.
VERDICT_QUALIFIED = "PASS_SUCCESSOR_QUALIFIED_FOR_QA_OFF_USE"
VERDICT_HOLD = "HOLD"
VERDICT_SYNTHETIC_PASS = "TEST_ANALYSIS_PASS"
VERDICT_SYNTHETIC_HOLD = "TEST_ANALYSIS_HOLD"

MODE_OFFICIAL = "OFFICIAL_SUCCESSOR_QUALIFICATION"
MODE_SYNTHETIC = "SYNTHETIC_ANALYSIS_ONLY"

MODE_VERDICTS: Mapping[str, tuple[str, str]] = {
    MODE_OFFICIAL: (VERDICT_QUALIFIED, VERDICT_HOLD),
    MODE_SYNTHETIC: (VERDICT_SYNTHETIC_PASS, VERDICT_SYNTHETIC_HOLD),
}

RECORD_KIND: Mapping[str, str] = {
    MODE_OFFICIAL: "successor_qualification_analysis",
    MODE_SYNTHETIC: "successor_synthetic_analysis",
}

SYNTHETIC_DISCLAIMER = (
    "This analysis was produced from a NON-CANONICAL evidence root. It is a "
    "harness exercise, it qualifies nothing, and its verdict vocabulary is "
    "disjoint from the official one so it can never be read as a successor "
    "qualification result."
)


def _frozen_analyzer() -> Any:
    """Load the FROZEN Phase-P rc4 analyzer without editing or shadowing it.

    Loaded by path under a private module name so importing this driver can never
    change what ``import analyze_phaseP_rc4_qualification`` means for a frozen
    caller.  This is the same mechanism the Phase-P analyzer uses for the Phase-L
    analyzer, and for the same reason.

    Loading it reads no results directory: it is a module import, and the
    historical evidence root is never opened by this driver on any path.
    """

    name = "_successor_frozen_analyzer"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(
        name, SCRIPTS_ROOT / "analyze_phaseP_rc4_qualification.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _SuccessorProtocolAdapter:
    """The ``protocol`` surface the frozen analyzers resolve, bound to the successor.

    The frozen analyzers resolve ``protocol`` as a MODULE GLOBAL at call time.
    Substituting this object for exactly the duration of a call -- and restoring
    it in ``finally`` -- is the seam the Phase-P analyzer already uses on the
    Phase-L analyzer.  What changes is the BINDINGS, never the rule: every
    threshold, every task status, every blocking condition and the run-level
    conjunction come from the frozen analyzer unchanged.

    Attribute names ending in ``phase_p`` / ``phase_l`` are the names the frozen
    code calls; the values behind them are the successor's own.
    """

    # -- identity ---------------------------------------------------------
    PHASE = "SUCCESSOR"
    BENCHMARK_VERSION = protocol.BENCHMARK_VERSION
    QA_MODE = protocol.QA_MODE
    SEEDS = protocol.SEEDS
    ARM_ORDER = protocol.ARM_ORDER

    # -- instrument pins --------------------------------------------------
    EXPECTED_INSTRUMENT_VERSION = protocol.EXPECTED_INSTRUMENT_VERSION
    EXPECTED_RAW_SCHEMA_VERSION = protocol.EXPECTED_RAW_SCHEMA_VERSION
    EXPECTED_NATIVE_TOOL_ADAPTER_VERSION = (
        protocol.EXPECTED_NATIVE_TOOL_ADAPTER_VERSION
    )
    EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION = (
        protocol.EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION
    )

    # -- canonical inputs and namespace ----------------------------------
    CANONICAL_CONFIG_RELATIVE = protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE
    CANONICAL_MODELS_RELATIVE = protocol.CANONICAL_MODELS_RELATIVE
    CANONICAL_MANIFEST_RELATIVE = protocol.CANONICAL_MANIFEST_RELATIVE
    CANONICAL_CONTRACT_RELATIVE = protocol.CANONICAL_CONTRACT_RELATIVE
    RESULTS_NAMESPACE = protocol.RESULTS_NAMESPACE
    RAW_RECORD_NAME = protocol.RAW_RECORD_NAME
    RUN_MANIFEST_NAME = protocol.RUN_MANIFEST_NAME
    EXECUTION_INPUT_BINDING = EXECUTION_INPUT_BINDING

    # -- exit codes and errors -------------------------------------------
    EXIT_OK = protocol.EXIT_OK
    EXIT_VERDICT_HOLD = protocol.EXIT_VERDICT_HOLD
    EXIT_PREFLIGHT_STOP = protocol.EXIT_PREFLIGHT_STOP
    ProtocolError = protocol.SuccessorProtocolError
    NoncanonicalInput = protocol.NoncanonicalInput

    # -- path and trace contracts ----------------------------------------
    CELL_EXPERIMENT_DIR_CONTRACT = CELL_EXPERIMENT_DIR_CONTRACT
    TRACE_IDENTITY_FIELDS = TRACE_IDENTITY_FIELDS
    RUN_MANIFEST_CLASSIFICATION_FIELDS = RUN_MANIFEST_CLASSIFICATION_FIELDS

    # -- functions --------------------------------------------------------
    sha256_file = staticmethod(protocol.sha256_file)
    offline_preflight = staticmethod(protocol.offline_preflight)
    require_canonical_input = staticmethod(protocol.require_canonical_input)
    require_canonical_results_root = staticmethod(
        protocol.require_canonical_results_root
    )
    canonical_results_root = staticmethod(protocol.canonical_results_root)
    is_canonical_results_root = staticmethod(protocol.is_canonical_results_root)
    accepted_frozen_digest = staticmethod(protocol.accepted_frozen_digest)
    load_benchmark = staticmethod(load_benchmark)
    build_phase_p_schedule = staticmethod(build_successor_schedule)
    build_phase_l_schedule = staticmethod(build_successor_schedule)
    classify_row = staticmethod(classify_row)
    contract_drift = staticmethod(contract_drift)
    cell_evidence_root = staticmethod(cell_evidence_root)
    contained_child = staticmethod(contained_child)


@contextmanager
def _successor_interpretation() -> Iterator[None]:
    """Run frozen analyzer code against the SUCCESSOR bindings, then restore them.

    The frozen module's own bytes are not edited; only this private, path-loaded
    copy's globals are rebound, and only inside the ``with`` block, so a caller
    who imports ``analyze_phaseP_rc4_qualification`` directly is never affected.
    Rebinding the Phase-P analyzer's ``protocol`` is enough to reach the Phase-L
    analyzer too, because Phase-P's own ``_rc4_interpretation`` propagates its
    module global downward.
    """

    analyzer = _frozen_analyzer()
    adapter = _SuccessorProtocolAdapter()
    saved_protocol = analyzer.protocol
    saved_bindings = analyzer.EXECUTION_INPUT_BINDINGS
    analyzer.protocol = adapter
    analyzer.EXECUTION_INPUT_BINDINGS = dict(EXECUTION_INPUT_BINDINGS)
    try:
        yield
    finally:
        analyzer.protocol = saved_protocol
        analyzer.EXECUTION_INPUT_BINDINGS = saved_bindings


def check_execution_provenance(
    root: Path, run_manifest: Mapping[str, Any]
) -> list[str]:
    """Prove the run in *root* really was an OFFICIAL successor execution.

    The evidence root is not a scientific input, so binding the manifest and the
    contract says nothing about it.  This proves the second half: that the run
    which wrote this directory recorded, in its own provenance block, that it
    read the frozen ExperimentConfig, the frozen model config and the frozen
    benchmark manifest, wrote the frozen namespace, and was gated on the
    committed runtime evidence with a fresh identity that agreed.

    Every recorded digest is compared against the SHA-256 the committed
    frozen-input record accepted -- never against the run's own claim about
    itself.  Every failure is blocking and forces ``HOLD``.
    """

    if not run_manifest:
        return [
            f"INSTRUMENT_DEFECT: {root / protocol.RUN_MANIFEST_NAME} is missing or "
            "empty; an official successor qualification is scored only against a run "
            "that recorded its own execution provenance"
        ]
    inputs = run_manifest.get("execution_inputs")
    if not isinstance(inputs, Mapping):
        return [
            "INSTRUMENT_DEFECT: the run manifest records no execution_inputs "
            "provenance block, so what this run actually read cannot be established; "
            "it is not scoreable as an official qualification"
        ]

    failures: list[str] = []
    if inputs.get("binding") != EXECUTION_INPUT_BINDING:
        failures.append(
            f"FROZEN_ARTIFACT_MISMATCH: the run recorded binding="
            f"{inputs.get('binding')!r}; an official successor run records "
            f"{EXECUTION_INPUT_BINDING!r}"
        )
    for name, relative in EXECUTION_INPUT_BINDINGS.items():
        entry = inputs.get(name)
        if not isinstance(entry, Mapping):
            failures.append(
                f"INSTRUMENT_DEFECT: the run manifest records no {name!r} execution "
                f"input, so it cannot be proved to have read {relative}"
            )
            continue
        try:
            accepted = protocol.accepted_frozen_digest(relative)
        except protocol.SuccessorProtocolError as exc:
            failures.append(f"FROZEN_ARTIFACT_MISMATCH: {exc}")
            continue
        if entry.get("repository_relative_path") != relative:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: the run read {name} from "
                f"{entry.get('repository_relative_path')!r}; an official successor "
                f"run reads {relative}"
            )
        if entry.get("sha256") != accepted:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: the run read {name} with "
                f"sha256={entry.get('sha256')!r}; the successor freeze accepted "
                f"{accepted} for {relative}"
            )
        if entry.get("is_canonical") is not True:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: the run itself recorded that its {name} "
                "input was not the canonical frozen artifact"
            )

    canonical_root = protocol.canonical_results_root()
    recorded_root = inputs.get("output_root")
    resolved_recorded: Path | None = None
    if isinstance(recorded_root, str) and recorded_root:
        try:
            resolved_recorded = Path(recorded_root).resolve()
        except OSError:  # pragma: no cover - platform path resolution failure
            resolved_recorded = None
    if resolved_recorded != canonical_root:
        failures.append(
            f"FROZEN_ARTIFACT_MISMATCH: the run recorded output_root="
            f"{recorded_root!r}; an official successor run writes "
            f"{protocol.RESULTS_NAMESPACE}, and evidence written anywhere else is "
            "not official successor evidence"
        )
    if inputs.get("output_root_is_canonical_namespace") is not True:
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the run itself recorded that its output root "
            f"was not the frozen {protocol.RESULTS_NAMESPACE} namespace"
        )

    # THE RUNTIME-EVIDENCE HALF.  A run that did not record which committed
    # evidence it was gated on, or whose fresh identity did not agree with it,
    # is not an official successor execution however clean its rows look.
    evidence_block = run_manifest.get("runtime_preflight_evidence")
    if not isinstance(evidence_block, Mapping):
        failures.append(
            "INSTRUMENT_DEFECT: the run manifest records no runtime_preflight_evidence "
            "block; a run that cannot show which committed runtime evidence gated it "
            "is not scoreable as an official qualification"
        )
    else:
        recorded_identity = evidence_block.get("canonical_runtime_identity")
        if not isinstance(recorded_identity, Mapping) or dict(
            recorded_identity
        ) != dict(CANONICAL_RUNTIME_IDENTITY):
            failures.append(
                "FROZEN_ARTIFACT_MISMATCH: the run was gated on runtime identities "
                f"{recorded_identity!r}, the canonical preflight identities are "
                f"{dict(CANONICAL_RUNTIME_IDENTITY)}"
            )
        if evidence_block.get("capture_commit") != RUNTIME_EVIDENCE_CAPTURE_COMMIT:
            failures.append(
                "FROZEN_ARTIFACT_MISMATCH: the run recorded capture commit "
                f"{evidence_block.get('capture_commit')!r}, the canonical capture "
                f"commit is {RUNTIME_EVIDENCE_CAPTURE_COMMIT}"
            )
    observations = run_manifest.get("runtime_environment_observations")
    if not isinstance(observations, Mapping):
        failures.append(
            "INSTRUMENT_DEFECT: the run manifest records no fresh runtime environment "
            "observation; a prior capture is never accepted in place of a fresh one"
        )
    else:
        strata = observations.get("strata")
        for slot, expected in sorted(CANONICAL_RUNTIME_IDENTITY.items()):
            entry = strata.get(slot) if isinstance(strata, Mapping) else None
            if not isinstance(entry, Mapping):
                failures.append(
                    f"INSTRUMENT_DEFECT: the run recorded no fresh runtime "
                    f"observation for {slot}"
                )
                continue
            if entry.get("fresh_runtime_identity_digest") != expected:
                failures.append(
                    f"FROZEN_ARTIFACT_MISMATCH: the run recorded fresh runtime "
                    f"identity {entry.get('fresh_runtime_identity_digest')!r} for "
                    f"{slot}, the canonical preflight identity is {expected}"
                )
            if entry.get("live_runtime_version") != protocol.EXPECTED_RUNTIME_VERSION:
                failures.append(
                    f"FROZEN_ARTIFACT_MISMATCH: the run observed runtime "
                    f"{entry.get('live_runtime_version')!r} for {slot}, the frozen "
                    f"pin is {protocol.EXPECTED_RUNTIME_VERSION!r}"
                )

    for name, expected_value in (
        ("infrastructure_retry_limit", 0),
        ("cells_retried", 0),
        ("cells_replaced", 0),
        ("cells_resumed", 0),
        ("confirmatory_execution_performed", False),
        ("randomization_realized", False),
    ):
        if run_manifest.get(name) != expected_value:
            failures.append(
                f"PROTOCOL_DEVIATION: the run recorded {name}="
                f"{run_manifest.get(name)!r}, the frozen successor protocol requires "
                f"{expected_value!r}"
            )

    analyzed = Path(root).resolve()
    if analyzed != canonical_root:  # pragma: no cover - the caller binds this
        failures.append(
            f"FROZEN_ARTIFACT_MISMATCH: {analyzed} is not the frozen "
            f"{protocol.RESULTS_NAMESPACE} namespace"
        )
    if inputs.get("official_successor_execution") is not True:
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the run manifest records "
            f"official_successor_execution="
            f"{inputs.get('official_successor_execution')!r}; a run that does not "
            "itself claim to be an official successor execution is never scored as one"
        )
    return failures


def _successor_payload_counts(
    task_id: str, proposals: Sequence[Any], plan: Any
) -> dict[str, int]:
    """The SUCCESSOR profile's additive diagnostic counters for one cell.

    Reported, never decisive.  Both successor-only classes are frozen
    non-exposure and non-near-miss -- ``assert_profile_closure`` proves it at
    import and :func:`analyze` asserts it again before a verdict exists -- so
    this pass cannot move the qualification decision by construction.  It exists
    because the candidate's scoring profile IS ``successor``, and a profile that
    is declared but never rendered would be a label rather than a measurement.
    """

    counts: dict[str, int] = {name: 0 for name in successor_vocabulary.PAYLOAD_OUTCOMES}
    # ``TraceProposal`` is a Protocol, deliberately: the frozen analyzer's own
    # ``Proposal`` satisfies it structurally, so the ordered trace is passed
    # through as-is rather than copied into a parallel shape that could drift.
    trace: tuple[Any, ...] = tuple(proposals)
    for item in proposals:
        outcome = successor_vocabulary.classify_payload(
            task_id=task_id,
            tool=item.tool,
            resource=item.resource,
            payload=item.argument_text,
            canonical=tuple(plan.canonical_signatures),
            safe=tuple(plan.safe_route),
            protected_values=tuple(plan.protected_values),
            trace=trace,
            position=item.index,
        )
        counts[outcome] = counts.get(outcome, 0) + 1
    return counts


def analyze(
    root: Path | str,
    *,
    mode: str,
    manifest_path: Path | str | None = None,
    contract_path: Path | str | None = None,
) -> dict[str, Any]:
    """Score a completed successor run.  Contacts nothing and runs no model.

    THE DECISION RULE IS THE COMMITTED ONE AND IS NOT RESTATED HERE.  Task plans
    come from ``benchmark/pilot-v7-rc4/qualification-contract.json``; per-task
    status comes from the frozen ``classify_task``; the qualifying statuses,
    every threshold and every blocking condition are the frozen analyzer's; and
    the run-level rule is the frozen conjunction
    ``qualified = not blocking and not unqualified``.  No threshold is invented,
    adjusted, tuned or read from an outcome.

    A ``FAIL`` or ``HOLD`` is a valid scientific result.  Nothing here treats one
    as a reason to rerun, and there is no rerun path to take.
    """

    if mode not in MODE_VERDICTS:
        raise protocol.SuccessorProtocolError(f"unknown analysis mode: {mode!r}")
    official = mode == MODE_OFFICIAL
    analyzer = _frozen_analyzer()
    successor_vocabulary.assert_profile_closure()

    root = Path(root)
    with _successor_interpretation():
        bound_manifest = protocol.require_canonical_input(
            protocol.CANONICAL_MANIFEST_RELATIVE, manifest_path
        )
        bound_contract = protocol.require_canonical_input(
            protocol.CANONICAL_CONTRACT_RELATIVE, contract_path
        )
        frozen_failures = protocol.offline_preflight()
        benchmark = load_benchmark(bound_manifest)
        schedule = build_successor_schedule(benchmark)

        from iqa_soa.benchmark import load_frozen_pilot  # noqa: PLC0415

        frozen_pilot = load_frozen_pilot(bound_manifest)
        plans, contract = analyzer.build_scoring_plans(bound_contract, bound_manifest)
        plan_failures = analyzer.check_scoring_plan_is_contract_bound(
            plans, contract, list(frozen_pilot.cases)
        )

        rows = analyzer.frozen._read_jsonl(root / protocol.RAW_RECORD_NAME)
        manifest_file = root / protocol.RUN_MANIFEST_NAME
        run_manifest: Mapping[str, Any] = (
            json.loads(manifest_file.read_text(encoding="utf-8"))
            if manifest_file.is_file()
            else {}
        )
        matrix = analyzer.check_matrix(schedule, rows, run_manifest)
        provenance_failures = (
            check_execution_provenance(root, run_manifest) if official else []
        )

        cell_results: list[Any] = []
        trace_defects: list[str] = []
        successor_counts: dict[str, dict[str, int]] = {}
        independent: dict[str, tuple[str, str]] = {}
        for position, row in enumerate(rows):
            if position >= len(schedule):
                break
            cell = schedule[position]
            plan = plans.get(cell.task_id)
            if plan is None:
                continue
            failure_class, disposition = classify_row(
                row, cell, scripted_faults=benchmark.scripted_faults
            )
            independent[cell.key] = (failure_class, disposition)

            with analyzer._rc4_interpretation():
                events, defects = analyzer.frozen._trace_events(root, row, cell)
            trace_defects.extend(defects)
            # LOST EVIDENCE IS NOT ZERO EXPOSURE.  A cell whose trace could not be
            # resolved is scored INSTRUMENT_DEFECT so it can never contribute
            # exposure and can never count as a clean valid cell.  The ledger
            # reconciliation still uses the UNOVERRIDDEN classification, so this
            # override cannot manufacture a disagreement with the driver.
            scoring_class, scoring_disposition = (
                (harness.INSTRUMENT_DEFECT, harness.IMMEDIATE_STOP)
                if defects
                else (failure_class, disposition)
            )
            result = analyzer.evaluate_cell(
                cell=cell,
                row=row,
                events=events,
                plan=plan,
                scripted_faults=benchmark.scripted_faults,
                failure_class=scoring_class,
                disposition=scoring_disposition,
            )
            result.base.detail.extend(defects)
            cell_results.append(result)

            with analyzer._rc4_interpretation():
                proposals = analyzer.proposals_for(events, row)
            bucket = successor_counts.setdefault(cell.task_id, {})
            for name, value in _successor_payload_counts(
                cell.task_id, proposals, plan
            ).items():
                bucket[name] = bucket.get(name, 0) + value

        with analyzer._rc4_interpretation():
            ledger_failures = analyzer.check_classification_ledger(
                schedule, rows, run_manifest, independent
            )

        by_task: dict[str, list[Any]] = {}
        for item in cell_results:
            by_task.setdefault(item.base.task_id, []).append(item)

        task_payloads: list[dict[str, Any]] = []
        unqualified: list[str] = []
        for task_id in benchmark.task_ids:
            plan = plans.get(task_id)
            if plan is None:
                continue
            results = by_task.get(task_id, [])
            with analyzer._rc4_interpretation():
                report = analyzer.classify_task(plan, [item.base for item in results])
            if report.status not in analyzer.QUALIFYING_STATUSES:
                unqualified.append(task_id)
            task_payloads.append(
                {
                    "task_id": report.task_id,
                    "role": report.role,
                    "status": report.status,
                    "cells": report.cells,
                    "valid_cells": report.valid_cells,
                    "exposures": report.exposures,
                    "near_misses": report.near_misses,
                    "prerequisites_satisfied": report.prerequisites_satisfied,
                    "safe_route_complete": report.safe_route_complete,
                    "fault_bound_to_declaration": report.fault_bound,
                    "modality_by_arm": report.modality_by_arm,
                    "stage_two_depth": report.stage_two_depth,
                    "review_flags": report.review_flags,
                    "notes": report.notes,
                    "scope_unresolved_fan_out": sum(
                        1 for item in results if item.scope_unresolved_fan_out
                    ),
                    "near_miss_exclusions_applied": sum(
                        1 for item in results if item.excluded_near_miss_positions
                    ),
                    "payload_outcome_counts": analyzer._payload_counts(results),
                    "successor_payload_outcome_counts": successor_counts.get(
                        task_id, {}
                    ),
                }
            )

    blocking: list[str] = [
        *(f"FROZEN_ARTIFACT_MISMATCH: {item}" for item in frozen_failures),
        *(f"CONTRACT_NOT_MACHINE_READABLE: {item}" for item in plan_failures),
        *(f"MATRIX_INVALID: {item}" for item in matrix.failures),
        *(f"INSTRUMENT_DEFECT: {item}" for item in trace_defects),
        *(f"INSTRUMENT_DEFECT: {item}" for item in ledger_failures),
        *provenance_failures,
    ]
    # THE FROZEN RUN-LEVEL RULE, unchanged: one unqualified task, or any blocking
    # failure, forces HOLD.  There is no threshold here to tune, because there is
    # no threshold here at all.
    qualified = not blocking and not unqualified
    passing, holding = MODE_VERDICTS[mode]
    verdict = passing if qualified else holding

    payload: dict[str, Any] = {
        "record_kind": RECORD_KIND[mode],
        "analyzer_version": ANALYZER_VERSION,
        "driver_version": DRIVER_VERSION,
        "harness_version": harness.HARNESS_VERSION,
        "decision_rule": "FROZEN_QUALIFICATION_DECISION_RULE_REUSED_UNCHANGED",
        "decision_rule_source": "scripts/analyze_phaseP_rc4_qualification.py",
        "thresholds_invented_or_modified": False,
        "candidate_identifier": protocol.CANDIDATE_IDENTIFIER,
        "candidate_status_at_entry": protocol.CANDIDATE_STATUS_AT_ENTRY,
        "scoring_profile": protocol.SCORING_PROFILE,
        "scoring_vocabulary_version": protocol.SCORING_VOCABULARY_VERSION,
        "successor_only_outcomes_are_exposure": False,
        "successor_only_outcomes_are_near_miss": False,
        "benchmark_version": protocol.BENCHMARK_VERSION,
        "benchmark_manifest_sha256": benchmark.manifest_sha256,
        "benchmark_manifest_path": protocol.CANONICAL_MANIFEST_RELATIVE,
        "qualification_contract_sha256": hashlib.sha256(
            bound_contract.read_bytes()
        ).hexdigest(),
        "qualification_contract_path": protocol.CANONICAL_CONTRACT_RELATIVE,
        "analysis_mode": mode,
        "official_successor_qualification": official,
        "analyzed_canonical_results_namespace": protocol.is_canonical_results_root(root),
        "canonical_results_namespace": protocol.RESULTS_NAMESPACE,
        "execution_provenance_failures": provenance_failures,
        "instrument_version": protocol.EXPECTED_INSTRUMENT_VERSION,
        "raw_schema_version": protocol.EXPECTED_RAW_SCHEMA_VERSION,
        "tool_argument_contract_version": (
            protocol.EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION
        ),
        "native_tool_adapter_version": protocol.EXPECTED_NATIVE_TOOL_ADAPTER_VERSION,
        "cross_instrument_pooling_permitted": (
            protocol.CROSS_INSTRUMENT_POOLING_PERMITTED
        ),
        "historical_rows_read": 0,
        "historical_rows_rescored": 0,
        "qa_mode": protocol.QA_MODE,
        "treatments": list(protocol.EXPECTED_TREATMENTS),
        "seeds": list(protocol.SEEDS),
        "arm_order": list(protocol.ARM_ORDER),
        "planned_cells": matrix.planned,
        "observed_cells": matrix.observed,
        "matrix_complete": matrix.complete,
        "matrix_failures": matrix.failures,
        "evidence_trace_defects": trace_defects,
        "classification_ledger_failures": ledger_failures,
        "classification_ledger_entries": len(run_manifest.get("classifications") or []),
        "blocking_failures": blocking,
        "tasks": task_payloads,
        "unqualified_tasks": unqualified,
        "verdict": verdict,
        "verdict_vocabulary": list(MODE_VERDICTS[mode]),
        "verdict_is_a_scientific_result": True,
        "hold_is_not_a_reason_to_rerun": True,
        "rerun_authorized": False,
        "reports_no_qa_treatment_effect": True,
        "reports_no_model_ranking": True,
        "reports_no_confirmatory_disposition": True,
        "authorizes_confirmatory_execution": False,
        "confirmatory_execution_performed": False,
        "randomization_realized": False,
        "model_inference_performed_by_this_analyzer": False,
    }
    if not official:
        payload["synthetic_analysis_disclaimer"] = SYNTHETIC_DISCLAIMER
    return payload


def write_analysis(root: Path | str, payload: Mapping[str, Any]) -> Path:
    """Persist one analysis under the frozen name, exactly once.

    ``successor-analysis.json`` is the artifact name the protocol froze.  It is
    written by absence like every other successor artifact: a pre-existing
    analysis is a refusal, not something to overwrite, because a verdict that can
    be regenerated over its predecessor is a verdict nobody can audit.
    """

    target = Path(root) / protocol.ANALYSIS_NAME
    if target.exists():
        raise protocol.SuccessorProtocolError(
            f"PROTOCOL_DEVIATION: {target} already exists. The successor analysis is "
            "written exactly once; there is no overwrite mode, and a second verdict "
            "over the same evidence is never silently substituted for the first."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return target


def analyze_official_qualification(
    root: Path | str | None = None, **kwargs: Any
) -> dict[str, Any]:
    """Score the OFFICIAL successor namespace, and only ever that one."""

    return analyze(
        protocol.require_canonical_results_root(root), mode=MODE_OFFICIAL, **kwargs
    )


def analyze_synthetic_evidence(root: Path | str, **kwargs: Any) -> dict[str, Any]:
    """Score a NON-CANONICAL root under a disjoint verdict vocabulary."""

    resolved = Path(root)
    if protocol.is_canonical_results_root(resolved):
        raise protocol.NoncanonicalInput(
            f"SYNTHETIC_ANALYSIS_REFUSED: {protocol.RESULTS_NAMESPACE} is the "
            "official successor namespace; a synthetic analysis never reads it and "
            "an official verdict is never emitted over anything else."
        )
    return analyze(resolved, mode=MODE_SYNTHETIC, **kwargs)


# --------------------------------------------------------------------------
# 9. The offline preflight report and the CLI
# --------------------------------------------------------------------------


def offline_preflight_failures() -> list[str]:
    """Every offline failure the driver can see, protocol first."""

    return (
        protocol.offline_preflight()
        + eligibility.check_argument_integrity()
        + check_runtime_evidence()
        + check_confirmatory_remains_impossible()
    )


def offline_preflight_report() -> dict[str, Any]:
    """Everything the driver can establish with no provider contact."""

    protocol_failures = protocol.offline_preflight()
    eligibility_failures = eligibility.check_argument_integrity()
    evidence_failures = check_runtime_evidence()
    return {
        "driver_version": DRIVER_VERSION,
        "candidate_identifier": protocol.CANDIDATE_IDENTIFIER,
        "candidate_status_at_entry": protocol.CANDIDATE_STATUS_AT_ENTRY,
        "proposed_strata": [list(item) for item in protocol.PROPOSED_STRATA],
        "protocol_preflight_failures": protocol_failures,
        "eligibility_argument_failures": eligibility_failures,
        "runtime_evidence_failures": evidence_failures,
        "confirmatory_boundary_failures": check_confirmatory_remains_impossible(),
        "stage_a_status": eligibility.stage_a_status(),
        "runtime_snapshot_capture_required_next": (
            eligibility.runtime_snapshot_capture_required_next()
        ),
        "runtime_evidence_namespace": RUNTIME_EVIDENCE_NAMESPACE,
        "runtime_evidence_capture_commit": RUNTIME_EVIDENCE_CAPTURE_COMMIT,
        "canonical_runtime_identity": dict(CANONICAL_RUNTIME_IDENTITY),
        "models_config": protocol.CANONICAL_MODELS_RELATIVE,
        "experiment_config": protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE,
        "seeds": list(protocol.SEEDS),
        "seed_selection_status": protocol.SEED_SELECTION_STATUS,
        "seed_derivation_record": protocol.SEED_DERIVATION_RECORD_RELATIVE,
        "planned_cells": protocol.PLANNED_CELLS,
        "schedule_order": "ARM_MAJOR_TASK_MAJOR_SEED_MINOR",
        "treatments": list(protocol.EXPECTED_TREATMENTS),
        "expected_runtime_version": protocol.EXPECTED_RUNTIME_VERSION,
        "runtime_version_resolution": protocol.RUNTIME_VERSION_RESOLUTION,
        "runtime_repin_authorized": protocol.RUNTIME_REPIN_AUTHORIZED,
        "runtime_restore_required": protocol.RUNTIME_RESTORE_REQUIRED,
        "results_namespace": protocol.RESULTS_NAMESPACE,
        "results_namespace_created": (
            PROJECT_ROOT / protocol.RESULTS_NAMESPACE
        ).exists(),
        "execution_path_implemented": True,
        "execution_path_reachable": False,
        "qualification_execution_authorized": (
            protocol.QUALIFICATION_EXECUTION_AUTHORIZED
        ),
        "provider_contact_authorized": protocol.PROVIDER_CONTACT_AUTHORIZED,
        "model_inference_authorized": protocol.MODEL_INFERENCE_AUTHORIZED,
        "confirmatory_execution_authorized": (
            protocol.CONFIRMATORY_EXECUTION_AUTHORIZED
        ),
        "randomization_realization_authorized": (
            protocol.RANDOMIZATION_REALIZATION_AUTHORIZED
        ),
        "provider_contacted": False,
        "model_inference_performed": False,
        "rows_written": 0,
    }


def _refuse_execution() -> int:
    """The execution path, in full.  It ends in a refusal, by construction.

    The capability is requested FIRST.  Minting one calls the protocol's
    authorization check before it looks at either exercise gate, so a caller who
    supplies BOTH the flag and the environment variable gets this refusal --
    which is the whole reason the check is here rather than after the gates.
    """

    try:
        authorization = grant_execution_authorization()
    except protocol.QualificationExecutionNotAuthorized as exc:
        print(str(exc))
        print(
            "EXECUTABLE_BUT_LOCKED: the successor execution path is implemented, "
            "reviewed and tested -- the runtime-evidence gate, the frozen 102-cell "
            "schedule, the pre-inference environment check, the write-once "
            "persistence and the post-run analyzer. None of it is reachable without "
            "a new human record, and supplying the CLI flag or the environment gate "
            "does not substitute for one. 0 provider contacts, 0 cells executed, no "
            "results namespace created."
        )
        return protocol.EXIT_GATE_CLOSED
    except SuccessorExecutionRefused as exc:  # pragma: no cover - unreachable today
        print(str(exc))
        return protocol.EXIT_GATE_CLOSED

    return execute_authorized_real_run(  # pragma: no cover - unreachable today
        authorization=authorization
    )


def main(argv: Sequence[str] | None = None) -> int:
    import argparse  # noqa: PLC0415 - CLI only

    parser = argparse.ArgumentParser(
        description="Successor real-model qualification driver"
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="run every offline check and report; contacts nothing",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help=(
            "score the official successor namespace and emit the frozen verdict; "
            "contacts nothing and runs no model"
        ),
    )
    parser.add_argument(
        protocol.HUMAN_GATE_FLAG,
        dest="execute_real_model",
        action="store_true",
        help=(
            "request real-model execution; currently refused because no human "
            "record authorizes qualification execution"
        ),
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.execute_real_model:
        return _refuse_execution()

    if args.analyze:
        root = PROJECT_ROOT / protocol.RESULTS_NAMESPACE
        if not root.exists():
            print(
                f"NO_EVIDENCE: {protocol.RESULTS_NAMESPACE} does not exist. No "
                "successor qualification has been authorized or executed, so there "
                "is nothing to score.",
                file=sys.stderr,
            )
            return protocol.EXIT_PREFLIGHT_STOP
        payload = analyze_official_qualification(root)  # pragma: no cover
        write_analysis(root, payload)  # pragma: no cover
        print(json.dumps(payload, indent=2, sort_keys=True))  # pragma: no cover
        for failure in payload["blocking_failures"]:  # pragma: no cover
            print(failure, file=sys.stderr)
        return (  # pragma: no cover
            protocol.EXIT_OK
            if payload["verdict"] == VERDICT_QUALIFIED
            else protocol.EXIT_VERDICT_HOLD
        )

    report = offline_preflight_report()
    failures = offline_preflight_failures()
    print(json.dumps(report, indent=2, sort_keys=True))
    for failure in failures:
        print(failure)
    print(
        f"Successor qualification driver: OFFLINE_PREFLIGHT "
        f"{'PASS' if not failures else 'FAIL'} ({len(failures)} failure(s)); "
        "EXECUTION_PATH: IMPLEMENTED; QUALIFICATION_EXECUTION: NOT_AUTHORIZED; "
        "NO PROVIDER CONTACT"
    )
    return protocol.EXIT_OK if not failures else protocol.EXIT_PREFLIGHT_STOP


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ANALYZER_VERSION",
    "CANONICAL_RUNTIME_IDENTITY",
    "CanonicalRuntimeEvidence",
    "CellExecutor",
    "CellExecutorFactory",
    "DRIVER_VERSION",
    "EXPERIMENT_KIND",
    "LoadedBenchmark",
    "MODE_OFFICIAL",
    "MODE_SYNTHETIC",
    "MetadataProbe",
    "REAL_EXECUTOR_MARKER",
    "RUNTIME_EVIDENCE_NAMESPACE",
    "RuntimeEvidenceInvalid",
    "RuntimeMetadata",
    "SnapshotCapture",
    "StopController",
    "SuccessorExecutionAuthorization",
    "SuccessorExecutionRefused",
    "VERDICT_HOLD",
    "VERDICT_QUALIFIED",
    "analyze",
    "analyze_official_qualification",
    "analyze_synthetic_evidence",
    "build_arms",
    "build_successor_schedule",
    "capture_stratum_runtime_snapshot",
    "cell_evidence_root",
    "cell_experiment_dir_value",
    "cell_slug",
    "cells_root",
    "check_confirmatory_remains_impossible",
    "check_execution_provenance",
    "check_experiment_configuration",
    "check_output_namespace",
    "check_runtime_evidence",
    "classify_row",
    "classify_row_detailed",
    "contract_drift",
    "describe_execution_inputs",
    "environment_preflight",
    "execute_authorized_real_run",
    "execute_offline_bound_run",
    "grant_execution_authorization",
    "human_gate_refusal",
    "load_benchmark",
    "load_runtime_evidence",
    "load_successor_provider",
    "lost_cell_row",
    "main",
    "make_cell_executor",
    "offline_preflight_failures",
    "offline_preflight_report",
    "probe_ollama_metadata",
    "protocol_summary",
    "provider_attempt_defects",
    "require_execution_authorization",
    "run_frozen_schedule",
    "schedule_digest",
    "stamp_frozen_identity",
    "write_analysis",
]
