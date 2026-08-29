"""Focused tests for the Stage-B eligibility manifest schema and immutability.

Every artifact these tests write lives in a pytest ``tmp_path``.  No real
``design_id``, task, provider, model, endpoint, or runtime appears anywhere here,
nothing is written under ``results/``, and no provider, model, network, or
randomness is touched.

**No eligibility is assessed here.**  Every predicate status, evidence
reference, symmetry finding, and disposition below is a synthetic value chosen to
exercise the frozen schema.  The code implementation authorization keeps
``ACTUAL_CONFIRMATORY_REGISTRATION_AUTHORIZED: NO`` and design decision §9 keeps
``CURRENT_PROVIDER_ELIGIBILITY: UNASSESSED`` for every configured provider and
runtime; nothing in this module changes either.

The Stage-A drafts these tests bind to are built with the committed Work Unit 1
helpers (``draft_registration``, ``write_registration_draft``), never with a
reimplemented parser.
"""

from __future__ import annotations

import ast
from dataclasses import fields as dataclass_fields, replace
from datetime import UTC, datetime, timedelta, timezone
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any, Callable, Iterator

import pytest

from iqa_soa.experiment import confirmatory_eligibility as eligibility_module
from iqa_soa.experiment.confirmatory_eligibility import (
    CHANNEL_IDS,
    CHECK_STATUSES,
    DISPOSITIONS,
    ELIGIBILITY_MANIFEST_FILENAME,
    ELIGIBILITY_MANIFEST_SCHEMA_VERSION,
    EVIDENCE_KINDS,
    FORBIDDEN_KEY_NAMES,
    PREDICATE_IDS,
    PREDICATE_STATUSES,
    REGISTRATION_STATE_ELIGIBILITY_FROZEN,
    SYMMETRY_RESULTS,
    ConfirmatoryEligibilityError,
    EligibilityManifestV1,
    EligibilityPredicateRecordV1,
    EligibilityStratumRecordV1,
    EvidenceReferenceV1,
    InfrastructureSymmetryAuditV1,
    InfrastructureSymmetryChannelV1,
    derive_disposition,
    derive_infrastructure_symmetry_status,
    eligibility_manifest_path,
    freeze_eligibility,
    load_eligibility_manifest,
    write_eligibility_manifest,
)
from iqa_soa.experiment.confirmatory_registration import (
    BASELINE_LABEL_FULL,
    BASELINE_LABEL_OFF,
    CONFIRMATORY_PROFILE,
    ProposedPositionV1,
    ProposedProviderSeedEntryV1,
    ProposedRepetitionsEntryV1,
    ProposedRuntimeConfigurationV1,
    ProposedStratumV1,
    REGISTRATION_STATE_DRAFT,
    RegistrationDraft,
    RetryPolicyV1,
    RuntimeSnapshotV1,
    SELF_DIGEST_FIELD,
    attach_self_digest,
    canonical_json_bytes,
    compute_self_digest,
    draft_registration,
    registration_draft_path,
    serialize_artifact,
    verify_self_digest,
    write_registration_draft,
)

SYNTHETIC_DESIGN_ID = "synthetic-eligibility-000"
SYNTHETIC_CREATED_AT = datetime(2026, 2, 2, 3, 4, 5, tzinfo=UTC)
SYNTHETIC_CREATED_AT_TEXT = "2026-02-02T03:04:05Z"
SYNTHETIC_TASKS = ("synthetic-task-a",)

#: Two invented strata, already in ``(provider, model)`` ascending order.
STRATUM_A = ("synthetic-provider-a", "synthetic-model-a")
STRATUM_B = ("synthetic-provider-b", "synthetic-model-b")

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_UNASSESSED = "UNASSESSED"

#: The clarification §17 illustration: one recorded ``PASS`` and three
#: unassessed predicates, which derives ``DESCRIPTIVE_ONLY_UNASSESSED``.
DEFAULT_STATUSES = (STATUS_PASS, STATUS_UNASSESSED, STATUS_UNASSESSED, STATUS_UNASSESSED)
ALL_PASS = (STATUS_PASS,) * 4
ALL_UNASSESSED = (STATUS_UNASSESSED,) * 4

#: The single trailing LF the frozen persistence appends after every digest.
_TRAILING_LF = b"\n"

REPOSITORY_DIGEST = "a" * 64
ATTESTATION_DIGEST = "b" * 64
FOREIGN_DIGEST = "c" * 64


# ---------------------------------------------------------------------------
# Synthetic Stage-A drafts, built through the committed Work Unit 1 helpers
# ---------------------------------------------------------------------------


def _synthetic_snapshot(provider: str, model: str, **overrides: Any) -> RuntimeSnapshotV1:
    arguments: dict[str, Any] = {
        "provider_name": provider,
        "model": model,
        "endpoint": f"https://{provider}.invalid/v1",
        "provider_config_digest": "0" * 64,
        "provider_parameters_digest": "1" * 64,
        "timeout_seconds": "30.5",
        "retry_policy": RetryPolicyV1(
            max_attempts=1,
            backoff_kind="NONE",
            initial_delay_seconds="0",
            max_delay_seconds="0",
            retryable_error_classes=("SYNTHETIC_A",),
        ),
        "tool_contract_policy": "SYNTHETIC_TOOL_POLICY_V1",
        "native_tool_adapter_version": "synthetic-adapter-v1",
        "package_source_sha256": "2" * 64,
        "python_version": "3.11.0",
        "artifact_version": "synthetic-artifact-v1",
        "prompt_digest": "3" * 64,
        "experiment_config_digest": "4" * 64,
        "models_config_digest": "5" * 64,
        "environment_fingerprint": "6" * 64,
        "captured_at": SYNTHETIC_CREATED_AT.isoformat(),
    }
    arguments.update(overrides)
    return RuntimeSnapshotV1(**arguments)


def _synthetic_draft(
    *strata: tuple[str, str], design_id: str = SYNTHETIC_DESIGN_ID
) -> RegistrationDraft:
    """A minimal valid Stage-A draft over one task and the named strata."""

    pairs = strata or (STRATUM_A,)
    proposed_strata = tuple(
        ProposedStratumV1(provider=provider, model=model) for provider, model in pairs
    )
    repetitions = tuple(
        ProposedRepetitionsEntryV1(
            task_id=task_id, provider=provider, model=model, repetition_count=1
        )
        for task_id in SYNTHETIC_TASKS
        for provider, model in pairs
    )
    positions = tuple(
        ProposedPositionV1(
            task_id=entry.task_id,
            provider=entry.provider,
            model=entry.model,
            repetition=0,
            provider_seed=11,
            slot=slot,
            baseline_label=label,
        )
        for entry in repetitions
        for slot, label in ((1, BASELINE_LABEL_OFF), (2, BASELINE_LABEL_FULL))
    )
    return draft_registration(
        design_id=design_id,
        created_at=SYNTHETIC_CREATED_AT,
        proposed_tasks=SYNTHETIC_TASKS,
        proposed_strata=proposed_strata,
        proposed_repetitions=repetitions,
        proposed_provider_seeds=(
            ProposedProviderSeedEntryV1(repetition=0, provider_seed=11),
        ),
        proposed_positions=positions,
        proposed_runtime_configuration=ProposedRuntimeConfigurationV1(
            registration_expected_runtime_snapshots=tuple(
                _synthetic_snapshot(provider, model) for provider, model in pairs
            )
        ),
    )


def _runtime_digests(draft: RegistrationDraft) -> tuple[str, ...]:
    return tuple(
        snapshot.runtime_identity_digest
        for snapshot in (
            draft.proposed_runtime_configuration.registration_expected_runtime_snapshots
        )
    )


# ---------------------------------------------------------------------------
# Synthetic eligibility records — invented findings, never real assessments
# ---------------------------------------------------------------------------


def _repository_evidence(
    locator: str = "docs/synthetic-offline-review.md",
    digest: str = REPOSITORY_DIGEST,
) -> EvidenceReferenceV1:
    return EvidenceReferenceV1(
        evidence_kind="REPOSITORY_PATH", locator=locator, content_digest=digest
    )


def _attestation_evidence(
    locator: str = "https://synthetic-provider.invalid/attestation",
    digest: str = ATTESTATION_DIGEST,
) -> EvidenceReferenceV1:
    return EvidenceReferenceV1(
        evidence_kind="EXTERNAL_ATTESTATION", locator=locator, content_digest=digest
    )


def _draft_field_evidence(
    draft_digest: str,
    locator: str = "registration_draft.json#/proposed_runtime_configuration",
) -> EvidenceReferenceV1:
    return EvidenceReferenceV1(
        evidence_kind="DESIGN_ARTIFACT_FIELD",
        locator=locator,
        content_digest=draft_digest,
    )


def _channel(
    index: int,
    *,
    checked: bool,
    asymmetry: bool = False,
    evidence: tuple[EvidenceReferenceV1, ...] | None = None,
    channel_id: str | None = None,
    symmetry_result: str | None = None,
) -> InfrastructureSymmetryChannelV1:
    default_evidence: tuple[EvidenceReferenceV1, ...]
    if checked:
        default_result = "ASYMMETRY_FOUND" if asymmetry else "NO_ASYMMETRY_FOUND"
        default_evidence = (_repository_evidence(f"docs/synthetic-channel-{index}.md"),)
    else:
        default_result = "SYMMETRY_NOT_ASSESSED"
        default_evidence = ()
    return InfrastructureSymmetryChannelV1(
        channel_id=CHANNEL_IDS[index] if channel_id is None else channel_id,
        check_status="CHECKED" if checked else "NOT_CHECKED",
        symmetry_result=default_result if symmetry_result is None else symmetry_result,
        evidence_refs=default_evidence if evidence is None else evidence,
    )


def _audit_for(status: str) -> InfrastructureSymmetryAuditV1:
    """The channel configuration that derives ``status`` by §10.4."""

    if status == STATUS_PASS:
        channels = tuple(_channel(index, checked=True) for index in range(4))
    elif status == STATUS_FAIL:
        channels = (
            _channel(0, checked=True, asymmetry=True),
            *(_channel(index, checked=False) for index in range(1, 4)),
        )
    else:
        channels = tuple(_channel(index, checked=False) for index in range(4))
    return InfrastructureSymmetryAuditV1(channels=channels)


def _predicates(statuses: tuple[str, ...]) -> tuple[EligibilityPredicateRecordV1, ...]:
    records: list[EligibilityPredicateRecordV1] = []
    for index, status in enumerate(statuses):
        if index == 1 or status == STATUS_UNASSESSED:
            refs: tuple[EvidenceReferenceV1, ...] = ()
        else:
            refs = (_repository_evidence(f"docs/synthetic-predicate-{index}.md"),)
        records.append(
            EligibilityPredicateRecordV1(
                predicate_id=PREDICATE_IDS[index], status=status, evidence_refs=refs
            )
        )
    return tuple(records)


def _record(
    stratum: tuple[str, str],
    runtime_digest: str,
    statuses: tuple[str, ...] = DEFAULT_STATUSES,
) -> EligibilityStratumRecordV1:
    provider, model = stratum
    return EligibilityStratumRecordV1(
        provider=provider,
        model=model,
        predicates=_predicates(statuses),
        infrastructure_symmetry_audit=_audit_for(statuses[1]),
        runtime_identity_digest=runtime_digest,
    )


def _records_for(
    draft: RegistrationDraft, *statuses: tuple[str, ...]
) -> tuple[EligibilityStratumRecordV1, ...]:
    digests = _runtime_digests(draft)
    per_stratum = statuses or (DEFAULT_STATUSES,) * len(draft.proposed_strata)
    return tuple(
        _record((stratum.provider, stratum.model), digests[index], per_stratum[index])
        for index, stratum in enumerate(draft.proposed_strata)
    )


def _manifest(
    draft: RegistrationDraft, *statuses: tuple[str, ...]
) -> EligibilityManifestV1:
    return freeze_eligibility(
        registration_draft=draft,
        created_at=SYNTHETIC_CREATED_AT,
        eligibility_records=_records_for(draft, *statuses),
    )


# ---------------------------------------------------------------------------
# Persistence and adversarial-construction helpers
# ---------------------------------------------------------------------------


def _written_draft(tmp_path: Path, *strata: tuple[str, str]) -> RegistrationDraft:
    draft = _synthetic_draft(*strata)
    write_registration_draft(draft, confirmatory_root=tmp_path)
    return draft


def _persist(artifact: dict[str, Any], tmp_path: Path) -> Path:
    """Persist a hand-built artifact with a freshly recomputed ``self_digest``."""

    path = tmp_path / ELIGIBILITY_MANIFEST_FILENAME
    path.write_bytes(serialize_artifact(attach_self_digest(artifact)))
    return path


def _persist_unsealed(artifact: dict[str, Any], tmp_path: Path) -> Path:
    """Persist a hand-built artifact **without** refreshing its ``self_digest``.

    Used by the precedence table to give an artifact a stale digest alongside a
    schema defect, so E20 is genuinely one of the two simultaneous failures.
    """

    path = tmp_path / ELIGIBILITY_MANIFEST_FILENAME
    path.write_bytes(canonical_json_bytes(artifact) + _TRAILING_LF)
    return path


def _load_mutated(
    manifest: EligibilityManifestV1,
    draft: RegistrationDraft,
    tmp_path: Path,
    mutate: Callable[[dict[str, Any]], None],
) -> EligibilityManifestV1:
    """Mutate the persisted artifact, re-seal it, and load it.

    Re-sealing is deliberate: it proves the rule under test rejects on its own
    schema grounds rather than merely because a digest stopped matching.
    """

    artifact = manifest.to_artifact()
    mutate(artifact)
    return load_eligibility_manifest(
        _persist(artifact, tmp_path), registration_draft=draft
    )


def _first_record(artifact: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = artifact["eligibility_records"][0]
    return record


def _channels_of(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    channels: list[dict[str, Any]] = _first_record(artifact)[
        "infrastructure_symmetry_audit"
    ]["channels"]
    return channels


def _forge_like(instance: Any, **overrides: Any) -> Any:
    """Build a schema-invalid twin, bypassing ``__post_init__`` entirely."""

    values = {
        item.name: getattr(instance, item.name) for item in dataclass_fields(instance)
    }
    values.update(overrides)
    forged = object.__new__(type(instance))
    for name, value in values.items():
        object.__setattr__(forged, name, value)
    return forged


def _resealed(manifest: EligibilityManifestV1) -> EligibilityManifestV1:
    """Give a directly constructed adversarial manifest a valid ``self_digest``."""

    return replace(manifest, self_digest=compute_self_digest(manifest.canonical_payload()))


def _resealed_draft(draft: RegistrationDraft) -> RegistrationDraft:
    return replace(draft, self_digest=compute_self_digest(draft.canonical_payload()))


def _iter_keys(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _iter_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_keys(item)


# ===========================================================================
# A. Frozen literals and the top-level schema (§4, §5; E1-E7)
# ===========================================================================


def test_frozen_literals_are_exactly_as_specified() -> None:
    assert ELIGIBILITY_MANIFEST_SCHEMA_VERSION == "EligibilityManifestV1"
    assert REGISTRATION_STATE_ELIGIBILITY_FROZEN == "ELIGIBILITY_FROZEN"
    assert ELIGIBILITY_MANIFEST_FILENAME == "eligibility_manifest.json"
    assert CONFIRMATORY_PROFILE == "post_phaseP_confirmatory_randomization_v1"
    assert PREDICATE_IDS == (
        "POSITION_STATE_ISOLATION",
        "INFRASTRUCTURE_SYMMETRY",
        "TOTAL_OBSERVATION",
        "RUNTIME_CONFIGURATION_FROZEN",
    )
    assert PREDICATE_STATUSES == ("PASS", "FAIL", "UNASSESSED")
    assert DISPOSITIONS == (
        "CONFIRMATORY_ELIGIBLE",
        "DESCRIPTIVE_ONLY_STATE_NOT_ISOLATED",
        "DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY",
        "DESCRIPTIVE_ONLY_OBSERVABILITY_NOT_TOTAL",
        "DESCRIPTIVE_ONLY_RUNTIME_NOT_FROZEN",
        "DESCRIPTIVE_ONLY_UNASSESSED",
    )
    assert CHANNEL_IDS == (
        "PROMPT_SYSTEM_MESSAGE_CONTENT",
        "GATEWAY_PATH_LATENCY_SIGNATURE",
        "EVIDENCE_VOLUME",
        "PROVIDER_MODEL_SELECTION",
    )
    assert CHECK_STATUSES == ("CHECKED", "NOT_CHECKED")
    assert SYMMETRY_RESULTS == (
        "NO_ASYMMETRY_FOUND",
        "ASYMMETRY_FOUND",
        "SYMMETRY_NOT_ASSESSED",
    )
    assert EVIDENCE_KINDS == (
        "REPOSITORY_PATH",
        "DESIGN_ARTIFACT_FIELD",
        "EXTERNAL_ATTESTATION",
    )


def test_manifest_carries_exactly_the_eight_top_level_keys() -> None:
    """E1 — no ninth key, no missing key, and no ``eligibility_state``."""

    artifact = _manifest(_synthetic_draft()).to_artifact()
    assert set(artifact) == {
        "schema_version",
        "registration_state",
        "confirmatory_profile",
        "design_id",
        "created_at",
        "registration_draft_digest",
        "eligibility_records",
        SELF_DIGEST_FIELD,
    }
    assert artifact["schema_version"] == ELIGIBILITY_MANIFEST_SCHEMA_VERSION
    assert artifact["registration_state"] == REGISTRATION_STATE_ELIGIBILITY_FROZEN
    assert artifact["confirmatory_profile"] == CONFIRMATORY_PROFILE
    assert "eligibility_state" not in artifact


def test_manifest_stores_no_same_object_digest_alias() -> None:
    """§4.5 — ``eligibility_manifest_digest`` is a downstream-only reference name."""

    artifact = _manifest(_synthetic_draft()).to_artifact()
    assert "eligibility_manifest_digest" not in set(_iter_keys(artifact))
    digests = [key for key in _iter_keys(artifact) if key.endswith("_digest")]
    assert sorted(set(digests)) == [
        "content_digest",
        "registration_draft_digest",
        "runtime_identity_digest",
        SELF_DIGEST_FIELD,
    ]


def test_manifest_carries_exactly_one_timestamp() -> None:
    """§5 — one manifest-level ``created_at``; no per-stratum/predicate/channel one."""

    manifest = _manifest(_synthetic_draft())
    assert manifest.created_at == SYNTHETIC_CREATED_AT_TEXT
    keys = list(_iter_keys(manifest.to_artifact()))
    assert keys.count("created_at") == 1
    assert "assessed_at" not in keys


@pytest.mark.parametrize(
    ("field_name", "foreign_value"),
    [
        ("schema_version", "EligibilityManifestV2"),
        ("registration_state", "eligibility_frozen"),
        ("registration_state", "FINAL_REGISTRATION_FROZEN"),
        ("confirmatory_profile", "foreign_confirmatory_profile"),
    ],
)
def test_wrong_top_level_literal_is_rejected(
    field_name: str, foreign_value: str, tmp_path: Path
) -> None:
    """E2, E3, E4 — the three literals are exact."""

    draft = _synthetic_draft()
    with pytest.raises(ConfirmatoryEligibilityError, match="must be"):
        _load_mutated(
            _manifest(draft),
            draft,
            tmp_path,
            lambda artifact: artifact.__setitem__(field_name, foreign_value),
        )


@pytest.mark.parametrize("extra_key", ["eligibility_state", "notes", "assessor"])
def test_extra_top_level_key_is_rejected(extra_key: str, tmp_path: Path) -> None:
    """E1 — a ninth key is malformed."""

    draft = _synthetic_draft()
    with pytest.raises(ConfirmatoryEligibilityError, match="unexpected keys"):
        _load_mutated(
            _manifest(draft),
            draft,
            tmp_path,
            lambda artifact: artifact.__setitem__(extra_key, "synthetic"),
        )


@pytest.mark.parametrize(
    "missing_key",
    ["created_at", "design_id", "registration_draft_digest", "eligibility_records"],
)
def test_missing_top_level_key_is_rejected(missing_key: str, tmp_path: Path) -> None:
    """E1 — absence encodes nothing; it is malformed."""

    draft = _synthetic_draft()
    with pytest.raises(ConfirmatoryEligibilityError, match="missing keys"):
        _load_mutated(
            _manifest(draft),
            draft,
            tmp_path,
            lambda artifact: artifact.pop(missing_key),
        )


@pytest.mark.parametrize("retired_key", ["assessed_at", "eligibility_manifest_digest"])
def test_retired_top_level_key_is_rejected(retired_key: str, tmp_path: Path) -> None:
    """E1 — ``assessed_at`` and the same-object digest alias never load.

    Reported by **E1**, not by E21: the eight-key set is exhausted at rule 1, and
    §14 applies the rules in numbered order.  §14.3 says exactly this — E1, E8,
    E11, E14, E15, and E16 already make every forbidden name structurally
    impossible, and E21 restates the prohibition for an auditor rather than
    catching anything a conforming loader would reach.
    """

    draft = _synthetic_draft()
    with pytest.raises(ConfirmatoryEligibilityError, match="unexpected keys"):
        _load_mutated(
            _manifest(draft),
            draft,
            tmp_path,
            lambda artifact: artifact.__setitem__(retired_key, "0" * 64),
        )


@pytest.mark.parametrize(
    "created_at",
    [
        "2026-02-02T03:04:05+00:00",
        "2026-02-02T03:04:05.123Z",
        "2026-02-02T03:04:05",
        "2026-02-02T03:04:05z",
        "2026-02-02",
        "2026-02-30T03:04:05Z",
        "20260202T030405Z",
    ],
)
def test_malformed_created_at_is_rejected(created_at: str, tmp_path: Path) -> None:
    """E6 — one grammar only, never converted and never truncated."""

    draft = _synthetic_draft()
    with pytest.raises(ConfirmatoryEligibilityError, match="created_at"):
        _load_mutated(
            _manifest(draft),
            draft,
            tmp_path,
            lambda artifact: artifact.__setitem__("created_at", created_at),
        )


@pytest.mark.parametrize(
    "instant",
    [
        datetime(2026, 2, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=2))),
        datetime(2026, 2, 2, 3, 4, 5, 500000, tzinfo=UTC),
        datetime(2026, 2, 2, 3, 4, 5),
    ],
)
def test_construction_refuses_a_non_frozen_created_at(instant: datetime) -> None:
    """§5 — a registered, digest-authenticated value is never silently rewritten."""

    draft = _synthetic_draft()
    with pytest.raises(ConfirmatoryEligibilityError, match="created_at"):
        freeze_eligibility(
            registration_draft=draft,
            created_at=instant,
            eligibility_records=_records_for(draft),
        )


@pytest.mark.parametrize(
    "digest", ["A" * 64, "a" * 63, "a" * 65, "g" * 64, "", "0x" + "a" * 62]
)
def test_malformed_registration_draft_digest_is_rejected(
    digest: str, tmp_path: Path
) -> None:
    """E7 — lowercase 64-character hexadecimal, exactly."""

    draft = _synthetic_draft()
    with pytest.raises(ConfirmatoryEligibilityError):
        _load_mutated(
            _manifest(draft),
            draft,
            tmp_path,
            lambda artifact: artifact.__setitem__("registration_draft_digest", digest),
        )


def test_empty_design_id_is_rejected(tmp_path: Path) -> None:
    """E5 — ``design_id`` is a non-empty, path-safe single segment."""

    draft = _synthetic_draft()
    with pytest.raises(ConfirmatoryEligibilityError, match="design_id"):
        _load_mutated(
            _manifest(draft),
            draft,
            tmp_path,
            lambda artifact: artifact.__setitem__("design_id", ""),
        )


def test_forbidden_key_inventory_matches_the_frozen_list() -> None:
    """§14.3 — the exact retired/downstream/execution names E21 prohibits."""

    assert FORBIDDEN_KEY_NAMES == frozenset(
        {
            "assessed_at",
            "eligibility_manifest_digest",
            "isolation_evidence",
            "position_id",
            "baseline_label",
            "qa_mode",
            "task_assignment_bit",
            "bits",
            "b_k",
            "observation_status",
            "failure_class",
            "matrix_digest",
            "final_registration_digest",
            "assignment_digest",
            "randomization_mc_provenance_digest",
            "confirmatory_strata",
            "descriptive_only_strata",
            "descriptive_positions",
        }
    )


@pytest.mark.parametrize(
    "forbidden_key",
    ["position_id", "observation_status", "failure_class", "isolation_evidence", "qa_mode"],
)
def test_forbidden_key_nested_in_a_record_is_rejected(
    forbidden_key: str, tmp_path: Path
) -> None:
    """E8 — a forbidden name inside a record is caught by the six-key rule.

    The prohibition holds at any depth, but it is realized at the *earliest*
    numbered rule that owns the object, which for a stratum record is E8 — not by
    E21, which sits after E20 and would invert the frozen order (§14.3).
    """

    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        _first_record(artifact)[forbidden_key] = "synthetic"

    with pytest.raises(ConfirmatoryEligibilityError, match="unexpected keys"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


@pytest.mark.parametrize(
    "forbidden_key",
    ["confirmatory_strata", "descriptive_only_strata", "matrix_digest", "assignment_digest"],
)
def test_stage_c_derivation_key_is_rejected(forbidden_key: str, tmp_path: Path) -> None:
    """E1/§4.6 — Stage-C partitions and downstream digests are not Stage-B fields."""

    draft = _synthetic_draft()
    with pytest.raises(ConfirmatoryEligibilityError, match="unexpected keys"):
        _load_mutated(
            _manifest(draft),
            draft,
            tmp_path,
            lambda artifact: artifact.__setitem__(forbidden_key, []),
        )


def test_a_forbidden_word_inside_a_locator_value_is_not_a_violation(
    tmp_path: Path,
) -> None:
    """§14.3 — E21 is a key-name rule, never a raw-substring scan over values."""

    draft = _synthetic_draft()
    records = (
        EligibilityStratumRecordV1(
            provider=STRATUM_A[0],
            model=STRATUM_A[1],
            predicates=(
                EligibilityPredicateRecordV1(
                    predicate_id=PREDICATE_IDS[0],
                    status=STATUS_PASS,
                    evidence_refs=(
                        _repository_evidence("docs/position_id-and-matrix_digest.md"),
                    ),
                ),
                *_predicates(DEFAULT_STATUSES)[1:],
            ),
            infrastructure_symmetry_audit=_audit_for(STATUS_UNASSESSED),
            runtime_identity_digest=_runtime_digests(draft)[0],
        ),
    )
    manifest = freeze_eligibility(
        registration_draft=draft,
        created_at=SYNTHETIC_CREATED_AT,
        eligibility_records=records,
    )
    path = _persist(manifest.to_artifact(), tmp_path)
    assert load_eligibility_manifest(path, registration_draft=draft) == manifest


# ===========================================================================
# B. Per-stratum record shape (§6; E8, E9, E18)
# ===========================================================================


def test_stratum_record_carries_exactly_the_six_keys() -> None:
    """E8/§6.1 — six keys, and no nested ``schema_version`` (C2)."""

    record = _first_record(_manifest(_synthetic_draft()).to_artifact())
    assert set(record) == {
        "provider",
        "model",
        "predicates",
        "infrastructure_symmetry_audit",
        "runtime_identity_digest",
        "disposition",
    }
    assert "schema_version" not in record
    assert "stratum_id" not in record


@pytest.mark.parametrize("extra_key", ["stratum_id", "schema_version", "assessed_at"])
def test_extra_record_key_is_rejected(extra_key: str, tmp_path: Path) -> None:
    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        _first_record(artifact)[extra_key] = "synthetic"

    with pytest.raises(ConfirmatoryEligibilityError):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


@pytest.mark.parametrize("missing_key", ["provider", "model", "predicates", "disposition"])
def test_missing_record_key_is_rejected(missing_key: str, tmp_path: Path) -> None:
    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        _first_record(artifact).pop(missing_key)

    with pytest.raises(ConfirmatoryEligibilityError, match="missing keys"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


def test_empty_eligibility_records_is_rejected(tmp_path: Path) -> None:
    """E8 — the array is non-empty."""

    draft = _synthetic_draft()
    with pytest.raises(ConfirmatoryEligibilityError, match="empty"):
        _load_mutated(
            _manifest(draft),
            draft,
            tmp_path,
            lambda artifact: artifact.__setitem__("eligibility_records", []),
        )


def test_records_must_arrive_sorted_by_provider_then_model(tmp_path: Path) -> None:
    """E9 — sorted ascending by ``(provider, model)``; never re-sorted."""

    draft = _synthetic_draft(STRATUM_A, STRATUM_B)
    manifest = _manifest(draft)

    def mutate(artifact: dict[str, Any]) -> None:
        artifact["eligibility_records"] = list(
            reversed(artifact["eligibility_records"])
        )

    with pytest.raises(ConfirmatoryEligibilityError, match="sorted ascending"):
        _load_mutated(manifest, draft, tmp_path, mutate)


def test_duplicate_stratum_record_is_rejected(tmp_path: Path) -> None:
    """E9 — unique on ``(provider, model)``."""

    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        artifact["eligibility_records"] = [
            _first_record(artifact),
            json.loads(json.dumps(_first_record(artifact))),
        ]

    with pytest.raises(ConfirmatoryEligibilityError, match="duplicate"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


@pytest.mark.parametrize("field_name", ["provider", "model"])
def test_empty_provider_or_model_is_rejected(field_name: str, tmp_path: Path) -> None:
    """E9 — both stratum identifiers are non-empty strings."""

    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        _first_record(artifact)[field_name] = ""

    with pytest.raises(ConfirmatoryEligibilityError, match="non-empty"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


@pytest.mark.parametrize("digest", ["A" * 64, "a" * 63, "not-a-digest", ""])
def test_malformed_runtime_identity_digest_is_rejected(
    digest: str, tmp_path: Path
) -> None:
    """E18 — lowercase 64-character hexadecimal."""

    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        _first_record(artifact)["runtime_identity_digest"] = digest

    with pytest.raises(ConfirmatoryEligibilityError):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


# ===========================================================================
# C. Predicate records (§7; E10, E11)
# ===========================================================================


def test_predicates_are_the_four_frozen_ids_in_the_frozen_order() -> None:
    """E10 — a positional semantic array, in design decision §9's order."""

    record = _first_record(_manifest(_synthetic_draft()).to_artifact())
    assert [item["predicate_id"] for item in record["predicates"]] == list(PREDICATE_IDS)
    for predicate in record["predicates"]:
        assert set(predicate) == {"predicate_id", "status", "evidence_refs"}


def test_reordered_predicates_are_rejected(tmp_path: Path) -> None:
    """E10 — alphabetical or any other order is refused, never re-sorted."""

    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        predicates = _first_record(artifact)["predicates"]
        predicates[0], predicates[1] = predicates[1], predicates[0]

    with pytest.raises(ConfirmatoryEligibilityError, match="predicate_id must be"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


def test_missing_predicate_is_rejected(tmp_path: Path) -> None:
    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        del _first_record(artifact)["predicates"][3]

    with pytest.raises(ConfirmatoryEligibilityError, match="exactly 4 records"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


def test_duplicate_predicate_is_rejected(tmp_path: Path) -> None:
    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        predicates = _first_record(artifact)["predicates"]
        predicates[3] = json.loads(json.dumps(predicates[0]))

    with pytest.raises(ConfirmatoryEligibilityError, match="predicate_id must be"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


def test_unknown_predicate_id_is_rejected(tmp_path: Path) -> None:
    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        _first_record(artifact)["predicates"][2]["predicate_id"] = "TOTAL_DETERMINISM"

    with pytest.raises(ConfirmatoryEligibilityError, match="predicate_id must be"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


@pytest.mark.parametrize("status", ["pass", "SKIPPED", "NOT_APPLICABLE", "PENDING", None])
def test_illegal_predicate_status_is_rejected(status: Any, tmp_path: Path) -> None:
    """E11 — exactly three tokens; ``null`` is not an encoding of ``UNASSESSED``."""

    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        _first_record(artifact)["predicates"][2]["status"] = status

    with pytest.raises(ConfirmatoryEligibilityError, match="status must be one of"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


def test_missing_predicate_status_key_is_rejected(tmp_path: Path) -> None:
    """E11 — absence of the field is malformed, not an encoding of anything."""

    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        del _first_record(artifact)["predicates"][2]["status"]

    with pytest.raises(ConfirmatoryEligibilityError, match="missing keys"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


@pytest.mark.parametrize("extra_key", ["checked_at", "schema_version", "assessed_at"])
def test_extra_predicate_key_is_rejected(extra_key: str, tmp_path: Path) -> None:
    """E11 — exactly three predicate keys, retired names included."""

    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        _first_record(artifact)["predicates"][2][extra_key] = SYNTHETIC_CREATED_AT_TEXT

    with pytest.raises(ConfirmatoryEligibilityError, match="unexpected keys"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


@pytest.mark.parametrize("field_name", ["eligibility_records", "predicates"])
def test_a_frozen_array_field_written_as_an_object_is_rejected(
    field_name: str, tmp_path: Path
) -> None:
    """E8/E10 — both are JSON arrays; neither is coerced from another shape."""

    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        if field_name == "eligibility_records":
            artifact[field_name] = {"0": _first_record(artifact)}
        else:
            _first_record(artifact)[field_name] = {}

    with pytest.raises(ConfirmatoryEligibilityError, match="must be a JSON array"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


# ===========================================================================
# D. All 81 status combinations and the disposition derivation (§7.4, §8; E12, E19)
# ===========================================================================

ALL_COMBINATIONS: tuple[tuple[str, ...], ...] = tuple(
    itertools.product(PREDICATE_STATUSES, repeat=4)
)


def _expected_disposition(statuses: tuple[str, ...]) -> str:
    """The §8.2 rule, restated independently of the implementation."""

    failures = [index for index, status in enumerate(statuses) if status == STATUS_FAIL]
    if failures:
        return DISPOSITIONS[1 + min(failures)]
    if STATUS_UNASSESSED in statuses:
        return "DESCRIPTIVE_ONLY_UNASSESSED"
    return "CONFIRMATORY_ELIGIBLE"


def test_total_disposition_over_four_predicates() -> None:
    """§8.2 — total and single-valued over all 81 combinations, with §8.2's partition."""

    assert len(ALL_COMBINATIONS) == 81
    derived = {statuses: derive_disposition(statuses) for statuses in ALL_COMBINATIONS}
    assert all(value in DISPOSITIONS for value in derived.values())
    assert all(
        derived[statuses] == _expected_disposition(statuses)
        for statuses in ALL_COMBINATIONS
    )
    counts = {token: sum(1 for value in derived.values() if value == token) for token in DISPOSITIONS}
    assert counts == {
        "CONFIRMATORY_ELIGIBLE": 1,
        "DESCRIPTIVE_ONLY_STATE_NOT_ISOLATED": 27,
        "DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY": 18,
        "DESCRIPTIVE_ONLY_OBSERVABILITY_NOT_TOTAL": 12,
        "DESCRIPTIVE_ONLY_RUNTIME_NOT_FROZEN": 8,
        "DESCRIPTIVE_ONLY_UNASSESSED": 15,
    }
    assert sum(counts.values()) == 81


@pytest.mark.parametrize("statuses", ALL_COMBINATIONS)
def test_every_status_combination_is_accepted_at_the_status_layer(
    statuses: tuple[str, ...],
) -> None:
    """E12 — a status combination is never itself a rejection ground (§7.4)."""

    draft = _synthetic_draft()
    record = _record(STRATUM_A, _runtime_digests(draft)[0], statuses)
    assert tuple(item.status for item in record.predicates) == statuses
    assert record.disposition == _expected_disposition(statuses)


@pytest.mark.parametrize("statuses", ALL_COMBINATIONS)
def test_every_status_combination_round_trips_through_a_persisted_manifest(
    statuses: tuple[str, ...], tmp_path: Path
) -> None:
    """E12 — the loader admits all 81 and never narrows what may be recorded."""

    draft = _synthetic_draft()
    manifest = _manifest(draft, statuses)
    loaded = load_eligibility_manifest(
        _persist(manifest.to_artifact(), tmp_path), registration_draft=draft
    )
    assert loaded == manifest
    assert loaded.eligibility_records[0].disposition == _expected_disposition(statuses)


def test_confirmatory_eligible_requires_all_four_pass() -> None:
    """§8.2 step 3 — the conjunction, unreachable from any FAIL or UNASSESSED."""

    draft = _synthetic_draft()
    digest = _runtime_digests(draft)[0]
    assert _record(STRATUM_A, digest, ALL_PASS).disposition == "CONFIRMATORY_ELIGIBLE"
    for index in range(4):
        for weaker in (STATUS_FAIL, STATUS_UNASSESSED):
            statuses = list(ALL_PASS)
            statuses[index] = weaker
            record = _record(STRATUM_A, digest, tuple(statuses))
            assert record.disposition != "CONFIRMATORY_ELIGIBLE"


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        (
            (STATUS_PASS, STATUS_FAIL, STATUS_FAIL, STATUS_PASS),
            "DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY",
        ),
        (
            (STATUS_FAIL, STATUS_FAIL, STATUS_FAIL, STATUS_FAIL),
            "DESCRIPTIVE_ONLY_STATE_NOT_ISOLATED",
        ),
        (
            (STATUS_PASS, STATUS_FAIL, STATUS_PASS, STATUS_UNASSESSED),
            "DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY",
        ),
        (
            (STATUS_PASS, STATUS_PASS, STATUS_FAIL, STATUS_FAIL),
            "DESCRIPTIVE_ONLY_OBSERVABILITY_NOT_TOTAL",
        ),
        (
            (STATUS_PASS, STATUS_PASS, STATUS_PASS, STATUS_FAIL),
            "DESCRIPTIVE_ONLY_RUNTIME_NOT_FROZEN",
        ),
    ],
)
def test_first_failing_predicate_is_reported_reason(
    statuses: tuple[str, ...], expected: str
) -> None:
    """§8.2 step 1 — the earliest FAIL supplies the one reason; the rest are retained."""

    draft = _synthetic_draft()
    record = _record(STRATUM_A, _runtime_digests(draft)[0], statuses)
    assert record.disposition == expected
    assert tuple(item.status for item in record.predicates) == statuses


def test_default_disposition_is_unassessed() -> None:
    """§8.2 step 2 — the frozen default state of every provider/runtime today."""

    draft = _synthetic_draft()
    record = _record(STRATUM_A, _runtime_digests(draft)[0], ALL_UNASSESSED)
    assert record.disposition == "DESCRIPTIVE_ONLY_UNASSESSED"


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        (
            (STATUS_UNASSESSED, STATUS_FAIL, STATUS_UNASSESSED, STATUS_UNASSESSED),
            "DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY",
        ),
        (
            (STATUS_UNASSESSED, STATUS_UNASSESSED, STATUS_UNASSESSED, STATUS_FAIL),
            "DESCRIPTIVE_ONLY_RUNTIME_NOT_FROZEN",
        ),
    ],
)
def test_unassessed_before_a_later_fail_does_not_hide_the_fail(
    statuses: tuple[str, ...], expected: str
) -> None:
    """§8.2 — FAIL outranks UNASSESSED at every position; nothing is buried."""

    draft = _synthetic_draft()
    assert _record(STRATUM_A, _runtime_digests(draft)[0], statuses).disposition == expected


@pytest.mark.parametrize(
    "statuses",
    [
        (STATUS_UNASSESSED, STATUS_PASS, STATUS_PASS, STATUS_PASS),
        (STATUS_PASS, STATUS_UNASSESSED, STATUS_PASS, STATUS_PASS),
        (STATUS_PASS, STATUS_PASS, STATUS_PASS, STATUS_UNASSESSED),
    ],
)
def test_no_fail_with_any_unassessed_is_descriptive_only_unassessed(
    statuses: tuple[str, ...],
) -> None:
    """§8.2 step 2, and a PASS may follow an UNASSESSED (§7.4)."""

    draft = _synthetic_draft()
    record = _record(STRATUM_A, _runtime_digests(draft)[0], statuses)
    assert record.disposition == "DESCRIPTIVE_ONLY_UNASSESSED"


@pytest.mark.parametrize(
    "disposition", ["descriptive_only_unassessed", "DESCRIPTIVE_ONLY_INELIGIBLE", "", None]
)
def test_illegal_stored_disposition_is_rejected(
    disposition: Any, tmp_path: Path
) -> None:
    """E19 — exactly the six frozen tokens."""

    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        _first_record(artifact)["disposition"] = disposition

    with pytest.raises(ConfirmatoryEligibilityError, match="disposition must be one of"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


def test_no_confirmatory_randomization_disposition_is_rejected(tmp_path: Path) -> None:
    """E19/§8.1 — an assignment-layer token is not an eligibility disposition."""

    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        _first_record(artifact)["disposition"] = (
            "DESCRIPTIVE_ONLY_NO_CONFIRMATORY_RANDOMIZATION"
        )

    with pytest.raises(
        ConfirmatoryEligibilityError, match="assignment/randomization-layer token"
    ):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


def test_stored_disposition_mismatching_its_predicates_is_rejected(
    tmp_path: Path,
) -> None:
    """E19/§8.3 — a recorded derivation is cross-checked, never trusted."""

    draft = _synthetic_draft()
    manifest = _manifest(draft, ALL_PASS)
    assert manifest.eligibility_records[0].disposition == "CONFIRMATORY_ELIGIBLE"

    def mutate(artifact: dict[str, Any]) -> None:
        _first_record(artifact)["disposition"] = "DESCRIPTIVE_ONLY_UNASSESSED"

    with pytest.raises(ConfirmatoryEligibilityError, match="derive"):
        _load_mutated(manifest, draft, tmp_path, mutate)


def test_multi_fail_record_is_not_rejected_for_its_status_combination(
    tmp_path: Path,
) -> None:
    """E12, stated as the frozen contract states it: this must NOT be refused."""

    draft = _synthetic_draft()
    statuses = (STATUS_PASS, STATUS_FAIL, STATUS_FAIL, STATUS_PASS)
    manifest = _manifest(draft, statuses)
    loaded = load_eligibility_manifest(
        _persist(manifest.to_artifact(), tmp_path), registration_draft=draft
    )
    record = loaded.eligibility_records[0]
    assert tuple(item.status for item in record.predicates) == statuses
    assert record.disposition == "DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY"


# ===========================================================================
# E. Infrastructure symmetry audit (§10; E15, E16, E17)
# ===========================================================================


def test_audit_is_a_one_key_record_over_four_positional_channels() -> None:
    """E15/§10.1, §10.2 — an object, not a bare array, and no ``schema_version``."""

    audit = _first_record(_manifest(_synthetic_draft()).to_artifact())[
        "infrastructure_symmetry_audit"
    ]
    assert set(audit) == {"channels"}
    assert [channel["channel_id"] for channel in audit["channels"]] == list(CHANNEL_IDS)
    for channel in audit["channels"]:
        assert set(channel) == {
            "channel_id",
            "check_status",
            "symmetry_result",
            "evidence_refs",
        }


def test_all_checked_with_no_asymmetry_derives_pass() -> None:
    audit = InfrastructureSymmetryAuditV1(
        channels=tuple(_channel(index, checked=True) for index in range(4))
    )
    assert derive_infrastructure_symmetry_status(audit) == STATUS_PASS


@pytest.mark.parametrize("asymmetric_index", [0, 1, 2, 3])
def test_any_asymmetry_found_derives_fail(asymmetric_index: int) -> None:
    audit = InfrastructureSymmetryAuditV1(
        channels=tuple(
            _channel(index, checked=True, asymmetry=index == asymmetric_index)
            for index in range(4)
        )
    )
    assert derive_infrastructure_symmetry_status(audit) == STATUS_FAIL


@pytest.mark.parametrize("checked_count", [0, 1, 2, 3])
def test_partial_checks_with_no_asymmetry_derive_unassessed(checked_count: int) -> None:
    """§10.4/§5.F — PASS requires **every** channel checked; partial is UNASSESSED."""

    audit = InfrastructureSymmetryAuditV1(
        channels=tuple(
            _channel(index, checked=index < checked_count) for index in range(4)
        )
    )
    assert derive_infrastructure_symmetry_status(audit) == STATUS_UNASSESSED


def test_asymmetry_found_does_not_require_the_other_channels_to_be_checked() -> None:
    """§10.4 — the FAIL branch is unconditional on the remaining channels."""

    audit = InfrastructureSymmetryAuditV1(
        channels=(
            _channel(0, checked=True, asymmetry=True),
            *(_channel(index, checked=False) for index in range(1, 4)),
        )
    )
    assert derive_infrastructure_symmetry_status(audit) == STATUS_FAIL


def test_checked_channel_with_symmetry_not_assessed_is_rejected() -> None:
    """E16 — a checked channel without a symmetry result."""

    with pytest.raises(ConfirmatoryEligibilityError, match="is CHECKED and must carry"):
        _channel(0, checked=True, symmetry_result="SYMMETRY_NOT_ASSESSED")


@pytest.mark.parametrize("result", ["NO_ASYMMETRY_FOUND", "ASYMMETRY_FOUND"])
def test_not_checked_channel_claiming_a_result_is_rejected(result: str) -> None:
    """E16 — a not-checked channel contradicting its own status."""

    with pytest.raises(
        ConfirmatoryEligibilityError, match="is NOT_CHECKED and must carry"
    ):
        _channel(0, checked=False, symmetry_result=result)


def test_checked_channel_with_no_evidence_is_rejected() -> None:
    """E16/§9.3 — a CHECKED channel carries at least one reference."""

    with pytest.raises(ConfirmatoryEligibilityError, match="at least one reference"):
        _channel(0, checked=True, evidence=())


def test_not_checked_channel_carrying_evidence_is_rejected() -> None:
    """E16/§9.3 — a NOT_CHECKED channel carries exactly []."""

    with pytest.raises(ConfirmatoryEligibilityError, match=r"must be exactly \[\]"):
        _channel(0, checked=False, evidence=(_repository_evidence(),))


@pytest.mark.parametrize("check_status", ["checked", "SKIPPED", None])
def test_illegal_check_status_is_rejected(check_status: Any, tmp_path: Path) -> None:
    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        _channels_of(artifact)[0]["check_status"] = check_status

    with pytest.raises(ConfirmatoryEligibilityError, match="check_status must be one of"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


def test_missing_channel_is_rejected(tmp_path: Path) -> None:
    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        del _channels_of(artifact)[3]

    with pytest.raises(ConfirmatoryEligibilityError, match="exactly 4 records"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


def test_duplicate_channel_is_rejected(tmp_path: Path) -> None:
    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        channels = _channels_of(artifact)
        channels[3] = json.loads(json.dumps(channels[0]))

    with pytest.raises(ConfirmatoryEligibilityError, match="channel_id must be"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


def test_reordered_channels_are_rejected(tmp_path: Path) -> None:
    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        channels = _channels_of(artifact)
        channels[0], channels[2] = channels[2], channels[0]

    with pytest.raises(ConfirmatoryEligibilityError, match="channel_id must be"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


def test_fifth_channel_is_rejected(tmp_path: Path) -> None:
    """E15 — §5.F froze the candidate set at exactly four."""

    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        channels = _channels_of(artifact)
        extra = json.loads(json.dumps(channels[0]))
        extra["channel_id"] = "TOKENIZER_VERSION"
        channels.append(extra)

    with pytest.raises(ConfirmatoryEligibilityError, match="exactly 4 records"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


def test_unknown_channel_id_is_rejected(tmp_path: Path) -> None:
    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        _channels_of(artifact)[2]["channel_id"] = "TOKENIZER_VERSION"

    with pytest.raises(ConfirmatoryEligibilityError, match="channel_id must be"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


def test_audit_written_as_a_bare_array_is_rejected(tmp_path: Path) -> None:
    """E15/§10.1 — it is an object with exactly the key ``channels``."""

    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        record = _first_record(artifact)
        record["infrastructure_symmetry_audit"] = record[
            "infrastructure_symmetry_audit"
        ]["channels"]

    with pytest.raises(ConfirmatoryEligibilityError, match="must be a JSON object"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


def test_audit_extra_key_is_rejected(tmp_path: Path) -> None:
    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        _first_record(artifact)["infrastructure_symmetry_audit"]["schema_version"] = (
            "InfrastructureSymmetryAuditV1"
        )

    with pytest.raises(ConfirmatoryEligibilityError, match="unexpected keys"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


def test_channel_extra_key_is_rejected(tmp_path: Path) -> None:
    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        _channels_of(artifact)[0]["notes"] = "synthetic"

    with pytest.raises(ConfirmatoryEligibilityError, match="unexpected keys"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


@pytest.mark.parametrize(
    ("recorded", "audit_status"),
    [
        (STATUS_PASS, STATUS_UNASSESSED),
        (STATUS_UNASSESSED, STATUS_PASS),
        (STATUS_PASS, STATUS_FAIL),
        (STATUS_FAIL, STATUS_UNASSESSED),
    ],
)
def test_symmetry_status_mismatching_its_channels_is_rejected(
    recorded: str, audit_status: str
) -> None:
    """E17 — the recorded predicate status is recomputed from the channels."""

    draft = _synthetic_draft()
    statuses = (STATUS_PASS, recorded, STATUS_UNASSESSED, STATUS_UNASSESSED)
    with pytest.raises(ConfirmatoryEligibilityError, match="channels derive"):
        EligibilityStratumRecordV1(
            provider=STRATUM_A[0],
            model=STRATUM_A[1],
            predicates=_predicates(statuses),
            infrastructure_symmetry_audit=_audit_for(audit_status),
            runtime_identity_digest=_runtime_digests(draft)[0],
        )


def test_three_checked_channels_cannot_record_a_passing_symmetry_predicate(
    tmp_path: Path,
) -> None:
    """E17/§19 case 38 — this stratum can never be CONFIRMATORY_ELIGIBLE."""

    draft = _synthetic_draft()
    manifest = _manifest(draft, ALL_PASS)

    def mutate(artifact: dict[str, Any]) -> None:
        channel = _channels_of(artifact)[3]
        channel["check_status"] = "NOT_CHECKED"
        channel["symmetry_result"] = "SYMMETRY_NOT_ASSESSED"
        channel["evidence_refs"] = []

    with pytest.raises(ConfirmatoryEligibilityError, match="channels derive"):
        _load_mutated(manifest, draft, tmp_path, mutate)


# ===========================================================================
# F. Evidence references (§9; E13, E14)
# ===========================================================================


def test_all_three_evidence_kinds_are_accepted_in_sorted_order(tmp_path: Path) -> None:
    """§9.1-§9.3 — one sorted, unique array over the three closed kinds."""

    draft = _synthetic_draft()
    refs = (
        _draft_field_evidence(draft.self_digest),
        _attestation_evidence(),
        _repository_evidence(),
    )
    assert [ref.sort_key for ref in refs] == sorted(ref.sort_key for ref in refs)
    record = EligibilityStratumRecordV1(
        provider=STRATUM_A[0],
        model=STRATUM_A[1],
        predicates=(
            EligibilityPredicateRecordV1(
                predicate_id=PREDICATE_IDS[0], status=STATUS_PASS, evidence_refs=refs
            ),
            *_predicates(DEFAULT_STATUSES)[1:],
        ),
        infrastructure_symmetry_audit=_audit_for(STATUS_UNASSESSED),
        runtime_identity_digest=_runtime_digests(draft)[0],
    )
    manifest = freeze_eligibility(
        registration_draft=draft,
        created_at=SYNTHETIC_CREATED_AT,
        eligibility_records=(record,),
    )
    loaded = load_eligibility_manifest(
        _persist(manifest.to_artifact(), tmp_path), registration_draft=draft
    )
    assert loaded.eligibility_records[0].predicates[0].evidence_refs == refs


@pytest.mark.parametrize(
    "locator",
    [
        "/etc/passwd",
        "../secrets/x",
        "./docs/review.md",
        "docs/../secrets/x",
        "docs//review.md",
        "docs\\review.md",
        "docs/review.md/",
        ".",
        "..",
        "C:/docs/review.md",
    ],
)
def test_invalid_repository_path_locator_is_rejected(locator: str) -> None:
    """§9.2 — repository-relative POSIX path only; no navigation, no absolute form."""

    with pytest.raises(ConfirmatoryEligibilityError, match="REPOSITORY_PATH locator"):
        _repository_evidence(locator)


@pytest.mark.parametrize(
    "locator",
    [
        "docs/review.md",
        "src/iqa_soa/experiment/confirmatory_eligibility.py",
        "NOTES.md",
        "docs/sub-dir_1/probe.2026.txt",
    ],
)
def test_valid_repository_path_locator_is_accepted(locator: str) -> None:
    assert _repository_evidence(locator).locator == locator


def test_valid_design_artifact_field_evidence_is_accepted() -> None:
    draft = _synthetic_draft()
    ref = _draft_field_evidence(
        draft.self_digest, "registration_draft.json#/proposed_strata/0/provider"
    )
    assert ref.content_digest == draft.self_digest


@pytest.mark.parametrize(
    "locator",
    [
        "registration_manifest.json#/confirmatory_strata",
        "assignment_manifest.json#/bits",
        "eligibility_manifest.json#/eligibility_records",
        "registration_draft.json#",
        "registration_draft.json",
        "registration_draft.json#proposed_strata",
    ],
)
def test_invalid_design_artifact_field_locator_is_rejected(locator: str) -> None:
    """§9.2 — only ``registration_draft.json`` exists at Stage B, and it needs a pointer."""

    with pytest.raises(
        ConfirmatoryEligibilityError, match="DESIGN_ARTIFACT_FIELD locator"
    ):
        EvidenceReferenceV1(
            evidence_kind="DESIGN_ARTIFACT_FIELD",
            locator=locator,
            content_digest=REPOSITORY_DIGEST,
        )


def test_design_artifact_field_digest_must_equal_the_bound_draft_digest() -> None:
    """E14 — the referenced artifact's ``self_digest`` is the draft digest."""

    draft = _synthetic_draft()
    record = EligibilityStratumRecordV1(
        provider=STRATUM_A[0],
        model=STRATUM_A[1],
        predicates=(
            EligibilityPredicateRecordV1(
                predicate_id=PREDICATE_IDS[0],
                status=STATUS_PASS,
                evidence_refs=(_draft_field_evidence(FOREIGN_DIGEST),),
            ),
            *_predicates(DEFAULT_STATUSES)[1:],
        ),
        infrastructure_symmetry_audit=_audit_for(STATUS_UNASSESSED),
        runtime_identity_digest=_runtime_digests(draft)[0],
    )
    with pytest.raises(
        ConfirmatoryEligibilityError, match="must equal the manifest's"
    ):
        freeze_eligibility(
            registration_draft=draft,
            created_at=SYNTHETIC_CREATED_AT,
            eligibility_records=(record,),
        )


@pytest.mark.parametrize(
    "locator",
    ["https://provider.invalid/statement", "https://a.b/c?d=e#f"],
)
def test_valid_https_external_attestation_is_accepted(locator: str) -> None:
    assert _attestation_evidence(locator).locator == locator


@pytest.mark.parametrize(
    "locator",
    [
        "http://provider.invalid/statement",
        "ftp://provider.invalid/statement",
        "provider.invalid/statement",
        "https://provider.invalid/a b",
    ],
)
def test_invalid_external_attestation_locator_is_rejected(locator: str) -> None:
    with pytest.raises(
        ConfirmatoryEligibilityError, match="EXTERNAL_ATTESTATION locator"
    ):
        _attestation_evidence(locator)


@pytest.mark.parametrize("digest", ["A" * 64, "a" * 63, "z" * 64, ""])
def test_malformed_evidence_content_digest_is_rejected(digest: str) -> None:
    with pytest.raises(ConfirmatoryEligibilityError):
        _repository_evidence(digest=digest)


def test_unknown_evidence_kind_is_rejected() -> None:
    with pytest.raises(ConfirmatoryEligibilityError, match="evidence_kind"):
        EvidenceReferenceV1(
            evidence_kind="SCREENSHOT",
            locator="docs/review.md",
            content_digest=REPOSITORY_DIGEST,
        )


def test_bare_string_evidence_is_rejected(tmp_path: Path) -> None:
    """E14/§9.1 — evidence references are structured records, never bare strings."""

    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        _first_record(artifact)["predicates"][0]["evidence_refs"] = ["docs/review.md"]

    with pytest.raises(ConfirmatoryEligibilityError, match="must be a JSON object"):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


@pytest.mark.parametrize("extra_key", ["note", "summary", "author", "assessed_at"])
def test_extra_evidence_key_is_rejected(extra_key: str, tmp_path: Path) -> None:
    draft = _synthetic_draft()

    def mutate(artifact: dict[str, Any]) -> None:
        _first_record(artifact)["predicates"][0]["evidence_refs"][0][extra_key] = "x"

    with pytest.raises(ConfirmatoryEligibilityError):
        _load_mutated(_manifest(draft), draft, tmp_path, mutate)


def test_unsorted_evidence_array_is_rejected() -> None:
    """§9.3 — refused, never re-sorted on the caller's behalf."""

    refs = (_repository_evidence("docs/b.md"), _repository_evidence("docs/a.md"))
    with pytest.raises(ConfirmatoryEligibilityError, match="sorted ascending"):
        EligibilityPredicateRecordV1(
            predicate_id=PREDICATE_IDS[0], status=STATUS_PASS, evidence_refs=refs
        )


def test_duplicate_evidence_reference_is_rejected() -> None:
    """§9.3 — refused, never deduplicated on the caller's behalf."""

    refs = (_repository_evidence("docs/a.md"), _repository_evidence("docs/a.md"))
    with pytest.raises(ConfirmatoryEligibilityError, match="duplicate"):
        EligibilityPredicateRecordV1(
            predicate_id=PREDICATE_IDS[0], status=STATUS_PASS, evidence_refs=refs
        )


@pytest.mark.parametrize("predicate_index", [0, 2, 3])
@pytest.mark.parametrize("status", [STATUS_PASS, STATUS_FAIL])
def test_recorded_result_with_no_evidence_is_rejected(
    predicate_index: int, status: str
) -> None:
    """E13 — an unsupported assertion (§9.3)."""

    with pytest.raises(ConfirmatoryEligibilityError, match="at least one reference"):
        EligibilityPredicateRecordV1(
            predicate_id=PREDICATE_IDS[predicate_index], status=status, evidence_refs=()
        )


@pytest.mark.parametrize("predicate_index", [0, 2, 3])
def test_unassessed_predicate_carrying_evidence_is_rejected(predicate_index: int) -> None:
    """E13 — evidence contradicts its own status (§9.3)."""

    with pytest.raises(ConfirmatoryEligibilityError, match=r"must be exactly \[\]"):
        EligibilityPredicateRecordV1(
            predicate_id=PREDICATE_IDS[predicate_index],
            status=STATUS_UNASSESSED,
            evidence_refs=(_repository_evidence(),),
        )


@pytest.mark.parametrize("status", list(PREDICATE_STATUSES))
def test_symmetry_predicate_evidence_is_always_empty(status: str) -> None:
    """E13/§9.5 — its evidence lives exclusively on the audit channels."""

    assert (
        EligibilityPredicateRecordV1(
            predicate_id="INFRASTRUCTURE_SYMMETRY", status=status
        ).evidence_refs
        == ()
    )
    with pytest.raises(
        ConfirmatoryEligibilityError, match="lives exclusively on"
    ):
        EligibilityPredicateRecordV1(
            predicate_id="INFRASTRUCTURE_SYMMETRY",
            status=status,
            evidence_refs=(_repository_evidence(),),
        )


def test_writer_and_loader_never_dereference_a_repository_path(
    tmp_path: Path,
) -> None:
    """§9.2 — validation is structural and offline; no evidence file is ever opened."""

    draft = _written_draft(tmp_path)
    locator = "docs/this-file-does-not-exist-anywhere.md"
    assert not (Path.cwd() / locator).exists()
    record = EligibilityStratumRecordV1(
        provider=STRATUM_A[0],
        model=STRATUM_A[1],
        predicates=(
            EligibilityPredicateRecordV1(
                predicate_id=PREDICATE_IDS[0],
                status=STATUS_PASS,
                evidence_refs=(_repository_evidence(locator, FOREIGN_DIGEST),),
            ),
            *_predicates(DEFAULT_STATUSES)[1:],
        ),
        infrastructure_symmetry_audit=_audit_for(STATUS_UNASSESSED),
        runtime_identity_digest=_runtime_digests(draft)[0],
    )
    manifest = freeze_eligibility(
        registration_draft=draft,
        created_at=SYNTHETIC_CREATED_AT,
        eligibility_records=(record,),
    )
    path = write_eligibility_manifest(manifest, confirmatory_root=tmp_path)
    loaded = load_eligibility_manifest(path, registration_draft=draft)
    assert loaded.eligibility_records[0].predicates[0].evidence_refs[0].locator == locator


def test_loader_never_dereferences_an_unreachable_https_attestation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§9.2/§19 case 31 — a rotted URL is not a failure at any time."""

    import socket

    def _forbid(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Stage-B validation must never open a network connection")

    monkeypatch.setattr(socket, "socket", _forbid)
    monkeypatch.setattr(socket, "create_connection", _forbid)

    draft = _synthetic_draft()
    locator = "https://unreachable.invalid/attestation-that-404s"
    record = EligibilityStratumRecordV1(
        provider=STRATUM_A[0],
        model=STRATUM_A[1],
        predicates=(
            EligibilityPredicateRecordV1(
                predicate_id=PREDICATE_IDS[0],
                status=STATUS_PASS,
                evidence_refs=(_attestation_evidence(locator),),
            ),
            *_predicates(DEFAULT_STATUSES)[1:],
        ),
        infrastructure_symmetry_audit=_audit_for(STATUS_UNASSESSED),
        runtime_identity_digest=_runtime_digests(draft)[0],
    )
    manifest = freeze_eligibility(
        registration_draft=draft,
        created_at=SYNTHETIC_CREATED_AT,
        eligibility_records=(record,),
    )
    loaded = load_eligibility_manifest(
        _persist(manifest.to_artifact(), tmp_path), registration_draft=draft
    )
    assert loaded == manifest


# ===========================================================================
# G. Binding to the registration draft (§13, §14.2; E22-E26)
# ===========================================================================


def test_registration_draft_digest_binds_the_draft_self_digest() -> None:
    draft = _synthetic_draft()
    manifest = _manifest(draft)
    assert manifest.registration_draft_digest == draft.self_digest
    assert manifest.design_id == draft.design_id
    assert manifest.confirmatory_profile == draft.confirmatory_profile


def test_registration_draft_digest_mismatch_is_rejected(tmp_path: Path) -> None:
    """E22 — the manifest names a different draft than the one supplied."""

    draft = _synthetic_draft()
    with pytest.raises(ConfirmatoryEligibilityError, match="does not match the bound"):
        _load_mutated(
            _manifest(draft),
            draft,
            tmp_path,
            lambda artifact: artifact.__setitem__(
                "registration_draft_digest", FOREIGN_DIGEST
            ),
        )


def test_design_id_mismatch_with_the_draft_is_rejected(tmp_path: Path) -> None:
    """E23 — byte-for-byte agreement with the draft's ``design_id``."""

    draft = _synthetic_draft()
    with pytest.raises(ConfirmatoryEligibilityError, match="design_id"):
        _load_mutated(
            _manifest(draft),
            draft,
            tmp_path,
            lambda artifact: artifact.__setitem__("design_id", "other-design-000"),
        )


def test_profile_mismatch_with_the_draft_is_rejected() -> None:
    """E23 — the manifest's stamped profile must equal the bound draft's."""

    foreign = _resealed_draft(
        _forge_like(_synthetic_draft(), confirmatory_profile="foreign_profile_v1")
    )
    with pytest.raises(ConfirmatoryEligibilityError, match="confirmatory_profile"):
        freeze_eligibility(
            registration_draft=foreign,
            created_at=SYNTHETIC_CREATED_AT,
            eligibility_records=_records_for(foreign),
        )


def test_missing_stratum_record_is_rejected(tmp_path: Path) -> None:
    """E24 — implementation design §6's refusal, made structural."""

    draft = _synthetic_draft(STRATUM_A, STRATUM_B)
    manifest = _manifest(draft)

    def mutate(artifact: dict[str, Any]) -> None:
        del artifact["eligibility_records"][1]

    with pytest.raises(ConfirmatoryEligibilityError, match="exactly once"):
        _load_mutated(manifest, draft, tmp_path, mutate)


def test_extra_stratum_record_is_rejected(tmp_path: Path) -> None:
    """E24 — no extra record beyond the proposed strata."""

    draft = _synthetic_draft()
    manifest = _manifest(draft)

    def mutate(artifact: dict[str, Any]) -> None:
        extra = json.loads(json.dumps(_first_record(artifact)))
        extra["provider"] = STRATUM_B[0]
        extra["model"] = STRATUM_B[1]
        artifact["eligibility_records"].append(extra)

    with pytest.raises(ConfirmatoryEligibilityError, match="exactly once"):
        _load_mutated(manifest, draft, tmp_path, mutate)


def test_foreign_stratum_record_is_rejected(tmp_path: Path) -> None:
    """E24 — a record for a ``(provider, model)`` not in ``proposed_strata``."""

    draft = _synthetic_draft()
    manifest = _manifest(draft)

    def mutate(artifact: dict[str, Any]) -> None:
        record = _first_record(artifact)
        record["provider"] = "synthetic-provider-z"
        record["model"] = "synthetic-model-z"

    with pytest.raises(ConfirmatoryEligibilityError, match="exactly once"):
        _load_mutated(manifest, draft, tmp_path, mutate)


def test_runtime_identity_copy_mismatch_is_rejected(tmp_path: Path) -> None:
    """E25/§13.3 — artifact-chain corruption, never a DESCRIPTIVE_ONLY disposition."""

    draft = _synthetic_draft()
    manifest = _manifest(draft)

    def mutate(artifact: dict[str, Any]) -> None:
        _first_record(artifact)["runtime_identity_digest"] = FOREIGN_DIGEST

    with pytest.raises(ConfirmatoryEligibilityError, match="not an exact copy"):
        _load_mutated(manifest, draft, tmp_path, mutate)


def test_runtime_identity_copied_from_the_wrong_stratum_is_rejected() -> None:
    """E25/§19 case 44 — index-aligned equality; the whole manifest is refused."""

    draft = _synthetic_draft(STRATUM_A, STRATUM_B)
    digests = _runtime_digests(draft)
    assert digests[0] != digests[1]
    swapped = (
        _record(STRATUM_A, digests[1]),
        _record(STRATUM_B, digests[0]),
    )
    with pytest.raises(ConfirmatoryEligibilityError, match="not an exact copy"):
        freeze_eligibility(
            registration_draft=draft,
            created_at=SYNTHETIC_CREATED_AT,
            eligibility_records=swapped,
        )


def test_binding_to_a_non_draft_artifact_is_rejected() -> None:
    """E26 — the manifest binds to a Stage-A artifact, not some other stage's."""

    foreign = _resealed_draft(
        _forge_like(
            _synthetic_draft(), registration_state="FINAL_REGISTRATION_FROZEN"
        )
    )
    with pytest.raises(ConfirmatoryEligibilityError, match="registration_state"):
        freeze_eligibility(
            registration_draft=foreign,
            created_at=SYNTHETIC_CREATED_AT,
            eligibility_records=_records_for(foreign),
        )


def test_missing_registration_draft_is_rejected(tmp_path: Path) -> None:
    """§5.A — Stage B occurs strictly after ``registration_draft.json`` exists."""

    draft = _synthetic_draft()
    manifest = _manifest(draft)
    root = tmp_path / "no-draft"
    with pytest.raises(ConfirmatoryEligibilityError, match="does not exist"):
        write_eligibility_manifest(manifest, confirmatory_root=root)
    assert not root.exists()


def test_corrupt_registration_draft_self_digest_is_rejected(tmp_path: Path) -> None:
    """E22 — the bound draft's own digest must verify before anything is written."""

    draft = _written_draft(tmp_path)
    manifest = _manifest(draft)
    draft_path = registration_draft_path(tmp_path, draft.design_id)
    tampered = json.loads(draft_path.read_bytes()[:-1].decode("utf-8"))
    tampered["created_at"] = "2026-02-02T03:04:06Z"
    draft_path.write_bytes(json.dumps(tampered, ensure_ascii=False).encode("utf-8") + b"\n")
    with pytest.raises(ConfirmatoryEligibilityError, match=SELF_DIGEST_FIELD):
        write_eligibility_manifest(manifest, confirmatory_root=tmp_path)
    assert not eligibility_manifest_path(tmp_path, draft.design_id).exists()


def test_corrupt_eligibility_self_digest_is_rejected(tmp_path: Path) -> None:
    """E20 — a content edit that did not recompute the digest fails closed."""

    draft = _synthetic_draft()
    artifact = _manifest(draft).to_artifact()
    artifact["created_at"] = "2026-02-02T03:04:06Z"
    path = tmp_path / ELIGIBILITY_MANIFEST_FILENAME
    path.write_bytes(canonical_json_bytes(artifact) + b"\n")
    with pytest.raises(ConfirmatoryEligibilityError, match=SELF_DIGEST_FIELD):
        load_eligibility_manifest(path, registration_draft=draft)


@pytest.mark.parametrize("digest", ["A" * 64, "a" * 63, "not-a-digest"])
def test_malformed_eligibility_self_digest_is_rejected(
    digest: str, tmp_path: Path
) -> None:
    """E20 — the claimed digest form is checked before anything is interpreted."""

    draft = _synthetic_draft()
    artifact = _manifest(draft).to_artifact()
    artifact[SELF_DIGEST_FIELD] = digest
    path = tmp_path / ELIGIBILITY_MANIFEST_FILENAME
    path.write_bytes(canonical_json_bytes(artifact) + b"\n")
    with pytest.raises(ConfirmatoryEligibilityError, match=SELF_DIGEST_FIELD):
        load_eligibility_manifest(path, registration_draft=draft)


def test_multi_stratum_manifest_round_trips(tmp_path: Path) -> None:
    """§6.3, §13.1 — three parallel arrays aligned by ``(provider, model)``."""

    draft = _written_draft(tmp_path, STRATUM_A, STRATUM_B)
    manifest = _manifest(draft, ALL_PASS, ALL_UNASSESSED)
    path = write_eligibility_manifest(manifest, confirmatory_root=tmp_path)
    loaded = load_eligibility_manifest(path, registration_draft=draft)
    assert loaded == manifest
    assert [record.identity for record in loaded.eligibility_records] == [
        STRATUM_A,
        STRATUM_B,
    ]
    assert [record.disposition for record in loaded.eligibility_records] == [
        "CONFIRMATORY_ELIGIBLE",
        "DESCRIPTIVE_ONLY_UNASSESSED",
    ]
    assert tuple(
        record.runtime_identity_digest for record in loaded.eligibility_records
    ) == _runtime_digests(draft)


# ===========================================================================
# H. Immutability, canonical JSON, and the digest chain (§15, §16, §21)
# ===========================================================================


def test_eligibility_manifest_writes_once_at_the_frozen_path(tmp_path: Path) -> None:
    draft = _written_draft(tmp_path)
    path = write_eligibility_manifest(_manifest(draft), confirmatory_root=tmp_path)
    assert path == tmp_path / draft.design_id / ELIGIBILITY_MANIFEST_FILENAME
    assert path == eligibility_manifest_path(tmp_path, draft.design_id)
    assert path.is_file()


def test_eligibility_manifest_immutable_after_finalize(tmp_path: Path) -> None:
    """§15 — a second write is refused and the existing bytes are untouched."""

    draft = _written_draft(tmp_path)
    manifest = _manifest(draft)
    path = write_eligibility_manifest(manifest, confirmatory_root=tmp_path)
    original = path.read_bytes()
    with pytest.raises(ConfirmatoryEligibilityError, match="immutable"):
        write_eligibility_manifest(manifest, confirmatory_root=tmp_path)
    assert path.read_bytes() == original


def test_no_reassessment_after_final_freeze_raises(tmp_path: Path) -> None:
    """§15 — no in-place promotion; reassessment needs a new ``design_id``."""

    draft = _written_draft(tmp_path)
    frozen = _manifest(draft, ALL_UNASSESSED)
    path = write_eligibility_manifest(frozen, confirmatory_root=tmp_path)
    original = path.read_bytes()
    promoted = _manifest(draft, ALL_PASS)
    assert promoted.eligibility_records[0].disposition == "CONFIRMATORY_ELIGIBLE"
    with pytest.raises(ConfirmatoryEligibilityError, match="immutable"):
        write_eligibility_manifest(promoted, confirmatory_root=tmp_path)
    assert path.read_bytes() == original
    assert (
        load_eligibility_manifest(path, registration_draft=draft) == frozen
    )


def test_invalid_manifest_fails_before_the_file_is_created(tmp_path: Path) -> None:
    """§21 — no eligibility artifact is created for a manifest that fails E1-E26."""

    draft = _written_draft(tmp_path)
    invalid = _resealed(replace(_manifest(draft), created_at="2026-02-02T03:04:05+00:00"))
    with pytest.raises(ConfirmatoryEligibilityError, match="created_at"):
        write_eligibility_manifest(invalid, confirmatory_root=tmp_path)
    assert not eligibility_manifest_path(tmp_path, draft.design_id).exists()


def test_digest_valid_direct_construction_bypass_cannot_create_a_file(
    tmp_path: Path,
) -> None:
    """§21 — a recomputed ``self_digest`` does not buy a malformed manifest a file."""

    draft = _written_draft(tmp_path)
    forged_record = _forge_like(
        _manifest(draft).eligibility_records[0],
        disposition="CONFIRMATORY_ELIGIBLE",
    )
    invalid = _resealed(
        replace(_manifest(draft), eligibility_records=(forged_record,))
    )
    with pytest.raises(ConfirmatoryEligibilityError, match="derive"):
        write_eligibility_manifest(invalid, confirmatory_root=tmp_path)
    assert not eligibility_manifest_path(tmp_path, draft.design_id).exists()


def test_direct_literal_bypass_cannot_create_a_file(tmp_path: Path) -> None:
    draft = _written_draft(tmp_path)
    invalid = _resealed(
        _forge_like(_manifest(draft), schema_version="EligibilityManifestV2")
    )
    with pytest.raises(ConfirmatoryEligibilityError, match="schema_version"):
        write_eligibility_manifest(invalid, confirmatory_root=tmp_path)
    assert not eligibility_manifest_path(tmp_path, draft.design_id).exists()


def test_canonical_self_digest_is_stable_and_order_independent(tmp_path: Path) -> None:
    draft = _synthetic_draft()
    manifest = _manifest(draft)
    reordered = dict(reversed(list(manifest.canonical_payload().items())))
    assert compute_self_digest(reordered) == manifest.self_digest
    assert _manifest(draft).self_digest == manifest.self_digest
    digest = manifest.self_digest
    assert len(digest) == 64
    assert digest == digest.lower()
    assert set(digest) <= set("0123456789abcdef")


def test_persisted_manifest_ends_with_exactly_one_lf(tmp_path: Path) -> None:
    draft = _written_draft(tmp_path)
    path = write_eligibility_manifest(_manifest(draft), confirmatory_root=tmp_path)
    raw = path.read_bytes()
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")
    assert raw.count(b"\n") == 1


def test_trailing_lf_is_excluded_from_the_self_digest(tmp_path: Path) -> None:
    draft = _written_draft(tmp_path)
    manifest = _manifest(draft)
    path = write_eligibility_manifest(manifest, confirmatory_root=tmp_path)
    raw = path.read_bytes()
    body = json.loads(raw[:-1].decode("utf-8"))
    del body[SELF_DIGEST_FIELD]
    assert hashlib.sha256(canonical_json_bytes(body)).hexdigest() == manifest.self_digest
    assert hashlib.sha256(raw).hexdigest() != manifest.self_digest


def test_round_trip_preserves_the_same_self_digest(tmp_path: Path) -> None:
    draft = _written_draft(tmp_path)
    manifest = _manifest(draft)
    path = write_eligibility_manifest(manifest, confirmatory_root=tmp_path)
    loaded = load_eligibility_manifest(path, registration_draft=draft)
    assert loaded == manifest
    assert serialize_artifact(loaded.to_artifact()) == path.read_bytes()


def test_reader_accepts_semantically_equivalent_noncanonical_input(
    tmp_path: Path,
) -> None:
    """§16 — no byte-for-byte input canonicality gate is added."""

    draft = _synthetic_draft()
    manifest = _manifest(draft)
    pretty = tmp_path / "pretty-eligibility-manifest.json"
    pretty.write_bytes(
        json.dumps(manifest.to_artifact(), indent=2, ensure_ascii=False).encode("utf-8")
        + b"\n"
    )
    assert load_eligibility_manifest(pretty, registration_draft=draft) == manifest

    shuffled = tmp_path / "reordered-eligibility-manifest.json"
    shuffled.write_bytes(
        json.dumps(
            dict(reversed(list(manifest.to_artifact().items()))), ensure_ascii=False
        ).encode("utf-8")
        + b"\n"
    )
    assert load_eligibility_manifest(shuffled, registration_draft=draft) == manifest


def _module_source() -> str:
    return Path(eligibility_module.__file__).read_text(encoding="utf-8")


def _dotted_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_dotted_name(node.value)}.{node.attr}"
    return ""


def _module_invocations() -> set[str]:
    """Every function the module invokes, including those routed through ``_reuse``.

    ``_reuse(verify_self_digest, artifact)`` invokes ``verify_self_digest`` just as
    surely as calling it directly, so the first positional argument of a
    ``_reuse`` call counts as an invocation too.  A local digest hidden behind
    that adapter would be caught by the same rule.
    """

    names: set[str] = set()
    for node in ast.walk(ast.parse(_module_source())):
        if not isinstance(node, ast.Call):
            continue
        target = _dotted_name(node.func)
        if target == "_reuse" and node.args:
            names.add(_dotted_name(node.args[0]))
        else:
            names.add(target)
    return names


def _module_imports() -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(_module_source())):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(alias.name for alias in node.names)
            if node.module:
                names.add(node.module)
    return names


def test_no_local_canonical_digest_operation_in_production_source() -> None:
    """§19 — the digest algorithm is Work Unit 1's, never spelled again here.

    Checked against the module's own syntax tree rather than by substring, so a
    prose mention in a docstring cannot pass it and a real call cannot hide from
    it.
    """

    imports = _module_imports()
    assert "hashlib" not in imports
    assert "canonical_json_bytes" not in imports

    calls = _module_invocations()
    local_digest_calls = {
        name
        for name in calls
        if "sha256" in name or "canonical_json_bytes" in name or "json.dumps" in name
    }
    assert local_digest_calls == set()

    source = _module_source()
    assert "sort_keys" not in source
    assert "ensure_ascii" not in source


def test_authoritative_digest_helpers_are_the_ones_actually_called() -> None:
    """§19 — E20, E22, the seal, and the write path all go through Work Unit 1."""

    namespace = vars(eligibility_module)
    assert namespace["compute_self_digest"] is compute_self_digest
    assert namespace["serialize_artifact"] is serialize_artifact
    assert namespace["verify_self_digest"] is verify_self_digest

    calls = _module_invocations()
    assert "verify_self_digest" in calls
    assert "compute_self_digest" in calls
    assert "serialize_artifact" in calls


def test_eligibility_manifest_path_refuses_an_escaping_design_id(
    tmp_path: Path,
) -> None:
    """§21 — ``design_id`` containment uses the Work Unit 1 path discipline."""

    for design_id in ("../escape", "nested/segment", ".", "", "CON"):
        with pytest.raises(ConfirmatoryEligibilityError):
            eligibility_manifest_path(tmp_path, design_id)


# ===========================================================================
# I. Stage-B scope: prospective only, no Stage-C or execution leakage (§11, §4.6)
# ===========================================================================


def test_total_observation_is_an_ordinary_prospective_predicate_record() -> None:
    """§11 — no ``observation_status``, no ``failure_class``, no endpoint data."""

    record = _first_record(_manifest(_synthetic_draft()).to_artifact())
    total_observation = record["predicates"][2]
    assert total_observation["predicate_id"] == "TOTAL_OBSERVATION"
    assert set(total_observation) == {"predicate_id", "status", "evidence_refs"}


def test_persisted_manifest_uses_only_the_frozen_key_vocabulary() -> None:
    """§4.6, §11, §14.3 — nothing Stage-C, assignment, or execution-shaped leaks in."""

    draft = _synthetic_draft(STRATUM_A, STRATUM_B)
    manifest = _manifest(draft, ALL_PASS, ALL_UNASSESSED)
    keys = set(_iter_keys(manifest.to_artifact()))
    assert keys.isdisjoint(FORBIDDEN_KEY_NAMES)
    assert keys == {
        "schema_version",
        "registration_state",
        "confirmatory_profile",
        "design_id",
        "created_at",
        "registration_draft_digest",
        "eligibility_records",
        SELF_DIGEST_FIELD,
        "provider",
        "model",
        "predicates",
        "infrastructure_symmetry_audit",
        "runtime_identity_digest",
        "disposition",
        "predicate_id",
        "status",
        "evidence_refs",
        "evidence_kind",
        "locator",
        "content_digest",
        "channels",
        "channel_id",
        "check_status",
        "symmetry_result",
    }


def test_manifest_contains_no_json_numbers() -> None:
    """§16 — every frozen field is a string, an array, or an object."""

    def _walk(value: Any) -> Iterator[Any]:
        if isinstance(value, dict):
            for item in value.values():
                yield from _walk(item)
        elif isinstance(value, list):
            for item in value:
                yield from _walk(item)
        else:
            yield value

    artifact = _manifest(_synthetic_draft()).to_artifact()
    assert all(isinstance(leaf, str) for leaf in _walk(artifact))


def test_module_binds_the_stage_a_draft_state_it_expects() -> None:
    """§14.2 E26 — the only upstream state this module accepts."""

    assert REGISTRATION_STATE_DRAFT == "REGISTRATION_DRAFT"
    draft = _synthetic_draft()
    assert draft.registration_state == REGISTRATION_STATE_DRAFT


# ===========================================================================
# J. §14 numbered order and first-failure precedence (E1-E26)
# ===========================================================================


def _rule_call_sequence(function_name: str) -> list[int]:
    """The ``_validate_eN`` calls a validation orchestrator makes, in source order."""

    tree = ast.parse(_module_source())
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != function_name:
            continue
        numbers: list[int] = []
        for statement in node.body:
            if isinstance(statement, ast.Expr):
                value: ast.expr | None = statement.value
            elif isinstance(statement, ast.Assign):
                value = statement.value
            else:
                value = None
            if (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id.startswith("_validate_e")
            ):
                numbers.append(int(value.func.id[len("_validate_e") :]))
        return numbers
    raise AssertionError(f"{function_name} is not defined in the module")


def test_tier_one_applies_e1_through_e21_in_numbered_order() -> None:
    """§14 — the order is contractually observable, so it is mechanically fixed."""

    assert _rule_call_sequence("_validate_tier_one") == list(range(1, 22))


def test_tier_two_applies_e22_through_e26_in_numbered_order() -> None:
    """§14.2 — Tier 2 runs only after Tier 1, and in its own numbered order."""

    assert _rule_call_sequence("_validate_tier_two") == list(range(22, 27))


def test_every_numbered_rule_has_its_own_validator() -> None:
    """§14 — twenty-six rules, twenty-six functions, no rule folded into another."""

    namespace = vars(eligibility_module)
    for number in range(1, 27):
        assert callable(namespace[f"_validate_e{number}"])


def test_raw_parse_does_not_verify_the_self_digest() -> None:
    """E20 must not run before E1: the envelope parse stops short of verification."""

    parse = vars(eligibility_module)["_parse_eligibility_bytes"]
    draft = _synthetic_draft()
    artifact = _manifest(draft).to_artifact()
    artifact[SELF_DIGEST_FIELD] = "0" * 64
    parsed = parse(canonical_json_bytes(artifact) + b"\n")
    assert parsed[SELF_DIGEST_FIELD] == "0" * 64

    calls = _rule_call_sequence("_validate_tier_one")
    assert calls.index(1) < calls.index(20)


# --- multi-defect artifacts: the lower-numbered rule is the first failure ---


def _add_top_level_key(key: str, value: Any) -> Callable[[dict[str, Any]], None]:
    def mutate(artifact: dict[str, Any]) -> None:
        artifact[key] = value

    return mutate


def _break_disposition(artifact: dict[str, Any]) -> None:
    """An E19 defect: a legal token that contradicts the recorded statuses."""

    record = _first_record(artifact)
    record["disposition"] = (
        "CONFIRMATORY_ELIGIBLE"
        if record["disposition"] != "CONFIRMATORY_ELIGIBLE"
        else "DESCRIPTIVE_ONLY_UNASSESSED"
    )


def _illegal_disposition(artifact: dict[str, Any]) -> None:
    """An E19 defect of the vocabulary kind: a token outside the frozen six.

    This is the mutation that discriminates the frozen order from a
    ``__post_init__``-driven one: reading ``disposition`` before constructing the
    record makes this fire ahead of E17 and E18, which §14 forbids.
    """

    _first_record(artifact)["disposition"] = "DESCRIPTIVE_ONLY_INELIGIBLE"


def _break_runtime_digest(artifact: dict[str, Any]) -> None:
    """An E18 defect: a syntactically invalid runtime identity digest."""

    _first_record(artifact)["runtime_identity_digest"] = "NOT-A-DIGEST"


def _break_symmetry_status(artifact: dict[str, Any]) -> None:
    """An E17 defect: a recorded symmetry status the channels do not derive."""

    predicate = _first_record(artifact)["predicates"][1]
    predicate["status"] = "PASS" if predicate["status"] != "PASS" else "UNASSESSED"


def _defects(
    *mutations: Callable[[dict[str, Any]], None],
) -> Callable[[dict[str, Any]], None]:
    def mutate(artifact: dict[str, Any]) -> None:
        for mutation in mutations:
            mutation(artifact)

    return mutate


def _extra_record_key(artifact: dict[str, Any]) -> None:
    _first_record(artifact)["assessor"] = "synthetic"


def _unknown_predicate_id(artifact: dict[str, Any]) -> None:
    _first_record(artifact)["predicates"][3]["predicate_id"] = "TOTAL_DETERMINISM"


def _illegal_status(artifact: dict[str, Any]) -> None:
    _first_record(artifact)["predicates"][2]["status"] = "pass"


def _strip_pass_evidence(artifact: dict[str, Any]) -> None:
    """An E13 defect: predicates[0] records PASS with no supporting evidence."""

    _first_record(artifact)["predicates"][0]["evidence_refs"] = []


def _forbidden_key_in_evidence(artifact: dict[str, Any]) -> None:
    _first_record(artifact)["predicates"][0]["evidence_refs"][0]["assessed_at"] = "x"


def _drop_a_channel(artifact: dict[str, Any]) -> None:
    del _channels_of(artifact)[3]


def _incoherent_channel(artifact: dict[str, Any]) -> None:
    """An E16 defect: NOT_CHECKED while still claiming a result and evidence."""

    _channels_of(artifact)[3]["check_status"] = "NOT_CHECKED"


def _foreign_draft_digest(artifact: dict[str, Any]) -> None:
    artifact["registration_draft_digest"] = FOREIGN_DIGEST


def _foreign_design_id(artifact: dict[str, Any]) -> None:
    artifact["design_id"] = "other-design-000"


def _foreign_stratum(artifact: dict[str, Any]) -> None:
    record = _first_record(artifact)
    record["provider"] = "synthetic-provider-z"
    record["model"] = "synthetic-model-z"


#: ``(label, base statuses, mutation, reseal, first-failure pattern)``.
#: Every artifact carries **both** named defects at once; the assertion is that
#: the lower-numbered rule is the one observed.  ``reseal=False`` leaves the
#: ``self_digest`` stale, so E20 is a genuine simultaneous defect.
PRECEDENCE_CASES: tuple[
    tuple[str, tuple[str, ...], Callable[[dict[str, Any]], None], bool, str], ...
] = (
    (
        "E1 outranks E20",
        DEFAULT_STATUSES,
        _add_top_level_key("assessor", "synthetic"),
        False,
        "unexpected keys",
    ),
    (
        "E1 outranks E21",
        DEFAULT_STATUSES,
        _add_top_level_key("assessed_at", SYNTHETIC_CREATED_AT_TEXT),
        True,
        "unexpected keys",
    ),
    (
        "E8 outranks E19",
        DEFAULT_STATUSES,
        _defects(_extra_record_key, _break_disposition),
        True,
        "unexpected keys",
    ),
    (
        "E10 outranks E17",
        DEFAULT_STATUSES,
        _defects(_unknown_predicate_id, _break_symmetry_status),
        True,
        "predicate_id must be",
    ),
    (
        "E10 outranks E19",
        DEFAULT_STATUSES,
        _defects(_unknown_predicate_id, _break_disposition),
        True,
        "predicate_id must be",
    ),
    (
        "E11 outranks E19",
        DEFAULT_STATUSES,
        _defects(_illegal_status, _break_disposition),
        True,
        "status must be one of",
    ),
    (
        "E13 outranks E17",
        DEFAULT_STATUSES,
        _defects(_strip_pass_evidence, _break_symmetry_status),
        True,
        "at least one reference",
    ),
    (
        "E14 outranks E20 and E21",
        DEFAULT_STATUSES,
        _forbidden_key_in_evidence,
        False,
        "unexpected keys",
    ),
    (
        "E17 outranks E18",
        DEFAULT_STATUSES,
        _defects(_break_symmetry_status, _break_runtime_digest),
        True,
        "channels derive",
    ),
    (
        "E17 outranks E19",
        DEFAULT_STATUSES,
        _defects(_break_symmetry_status, _break_disposition),
        True,
        "channels derive",
    ),
    (
        "E18 outranks E19",
        DEFAULT_STATUSES,
        _defects(_break_runtime_digest, _break_disposition),
        True,
        "runtime_identity_digest",
    ),
    (
        "E17 outranks the E19 vocabulary check",
        DEFAULT_STATUSES,
        _defects(_break_symmetry_status, _illegal_disposition),
        True,
        "channels derive",
    ),
    (
        "E18 outranks the E19 vocabulary check",
        DEFAULT_STATUSES,
        _defects(_break_runtime_digest, _illegal_disposition),
        True,
        "runtime_identity_digest",
    ),
    (
        "E19 outranks E20",
        DEFAULT_STATUSES,
        _break_disposition,
        False,
        "cross-checked",
    ),
    (
        "E15 outranks E17",
        ALL_PASS,
        _defects(_drop_a_channel, _break_symmetry_status),
        True,
        "exactly 4 records",
    ),
    (
        "E16 outranks E17",
        ALL_PASS,
        _incoherent_channel,
        True,
        "is NOT_CHECKED and must carry",
    ),
    (
        "E22 outranks E23",
        DEFAULT_STATUSES,
        _defects(_foreign_draft_digest, _foreign_design_id),
        True,
        "does not match the bound",
    ),
    (
        "E23 outranks E24",
        DEFAULT_STATUSES,
        _defects(_foreign_design_id, _foreign_stratum),
        True,
        "design_id",
    ),
)


@pytest.mark.parametrize(
    ("label", "statuses", "mutate", "reseal", "expected"),
    PRECEDENCE_CASES,
    ids=[case[0] for case in PRECEDENCE_CASES],
)
def test_first_failure_follows_the_frozen_rule_number(
    label: str,
    statuses: tuple[str, ...],
    mutate: Callable[[dict[str, Any]], None],
    reseal: bool,
    expected: str,
    tmp_path: Path,
) -> None:
    """§14 — two simultaneous defects, and the lower-numbered rule is reported."""

    draft = _synthetic_draft()
    artifact = _manifest(draft, statuses).to_artifact()
    mutate(artifact)
    path = (
        _persist(artifact, tmp_path) if reseal else _persist_unsealed(artifact, tmp_path)
    )
    with pytest.raises(ConfirmatoryEligibilityError, match=expected):
        load_eligibility_manifest(path, registration_draft=draft)


def test_e24_outranks_e25(tmp_path: Path) -> None:
    """§14.2 — a missing stratum record is reported before a runtime copy mismatch."""

    draft = _synthetic_draft(STRATUM_A, STRATUM_B)
    artifact = _manifest(draft).to_artifact()
    del artifact["eligibility_records"][1]
    _first_record(artifact)["runtime_identity_digest"] = FOREIGN_DIGEST
    with pytest.raises(ConfirmatoryEligibilityError, match="exactly once"):
        load_eligibility_manifest(_persist(artifact, tmp_path), registration_draft=draft)


def test_e25_outranks_e26() -> None:
    """§14.2 — a runtime copy mismatch is reported before the bound-state check."""

    foreign = _resealed_draft(
        _forge_like(
            _synthetic_draft(STRATUM_A, STRATUM_B),
            registration_state="FINAL_REGISTRATION_FROZEN",
        )
    )
    digests = _runtime_digests(foreign)
    swapped = (_record(STRATUM_A, digests[1]), _record(STRATUM_B, digests[0]))
    with pytest.raises(ConfirmatoryEligibilityError, match="not an exact copy"):
        freeze_eligibility(
            registration_draft=foreign,
            created_at=SYNTHETIC_CREATED_AT,
            eligibility_records=swapped,
        )


def test_nested_post_init_no_longer_decides_first_failure(tmp_path: Path) -> None:
    """§14 — three nested defects, and the earliest numbered rule is the one raised.

    The record carries an E17 defect (a symmetry status the channels do not
    derive), an E18 defect (a malformed ``runtime_identity_digest``), and an E19
    defect (a disposition token outside the frozen six).

    This combination is the one that discriminates.  A loader that realized these
    rules through the frozen dataclasses reads ``disposition`` out of the mapping
    before it can construct ``EligibilityStratumRecordV1`` — the record derives
    its own disposition, so the persisted token has to be validated separately —
    and therefore reports the E19 vocabulary failure first, ahead of the E17 and
    E18 checks that live in ``__post_init__``.  §14 requires E17.
    """

    draft = _synthetic_draft()
    artifact = _manifest(draft).to_artifact()
    _break_symmetry_status(artifact)
    _break_runtime_digest(artifact)
    _illegal_disposition(artifact)
    with pytest.raises(ConfirmatoryEligibilityError, match="channels derive"):
        load_eligibility_manifest(_persist(artifact, tmp_path), registration_draft=draft)


def test_nested_evidence_rule_outranks_the_record_level_rules(tmp_path: Path) -> None:
    """§14 — E13 sits below E17/E18/E19 and is reported ahead of all three."""

    draft = _synthetic_draft()
    artifact = _manifest(draft).to_artifact()
    _strip_pass_evidence(artifact)
    _break_symmetry_status(artifact)
    _break_runtime_digest(artifact)
    _illegal_disposition(artifact)
    with pytest.raises(ConfirmatoryEligibilityError, match="at least one reference"):
        load_eligibility_manifest(_persist(artifact, tmp_path), registration_draft=draft)


def test_write_path_uses_the_same_ordered_machinery(tmp_path: Path) -> None:
    """§7 — one validation implementation, and it runs before any side effect."""

    draft = _written_draft(tmp_path)
    manifest = _manifest(draft)
    forged_record = _forge_like(
        manifest.eligibility_records[0], runtime_identity_digest="NOT-A-DIGEST"
    )
    invalid = _resealed(
        _forge_like(
            replace(manifest, eligibility_records=(forged_record,)),
            schema_version="EligibilityManifestV2",
        )
    )
    # E2 and E18 are both violated; E2 is the frozen first failure.
    with pytest.raises(ConfirmatoryEligibilityError, match="schema_version"):
        write_eligibility_manifest(invalid, confirmatory_root=tmp_path)
    assert not eligibility_manifest_path(tmp_path, draft.design_id).exists()


def test_write_path_validates_tier_one_before_reading_the_bound_draft(
    tmp_path: Path,
) -> None:
    """§7, §21 — no filesystem read or write happens for a Tier-1-invalid manifest."""

    draft = _synthetic_draft()
    invalid = _resealed(
        _forge_like(_manifest(draft), created_at="2026-02-02T03:04:05+00:00")
    )
    root = tmp_path / "no-draft-at-all"
    with pytest.raises(ConfirmatoryEligibilityError, match="created_at"):
        write_eligibility_manifest(invalid, confirmatory_root=root)
    assert not root.exists()


def test_e21_is_implemented_even_though_earlier_rules_subsume_it() -> None:
    """§14.3 — E21 restates the prohibition; it is checked directly here.

    Every forbidden name is structurally impossible by E1/E8/E11/E14/E15/E16, so
    E21 is unreachable through a conforming loader — which is why the public-path
    tests above assert the *earlier* rule.  The rule still exists and still fails
    closed, and this is the proof.
    """

    validate_e21 = vars(eligibility_module)["_validate_e21"]
    draft = _synthetic_draft()
    validate_e21(_manifest(draft).to_artifact())
    for forbidden in sorted(FORBIDDEN_KEY_NAMES):
        artifact = _manifest(draft).to_artifact()
        _first_record(artifact)["predicates"][0]["evidence_refs"][0][forbidden] = "x"
        with pytest.raises(ConfirmatoryEligibilityError, match="forbidden key name"):
            validate_e21(artifact)
