#!/usr/bin/env python3
"""The OFFLINE PR-10 provider/runtime eligibility argument for the successor strata.

**NO PROVIDER CONTACT. NO ENDPOINT PROBE. NO MODEL METADATA QUERY.**
**NO MODEL INFERENCE. NO RUNTIME SNAPSHOT CAPTURE. NO SYNTHESIS OF ONE.**

WHAT THIS MODULE DECIDES, AND WHAT IT REFUSES TO DECIDE
=======================================================

``docs/post_phaseP_successor_provider_and_qualification_protocol_authorization.md``
selects two PROPOSED strata on the single ground of lineage continuity.
Selection is not eligibility.  ``docs/post_phaseP_confirmatory_randomization_design_decision.md``
section 12 makes PR-10 a **verification** obligation over a closed four-predicate
rule -- PR-4 ``POSITION_STATE_ISOLATION``, PR-5 ``INFRASTRUCTURE_SYMMETRY``,
PR-7 ``TOTAL_OBSERVATION`` and ``RUNTIME_CONFIGURATION_FROZEN`` -- and records
``CURRENT_PROVIDER_ELIGIBILITY: UNASSESSED`` for every provider configured in
this repository.  Nothing in the human selection changes that, and nothing here
does either.

This module evaluates each predicate as far as it can TRUTHFULLY be taken with
no provider contact, and says ``PENDING`` everywhere the remaining step is a live
runtime fact.  It never converts "I could not look" into "I looked and it was
fine".

THE PROJECTION IS NOT A RECORDED DISPOSITION -- AND THAT DISTINCTION MATTERS
============================================================================

If all four predicates were assessed today they would all be ``UNASSESSED``, and
the eligibility clarification's total derivation (section 8.2 step 2) would yield
``DESCRIPTIVE_ONLY_UNASSESSED``.  This module computes exactly that, through the
frozen :func:`derive_disposition`, and labels it a **projection**.

It is emphatically **not** recorded as a Stage-B disposition, and no
``eligibility_manifest.json`` is written, because doing so would be
*destructive*: eligibility clarification section 15 forbids promoting a recorded
``DESCRIPTIVE_ONLY_*`` stratum to ``CONFIRMATORY_ELIGIBLE`` in place, and
refused case 48 spells out the consequence -- the stratum could only be rescued
by abandoning the ``design_id`` and recreating it.  Recording today's unavoidable
ignorance as a disposition would therefore permanently exclude both selected
strata from the confirmatory matrix on the strength of evidence nobody has been
authorized to gather yet.  Stage B is entered later, once, with real evidence.

WHY NO ``RuntimeSnapshotV1`` IS BUILT HERE
==========================================

``RUNTIME_CONFIGURATION_FROZEN`` is evaluated against a per-stratum
registration-expected ``runtime_identity_digest``, which by eligibility
clarification section 12.3 lives inside one complete ``RuntimeSnapshotV1`` per
proposed stratum.  Implementation design section 5.I.5 makes that snapshot a
**capture point**, and section 5.I.3 puts live host and endpoint facts inside its
``environment_fingerprint`` preimage.  A snapshot assembled by a module that has
never observed the runtime is a fabrication no matter how well-formed it is, so
:func:`accept_captured_runtime_snapshot` refuses **every** offered snapshot --
including a structurally perfect one built by the frozen dataclass itself.  Shape
is not provenance.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping, NoReturn, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _root in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import successor_qualification_protocol as protocol  # noqa: E402
from iqa_soa.experiment.confirmatory_eligibility import (  # noqa: E402
    CHANNEL_IDS,
    DISPOSITIONS,
    EvidenceReferenceV1,
    InfrastructureSymmetryAuditV1,
    InfrastructureSymmetryChannelV1,
    PREDICATE_IDS,
    PREDICATE_STATUSES,
    derive_disposition,
    derive_infrastructure_symmetry_status,
)


class SuccessorEligibilityError(ValueError):
    """An offline eligibility precondition failed.  Always fail-closed."""


class SyntheticRuntimeSnapshotRejected(SuccessorEligibilityError):
    """A ``RuntimeSnapshotV1`` was offered to an offline module.

    Its own class so that no caller can confuse it with a schema-validation
    error.  This is not "your snapshot is malformed"; it is "no snapshot built
    without observing a runtime is a captured snapshot, whatever its shape".
    """


ARGUMENT_VERSION = "successor-pr10-offline-argument-1"
ARGUMENT_RECORD_RELATIVE = "docs/successor_pr10_offline_eligibility_argument.json"

#: This module's own three-token status vocabulary.  It is NOT the frozen Stage-B
#: vocabulary and is deliberately spelled differently where it differs:
#: ``PENDING`` says "the remaining step is evidence nobody is authorized to
#: gather yet", which is a stronger and more useful statement than the schema's
#: ``UNASSESSED``, even though it projects onto ``UNASSESSED`` exactly.
OFFLINE_STATUSES: tuple[str, ...] = ("PASS", "FAIL", "PENDING")

#: The total projection from this module's vocabulary onto the frozen one.
_OFFLINE_TO_STAGE_B: Mapping[str, str] = {
    "PASS": "PASS",
    "FAIL": "FAIL",
    "PENDING": "UNASSESSED",
}

STAGE_A_STATUS_BLOCKED = "BLOCKED_PENDING_RUNTIME_SNAPSHOT"
STAGE_B_ENTERED = False
ELIGIBILITY_MANIFEST_WRITTEN = False


def _digest(relative: str) -> str:
    """SHA-256 over the exact on-disk bytes of a repository-relative file."""

    return hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest()


def _ref(relative: str) -> EvidenceReferenceV1:
    """One ``REPOSITORY_PATH`` evidence reference, digest-bound at build time.

    Built through the FROZEN :class:`EvidenceReferenceV1` rather than a local
    dict, so a locator this module cannot express under the Stage-B grammar
    fails here rather than at Stage B, months later.
    """

    return EvidenceReferenceV1(
        evidence_kind="REPOSITORY_PATH",
        locator=relative,
        content_digest=_digest(relative),
    )


@dataclass(frozen=True, slots=True)
class OfflinePredicateAssessment:
    """One predicate, assessed as far as offline evidence honestly permits."""

    predicate_id: str
    offline_status: str
    established_offline: str
    blocking_facts: tuple[str, ...]
    offline_evidence: tuple[EvidenceReferenceV1, ...]

    def __post_init__(self) -> None:
        if self.predicate_id not in PREDICATE_IDS:
            raise SuccessorEligibilityError(
                f"{self.predicate_id!r} is not one of the four frozen predicates "
                f"{list(PREDICATE_IDS)}"
            )
        if self.offline_status not in OFFLINE_STATUSES:
            raise SuccessorEligibilityError(
                f"offline_status must be one of {list(OFFLINE_STATUSES)}, got "
                f"{self.offline_status!r}"
            )
        if self.offline_status == "PENDING" and not self.blocking_facts:
            raise SuccessorEligibilityError(
                f"{self.predicate_id}: PENDING must name at least one blocking "
                "fact; an unexplained PENDING is indistinguishable from a shrug"
            )
        if self.offline_status == "PASS" and not self.offline_evidence:
            raise SuccessorEligibilityError(
                f"{self.predicate_id}: PASS requires at least one evidence "
                "reference (eligibility clarification section 9.3, E13)"
            )

    @property
    def stage_b_status(self) -> str:
        """What Stage B would record for this predicate if assessed today."""

        return _OFFLINE_TO_STAGE_B[self.offline_status]

    @property
    def stage_b_evidence_refs(self) -> tuple[EvidenceReferenceV1, ...]:
        """The evidence a Stage-B record could legally carry, today.

        Section 9.3 is exact: ``UNASSESSED`` predicates carry **exactly** ``[]``,
        and ``INFRASTRUCTURE_SYMMETRY`` carries ``[]`` in every status because
        its evidence lives on the audit channels (section 9.5).  The offline
        evidence is not lost -- it stays on :attr:`offline_evidence`, which is a
        field of this module's record and not of the frozen schema.
        """

        if self.predicate_id == "INFRASTRUCTURE_SYMMETRY":
            return ()
        if self.stage_b_status == "UNASSESSED":
            return ()
        return self.offline_evidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "predicate_id": self.predicate_id,
            "offline_status": self.offline_status,
            "stage_b_status_if_assessed_today": self.stage_b_status,
            "established_offline": self.established_offline,
            "blocking_facts": list(self.blocking_facts),
            "offline_evidence_refs": [
                item.to_dict() for item in self.offline_evidence
            ],
            "stage_b_evidence_refs_if_assessed_today": [
                item.to_dict() for item in self.stage_b_evidence_refs
            ],
        }


def _channel(
    channel_id: str, observation: str, refs: Sequence[EvidenceReferenceV1]
) -> tuple[InfrastructureSymmetryChannelV1, dict[str, Any]]:
    """One PR-5 leak channel, recorded ``NOT_CHECKED`` with its offline finding.

    Every channel is ``NOT_CHECKED``.  Implementation design section 5.F states
    that this audit is "evidence-gathering, not architecture, and remains open by
    design", and the governing authorization does not authorize closing it.  Two
    of the four channels also depend on provider-side facts outright, so even a
    complete offline code review could not carry them.  Section 10.4 then settles
    the predicate: a partially audited stratum derives ``UNASSESSED``, never
    ``PASS``.

    The offline finding is carried alongside, in this module's own record, so the
    later audit starts from what has already been looked at rather than from
    nothing.
    """

    channel = InfrastructureSymmetryChannelV1(
        channel_id=channel_id,
        check_status="NOT_CHECKED",
        symmetry_result="SYMMETRY_NOT_ASSESSED",
        evidence_refs=(),
    )
    finding = {
        "channel_id": channel_id,
        "check_status": "NOT_CHECKED",
        "symmetry_result": "SYMMETRY_NOT_ASSESSED",
        "offline_observation": observation,
        "offline_evidence_refs": [item.to_dict() for item in refs],
    }
    return channel, finding


def _symmetry_channels() -> tuple[
    InfrastructureSymmetryAuditV1, tuple[dict[str, Any], ...]
]:
    """The four section 5.F channels, in the frozen positional order."""

    gateway_ref = _ref("src/iqa_soa/iqa/gateway.py")
    agent_ref = _ref("src/iqa_soa/agent/agent.py")
    providers_ref = _ref("src/iqa_soa/agent/providers.py")
    confirmatory_ref = _ref("src/iqa_soa/experiment/confirmatory.py")
    registration_ref = _ref("src/iqa_soa/experiment/confirmatory_registration.py")
    design_ref = _ref(
        "docs/post_phaseP_confirmatory_randomization_implementation_design.md"
    )

    specs = (
        (
            "PROMPT_SYSTEM_MESSAGE_CONTENT",
            (
                "Offline inspection finds no reference to qa_mode or QAMode "
                "anywhere in src/iqa_soa/agent/agent.py or "
                "src/iqa_soa/agent/providers.py, so the prompt-construction and "
                "request-serialization path is label-blind by construction. That "
                "is a necessary condition, not a sufficient one: under QA FULL "
                "the gateway can deny an action, and a denial changes what "
                "appears in the conversation history the NEXT turn sends. "
                "Deciding whether that difference stays inside the intended "
                "qa_mode semantics is the substance of this channel's audit and "
                "is not settled by the absence of a symbol."
            ),
            (agent_ref, providers_ref, gateway_ref),
        ),
        (
            "GATEWAY_PATH_LATENCY_SIGNATURE",
            (
                "Implementation design section 5.F states the difference itself: "
                "QAMode.OFF short-circuits to ALLOW without invoking the QA "
                "chain, which is an intended behavioural difference and a leak "
                "only if it also crosses a provider-side rate-limit or "
                "cache-tier boundary. Whether the local runtime has such a "
                "boundary is a provider-side fact. No committed artifact records "
                "it and no offline inspection of this repository can produce it."
            ),
            (gateway_ref, design_ref),
        ),
        (
            "EVIDENCE_VOLUME",
            (
                "FULL emits richer evidence than OFF. Whether evidence writing "
                "shares I/O capacity with the provider call path in a way the "
                "serving side can observe depends on the host and on the "
                "runtime's own I/O behaviour under load. Both are live facts."
            ),
            (design_ref,),
        ),
        (
            "PROVIDER_MODEL_SELECTION",
            (
                "Both selected strata name one endpoint, fixed by (provider, "
                "model) in configs/successor-models.yaml, with no qa_mode-"
                "conditional branch in the configuration. The residual exposure "
                "is at the interface, not the config: the frozen "
                "ProviderFactory.create_for_position contract receives a whole "
                "ConfirmatoryPositionV1, which carries baseline_label. The "
                "realized label is deliberately absent from that record, but "
                "baseline_label is label-correlated within a task once b_k is "
                "fixed, so a caller-supplied factory could in principle condition "
                "endpoint or pool selection on it. Closing this channel requires "
                "auditing the concrete factory implementation used at execution, "
                "which does not exist yet."
            ),
            (confirmatory_ref, registration_ref, design_ref),
        ),
    )

    channels: list[InfrastructureSymmetryChannelV1] = []
    findings: list[dict[str, Any]] = []
    for channel_id, observation, refs in specs:
        channel, finding = _channel(channel_id, observation, refs)
        channels.append(channel)
        findings.append(finding)
    if tuple(item.channel_id for item in channels) != CHANNEL_IDS:
        raise SuccessorEligibilityError(
            "the assembled channels are not the four frozen channel ids in order"
        )
    return InfrastructureSymmetryAuditV1(channels=tuple(channels)), tuple(findings)


def _pr4_assessment() -> OfflinePredicateAssessment:
    """PR-4 ``POSITION_STATE_ISOLATION`` -- local half yes, provider half no."""

    return OfflinePredicateAssessment(
        predicate_id="POSITION_STATE_ISOLATION",
        offline_status="PENDING",
        established_offline=(
            "The LOCAL half is structural and already holds. Implementation "
            "design section 5.E freezes ProviderFactory.create_for_position, and "
            "src/iqa_soa/experiment/confirmatory.py obtains exactly one new "
            "AgentProvider per position and never reuses an instance across two "
            "position_id values, so sandbox, tool registry and session objects "
            "are fresh per position by construction rather than by argument."
        ),
        blocking_facts=(
            "Implementation design section 5.E states outright that provider-side "
            "infrastructure which cannot be locally recreated -- routing, "
            "rate-limit buckets, shared serving infrastructure -- is outside what "
            "a fresh local context can prove, and closes with: 'This document "
            "still does not claim that any real provider passes PR-4; that "
            "remains [DEFERRED VERIFICATION].'",
            "For a local Ollama runtime specifically, the unresolved facts are "
            "server-side: whether prefix/KV cache state, a loaded-model slot or a "
            "connection pool is reused across requests in a way that could carry "
            "information about one position's label into another position's "
            "execution. No committed artifact in this repository records any of "
            "them, and obtaining them requires runtime contact.",
        ),
        offline_evidence=(
            _ref("src/iqa_soa/experiment/confirmatory.py"),
            _ref(
                "docs/post_phaseP_confirmatory_randomization_implementation_design.md"
            ),
        ),
    )


def _pr5_assessment() -> OfflinePredicateAssessment:
    """PR-5 ``INFRASTRUCTURE_SYMMETRY`` -- derived from the channels, never set."""

    audit, _ = _symmetry_channels()
    derived = derive_infrastructure_symmetry_status(audit)
    if derived != "UNASSESSED":  # pragma: no cover - defensive
        raise SuccessorEligibilityError(
            f"the four NOT_CHECKED channels derived {derived!r}, expected UNASSESSED"
        )
    return OfflinePredicateAssessment(
        predicate_id="INFRASTRUCTURE_SYMMETRY",
        offline_status="PENDING",
        established_offline=(
            "All four section 5.F leak channels are enumerated and each carries a "
            "recorded offline observation, so the later audit starts from what "
            "has already been looked at. The predicate status is DERIVED from the "
            "channels by the frozen derive_infrastructure_symmetry_status, never "
            "asserted: with four NOT_CHECKED channels, section 10.4 yields "
            "UNASSESSED."
        ),
        blocking_facts=(
            "Implementation design section 5.F declares this audit "
            "'evidence-gathering, not architecture', explicitly 'not resolved "
            "here' and 'open by design'. The governing authorization record does "
            "not authorize closing it.",
            "GATEWAY_PATH_LATENCY_SIGNATURE and EVIDENCE_VOLUME depend on "
            "provider-side and host-side behaviour under load, which no offline "
            "inspection of this repository can supply.",
            "Section 10.4 permits PASS only when EVERY channel is CHECKED with no "
            "asymmetry found, so no partial close can raise this predicate above "
            "UNASSESSED.",
        ),
        offline_evidence=(),
    )


def _pr7_assessment() -> OfflinePredicateAssessment:
    """PR-7 ``TOTAL_OBSERVATION`` -- prospective, and not completable yet."""

    return OfflinePredicateAssessment(
        predicate_id="TOTAL_OBSERVATION",
        offline_status="PENDING",
        established_offline=(
            "The instrument-side precondition is closed. Change C3 landed the "
            "provider failure-telemetry repair (instrument 5, raw schema 6), so "
            "every provider failure now carries structured provenance instead of "
            "collapsing into an untyped error, and implementation design section "
            "5.H requires the collection boundary to emit observation_status and "
            "failure_class explicitly for every confirmatory row rather than "
            "inferring observability from whether an endpoint value is present. "
            "That machinery is also label-blind, which is what a schedule-"
            "invariant observability argument would rest on."
        ),
        blocking_facts=(
            "Design decision section 12 requires the argument to hold for every "
            "admissible b in B, not merely the realized one. B is the admissible "
            "assignment set of a registered confirmatory matrix, and no "
            "registration draft exists for this candidate, so there is no B to "
            "quantify over yet.",
            "The evidence column requires an 'offline observability design "
            "argument PER PROVIDER/RUNTIME'. No such argument exists for either "
            "selected stratum; docs/post_phaseP_provider_observability_design.md "
            "is an instrument-level record and names no provider or model.",
            "Section 12's own failure example -- a known differential-timeout "
            "profile that is not part of the treatment mechanism -- is a live "
            "runtime property of each local model at the frozen 600-second "
            "timeout with zero retries. It is unobserved for both strata.",
        ),
        offline_evidence=(
            _ref("docs/post_phaseP_provider_observability_design.md"),
            _ref("src/iqa_soa/agent/providers.py"),
            _ref("src/iqa_soa/metrics/collector.py"),
        ),
    )


def _runtime_frozen_assessment() -> OfflinePredicateAssessment:
    """``RUNTIME_CONFIGURATION_FROZEN`` -- needs a capture, and captures are barred."""

    return OfflinePredicateAssessment(
        predicate_id="RUNTIME_CONFIGURATION_FROZEN",
        offline_status="PENDING",
        established_offline=(
            "Everything this predicate compares AGAINST is frozen and citable: "
            "the model identity and digest pins, the runtime-version pin, the "
            "per-slot tool contract policy, the protocol, the endpoint and the "
            "600-second timeout with infrastructure_retry_limit 0 all live in "
            "scripts/successor_qualification_protocol.py and "
            "configs/successor-models.yaml, and successor_qualification_protocol."
            "verify_runtime_identity already fixes, offline, that any live "
            "disagreement is an ENVIRONMENT_HOLD rather than a repair. Both "
            "configuration digests a RuntimeSnapshotV1 carries now have a "
            "successor-owned file to digest: models_config_digest over "
            "configs/successor-models.yaml and experiment_config_digest over "
            "configs/successor-qualification.yaml, the successor ExperimentConfig, "
            "which is itself digest-bound by "
            "docs/successor_frozen_execution_inputs.json. The comparison rule is "
            "frozen; only the observation is missing."
        ),
        blocking_facts=(
            "Eligibility clarification section 12.3 requires one complete "
            "RuntimeSnapshotV1 per proposed stratum, and the registration-"
            "expected runtime identity for a stratum IS that snapshot's "
            "runtime_identity_digest. Neither stratum has one.",
            "Implementation design section 5.I.5 makes the registration-expected "
            "snapshot a CAPTURE POINT, and section 5.I.3 puts live host facts "
            "(platform_system, platform_release, platform_machine, "
            "python_implementation, python_version) and the provider endpoint "
            "inside the environment_fingerprint preimage. A snapshot assembled "
            "without observing the runtime is a fabrication regardless of shape.",
            "The model-digest and runtime-version pins are carried forward "
            "PROSPECTIVELY from committed non-outcome lineage records. Whether "
            "the live runtime still presents them is exactly the unobserved fact, "
            "and is the ENVIRONMENT_HOLD boundary rather than something this "
            "module may assume.",
            "The governing authorization record section 5A carries a "
            "human-reported environment runtime version that is NOT the frozen "
            "pin, resolved as RESTORE_FROZEN_RUNTIME with RUNTIME_REPIN "
            "NOT_AUTHORIZED. This module probed nothing and confirms nothing "
            "about it; it records only that the environment must be restored to "
            "the pinned runtime BEFORE a capture, so a capture taken against an "
            "unrestored environment would be an ENVIRONMENT_HOLD rather than "
            "evidence for this predicate.",
        ),
        offline_evidence=(
            _ref("configs/successor-models.yaml"),
            _ref("configs/successor-qualification.yaml"),
            _ref("scripts/successor_qualification_protocol.py"),
            _ref("docs/post_phaseP_confirmatory_eligibility_schema_clarification.md"),
        ),
    )


def offline_assessments() -> tuple[OfflinePredicateAssessment, ...]:
    """The four predicates, in the frozen order, assessed offline."""

    assessments = (
        _pr4_assessment(),
        _pr5_assessment(),
        _pr7_assessment(),
        _runtime_frozen_assessment(),
    )
    if tuple(item.predicate_id for item in assessments) != PREDICATE_IDS:
        raise SuccessorEligibilityError(
            "the assembled assessments are not the four frozen predicates in order"
        )
    return assessments


def projected_disposition(
    assessments: Sequence[OfflinePredicateAssessment],
) -> str:
    """What Stage B WOULD derive today -- through the frozen derivation.

    Computed by :func:`derive_disposition` rather than by a local rule, so this
    projection can never disagree with the schema it projects onto.  It is a
    projection and nothing more: see the module docstring on why recording it as
    an actual Stage-B disposition would be destructive.
    """

    statuses = [item.stage_b_status for item in assessments]
    for status in statuses:
        if status not in PREDICATE_STATUSES:
            raise SuccessorEligibilityError(
                f"{status!r} is not one of the frozen statuses {list(PREDICATE_STATUSES)}"
            )
    disposition = derive_disposition(statuses)
    if disposition not in DISPOSITIONS:  # pragma: no cover - defensive
        raise SuccessorEligibilityError(f"{disposition!r} is not a frozen disposition")
    return disposition


def accept_captured_runtime_snapshot(payload: Any) -> NoReturn:
    """Refuse EVERY runtime snapshot offered to this offline module.

    There is no argument that makes this return.  A ``RuntimeSnapshotV1`` is
    defined by implementation design section 5.I.5 as something CAPTURED at one
    of three points; a value handed to a module that has never observed a runtime
    was not captured, and a structurally perfect object built by the frozen
    dataclass is exactly the case this refusal exists for.  Shape is not
    provenance, and the schema cannot tell the difference -- which is why the
    refusal lives here rather than in the schema.
    """

    raise SyntheticRuntimeSnapshotRejected(
        "SYNTHETIC_RUNTIME_SNAPSHOT_REFUSED: the offline eligibility preflight "
        "accepts no RuntimeSnapshotV1, however well-formed. Implementation design "
        "section 5.I.5 defines the registration-expected snapshot as CAPTURED "
        "before eligibility/final registration, and section 5.I.3 places live host "
        "and endpoint facts inside its environment_fingerprint preimage. This "
        "module has contacted no runtime, so anything it accepted here would be "
        "fabricated evidence for RUNTIME_CONFIGURATION_FROZEN. Capture requires a "
        "separately authorized runtime preflight."
    )


def runtime_snapshot_capture_required_next() -> bool:
    """Whether a real runtime capture is the next blocking step.  It is."""

    return True


def stage_a_status() -> str:
    """Whether a VALID Stage-A registration draft can be generated today.

    It cannot.  A ``RegistrationDraftV1`` validates V10' -- ``proposed_runtime_``
    ``configuration`` holds one complete, digest-verifying ``RuntimeSnapshotV1``
    per proposed stratum, an exact element-wise cover of ``proposed_strata``
    (eligibility clarification section 12.3, RC-1..RC-5).  With two proposed
    strata and zero captured snapshots the cover is unsatisfiable, and the only
    way to satisfy it today would be to fabricate two snapshots, which
    :func:`accept_captured_runtime_snapshot` refuses.
    """

    return STAGE_A_STATUS_BLOCKED


def stratum_argument(provider: str, model: str) -> dict[str, Any]:
    """The complete offline PR-10 argument for ONE proposed stratum.

    The four predicates are provider-independent as assessed today, and that is
    itself a finding rather than a shortcut: every blocking fact is a live
    runtime observation, and neither stratum has any.  The argument is still
    emitted per stratum, because PR-10 is a per-stratum obligation and a shared
    conclusion is not a shared record.
    """

    if (provider, model) not in protocol.PROPOSED_STRATA:
        raise SuccessorEligibilityError(
            f"{(provider, model)!r} is not one of the proposed strata "
            f"{[list(item) for item in protocol.PROPOSED_STRATA]}"
        )
    assessments = offline_assessments()
    audit, channel_findings = _symmetry_channels()
    return {
        "provider": provider,
        "model": model,
        "selection_basis": protocol.STRATUM_SELECTION_SEMANTICS["selection_basis"],
        "selection_establishes": protocol.STRATUM_SELECTION_SEMANTICS[
            "selection_establishes"
        ],
        "expected_model_digest_pin": protocol.EXPECTED_MODEL_DIGEST[model],
        "expected_runtime_version_pin": protocol.EXPECTED_RUNTIME_VERSION,
        "accepted_runtime_versions": list(protocol.ACCEPTED_RUNTIME_VERSIONS),
        "runtime_version_comparison": protocol.RUNTIME_VERSION_COMPARISON,
        "runtime_version_resolution": protocol.RUNTIME_VERSION_RESOLUTION,
        "runtime_repin_authorized": protocol.RUNTIME_REPIN_AUTHORIZED,
        "runtime_restore_required": protocol.RUNTIME_RESTORE_REQUIRED,
        "experiment_config": protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE,
        "runtime_identity_pin_status": "PROSPECTIVE_UNVERIFIED",
        "captured_runtime_snapshot_count": 0,
        "registration_expected_runtime_identity_digest": None,
        "predicates": [item.to_dict() for item in assessments],
        "infrastructure_symmetry_audit": {
            "derived_status": derive_infrastructure_symmetry_status(audit),
            "channels": [item.to_dict() for item in audit.channels],
            "offline_channel_findings": list(channel_findings),
        },
        "projected_stage_b_disposition": projected_disposition(assessments),
        "projected_disposition_is_recorded": False,
        "disposition": "NOT_ASSIGNED_STAGE_B_NOT_ENTERED",
        "confirmatory_eligible": False,
        "provider_contacted": False,
        "model_inference_performed": False,
    }


def argument_record() -> dict[str, Any]:
    """The complete offline PR-10 argument artifact for both proposed strata."""

    return {
        "argument_version": ARGUMENT_VERSION,
        "record_kind": "successor_pr10_offline_eligibility_argument",
        "schema_version": 1,
        "authorization_record": protocol.AUTHORIZATION_RECORD_RELATIVE,
        "canonical_base_commit": protocol.CANONICAL_BASE_COMMIT,
        "candidate_identifier": protocol.CANDIDATE_IDENTIFIER,
        "candidate_status_at_entry": protocol.CANDIDATE_STATUS_AT_ENTRY,
        "predicate_order": list(PREDICATE_IDS),
        "offline_status_vocabulary": list(OFFLINE_STATUSES),
        "offline_to_stage_b_projection": dict(_OFFLINE_TO_STAGE_B),
        "strata": [
            stratum_argument(provider, model)
            for provider, model in protocol.PROPOSED_STRATA
        ],
        "stage_a_status": stage_a_status(),
        "stage_b_entered": STAGE_B_ENTERED,
        "eligibility_manifest_written": ELIGIBILITY_MANIFEST_WRITTEN,
        "registration_draft_written": False,
        "runtime_snapshot_capture_required_next": runtime_snapshot_capture_required_next(),
        "runtime_snapshots_captured": 0,
        "runtime_snapshots_synthesized": 0,
        "why_the_projection_is_not_recorded": (
            "Eligibility clarification section 15 forbids promoting a recorded "
            "DESCRIPTIVE_ONLY_* stratum to CONFIRMATORY_ELIGIBLE in place, and "
            "refused case 48 makes the consequence explicit: such a stratum can "
            "only be rescued by abandoning the design_id and recreating it. "
            "Recording today's unavoidable ignorance as a Stage-B disposition "
            "would therefore permanently exclude both selected strata from the "
            "confirmatory matrix on the strength of evidence nobody has been "
            "authorized to gather. Stage B is entered later, once, with real "
            "evidence."
        ),
        "provider_contacted": False,
        "endpoint_probed": False,
        "model_metadata_queried": False,
        "model_inference_performed": False,
        "confirmatory_execution_authorized": protocol.CONFIRMATORY_EXECUTION_AUTHORIZED,
        "qualification_execution_authorized": protocol.QUALIFICATION_EXECUTION_AUTHORIZED,
        "current_provider_eligibility": "UNASSESSED",
    }


def check_argument_integrity() -> list[str]:
    """Offline self-checks over the argument this module produces."""

    failures: list[str] = []
    record = argument_record()
    strata = record["strata"]
    if len(strata) != 2:
        failures.append(f"PR10: {len(strata)} strata are argued, expected exactly 2")
    for stratum in strata:
        label = f"{stratum['provider']}/{stratum['model']}"
        if stratum["confirmatory_eligible"]:
            failures.append(f"PR10: {label} claims confirmatory eligibility")
        if stratum["disposition"] != "NOT_ASSIGNED_STAGE_B_NOT_ENTERED":
            failures.append(f"PR10: {label} carries a recorded Stage-B disposition")
        if stratum["projected_stage_b_disposition"] == "CONFIRMATORY_ELIGIBLE":
            failures.append(
                f"PR10: {label} projects CONFIRMATORY_ELIGIBLE with no captured "
                "runtime evidence"
            )
        if stratum["captured_runtime_snapshot_count"] != 0:
            failures.append(f"PR10: {label} claims a captured runtime snapshot")
        if stratum["accepted_runtime_versions"] != [protocol.EXPECTED_RUNTIME_VERSION]:
            failures.append(
                f"PR10: {label} accepts a runtime version other than the frozen pin"
            )
        if stratum["runtime_version_comparison"] != "EXACT_STRING_EQUALITY":
            failures.append(f"PR10: {label} softens the runtime version comparison")
        if stratum["runtime_repin_authorized"]:
            failures.append(f"PR10: {label} claims a runtime repin is authorized")
        if stratum["registration_expected_runtime_identity_digest"] is not None:
            failures.append(
                f"PR10: {label} claims a registration-expected runtime identity"
            )
        statuses = [item["offline_status"] for item in stratum["predicates"]]
        if any(status not in OFFLINE_STATUSES for status in statuses):
            failures.append(f"PR10: {label} carries a status outside the vocabulary")
    if record["stage_a_status"] != STAGE_A_STATUS_BLOCKED:
        failures.append("PR10: Stage A is not reported blocked")
    if record["stage_b_entered"] or record["eligibility_manifest_written"]:
        failures.append("PR10: Stage B is claimed entered")
    if record["runtime_snapshots_synthesized"] != 0:
        failures.append("PR10: a synthesized runtime snapshot is claimed")
    if record["current_provider_eligibility"] != "UNASSESSED":
        failures.append("PR10: provider eligibility is claimed to be assessed")
    return failures


def main(argv: Sequence[str] | None = None) -> int:
    """Emit the offline PR-10 argument and its self-check verdict."""

    import argparse  # noqa: PLC0415 - CLI only

    parser = argparse.ArgumentParser(description="Successor offline PR-10 argument")
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the argument record; refuses to overwrite an existing one",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    record = argument_record()
    failures = check_argument_integrity()

    if args.write:
        target = PROJECT_ROOT / ARGUMENT_RECORD_RELATIVE
        if target.exists():
            print(
                f"REFUSED: {ARGUMENT_RECORD_RELATIVE} already exists; the offline "
                "PR-10 argument is written once and never overwritten"
            )
            return 2
        if failures:
            print("REFUSED: the argument fails its own integrity checks")
            for failure in failures:
                print(failure)
            return 2
        payload = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True)
        target.write_text(payload + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {ARGUMENT_RECORD_RELATIVE}")
        return 0

    print(json.dumps(record, indent=2, sort_keys=True))
    for failure in failures:
        print(failure)
    print(
        f"Successor offline PR-10 argument: {'PASS' if not failures else 'FAIL'} "
        f"({len(failures)} failure(s)); NO PROVIDER CONTACT; NO RUNTIME CAPTURE"
    )
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
