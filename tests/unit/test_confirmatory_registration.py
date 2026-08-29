"""Focused tests for the Stage-A draft, the canonical digest profile, and Stage C.

Every artifact these tests write lives in a pytest ``tmp_path``.  No real
``design_id``, task, provider, model, seed, or endpoint appears anywhere here,
nothing is written under ``results/``, and no randomness, provider, or network is
touched: the code implementation authorization keeps
``ACTUAL_CONFIRMATORY_REGISTRATION_AUTHORIZED: NO``, so these are synthetic test
artifacts and nothing more.

The proposed baseline labels below are likewise synthetic: they exercise the
schema's structural balance rule, and no assignment bit is drawn anywhere in
this module.

The Stage-C sections exercise ``FINAL_REGISTRATION_FROZEN``: the sixteen-key
``RegistrationManifestV1`` schema, the deterministic partition, ``position_id``,
``K``, ``randomization_mode``, the five-key ``matrix_digest`` preimage, the
``F1``-``F39`` first-failure order, and immutable persistence.  **No eligibility is
assessed here.**  Every predicate status, symmetry finding, and disposition below
is a synthetic value chosen to exercise the frozen schema, and the Stage-B
manifests are built through Work Unit 2's committed public API rather than a
reimplemented one.  No assignment bit, Monte Carlo seed, provenance artifact,
provider call, or network access occurs anywhere in this module.
"""

from __future__ import annotations

import ast
from dataclasses import fields as dataclass_fields, replace
from datetime import UTC, datetime, timedelta, timezone
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any, Callable, NamedTuple

import pytest

from iqa_soa.experiment import confirmatory_registration as registration_module
from iqa_soa.experiment.confirmatory_eligibility import (
    CHANNEL_IDS,
    DISPOSITIONS,
    ELIGIBILITY_MANIFEST_FILENAME,
    PREDICATE_IDS,
    REGISTRATION_STATE_ELIGIBILITY_FROZEN,
    EligibilityManifestV1,
    EligibilityPredicateRecordV1,
    EligibilityStratumRecordV1,
    EvidenceReferenceV1,
    InfrastructureSymmetryAuditV1,
    InfrastructureSymmetryChannelV1,
    freeze_eligibility,
    write_eligibility_manifest,
)
from iqa_soa.experiment.confirmatory_registration import (
    AGGREGATION_RULE,
    ALPHA,
    BASELINE_LABEL_FULL,
    BASELINE_LABEL_OFF,
    BASELINE_LABELS,
    CONFIRMATORY_PROFILE,
    ConfirmatoryPositionV1,
    ConfirmatoryRegistrationError,
    ConfirmatoryStratumV1,
    DISPOSITION_CONFIRMATORY_ELIGIBLE,
    MULTIPLICITY_ARCHITECTURE,
    PRIMARY_ENDPOINT,
    PRIMARY_ESTIMAND_ARCHITECTURE,
    PROPOSED_STATISTICAL_CONFIGURATION_SCHEMA_VERSION,
    ProposedPositionV1,
    ProposedProviderSeedEntryV1,
    ProposedRepetitionsEntryV1,
    ProposedRuntimeConfigurationV1,
    ProposedStatisticalConfigurationV1,
    ProposedStratumV1,
    RANDOMIZATION_EXACT_ENUMERATION_MAX_K,
    RANDOMIZATION_MODES,
    RANDOMIZATION_MODE_EXACT_ENUMERATION,
    RANDOMIZATION_MODE_MONTE_CARLO,
    REGISTRATION_DRAFT_FILENAME,
    REGISTRATION_DRAFT_SCHEMA_VERSION,
    REGISTRATION_MANIFEST_FILENAME,
    REGISTRATION_MANIFEST_FORBIDDEN_KEY_NAMES,
    REGISTRATION_MANIFEST_SCHEMA_VERSION,
    REGISTRATION_STATE_DRAFT,
    REGISTRATION_STATE_FINAL_REGISTRATION_FROZEN,
    RegistrationDraft,
    RegistrationManifest,
    RetryPolicyV1,
    RuntimeSnapshotV1,
    SECONDARY_ENDPOINT_SEQUENCE,
    SELF_DIGEST_FIELD,
    STATISTIC_SPEC_ID,
    TREATMENT_CONTRAST_ORIENTATION,
    attach_self_digest,
    canonical_json_bytes,
    compute_self_digest,
    draft_registration,
    freeze_final_registration,
    load_registration_draft,
    load_registration_manifest,
    parse_artifact,
    registration_draft_path,
    registration_manifest_path,
    serialize_artifact,
    verify_self_digest,
    write_registration_draft,
    write_registration_manifest,
)

SYNTHETIC_DESIGN_ID = "synthetic-design-000"
SYNTHETIC_CREATED_AT = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
SYNTHETIC_CREATED_AT_TEXT = "2026-01-01T00:00:00Z"
SYNTHETIC_DIGEST = "0" * 64
SYNTHETIC_PROVIDER = "synthetic-provider"
SYNTHETIC_MODEL = "synthetic-model"
#: A second invented stratum.  ``(SYNTHETIC_PROVIDER, SYNTHETIC_MODEL)`` sorts
#: strictly before it, so the two-stratum fixtures are already in RC-3 order.
SYNTHETIC_PROVIDER_B = "synthetic-provider-b"
SYNTHETIC_MODEL_B = "synthetic-model-b"
SYNTHETIC_TASKS = ("synthetic-task-a", "synthetic-task-b")
SYNTHETIC_REPETITION_COUNT = 2

#: The ten stamped statistical constants and a foreign value for each (§7.2).
STAMPED_STATISTICAL_CONSTANTS: tuple[tuple[str, Any], ...] = (
    ("schema_version", "ForeignStatisticalConfigurationV9"),
    ("statistic_spec_id", "confirmatory_task_sign_flip_v2"),
    ("alpha", "0.10"),
    ("multiplicity_architecture", "BONFERRONI"),
    ("primary_endpoint", "some_other_endpoint"),
    ("secondary_endpoint_sequence", ["attack_success"]),
    ("primary_estimand_architecture", "SOMETHING_ELSE"),
    ("aggregation_rule", "UNWEIGHTED_POOLED"),
    ("treatment_contrast_orientation", "OFF_MINUS_FULL"),
    ("randomization_exact_enumeration_max_k", 32),
)


def _seed_for(repetition: int) -> int:
    """Ordinary provider seed for a repetition index — never assignment material."""

    return 11 + repetition


def _synthetic_snapshot(**overrides: Any) -> RuntimeSnapshotV1:
    retry_policy = RetryPolicyV1(
        max_attempts=1,
        backoff_kind="NONE",
        initial_delay_seconds="0",
        max_delay_seconds="0",
        retryable_error_classes=("SYNTHETIC_A", "SYNTHETIC_B"),
    )
    arguments: dict[str, Any] = {
        "provider_name": SYNTHETIC_PROVIDER,
        "model": SYNTHETIC_MODEL,
        "endpoint": "https://synthetic.invalid/v1",
        "provider_config_digest": SYNTHETIC_DIGEST,
        "provider_parameters_digest": "1" * 64,
        "timeout_seconds": "30.5",
        "retry_policy": retry_policy,
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


def _synthetic_snapshot_b(**overrides: Any) -> RuntimeSnapshotV1:
    """The second stratum's snapshot: a deliberately different runtime policy.

    Its ``timeout_seconds`` and ``retry_policy`` differ from
    :func:`_synthetic_snapshot`, which is what proves no accidental global
    equality constraint survives the removal of the configuration-level pair.
    """

    arguments: dict[str, Any] = {
        "provider_name": SYNTHETIC_PROVIDER_B,
        "model": SYNTHETIC_MODEL_B,
        "endpoint": "https://synthetic-b.invalid/v1",
        "timeout_seconds": "12",
        "retry_policy": RetryPolicyV1(
            max_attempts=3,
            backoff_kind="EXPONENTIAL",
            initial_delay_seconds="0.5",
            max_delay_seconds="8",
            retryable_error_classes=("SYNTHETIC_C",),
        ),
    }
    arguments.update(overrides)
    return _synthetic_snapshot(**arguments)


def _synthetic_runtime(
    *, snapshots: tuple[RuntimeSnapshotV1, ...] | None = None
) -> ProposedRuntimeConfigurationV1:
    """The one-key runtime collection: one snapshot per proposed stratum."""

    return ProposedRuntimeConfigurationV1(
        registration_expected_runtime_snapshots=(
            (_synthetic_snapshot(),) if snapshots is None else snapshots
        ),
    )


def _synthetic_strata() -> tuple[ProposedStratumV1, ...]:
    return (ProposedStratumV1(provider=SYNTHETIC_PROVIDER, model=SYNTHETIC_MODEL),)


def _multi_strata() -> tuple[ProposedStratumV1, ...]:
    """Two proposed strata, sorted ascending by ``(provider, model)``."""

    return (
        ProposedStratumV1(provider=SYNTHETIC_PROVIDER, model=SYNTHETIC_MODEL),
        ProposedStratumV1(provider=SYNTHETIC_PROVIDER_B, model=SYNTHETIC_MODEL_B),
    )


def _multi_snapshots() -> tuple[RuntimeSnapshotV1, ...]:
    """The exact element-wise runtime cover of :func:`_multi_strata`."""

    return (_synthetic_snapshot(), _synthetic_snapshot_b())


def _repetitions_over(
    strata: tuple[ProposedStratumV1, ...],
    *,
    tasks: tuple[str, ...] = SYNTHETIC_TASKS,
    count: int = SYNTHETIC_REPETITION_COUNT,
) -> tuple[ProposedRepetitionsEntryV1, ...]:
    """The full task x stratum cross product, in registered order."""

    return tuple(
        ProposedRepetitionsEntryV1(
            task_id=task_id,
            provider=stratum.provider,
            model=stratum.model,
            repetition_count=count,
        )
        for task_id in tasks
        for stratum in strata
    )


def _positions_over(
    strata: tuple[ProposedStratumV1, ...],
    *,
    tasks: tuple[str, ...] = SYNTHETIC_TASKS,
    count: int = SYNTHETIC_REPETITION_COUNT,
) -> tuple[ProposedPositionV1, ...]:
    """One OFF and one FULL per matched contrast, over every stratum."""

    positions: list[ProposedPositionV1] = []
    for task_id in tasks:
        for stratum in strata:
            for repetition in range(count):
                for slot, label in ((1, BASELINE_LABEL_OFF), (2, BASELINE_LABEL_FULL)):
                    positions.append(
                        ProposedPositionV1(
                            task_id=task_id,
                            provider=stratum.provider,
                            model=stratum.model,
                            repetition=repetition,
                            provider_seed=_seed_for(repetition),
                            slot=slot,
                            baseline_label=label,
                        )
                    )
    return tuple(positions)


def _synthetic_repetitions(
    *,
    tasks: tuple[str, ...] = SYNTHETIC_TASKS,
    count: int = SYNTHETIC_REPETITION_COUNT,
) -> tuple[ProposedRepetitionsEntryV1, ...]:
    return tuple(
        ProposedRepetitionsEntryV1(
            task_id=task_id,
            provider=SYNTHETIC_PROVIDER,
            model=SYNTHETIC_MODEL,
            repetition_count=count,
        )
        for task_id in tasks
    )


def _synthetic_provider_seeds(
    *, count: int = SYNTHETIC_REPETITION_COUNT
) -> tuple[ProposedProviderSeedEntryV1, ...]:
    return tuple(
        ProposedProviderSeedEntryV1(repetition=index, provider_seed=_seed_for(index))
        for index in range(count)
    )


def _synthetic_positions(
    *,
    tasks: tuple[str, ...] = SYNTHETIC_TASKS,
    count: int = SYNTHETIC_REPETITION_COUNT,
) -> tuple[ProposedPositionV1, ...]:
    """The proposed baseline schedule: one OFF and one FULL per matched contrast."""

    positions: list[ProposedPositionV1] = []
    for task_id in tasks:
        for repetition in range(count):
            for slot, label in ((1, BASELINE_LABEL_OFF), (2, BASELINE_LABEL_FULL)):
                positions.append(
                    ProposedPositionV1(
                        task_id=task_id,
                        provider=SYNTHETIC_PROVIDER,
                        model=SYNTHETIC_MODEL,
                        repetition=repetition,
                        provider_seed=_seed_for(repetition),
                        slot=slot,
                        baseline_label=label,
                    )
                )
    return tuple(positions)


def _synthetic_draft(**overrides: Any) -> RegistrationDraft:
    """A synthetic Stage-A draft over invented identifiers only."""

    arguments: dict[str, Any] = {
        "design_id": SYNTHETIC_DESIGN_ID,
        "created_at": SYNTHETIC_CREATED_AT,
        "proposed_tasks": SYNTHETIC_TASKS,
        "proposed_strata": _synthetic_strata(),
        "proposed_repetitions": _synthetic_repetitions(),
        "proposed_provider_seeds": _synthetic_provider_seeds(),
        "proposed_positions": _synthetic_positions(),
        "proposed_runtime_configuration": _synthetic_runtime(),
        "proposed_randomization_mc_samples": None,
    }
    arguments.update(overrides)
    return draft_registration(**arguments)


def _multi_stratum_draft(**overrides: Any) -> RegistrationDraft:
    """A synthetic two-stratum draft with an exact one-to-one runtime cover."""

    strata = _multi_strata()
    arguments: dict[str, Any] = {
        "design_id": SYNTHETIC_DESIGN_ID,
        "created_at": SYNTHETIC_CREATED_AT,
        "proposed_tasks": SYNTHETIC_TASKS,
        "proposed_strata": strata,
        "proposed_repetitions": _repetitions_over(strata),
        "proposed_provider_seeds": _synthetic_provider_seeds(),
        "proposed_positions": _positions_over(strata),
        "proposed_runtime_configuration": _synthetic_runtime(
            snapshots=_multi_snapshots()
        ),
        "proposed_randomization_mc_samples": None,
    }
    arguments.update(overrides)
    return draft_registration(**arguments)


def _written_draft(tmp_path: Path) -> tuple[RegistrationDraft, Path]:
    draft = _synthetic_draft()
    path = write_registration_draft(draft, confirmatory_root=tmp_path)
    return draft, path


def _reseal_direct_draft(draft: RegistrationDraft) -> RegistrationDraft:
    """Give a directly constructed adversarial draft an internally valid digest."""

    return replace(
        draft,
        self_digest=compute_self_digest(draft.canonical_payload()),
    )


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


def _persist_artifact(artifact: dict[str, Any], path: Path) -> Path:
    """Persist a hand-built artifact with a freshly recomputed ``self_digest``."""

    path.write_bytes(serialize_artifact(attach_self_digest(artifact)))
    return path


# --- A: canonical serialization is insertion-order independent --------------


def test_canonical_serialization_is_insertion_order_independent() -> None:
    first = {"b": 1, "a": {"z": [1, 2], "y": "value"}}
    second = {"a": {"y": "value", "z": [1, 2]}, "b": 1}
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert compute_self_digest(first) == compute_self_digest(second)


def test_draft_digest_is_independent_of_component_construction_order() -> None:
    draft = _synthetic_draft()
    reordered_payload = dict(reversed(list(draft.canonical_payload().items())))
    assert compute_self_digest(reordered_payload) == draft.self_digest


# --- B: Unicode preserved under ensure_ascii=False --------------------------


def test_unicode_is_preserved_under_ensure_ascii_false() -> None:
    payload = {"label": "τ-σχέδιο-é中"}
    encoded = canonical_json_bytes(payload)
    assert "\\u" not in encoded.decode("utf-8")
    assert "τ-σχέδιο-é中" in encoded.decode("utf-8")


# --- C: no insignificant whitespace ----------------------------------------


def test_canonical_payload_carries_no_insignificant_whitespace() -> None:
    encoded = canonical_json_bytes(_synthetic_draft().canonical_payload())
    assert b", " not in encoded
    assert b": " not in encoded
    assert b"\n" not in encoded
    assert b"\t" not in encoded


# --- D/E: exactly one trailing LF, excluded from the digest -----------------


def test_persisted_artifact_ends_with_exactly_one_lf(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    raw = path.read_bytes()
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")
    assert raw.count(b"\n") == 1


def test_trailing_lf_is_excluded_from_self_digest(tmp_path: Path) -> None:
    draft, path = _written_draft(tmp_path)
    raw = path.read_bytes()
    body = json.loads(raw[:-1].decode("utf-8"))
    del body[SELF_DIGEST_FIELD]
    expected = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    assert expected == draft.self_digest
    assert hashlib.sha256(raw).hexdigest() != draft.self_digest


# --- F: stable round-trip preserves the digest ------------------------------


def test_round_trip_preserves_the_same_self_digest(tmp_path: Path) -> None:
    draft, path = _written_draft(tmp_path)
    loaded = load_registration_draft(path)
    assert loaded == draft
    assert loaded.self_digest == draft.self_digest
    assert serialize_artifact(loaded.to_artifact()) == path.read_bytes()


def test_reserialization_is_byte_stable(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    reloaded = load_registration_draft(path)
    again = write_registration_draft(reloaded, confirmatory_root=tmp_path / "second")
    assert again.read_bytes() == path.read_bytes()


# --- AD: the frozen reader recanonicalizes; it adds no byte-for-byte gate ---


def test_reader_recanonicalizes_semantically_equivalent_json(tmp_path: Path) -> None:
    draft = _synthetic_draft()
    pretty = json.dumps(
        draft.to_artifact(),
        indent=2,
        ensure_ascii=False,
    ).encode("utf-8") + b"\n"
    path = tmp_path / "pretty-registration-draft.json"
    path.write_bytes(pretty)
    assert load_registration_draft(path) == draft


def test_reader_accepts_key_reordered_noncanonical_input(tmp_path: Path) -> None:
    draft = _synthetic_draft()
    shuffled = dict(reversed(list(draft.to_artifact().items())))
    path = tmp_path / "reordered-registration-draft.json"
    path.write_bytes(json.dumps(shuffled, ensure_ascii=False).encode("utf-8") + b"\n")
    assert load_registration_draft(path) == draft


# --- G: digest form ---------------------------------------------------------


def test_self_digest_is_lowercase_64_char_sha256_hex() -> None:
    digest = _synthetic_draft().self_digest
    assert len(digest) == 64
    assert digest == digest.lower()
    assert set(digest) <= set("0123456789abcdef")


# --- H: no same-object digest alias ----------------------------------------


def test_registration_draft_stores_no_same_object_digest_alias(tmp_path: Path) -> None:
    draft, path = _written_draft(tmp_path)
    artifact = draft.to_artifact()
    persisted = json.loads(path.read_bytes()[:-1].decode("utf-8"))
    for obj in (artifact, persisted):
        assert SELF_DIGEST_FIELD in obj
        assert "registration_draft_digest" not in obj
        digest_fields = [key for key in obj if key.endswith("_digest")]
        assert digest_fields == [SELF_DIGEST_FIELD]


def test_draft_carrying_a_digest_alias_field_is_rejected(tmp_path: Path) -> None:
    artifact = _synthetic_draft().to_artifact()
    artifact["registration_draft_digest"] = artifact[SELF_DIGEST_FIELD]
    target = _persist_artifact(artifact, tmp_path / "aliased.json")
    with pytest.raises(ConfirmatoryRegistrationError, match="unexpected keys"):
        load_registration_draft(target)


# --- I/J/K/L: digest verification fails closed ------------------------------


def test_content_mutation_without_digest_update_is_rejected(tmp_path: Path) -> None:
    draft = _synthetic_draft()
    artifact = draft.to_artifact()
    artifact["design_id"] = "synthetic-design-001"
    target = tmp_path / "mutated.json"
    target.write_bytes(canonical_json_bytes(artifact) + b"\n")
    with pytest.raises(ConfirmatoryRegistrationError, match="mismatch"):
        load_registration_draft(target)


def test_self_digest_mutation_is_rejected(tmp_path: Path) -> None:
    draft = _synthetic_draft()
    artifact = draft.to_artifact()
    flipped = "1" if draft.self_digest[0] == "0" else "0"
    artifact[SELF_DIGEST_FIELD] = flipped + draft.self_digest[1:]
    target = tmp_path / "redigested.json"
    target.write_bytes(canonical_json_bytes(artifact) + b"\n")
    with pytest.raises(ConfirmatoryRegistrationError, match="mismatch"):
        load_registration_draft(target)


def test_missing_self_digest_is_rejected() -> None:
    artifact = _synthetic_draft().canonical_payload()
    with pytest.raises(ConfirmatoryRegistrationError, match="missing"):
        verify_self_digest(artifact)
    with pytest.raises(ConfirmatoryRegistrationError, match="missing"):
        parse_artifact(canonical_json_bytes(artifact) + b"\n")


@pytest.mark.parametrize(
    "claimed",
    [
        "",
        "abc",
        "0" * 63,
        "0" * 65,
        "A" * 64,
        "g" * 64,
        1234,
        None,
    ],
)
def test_invalid_self_digest_syntax_is_rejected(claimed: object) -> None:
    artifact = _synthetic_draft().canonical_payload()
    artifact[SELF_DIGEST_FIELD] = claimed
    with pytest.raises(ConfirmatoryRegistrationError):
        verify_self_digest(artifact)


def test_uppercase_self_digest_is_rejected() -> None:
    draft = _synthetic_draft()
    artifact = draft.to_artifact()
    artifact[SELF_DIGEST_FIELD] = draft.self_digest.upper()
    with pytest.raises(ConfirmatoryRegistrationError, match="lowercase"):
        verify_self_digest(artifact)


def test_serialize_refuses_a_draft_whose_digest_no_longer_matches() -> None:
    artifact = _synthetic_draft().to_artifact()
    artifact["created_at"] = "2026-02-02T00:00:00Z"
    with pytest.raises(ConfirmatoryRegistrationError, match="mismatch"):
        serialize_artifact(artifact)


# --- M: NaN / Infinity rejected --------------------------------------------


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_floats_are_rejected(value: float) -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="not canonically"):
        canonical_json_bytes({"value": value})
    with pytest.raises(ConfirmatoryRegistrationError, match="not canonically"):
        canonical_json_bytes({"nested": [{"value": value}]})


def test_non_string_object_keys_are_rejected() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="keys must be strings"):
        canonical_json_bytes({1: "value"})


# --- N: registered array order is preserved --------------------------------


def test_registered_array_order_is_preserved(tmp_path: Path) -> None:
    draft, path = _written_draft(tmp_path)
    persisted = json.loads(path.read_bytes()[:-1].decode("utf-8"))
    assert persisted["proposed_tasks"] == list(SYNTHETIC_TASKS)
    assert [
        (item["task_id"], item["repetition"], item["slot"])
        for item in persisted["proposed_positions"]
    ] == [
        (position.task_id, position.repetition, position.slot)
        for position in draft.proposed_positions
    ]
    assert [item["repetition"] for item in persisted["proposed_provider_seeds"]] == [
        0,
        1,
    ]
    assert persisted["proposed_statistical_configuration"][
        "secondary_endpoint_sequence"
    ] == list(SECONDARY_ENDPOINT_SEQUENCE)
    loaded = load_registration_draft(path)
    assert loaded.proposed_tasks == draft.proposed_tasks
    assert loaded.proposed_positions == draft.proposed_positions


def test_a_different_valid_matrix_changes_the_digest() -> None:
    baseline = _synthetic_draft()
    larger = _synthetic_draft(
        proposed_repetitions=_synthetic_repetitions(count=3),
        proposed_provider_seeds=_synthetic_provider_seeds(count=3),
        proposed_positions=_synthetic_positions(count=3),
    )
    assert larger.self_digest != baseline.self_digest


# --- O: existing artifact cannot be overwritten -----------------------------


def test_existing_registration_draft_cannot_be_overwritten(tmp_path: Path) -> None:
    draft, path = _written_draft(tmp_path)
    original = path.read_bytes()
    with pytest.raises(ConfirmatoryRegistrationError, match="immutable"):
        write_registration_draft(draft, confirmatory_root=tmp_path)
    assert path.read_bytes() == original


def test_overwrite_refusal_also_covers_a_different_draft(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    original = path.read_bytes()
    superseding = _synthetic_draft(
        created_at=datetime(2026, 3, 3, 0, 0, 0, tzinfo=UTC)
    )
    with pytest.raises(ConfirmatoryRegistrationError, match="immutable"):
        write_registration_draft(superseding, confirmatory_root=tmp_path)
    assert path.read_bytes() == original


def test_a_new_design_id_gets_its_own_artifact(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    successor = _synthetic_draft(design_id="synthetic-design-001")
    successor_path = write_registration_draft(successor, confirmatory_root=tmp_path)
    assert successor_path != path
    assert successor_path.parent.name == "synthetic-design-001"
    assert path.exists()


# --- AA/AB: direct construction cannot poison immutable storage -------------


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("schema_version", "WrongRegistrationDraftV1"),
        ("registration_state", "FINAL_REGISTRATION_FROZEN"),
        ("confirmatory_profile", "foreign_confirmatory_profile"),
    ],
)
def test_digest_valid_direct_literal_bypass_cannot_create_a_file(
    field_name: str, invalid_value: str, tmp_path: Path
) -> None:
    draft = _forge_like(_synthetic_draft(), **{field_name: invalid_value})
    invalid = _reseal_direct_draft(draft)
    root = tmp_path / "direct-literal-bypass"
    with pytest.raises(ConfirmatoryRegistrationError):
        write_registration_draft(invalid, confirmatory_root=root)
    assert not root.exists()


def test_digest_valid_direct_membership_bypass_cannot_create_a_file(
    tmp_path: Path,
) -> None:
    draft = replace(_synthetic_draft(), proposed_tasks=("different-task",))
    invalid = _reseal_direct_draft(draft)
    root = tmp_path / "direct-membership-bypass"
    with pytest.raises(ConfirmatoryRegistrationError, match="exactly once"):
        write_registration_draft(invalid, confirmatory_root=root)
    assert not root.exists()


def test_digest_valid_direct_runtime_bypass_cannot_create_a_file(
    tmp_path: Path,
) -> None:
    """A forged snapshot whose content contradicts its identity digest fails first."""

    forged_snapshot = _forge_like(
        _synthetic_snapshot(), endpoint="https://synthetic.invalid/forged"
    )
    invalid_runtime = _forge_like(
        _synthetic_runtime(),
        registration_expected_runtime_snapshots=(forged_snapshot,),
    )
    invalid = _reseal_direct_draft(
        replace(_synthetic_draft(), proposed_runtime_configuration=invalid_runtime)
    )
    root = tmp_path / "direct-runtime-bypass"
    with pytest.raises(
        ConfirmatoryRegistrationError, match="runtime_identity_digest"
    ):
        write_registration_draft(invalid, confirmatory_root=root)
    assert not root.exists()


@pytest.mark.parametrize(("field_name", "invalid_value"), STAMPED_STATISTICAL_CONSTANTS)
def test_digest_valid_direct_statistical_bypass_cannot_create_a_file(
    field_name: str, invalid_value: Any, tmp_path: Path
) -> None:
    forged = _forge_like(ProposedStatisticalConfigurationV1(), **{field_name: invalid_value})
    invalid = _reseal_direct_draft(
        replace(_synthetic_draft(), proposed_statistical_configuration=forged)
    )
    root = tmp_path / "direct-statistical-bypass"
    with pytest.raises(ConfirmatoryRegistrationError, match=field_name):
        write_registration_draft(invalid, confirmatory_root=root)
    assert not root.exists()


def test_digest_valid_direct_position_bypass_cannot_create_a_file(
    tmp_path: Path,
) -> None:
    positions = _synthetic_positions()
    forged = _forge_like(positions[0], baseline_label="partial")
    invalid = _reseal_direct_draft(
        replace(_synthetic_draft(), proposed_positions=(forged,) + positions[1:])
    )
    root = tmp_path / "direct-position-bypass"
    with pytest.raises(ConfirmatoryRegistrationError, match="baseline_label"):
        write_registration_draft(invalid, confirmatory_root=root)
    assert not root.exists()


def test_digest_valid_direct_repetitions_bypass_cannot_create_a_file(
    tmp_path: Path,
) -> None:
    entries = _synthetic_repetitions()
    forged = _forge_like(entries[0], repetition_count=0)
    invalid = _reseal_direct_draft(
        replace(_synthetic_draft(), proposed_repetitions=(forged,) + entries[1:])
    )
    root = tmp_path / "direct-repetitions-bypass"
    with pytest.raises(
        ConfirmatoryRegistrationError, match="repetition_count must be >= 1"
    ):
        write_registration_draft(invalid, confirmatory_root=root)
    assert not root.exists()


def test_digest_valid_direct_provider_seed_bypass_cannot_create_a_file(
    tmp_path: Path,
) -> None:
    entries = _synthetic_provider_seeds()
    forged = _forge_like(entries[0], provider_seed=999)
    invalid = _reseal_direct_draft(
        replace(_synthetic_draft(), proposed_provider_seeds=(forged,) + entries[1:])
    )
    root = tmp_path / "direct-seed-bypass"
    with pytest.raises(
        ConfirmatoryRegistrationError, match="does not match the proposed seed"
    ):
        write_registration_draft(invalid, confirmatory_root=root)
    assert not root.exists()


def test_digest_valid_direct_stratum_bypass_cannot_create_a_file(
    tmp_path: Path,
) -> None:
    forged = _forge_like(_synthetic_strata()[0], provider="")
    invalid = _reseal_direct_draft(
        replace(_synthetic_draft(), proposed_strata=(forged,))
    )
    root = tmp_path / "direct-stratum-bypass"
    with pytest.raises(ConfirmatoryRegistrationError):
        write_registration_draft(invalid, confirmatory_root=root)
    assert not root.exists()


# --- P: malformed JSON rejected --------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"{",
        b"not json at all\n",
        b'{"self_digest": }\n',
        b"[]\n",
        b'"a string"\n',
    ],
)
def test_malformed_artifact_bytes_are_rejected(payload: bytes, tmp_path: Path) -> None:
    target = tmp_path / "malformed.json"
    target.write_bytes(payload)
    with pytest.raises(ConfirmatoryRegistrationError):
        load_registration_draft(target)


def test_non_utf8_artifact_bytes_are_rejected(tmp_path: Path) -> None:
    target = tmp_path / "binary.json"
    target.write_bytes(b"\xff\xfe\x00\n")
    with pytest.raises(ConfirmatoryRegistrationError, match="UTF-8"):
        load_registration_draft(target)


def test_missing_draft_key_is_rejected(tmp_path: Path) -> None:
    artifact = _synthetic_draft().canonical_payload()
    del artifact["proposed_tasks"]
    target = _persist_artifact(artifact, tmp_path / "incomplete.json")
    with pytest.raises(ConfirmatoryRegistrationError, match="missing keys"):
        load_registration_draft(target)


# --- A: exact RegistrationDraftV1 top-level key set -------------------------


def test_registration_draft_top_level_key_set_is_exact(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    persisted = json.loads(path.read_bytes()[:-1].decode("utf-8"))
    assert set(persisted) == {
        "schema_version",
        "registration_state",
        "confirmatory_profile",
        "design_id",
        "created_at",
        "proposed_tasks",
        "proposed_strata",
        "proposed_repetitions",
        "proposed_provider_seeds",
        "proposed_positions",
        "proposed_runtime_configuration",
        "proposed_statistical_configuration",
        SELF_DIGEST_FIELD,
    }
    assert len(persisted) == 13


def test_extra_top_level_key_is_rejected(tmp_path: Path) -> None:
    artifact = _synthetic_draft().to_artifact()
    artifact["proposed_extra"] = "anything"
    target = _persist_artifact(artifact, tmp_path / "extra-key.json")
    with pytest.raises(ConfirmatoryRegistrationError, match="unexpected keys"):
        load_registration_draft(target)


def test_frozen_top_level_literals_are_stamped() -> None:
    draft = _synthetic_draft()
    assert draft.schema_version == REGISTRATION_DRAFT_SCHEMA_VERSION == (
        "RegistrationDraftV1"
    )
    assert draft.registration_state == REGISTRATION_STATE_DRAFT == "REGISTRATION_DRAFT"
    assert draft.confirmatory_profile == CONFIRMATORY_PROFILE == (
        "post_phaseP_confirmatory_randomization_v1"
    )


# --- B: created_at exact required format ------------------------------------


def test_created_at_uses_the_frozen_rfc3339_utc_form(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    persisted = json.loads(path.read_bytes()[:-1].decode("utf-8"))
    assert persisted["created_at"] == SYNTHETIC_CREATED_AT_TEXT
    assert persisted["created_at"].endswith("Z")
    assert "+" not in persisted["created_at"]
    assert "." not in persisted["created_at"]


def test_naive_created_at_is_rejected() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="timezone-aware"):
        _synthetic_draft(created_at=datetime(2026, 1, 1, 0, 0, 0))


def test_non_utc_created_at_offset_is_rejected() -> None:
    shifted = datetime(
        2026, 1, 1, 0, 0, 0, tzinfo=timezone(timedelta(hours=5))
    )
    with pytest.raises(ConfirmatoryRegistrationError, match="zero offset"):
        _synthetic_draft(created_at=shifted)


def test_fractional_second_created_at_is_rejected() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="whole-second"):
        _synthetic_draft(
            created_at=datetime(2026, 1, 1, 0, 0, 0, 123456, tzinfo=UTC)
        )


@pytest.mark.parametrize(
    "created_at",
    [
        "2026-01-01T00:00:00+00:00",
        "2026-01-01T00:00:00.500Z",
        "2026-01-01 00:00:00Z",
        "2026-01-01T00:00:00",
        "20260101T000000Z",
        "2026-13-01T00:00:00Z",
        "2026-01-32T00:00:00Z",
        "not-a-timestamp",
    ],
)
def test_persisted_created_at_outside_the_frozen_form_is_rejected(
    created_at: str, tmp_path: Path
) -> None:
    artifact = _synthetic_draft().canonical_payload()
    artifact["created_at"] = created_at
    target = _persist_artifact(artifact, tmp_path / "created-at.json")
    with pytest.raises(ConfirmatoryRegistrationError, match="created_at"):
        load_registration_draft(target)


# --- C: ProposedStratumV1 exact keys ----------------------------------------


def test_proposed_stratum_has_exactly_two_keys(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    persisted = json.loads(path.read_bytes()[:-1].decode("utf-8"))
    for stratum in persisted["proposed_strata"]:
        assert set(stratum) == {"provider", "model"}


def test_stratum_with_an_extra_key_is_rejected(tmp_path: Path) -> None:
    artifact = _synthetic_draft().canonical_payload()
    artifact["proposed_strata"][0]["endpoint"] = "https://synthetic.invalid/v1"
    target = _persist_artifact(artifact, tmp_path / "stratum-extra.json")
    with pytest.raises(ConfirmatoryRegistrationError, match="unexpected keys"):
        load_registration_draft(target)


# --- D/E: ProposedRepetitionsEntryV1 keys, cross product, count -------------


def test_proposed_repetitions_entry_has_exactly_four_keys(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    persisted = json.loads(path.read_bytes()[:-1].decode("utf-8"))
    for entry in persisted["proposed_repetitions"]:
        assert set(entry) == {"task_id", "provider", "model", "repetition_count"}


def test_proposed_repetitions_covers_the_full_cross_product() -> None:
    draft = _synthetic_draft()
    assert [entry.cell for entry in draft.proposed_repetitions] == [
        (task_id, SYNTHETIC_PROVIDER, SYNTHETIC_MODEL) for task_id in SYNTHETIC_TASKS
    ]


def test_missing_cross_product_cell_is_rejected() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="exactly once"):
        _synthetic_draft(
            proposed_repetitions=_synthetic_repetitions(tasks=(SYNTHETIC_TASKS[0],))
        )


def test_extra_cross_product_cell_is_rejected() -> None:
    extra = ProposedRepetitionsEntryV1(
        task_id="synthetic-task-c",
        provider=SYNTHETIC_PROVIDER,
        model=SYNTHETIC_MODEL,
        repetition_count=SYNTHETIC_REPETITION_COUNT,
    )
    with pytest.raises(ConfirmatoryRegistrationError, match="exactly once"):
        _synthetic_draft(proposed_repetitions=_synthetic_repetitions() + (extra,))


def test_duplicate_cross_product_cell_is_rejected() -> None:
    entries = _synthetic_repetitions()
    with pytest.raises(ConfirmatoryRegistrationError, match="duplicate"):
        _synthetic_draft(proposed_repetitions=entries + (entries[0],))


@pytest.mark.parametrize("count", [0, -1, True, 1.0, "2"])
def test_invalid_repetition_count_is_rejected(count: Any) -> None:
    with pytest.raises(ConfirmatoryRegistrationError):
        ProposedRepetitionsEntryV1(
            task_id=SYNTHETIC_TASKS[0],
            provider=SYNTHETIC_PROVIDER,
            model=SYNTHETIC_MODEL,
            repetition_count=count,
        )


def test_repetition_count_bool_is_not_an_integer() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="JSON integer"):
        ProposedRepetitionsEntryV1(
            task_id=SYNTHETIC_TASKS[0],
            provider=SYNTHETIC_PROVIDER,
            model=SYNTHETIC_MODEL,
            repetition_count=True,
        )


# --- F/G/H: ProposedProviderSeedEntryV1 keys, coverage, agreement -----------


def test_proposed_provider_seed_entry_has_exactly_two_keys(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    persisted = json.loads(path.read_bytes()[:-1].decode("utf-8"))
    for entry in persisted["proposed_provider_seeds"]:
        assert set(entry) == {"repetition", "provider_seed"}


def test_provider_seeds_cover_exactly_the_used_repetition_indexes() -> None:
    draft = _synthetic_draft()
    assert [entry.repetition for entry in draft.proposed_provider_seeds] == [0, 1]
    assert sorted({p.repetition for p in draft.proposed_positions}) == [0, 1]


def test_missing_provider_seed_entry_is_rejected() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="exactly once"):
        _synthetic_draft(proposed_provider_seeds=_synthetic_provider_seeds(count=1))


def test_extra_provider_seed_entry_is_rejected() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="exactly once"):
        _synthetic_draft(proposed_provider_seeds=_synthetic_provider_seeds(count=3))


def test_position_seed_disagreeing_with_the_seed_table_is_rejected() -> None:
    positions = list(_synthetic_positions())
    positions[0] = replace(positions[0], provider_seed=_seed_for(0) + 500)
    with pytest.raises(
        ConfirmatoryRegistrationError, match="does not match the proposed seed"
    ):
        _synthetic_draft(proposed_positions=tuple(positions))


def test_provider_seed_bool_is_not_an_integer() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="JSON integer"):
        ProposedProviderSeedEntryV1(repetition=0, provider_seed=True)


# --- I/J/K/L/N: ProposedPositionV1 record versus identity payload -----------


def test_proposed_position_has_exactly_seven_keys(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    persisted = json.loads(path.read_bytes()[:-1].decode("utf-8"))
    for position in persisted["proposed_positions"]:
        assert set(position) == {
            "task_id",
            "provider",
            "model",
            "repetition",
            "provider_seed",
            "slot",
            "baseline_label",
        }


def test_no_position_id_anywhere_in_the_draft(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    raw = path.read_bytes().decode("utf-8")
    assert "position_id" not in raw
    persisted = json.loads(raw[:-1])
    assert "position_id" not in persisted
    for position in persisted["proposed_positions"]:
        assert "position_id" not in position


def test_baseline_label_is_not_part_of_the_identity_payload() -> None:
    position = _synthetic_draft().proposed_positions[0]
    payload = position.identity_payload()
    assert set(payload) == {
        "task_id",
        "provider",
        "model",
        "repetition",
        "provider_seed",
        "slot",
    }
    assert "baseline_label" not in payload
    assert len(position.identity) == 6
    assert position.baseline_label not in position.identity


def test_two_positions_differing_only_in_label_share_an_identity_payload() -> None:
    off = ProposedPositionV1(
        task_id=SYNTHETIC_TASKS[0],
        provider=SYNTHETIC_PROVIDER,
        model=SYNTHETIC_MODEL,
        repetition=0,
        provider_seed=_seed_for(0),
        slot=1,
        baseline_label=BASELINE_LABEL_OFF,
    )
    full = replace(off, baseline_label=BASELINE_LABEL_FULL)
    assert off.identity_payload() == full.identity_payload()
    assert off.identity == full.identity


@pytest.mark.parametrize(
    "label", ["partial", "ablation", "OFF", "Full", "", "none", "off "]
)
def test_baseline_label_outside_the_frozen_vocabulary_is_rejected(label: str) -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="baseline_label"):
        ProposedPositionV1(
            task_id=SYNTHETIC_TASKS[0],
            provider=SYNTHETIC_PROVIDER,
            model=SYNTHETIC_MODEL,
            repetition=0,
            provider_seed=_seed_for(0),
            slot=1,
            baseline_label=label,
        )


def test_baseline_label_vocabulary_is_the_existing_qamode_serialization() -> None:
    assert BASELINE_LABEL_OFF == "off"
    assert BASELINE_LABEL_FULL == "full"
    assert BASELINE_LABELS == ("off", "full")


@pytest.mark.parametrize("slot", [0, 3, -1, True, 1.0, "1"])
def test_slot_outside_one_and_two_is_rejected(slot: Any) -> None:
    with pytest.raises(ConfirmatoryRegistrationError):
        ProposedPositionV1(
            task_id=SYNTHETIC_TASKS[0],
            provider=SYNTHETIC_PROVIDER,
            model=SYNTHETIC_MODEL,
            repetition=0,
            provider_seed=_seed_for(0),
            slot=slot,
            baseline_label=BASELINE_LABEL_OFF,
        )


def test_slots_are_exactly_one_and_two_in_every_group() -> None:
    draft = _synthetic_draft()
    slots_by_group: dict[tuple[str, str, str, int], list[int]] = {}
    for position in draft.proposed_positions:
        slots_by_group.setdefault(position.group, []).append(position.slot)
    assert slots_by_group
    for slots in slots_by_group.values():
        assert sorted(slots) == [1, 2]


# --- M/O/P: matched-contrast group structure and baseline balance -----------


def test_every_group_has_exactly_two_positions() -> None:
    draft = _synthetic_draft()
    counts: dict[tuple[str, str, str, int], int] = {}
    for position in draft.proposed_positions:
        counts[position.group] = counts.get(position.group, 0) + 1
    assert set(counts.values()) == {2}
    assert len(counts) == len(SYNTHETIC_TASKS) * SYNTHETIC_REPETITION_COUNT


def test_every_group_carries_one_off_and_one_full() -> None:
    draft = _synthetic_draft()
    labels: dict[tuple[str, str, str, int], list[str]] = {}
    for position in draft.proposed_positions:
        labels.setdefault(position.group, []).append(position.baseline_label)
    for group_labels in labels.values():
        assert sorted(group_labels) == ["full", "off"]


def test_group_with_two_identical_labels_is_rejected() -> None:
    positions = list(_synthetic_positions())
    positions[1] = replace(positions[1], baseline_label=BASELINE_LABEL_OFF)
    with pytest.raises(
        ConfirmatoryRegistrationError, match="exactly one 'off' and one 'full'"
    ):
        _synthetic_draft(proposed_positions=tuple(positions))


def test_missing_position_from_a_group_is_rejected() -> None:
    positions = _synthetic_positions()
    with pytest.raises(ConfirmatoryRegistrationError, match="exactly once"):
        _synthetic_draft(proposed_positions=positions[1:])


def test_duplicate_position_placement_is_rejected() -> None:
    positions = _synthetic_positions()
    with pytest.raises(ConfirmatoryRegistrationError, match="duplicate"):
        _synthetic_draft(proposed_positions=positions + (positions[0],))


def test_extra_unregistered_position_group_is_rejected() -> None:
    stray = ProposedPositionV1(
        task_id="synthetic-task-unregistered",
        provider=SYNTHETIC_PROVIDER,
        model=SYNTHETIC_MODEL,
        repetition=0,
        provider_seed=_seed_for(0),
        slot=1,
        baseline_label=BASELINE_LABEL_OFF,
    )
    with pytest.raises(ConfirmatoryRegistrationError, match="exactly once"):
        _synthetic_draft(proposed_positions=_synthetic_positions() + (stray,))


def test_repetition_count_must_match_the_position_set() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="exactly once"):
        _synthetic_draft(proposed_repetitions=_synthetic_repetitions(count=3))


# --- Q/R/S/T: ordering and uniqueness of every registered array -------------


def test_unsorted_proposed_tasks_are_rejected() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="sorted ascending"):
        _synthetic_draft(proposed_tasks=tuple(reversed(SYNTHETIC_TASKS)))


def test_duplicate_proposed_task_is_rejected() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="duplicates"):
        _synthetic_draft(proposed_tasks=(SYNTHETIC_TASKS[0], SYNTHETIC_TASKS[0]))


def test_empty_proposed_tasks_are_rejected() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="must not be empty"):
        _synthetic_draft(proposed_tasks=())


def test_unsorted_proposed_strata_are_rejected() -> None:
    strata = (
        ProposedStratumV1(provider="synthetic-provider-b", model=SYNTHETIC_MODEL),
        ProposedStratumV1(provider="synthetic-provider-a", model=SYNTHETIC_MODEL),
    )
    with pytest.raises(ConfirmatoryRegistrationError, match="sorted ascending"):
        _synthetic_draft(proposed_strata=strata)


def test_duplicate_proposed_stratum_is_rejected() -> None:
    stratum = _synthetic_strata()[0]
    with pytest.raises(ConfirmatoryRegistrationError, match="duplicates"):
        _synthetic_draft(proposed_strata=(stratum, stratum))


def test_empty_proposed_strata_are_rejected() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="must not be empty"):
        _synthetic_draft(proposed_strata=())


def test_unsorted_proposed_repetitions_are_rejected() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="sorted ascending"):
        _synthetic_draft(
            proposed_repetitions=tuple(reversed(_synthetic_repetitions()))
        )


def test_unsorted_proposed_provider_seeds_are_rejected() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="sorted ascending"):
        _synthetic_draft(
            proposed_provider_seeds=tuple(reversed(_synthetic_provider_seeds()))
        )


def test_unsorted_proposed_positions_are_rejected() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="sorted ascending"):
        _synthetic_draft(proposed_positions=tuple(reversed(_synthetic_positions())))


def test_load_does_not_silently_sort_a_persisted_array(tmp_path: Path) -> None:
    artifact = _synthetic_draft().canonical_payload()
    artifact["proposed_tasks"] = list(reversed(SYNTHETIC_TASKS))
    target = _persist_artifact(artifact, tmp_path / "unsorted-tasks.json")
    with pytest.raises(ConfirmatoryRegistrationError, match="sorted ascending"):
        load_registration_draft(target)


# --- U/V/W/X/Y/Z: ProposedStatisticalConfigurationV1 ------------------------


def test_statistical_configuration_key_set_is_exactly_eleven(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    persisted = json.loads(path.read_bytes()[:-1].decode("utf-8"))
    statistical = persisted["proposed_statistical_configuration"]
    assert set(statistical) == {
        "schema_version",
        "statistic_spec_id",
        "randomization_mc_samples",
        "alpha",
        "multiplicity_architecture",
        "primary_endpoint",
        "secondary_endpoint_sequence",
        "primary_estimand_architecture",
        "aggregation_rule",
        "treatment_contrast_orientation",
        "randomization_exact_enumeration_max_k",
    }
    assert len(statistical) == 11


def test_every_stamped_statistical_constant_is_recorded(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    statistical = json.loads(path.read_bytes()[:-1].decode("utf-8"))[
        "proposed_statistical_configuration"
    ]
    assert statistical["schema_version"] == (
        PROPOSED_STATISTICAL_CONFIGURATION_SCHEMA_VERSION
    ) == "ProposedStatisticalConfigurationV1"
    assert statistical["statistic_spec_id"] == STATISTIC_SPEC_ID == (
        "confirmatory_task_sign_flip_v1"
    )
    assert statistical["alpha"] == ALPHA == "0.05"
    assert statistical["multiplicity_architecture"] == MULTIPLICITY_ARCHITECTURE == (
        "FIXED_SEQUENCE_GATEKEEPING"
    )
    assert statistical["primary_endpoint"] == PRIMARY_ENDPOINT == (
        "unsafe_action_executed"
    )
    assert statistical["secondary_endpoint_sequence"] == [
        "safety_security_violation",
        "unsafe_action_proposed",
        "constraint_violation",
        "privacy_leak",
        "attack_success",
    ]
    assert statistical["primary_estimand_architecture"] == (
        PRIMARY_ESTIMAND_ARCHITECTURE
    ) == "SCHEDULED_ATTEMPT_PRIMARY_WITH_MECHANISM_SECONDARIES"
    assert statistical["aggregation_rule"] == AGGREGATION_RULE == (
        "NESTED_EQUAL_WEIGHT_FIXED_PRE_RUN"
    )
    assert statistical["treatment_contrast_orientation"] == (
        TREATMENT_CONTRAST_ORIENTATION
    ) == "FULL_MINUS_OFF"
    assert statistical["randomization_exact_enumeration_max_k"] == (
        RANDOMIZATION_EXACT_ENUMERATION_MAX_K
    ) == 16


def test_alpha_is_a_canonical_decimal_string_not_a_float(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    raw = path.read_bytes().decode("utf-8")
    assert '"alpha":"0.05"' in raw


def test_max_k_is_a_json_integer_not_a_string(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    statistical = json.loads(path.read_bytes()[:-1].decode("utf-8"))[
        "proposed_statistical_configuration"
    ]
    value = statistical["randomization_exact_enumeration_max_k"]
    assert isinstance(value, int) and not isinstance(value, bool)


@pytest.mark.parametrize(("field_name", "invalid_value"), STAMPED_STATISTICAL_CONSTANTS)
def test_tampered_stamped_statistical_constant_is_rejected(
    field_name: str, invalid_value: Any, tmp_path: Path
) -> None:
    artifact = _synthetic_draft().canonical_payload()
    artifact["proposed_statistical_configuration"][field_name] = invalid_value
    target = _persist_artifact(artifact, tmp_path / f"statistical-{field_name}.json")
    with pytest.raises(ConfirmatoryRegistrationError, match=field_name):
        load_registration_draft(target)


def test_stamped_statistical_constants_are_not_caller_selectable() -> None:
    with pytest.raises(TypeError):
        ProposedStatisticalConfigurationV1(alpha="0.10")  # type: ignore[call-arg]


def test_reordered_secondary_endpoint_sequence_is_rejected(tmp_path: Path) -> None:
    artifact = _synthetic_draft().canonical_payload()
    artifact["proposed_statistical_configuration"]["secondary_endpoint_sequence"] = (
        sorted(SECONDARY_ENDPOINT_SEQUENCE)
    )
    target = _persist_artifact(artifact, tmp_path / "reordered-sequence.json")
    with pytest.raises(
        ConfirmatoryRegistrationError, match="secondary_endpoint_sequence"
    ):
        load_registration_draft(target)


def test_randomization_mc_samples_null_is_accepted(tmp_path: Path) -> None:
    draft = _synthetic_draft(proposed_randomization_mc_samples=None)
    assert draft.proposed_statistical_configuration.randomization_mc_samples is None
    path = write_registration_draft(draft, confirmatory_root=tmp_path)
    persisted = json.loads(path.read_bytes()[:-1].decode("utf-8"))
    statistical = persisted["proposed_statistical_configuration"]
    assert "randomization_mc_samples" in statistical
    assert statistical["randomization_mc_samples"] is None
    assert load_registration_draft(path) == draft


@pytest.mark.parametrize("samples", [1, 2, 9999, 100000])
def test_positive_randomization_mc_samples_is_accepted(
    samples: int, tmp_path: Path
) -> None:
    draft = _synthetic_draft(proposed_randomization_mc_samples=samples)
    assert draft.proposed_statistical_configuration.randomization_mc_samples == samples
    path = write_registration_draft(draft, confirmatory_root=tmp_path)
    assert load_registration_draft(path) == draft


@pytest.mark.parametrize("samples", [0, -1, True, False, 1.0, 100.5, "100", []])
def test_invalid_randomization_mc_samples_is_rejected(samples: Any) -> None:
    with pytest.raises(ConfirmatoryRegistrationError):
        ProposedStatisticalConfigurationV1(randomization_mc_samples=samples)


@pytest.mark.parametrize("samples", [0, -1, True, 1.0, "100"])
def test_invalid_persisted_randomization_mc_samples_is_rejected(
    samples: Any, tmp_path: Path
) -> None:
    artifact = _synthetic_draft().canonical_payload()
    artifact["proposed_statistical_configuration"]["randomization_mc_samples"] = samples
    target = _persist_artifact(artifact, tmp_path / "bad-samples.json")
    with pytest.raises(ConfirmatoryRegistrationError, match="randomization_mc_samples"):
        load_registration_draft(target)


def test_missing_randomization_mc_samples_key_is_rejected(tmp_path: Path) -> None:
    artifact = _synthetic_draft().canonical_payload()
    del artifact["proposed_statistical_configuration"]["randomization_mc_samples"]
    target = _persist_artifact(artifact, tmp_path / "absent-samples.json")
    with pytest.raises(ConfirmatoryRegistrationError, match="missing keys"):
        load_registration_draft(target)


def test_legacy_monte_carlo_samples_key_is_rejected(tmp_path: Path) -> None:
    artifact = _synthetic_draft().canonical_payload()
    statistical = artifact["proposed_statistical_configuration"]
    statistical["monte_carlo_samples"] = statistical.pop("randomization_mc_samples")
    target = _persist_artifact(artifact, tmp_path / "legacy-samples.json")
    with pytest.raises(ConfirmatoryRegistrationError, match="monte_carlo_samples"):
        load_registration_draft(target)


def test_no_legacy_monte_carlo_samples_key_is_ever_written(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    raw = path.read_bytes().decode("utf-8")
    assert '"monte_carlo_samples"' not in raw
    assert '"randomization_mc_samples"' in raw


def test_stage_a_records_no_k_or_randomization_mode(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    raw = path.read_bytes().decode("utf-8")
    assert '"randomization_mode"' not in raw
    assert '"K"' not in raw
    assert '"exact_support_size"' not in raw
    assert '"seed_hex"' not in raw


# --- Q: synthetic construction succeeds and is faithful ---------------------


def test_synthetic_draft_construction_succeeds() -> None:
    draft = _synthetic_draft()
    assert draft.schema_version == REGISTRATION_DRAFT_SCHEMA_VERSION
    assert draft.registration_state == REGISTRATION_STATE_DRAFT
    assert draft.confirmatory_profile == CONFIRMATORY_PROFILE
    assert draft.design_id == SYNTHETIC_DESIGN_ID
    assert draft.created_at == SYNTHETIC_CREATED_AT_TEXT
    assert draft.proposed_statistical_configuration.statistic_spec_id == (
        STATISTIC_SPEC_ID
    )
    assert draft.proposed_statistical_configuration.randomization_mc_samples is None
    snapshots = (
        draft.proposed_runtime_configuration.registration_expected_runtime_snapshots
    )
    assert snapshots[0].timeout_seconds == "30.5"
    assert snapshots[0].retry_policy.max_attempts == 1
    assert len(draft.proposed_positions) == 8
    verify_self_digest(draft.to_artifact())


def test_baseline_schedule_is_bound_at_stage_a(tmp_path: Path) -> None:
    """S_k is persisted and digest-authenticated the moment the draft is written."""

    draft, path = _written_draft(tmp_path)
    persisted = json.loads(path.read_bytes()[:-1].decode("utf-8"))
    schedule = {
        (
            item["task_id"],
            item["provider"],
            item["model"],
            item["repetition"],
            item["slot"],
        ): item["baseline_label"]
        for item in persisted["proposed_positions"]
    }
    assert len(schedule) == len(draft.proposed_positions)
    assert set(schedule.values()) == {BASELINE_LABEL_OFF, BASELINE_LABEL_FULL}
    assert load_registration_draft(path).proposed_positions == draft.proposed_positions


def test_no_assignment_material_is_recorded_at_stage_a(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    raw = path.read_bytes().decode("utf-8")
    for forbidden in (
        "task_assignment_bit",
        "assignment_manifest",
        "assignment_digest",
        "qa_mode",
        "bits",
        "b_k",
    ):
        assert forbidden not in raw


def test_registration_expected_runtime_snapshot_is_bound_in_full() -> None:
    draft = _synthetic_draft()
    runtime = draft.proposed_runtime_configuration
    snapshot = runtime.registration_expected_runtime_snapshots[0]
    payload = runtime.to_dict()["registration_expected_runtime_snapshots"][0]
    assert set(payload) == {
        "artifact_version",
        "captured_at",
        "endpoint",
        "environment_fingerprint",
        "experiment_config_digest",
        "model",
        "models_config_digest",
        "native_tool_adapter_version",
        "package_source_sha256",
        "prompt_digest",
        "provider_config_digest",
        "provider_name",
        "provider_parameters_digest",
        "python_version",
        "retry_policy",
        "runtime_identity_digest",
        "schema_version",
        SELF_DIGEST_FIELD,
        "timeout_seconds",
        "tool_contract_policy",
    }
    assert runtime.registration_expected_runtime_identity_digest(
        SYNTHETIC_PROVIDER, SYNTHETIC_MODEL
    ) == snapshot.runtime_identity_digest


def test_load_rejects_snapshot_content_mismatched_to_its_identity_digest(
    tmp_path: Path,
) -> None:
    artifact = _synthetic_draft().canonical_payload()
    snapshot = artifact["proposed_runtime_configuration"][
        "registration_expected_runtime_snapshots"
    ][0]
    snapshot["endpoint"] = "https://synthetic.invalid/v2"
    target = _persist_artifact(artifact, tmp_path / "runtime-mismatch.json")
    with pytest.raises(ConfirmatoryRegistrationError):
        load_registration_draft(target)


def test_draft_carries_every_proposed_group() -> None:
    payload = _synthetic_draft().canonical_payload()
    assert set(payload) == {
        "confirmatory_profile",
        "created_at",
        "design_id",
        "proposed_positions",
        "proposed_provider_seeds",
        "proposed_repetitions",
        "proposed_runtime_configuration",
        "proposed_statistical_configuration",
        "proposed_strata",
        "proposed_tasks",
        "registration_state",
        "schema_version",
    }


def test_integer_schema_fields_stay_json_integers(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    persisted = json.loads(path.read_bytes()[:-1].decode("utf-8"))
    for entry in persisted["proposed_repetitions"]:
        assert isinstance(entry["repetition_count"], int)
        assert not isinstance(entry["repetition_count"], bool)
    for entry in persisted["proposed_provider_seeds"]:
        for key in ("repetition", "provider_seed"):
            assert isinstance(entry[key], int) and not isinstance(entry[key], bool)
    for position in persisted["proposed_positions"]:
        for key in ("repetition", "provider_seed", "slot"):
            assert isinstance(position[key], int)
            assert not isinstance(position[key], bool)
    snapshot = persisted["proposed_runtime_configuration"][
        "registration_expected_runtime_snapshots"
    ][0]
    retry = snapshot["retry_policy"]
    assert isinstance(retry["max_attempts"], int)
    assert isinstance(retry["initial_delay_seconds"], str)
    assert isinstance(snapshot["timeout_seconds"], str)


# --- Construction-time fail-closed validation -------------------------------


@pytest.mark.parametrize("design_id", ["", ".", "..", "a/b", "a\\b", "a\x00b"])
def test_unsafe_design_id_is_rejected(design_id: str) -> None:
    with pytest.raises(ConfirmatoryRegistrationError):
        _synthetic_draft(design_id=design_id)


def test_boolean_is_not_accepted_where_an_integer_is_required() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="JSON integer"):
        ProposedPositionV1(
            task_id=SYNTHETIC_TASKS[0],
            provider=SYNTHETIC_PROVIDER,
            model=SYNTHETIC_MODEL,
            repetition=True,
            provider_seed=_seed_for(0),
            slot=1,
            baseline_label=BASELINE_LABEL_OFF,
        )


@pytest.mark.parametrize(
    "timeout", ["", "30.", "+30", "030", "3e1", "thirty", ".5", "30.5.1"]
)
def test_noncanonical_decimal_string_is_rejected(timeout: str) -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="canonical base-10"):
        _synthetic_snapshot(timeout_seconds=timeout)


@pytest.mark.parametrize("timeout", ["0", "30", "30.5", "0.25"])
def test_canonical_decimal_string_is_accepted(timeout: str) -> None:
    snapshot = _synthetic_snapshot(timeout_seconds=timeout)
    assert snapshot.timeout_seconds == timeout


def test_unsorted_or_duplicated_retryable_error_classes_are_rejected() -> None:
    for classes in (("SYNTHETIC_B", "SYNTHETIC_A"), ("SYNTHETIC_A", "SYNTHETIC_A")):
        with pytest.raises(ConfirmatoryRegistrationError, match="sorted and unique"):
            RetryPolicyV1(
                max_attempts=1,
                backoff_kind="NONE",
                initial_delay_seconds="0",
                max_delay_seconds="0",
                retryable_error_classes=classes,
            )


def test_unknown_backoff_kind_is_rejected() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match="backoff_kind"):
        RetryPolicyV1(
            max_attempts=1,
            backoff_kind="LINEAR",
            initial_delay_seconds="0",
            max_delay_seconds="0",
            retryable_error_classes=(),
        )


def test_zero_retry_policy_is_recorded_verbatim() -> None:
    policy = RetryPolicyV1(
        max_attempts=1,
        backoff_kind="NONE",
        initial_delay_seconds="0",
        max_delay_seconds="0",
        retryable_error_classes=(),
    )
    assert policy.to_dict()["retryable_error_classes"] == []
    assert policy.to_dict()["max_attempts"] == 1


def test_runtime_identity_digest_is_derived_from_the_complete_snapshot() -> None:
    snapshot = _synthetic_snapshot()
    expected = hashlib.sha256(
        canonical_json_bytes(snapshot.identity_payload())
    ).hexdigest()
    assert snapshot.runtime_identity_digest == expected
    assert "captured_at" not in snapshot.identity_payload()
    assert SELF_DIGEST_FIELD not in snapshot.identity_payload()


def test_runtime_identity_changes_when_an_invariant_field_changes() -> None:
    baseline = _synthetic_snapshot()
    changed = _synthetic_snapshot(endpoint="https://synthetic.invalid/v2")
    assert changed.runtime_identity_digest != baseline.runtime_identity_digest


def test_capture_metadata_alone_never_changes_runtime_identity() -> None:
    baseline = _synthetic_snapshot()
    later = _synthetic_snapshot(
        captured_at=datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC).isoformat()
    )
    assert later.runtime_identity_digest == baseline.runtime_identity_digest
    assert later.self_digest != baseline.self_digest


#: Fragments of the RC-1..RC-5 rejection messages, each naming the runtime key
#: so a test cannot pass on another array's cover, ordering, or emptiness error.
RUNTIME_COVER_ERROR = "registration_expected_runtime_snapshots must cover"
RUNTIME_EMPTY_ERROR = "registration_expected_runtime_snapshots must not be empty"
RUNTIME_DUPLICATE_ERROR = (
    "registration_expected_runtime_snapshots must not contain duplicates"
)
RUNTIME_UNSORTED_ERROR = (
    "registration_expected_runtime_snapshots must be sorted ascending"
)


# --- Runtime cardinality: one snapshot per proposed stratum (§12.3 RC-1..RC-5)
#
# The two superseded tests here — a configuration-level ``timeout_seconds`` and
# ``retry_policy`` having to agree with the one bound snapshot — are retired
# because the scalars they varied no longer exist (§12.4).  Their coverage is
# replaced below by per-snapshot presence/schema assertions plus the load-time
# refusal of either outer key, which is where that invariant now lives.


def test_timeout_seconds_is_present_and_canonical_in_every_runtime_snapshot() -> None:
    """Replaces the retired configuration-level timeout equality check."""

    runtime = _multi_stratum_draft().proposed_runtime_configuration
    snapshots = runtime.registration_expected_runtime_snapshots
    assert len(snapshots) == 2
    for snapshot in snapshots:
        # Present on every element, and persisted as a string, never a float.
        assert isinstance(snapshot.to_dict()["timeout_seconds"], str)
        assert snapshot.to_dict()["timeout_seconds"] == snapshot.timeout_seconds
        assert snapshot.timeout_seconds
    # Still validated as a canonical decimal on every element.
    with pytest.raises(ConfirmatoryRegistrationError, match="timeout_seconds"):
        _synthetic_snapshot(timeout_seconds="030.5")
    with pytest.raises(ConfirmatoryRegistrationError, match="timeout_seconds"):
        _synthetic_snapshot_b(timeout_seconds="")
    # No global equality constraint: the strata carry different timeouts.
    assert snapshots[0].timeout_seconds != snapshots[1].timeout_seconds


def test_retry_policy_is_present_and_schema_valid_in_every_runtime_snapshot() -> None:
    """Replaces the retired configuration-level retry-policy equality check."""

    runtime = _multi_stratum_draft().proposed_runtime_configuration
    snapshots = runtime.registration_expected_runtime_snapshots
    for snapshot in snapshots:
        assert isinstance(snapshot.retry_policy, RetryPolicyV1)
        assert set(snapshot.to_dict()["retry_policy"]) == {
            "backoff_kind",
            "initial_delay_seconds",
            "max_attempts",
            "max_delay_seconds",
            "retryable_error_classes",
        }
    # Still validated as a five-key RetryPolicyV1 on every element.
    with pytest.raises(ConfirmatoryRegistrationError, match="backoff_kind"):
        _synthetic_snapshot_b(
            retry_policy=RetryPolicyV1(
                max_attempts=1,
                backoff_kind="FOREIGN_BACKOFF",
                initial_delay_seconds="0",
                max_delay_seconds="0",
                retryable_error_classes=(),
            )
        )
    # No global equality constraint: the strata carry different retry policies.
    assert snapshots[0].retry_policy != snapshots[1].retry_policy


def test_timeout_and_retry_stay_inside_the_authenticated_runtime_identity() -> None:
    """Both values remain in the ``runtime_identity_digest`` preimage (§5.I.1)."""

    baseline = _synthetic_snapshot()
    identity = baseline.identity_payload()
    assert identity["timeout_seconds"] == baseline.timeout_seconds
    assert identity["retry_policy"] == baseline.retry_policy.to_dict()
    assert (
        _synthetic_snapshot(timeout_seconds="31").runtime_identity_digest
        != baseline.runtime_identity_digest
    )
    other_policy = RetryPolicyV1(
        max_attempts=3,
        backoff_kind="EXPONENTIAL",
        initial_delay_seconds="1",
        max_delay_seconds="8",
        retryable_error_classes=("SYNTHETIC_A",),
    )
    assert (
        _synthetic_snapshot(retry_policy=other_policy).runtime_identity_digest
        != baseline.runtime_identity_digest
    )


def test_no_outer_timeout_or_retry_key_is_ever_written(tmp_path: Path) -> None:
    _, path = _written_draft(tmp_path)
    persisted = json.loads(path.read_bytes()[:-1].decode("utf-8"))
    runtime = persisted["proposed_runtime_configuration"]
    assert "timeout_seconds" not in runtime
    assert "retry_policy" not in runtime
    assert "registration_expected_runtime_snapshot" not in runtime


def test_single_stratum_draft_binds_exactly_one_runtime_snapshot() -> None:
    draft = _synthetic_draft()
    snapshots = (
        draft.proposed_runtime_configuration.registration_expected_runtime_snapshots
    )
    assert len(snapshots) == len(draft.proposed_strata) == 1
    assert (snapshots[0].provider_name, snapshots[0].model) == (
        draft.proposed_strata[0].provider,
        draft.proposed_strata[0].model,
    )
    verify_self_digest(draft.to_artifact())


def test_multi_stratum_draft_binds_one_runtime_snapshot_per_stratum() -> None:
    draft = _multi_stratum_draft()
    snapshots = (
        draft.proposed_runtime_configuration.registration_expected_runtime_snapshots
    )
    assert len(draft.proposed_strata) == 2
    assert [(item.provider_name, item.model) for item in snapshots] == [
        stratum.identity for stratum in draft.proposed_strata
    ]
    # Distinct provider, model, and registered runtime identity per stratum.
    assert snapshots[0].runtime_identity_digest != snapshots[1].runtime_identity_digest
    verify_self_digest(draft.to_artifact())


def test_proposed_runtime_configuration_key_set_is_exactly_one_key(
    tmp_path: Path,
) -> None:
    _, path = _written_draft(tmp_path)
    persisted = json.loads(path.read_bytes()[:-1].decode("utf-8"))
    assert set(persisted["proposed_runtime_configuration"]) == {
        "registration_expected_runtime_snapshots"
    }
    assert "schema_version" not in persisted["proposed_runtime_configuration"]


def _runtime_payload_draft(runtime: dict[str, Any]) -> dict[str, Any]:
    """A synthetic draft payload carrying a hand-built runtime object."""

    artifact = _synthetic_draft().canonical_payload()
    artifact["proposed_runtime_configuration"] = runtime
    return artifact


def test_legacy_three_key_runtime_shape_is_rejected(tmp_path: Path) -> None:
    """The old ``registration_expected_runtime_snapshot`` shape fails closed."""

    original = _synthetic_draft().canonical_payload()[
        "proposed_runtime_configuration"
    ]
    snapshot = original["registration_expected_runtime_snapshots"][0]
    artifact = _runtime_payload_draft(
        {
            "registration_expected_runtime_snapshot": snapshot,
            "retry_policy": snapshot["retry_policy"],
            "timeout_seconds": snapshot["timeout_seconds"],
        }
    )
    target = _persist_artifact(artifact, tmp_path / "legacy-runtime-shape.json")
    with pytest.raises(ConfirmatoryRegistrationError, match="unexpected keys"):
        load_registration_draft(target)


@pytest.mark.parametrize("legacy_key", ["timeout_seconds", "retry_policy"])
def test_configuration_level_timeout_or_retry_key_is_rejected(
    legacy_key: str, tmp_path: Path
) -> None:
    artifact = _synthetic_draft().canonical_payload()
    runtime = artifact["proposed_runtime_configuration"]
    snapshot = runtime["registration_expected_runtime_snapshots"][0]
    runtime[legacy_key] = snapshot[legacy_key]
    target = _persist_artifact(artifact, tmp_path / f"outer-{legacy_key}.json")
    with pytest.raises(ConfirmatoryRegistrationError, match="unexpected keys"):
        load_registration_draft(target)


def test_empty_runtime_snapshot_collection_is_rejected() -> None:
    with pytest.raises(ConfirmatoryRegistrationError, match=RUNTIME_EMPTY_ERROR):
        _synthetic_runtime(snapshots=())


def test_empty_persisted_runtime_snapshot_collection_is_rejected(
    tmp_path: Path,
) -> None:
    artifact = _runtime_payload_draft({"registration_expected_runtime_snapshots": []})
    target = _persist_artifact(artifact, tmp_path / "empty-runtime.json")
    with pytest.raises(ConfirmatoryRegistrationError, match=RUNTIME_EMPTY_ERROR):
        load_registration_draft(target)


def test_proposed_stratum_without_a_runtime_snapshot_is_rejected() -> None:
    """RC-5: a second proposed stratum with no bound snapshot is refused."""

    strata = _multi_strata()
    with pytest.raises(ConfirmatoryRegistrationError, match=RUNTIME_COVER_ERROR):
        _multi_stratum_draft(
            proposed_runtime_configuration=_synthetic_runtime(
                snapshots=(_synthetic_snapshot(),)
            ),
            proposed_strata=strata,
        )


def test_foreign_runtime_snapshot_is_rejected() -> None:
    """RC-5: a snapshot for a stratum that was never proposed is refused."""

    with pytest.raises(ConfirmatoryRegistrationError, match=RUNTIME_COVER_ERROR):
        _synthetic_draft(
            proposed_runtime_configuration=_synthetic_runtime(
                snapshots=(_synthetic_snapshot_b(),)
            )
        )


def test_extra_runtime_snapshot_beyond_the_proposed_strata_is_rejected() -> None:
    """RC-5: one stratum, two bound snapshots is refused."""

    with pytest.raises(ConfirmatoryRegistrationError, match=RUNTIME_COVER_ERROR):
        _synthetic_draft(
            proposed_runtime_configuration=_synthetic_runtime(
                snapshots=_multi_snapshots()
            )
        )


def test_duplicate_provider_model_runtime_snapshot_is_rejected() -> None:
    """RC-4: the same runtime binding may not appear twice."""

    duplicate = _synthetic_snapshot(endpoint="https://synthetic.invalid/v2")
    with pytest.raises(ConfirmatoryRegistrationError, match=RUNTIME_DUPLICATE_ERROR):
        _synthetic_runtime(snapshots=(_synthetic_snapshot(), duplicate))


def test_unsorted_runtime_snapshots_are_rejected_not_sorted() -> None:
    """RC-3: an out-of-order collection is refused, never re-sorted."""

    reversed_pair = (_synthetic_snapshot_b(), _synthetic_snapshot())
    with pytest.raises(ConfirmatoryRegistrationError, match=RUNTIME_UNSORTED_ERROR):
        _synthetic_runtime(snapshots=reversed_pair)


def test_unsorted_persisted_runtime_snapshots_are_rejected(tmp_path: Path) -> None:
    artifact = _multi_stratum_draft().canonical_payload()
    snapshots = artifact["proposed_runtime_configuration"][
        "registration_expected_runtime_snapshots"
    ]
    snapshots.reverse()
    target = _persist_artifact(artifact, tmp_path / "unsorted-runtime.json")
    with pytest.raises(ConfirmatoryRegistrationError, match=RUNTIME_UNSORTED_ERROR):
        load_registration_draft(target)


@pytest.mark.parametrize(
    ("field_name", "foreign_value"),
    [("provider_name", SYNTHETIC_PROVIDER_B), ("model", SYNTHETIC_MODEL_B)],
)
def test_runtime_snapshot_must_match_its_stratum_element_wise(
    field_name: str, foreign_value: str
) -> None:
    """RC-5: neither half of ``(provider, model)`` may disagree with the stratum."""

    with pytest.raises(ConfirmatoryRegistrationError, match=RUNTIME_COVER_ERROR):
        _synthetic_draft(
            proposed_runtime_configuration=_synthetic_runtime(
                snapshots=(_synthetic_snapshot(**{field_name: foreign_value}),)
            )
        )


def test_runtime_identity_digest_lookup_returns_that_stratums_digest() -> None:
    runtime = _multi_stratum_draft().proposed_runtime_configuration
    first, second = runtime.registration_expected_runtime_snapshots
    assert runtime.registration_expected_runtime_identity_digest(
        SYNTHETIC_PROVIDER, SYNTHETIC_MODEL
    ) == first.runtime_identity_digest
    assert runtime.registration_expected_runtime_identity_digest(
        SYNTHETIC_PROVIDER_B, SYNTHETIC_MODEL_B
    ) == second.runtime_identity_digest
    assert first.runtime_identity_digest != second.runtime_identity_digest


@pytest.mark.parametrize(
    ("provider", "model"),
    [
        (SYNTHETIC_PROVIDER_B, SYNTHETIC_MODEL_B),
        (SYNTHETIC_PROVIDER, SYNTHETIC_MODEL_B),
        (SYNTHETIC_PROVIDER_B, SYNTHETIC_MODEL),
    ],
)
def test_runtime_identity_digest_lookup_for_an_unbound_stratum_raises(
    provider: str, model: str
) -> None:
    """An unbound stratum raises rather than yielding another stratum's digest."""

    runtime = _synthetic_draft().proposed_runtime_configuration
    with pytest.raises(ConfirmatoryRegistrationError, match="binds no"):
        runtime.registration_expected_runtime_identity_digest(provider, model)


def test_every_bound_runtime_snapshot_reverifies_both_of_its_digests(
    tmp_path: Path,
) -> None:
    """RC-2: each element's own identity and self digests still verify."""

    draft = _multi_stratum_draft()
    path = write_registration_draft(draft, confirmatory_root=tmp_path)
    for snapshot in load_registration_draft(
        path
    ).proposed_runtime_configuration.registration_expected_runtime_snapshots:
        payload = snapshot.to_dict()
        assert payload["runtime_identity_digest"] == hashlib.sha256(
            canonical_json_bytes(snapshot.identity_payload())
        ).hexdigest()
        assert payload[SELF_DIGEST_FIELD] == hashlib.sha256(
            canonical_json_bytes(snapshot.canonical_payload())
        ).hexdigest()
        verify_self_digest(payload)


def test_digest_valid_direct_runtime_cardinality_bypass_cannot_create_a_file(
    tmp_path: Path,
) -> None:
    """RC-1..RC-5 hold even against a forged object with a valid ``self_digest``."""

    forged = _forge_like(
        _synthetic_runtime(), registration_expected_runtime_snapshots=()
    )
    invalid = _reseal_direct_draft(
        replace(_synthetic_draft(), proposed_runtime_configuration=forged)
    )
    verify_self_digest(invalid.to_artifact())
    root = tmp_path / "direct-cardinality-bypass"
    with pytest.raises(ConfirmatoryRegistrationError, match=RUNTIME_EMPTY_ERROR):
        write_registration_draft(invalid, confirmatory_root=root)
    assert not root.exists()


def test_digest_valid_direct_foreign_runtime_cover_cannot_create_a_file(
    tmp_path: Path,
) -> None:
    """An RC-5 violation is refused before any directory or artifact exists."""

    forged = _forge_like(
        _synthetic_runtime(),
        registration_expected_runtime_snapshots=(_synthetic_snapshot_b(),),
    )
    invalid = _reseal_direct_draft(
        replace(_synthetic_draft(), proposed_runtime_configuration=forged)
    )
    root = tmp_path / "direct-foreign-cover-bypass"
    with pytest.raises(ConfirmatoryRegistrationError, match=RUNTIME_COVER_ERROR):
        write_registration_draft(invalid, confirmatory_root=root)
    assert not root.exists()
    assert not (root / SYNTHETIC_DESIGN_ID).exists()


def test_load_rejects_digest_valid_artifact_with_an_invalid_runtime_cover(
    tmp_path: Path,
) -> None:
    """A freshly resealed artifact still fails the RC-5 cross-check on load."""

    artifact = _multi_stratum_draft().canonical_payload()
    del artifact["proposed_runtime_configuration"][
        "registration_expected_runtime_snapshots"
    ][1]
    target = _persist_artifact(artifact, tmp_path / "invalid-cover.json")
    verify_self_digest(parse_artifact(target.read_bytes()))
    with pytest.raises(ConfirmatoryRegistrationError, match=RUNTIME_COVER_ERROR):
        load_registration_draft(target)


def test_multi_stratum_runtime_binding_round_trips_with_a_stable_digest(
    tmp_path: Path,
) -> None:
    """Canonical and digest behavior is unchanged by the cardinality repair."""

    draft = _multi_stratum_draft()
    path = write_registration_draft(draft, confirmatory_root=tmp_path)
    reloaded = load_registration_draft(path)
    assert reloaded == draft
    assert reloaded.self_digest == draft.self_digest
    assert serialize_artifact(reloaded.to_artifact()) == path.read_bytes()
    assert (
        reloaded.proposed_runtime_configuration.registration_expected_runtime_snapshots
        == draft.proposed_runtime_configuration.registration_expected_runtime_snapshots
    )


def test_foreign_confirmatory_profile_is_rejected(tmp_path: Path) -> None:
    artifact = _synthetic_draft().canonical_payload()
    artifact["confirmatory_profile"] = "some_other_profile_v1"
    target = _persist_artifact(artifact, tmp_path / "foreign_profile.json")
    with pytest.raises(ConfirmatoryRegistrationError, match="confirmatory_profile"):
        load_registration_draft(target)


def test_foreign_registration_state_is_rejected(tmp_path: Path) -> None:
    artifact = _synthetic_draft().canonical_payload()
    artifact["registration_state"] = "FINAL_REGISTRATION_FROZEN"
    target = _persist_artifact(artifact, tmp_path / "foreign_state.json")
    with pytest.raises(ConfirmatoryRegistrationError, match="registration_state"):
        load_registration_draft(target)


# --- R: only synthetic tmp_path artifact locations are used -----------------


def test_artifact_path_layout_is_design_id_scoped(tmp_path: Path) -> None:
    path = registration_draft_path(tmp_path, SYNTHETIC_DESIGN_ID)
    assert path == tmp_path / SYNTHETIC_DESIGN_ID / REGISTRATION_DRAFT_FILENAME
    assert path.name == "registration_draft.json"


@pytest.mark.parametrize(
    "design_id",
    [
        "..",
        "../escape",
        "..\\escape",
        "nested/child",
        "nested\\child",
        "C:",
        "C:escape",
        "\\\\server\\share",
        "with\x00null",
    ],
)
def test_registration_draft_path_rejects_cross_platform_escape_forms(
    design_id: str, tmp_path: Path
) -> None:
    with pytest.raises(ConfirmatoryRegistrationError):
        registration_draft_path(tmp_path, design_id)


@pytest.mark.parametrize(
    "design_id", ["synthetic-design-000", "synthetic_design.001", "SYNTHETIC-002"]
)
def test_registration_draft_path_accepts_normal_single_segment_ids(
    design_id: str, tmp_path: Path
) -> None:
    path = registration_draft_path(tmp_path, design_id)
    assert path.parent.name == design_id
    assert path.is_relative_to(tmp_path)


def test_written_artifact_stays_inside_the_temporary_directory(
    tmp_path: Path,
) -> None:
    _, path = _written_draft(tmp_path)
    assert path.is_relative_to(tmp_path)
    assert path.parent.name == SYNTHETIC_DESIGN_ID
    assert not Path("results/confirmatory").exists()


# ===========================================================================
# S. Stage-C FINAL_REGISTRATION_FROZEN — synthetic fixtures
#
# Every value below is invented.  No real design id, task, provider, model,
# seed, runtime, or eligibility finding appears, nothing is written outside a
# pytest ``tmp_path``, and no assignment bit, Monte Carlo seed, provider call, or
# network access happens anywhere in this section.
# ===========================================================================

STAGE_C_DESIGN_ID = "synthetic-final-000"
STAGE_C_CREATED_AT = datetime(2026, 3, 3, 4, 5, 6, tzinfo=UTC)
STAGE_C_TASK = "synthetic-task-a"
STAGE_C_SEED_BASE = 11
STAGE_C_EVIDENCE_DIGEST = "a" * 64

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_UNASSESSED = "UNASSESSED"

ALL_PASS = (STATUS_PASS,) * 4

#: The five descriptive-only status patterns, one per ``DESCRIPTIVE_ONLY_*``
#: token, so the partition is exercised against several reasons rather than one.
DESCRIPTIVE_STATUS_PATTERNS: tuple[tuple[str, ...], ...] = (
    (STATUS_FAIL, STATUS_PASS, STATUS_PASS, STATUS_PASS),
    (STATUS_PASS, STATUS_FAIL, STATUS_PASS, STATUS_PASS),
    (STATUS_PASS, STATUS_PASS, STATUS_FAIL, STATUS_PASS),
    (STATUS_PASS, STATUS_PASS, STATUS_PASS, STATUS_FAIL),
    (STATUS_PASS, STATUS_UNASSESSED, STATUS_PASS, STATUS_PASS),
)

#: The §9.2 five-key ``matrix_digest`` preimage, spelled independently here so
#: the tests never take the implementation's word for what the preimage is.
MATRIX_PREIMAGE_KEYS: tuple[str, ...] = (
    "K",
    "confirmatory_positions",
    "confirmatory_strata",
    "randomization_mode",
    "registered_statistical_configuration",
)

#: The §7.1 six-field identity payload, likewise spelled independently.
POSITION_IDENTITY_KEYS: tuple[str, ...] = (
    "task_id",
    "provider",
    "model",
    "repetition",
    "provider_seed",
    "slot",
)

STAGE_C_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {
        "K",
        "confirmatory_positions",
        "confirmatory_profile",
        "confirmatory_strata",
        "created_at",
        "descriptive_only_strata",
        "descriptive_positions",
        "design_id",
        "eligibility_manifest_digest",
        "matrix_digest",
        "randomization_mode",
        "registered_statistical_configuration",
        "registration_draft_digest",
        "registration_state",
        "schema_version",
        "self_digest",
    }
)


def _stage_c_pair(index: int) -> tuple[str, str]:
    """One invented stratum; ``index`` ordering matches ``(provider, model)`` order."""

    return (f"synthetic-provider-{index:02d}", f"synthetic-model-{index:02d}")


def _stage_c_tasks(count: int) -> tuple[str, ...]:
    return tuple(f"synthetic-task-{index:02d}" for index in range(count))


def _stage_c_snapshot(provider: str, model: str) -> RuntimeSnapshotV1:
    return RuntimeSnapshotV1(
        provider_name=provider,
        model=model,
        endpoint=f"https://{provider}.invalid/v1",
        provider_config_digest="0" * 64,
        provider_parameters_digest="1" * 64,
        timeout_seconds="30.5",
        retry_policy=RetryPolicyV1(
            max_attempts=1,
            backoff_kind="NONE",
            initial_delay_seconds="0",
            max_delay_seconds="0",
            retryable_error_classes=("SYNTHETIC_A",),
        ),
        tool_contract_policy="SYNTHETIC_TOOL_POLICY_V1",
        native_tool_adapter_version="synthetic-adapter-v1",
        package_source_sha256="2" * 64,
        python_version="3.11.0",
        artifact_version="synthetic-artifact-v1",
        prompt_digest="3" * 64,
        experiment_config_digest="4" * 64,
        models_config_digest="5" * 64,
        environment_fingerprint="6" * 64,
        captured_at=STAGE_C_CREATED_AT.isoformat(),
    )


def _stage_c_draft(
    *pairs: tuple[str, str],
    tasks: tuple[str, ...] = (STAGE_C_TASK,),
    count: int = 1,
    design_id: str = STAGE_C_DESIGN_ID,
    randomization_mc_samples: int | None = None,
) -> RegistrationDraft:
    """A valid Stage-A draft over invented identifiers, built through Work Unit 1."""

    strata = tuple(ProposedStratumV1(provider=p, model=m) for p, m in pairs)
    repetitions = tuple(
        ProposedRepetitionsEntryV1(
            task_id=task_id, provider=p, model=m, repetition_count=count
        )
        for task_id in tasks
        for p, m in pairs
    )
    positions = tuple(
        ProposedPositionV1(
            task_id=entry.task_id,
            provider=entry.provider,
            model=entry.model,
            repetition=repetition,
            provider_seed=STAGE_C_SEED_BASE + repetition,
            slot=slot,
            baseline_label=label,
        )
        for entry in repetitions
        for repetition in range(count)
        for slot, label in ((1, BASELINE_LABEL_OFF), (2, BASELINE_LABEL_FULL))
    )
    return draft_registration(
        design_id=design_id,
        created_at=STAGE_C_CREATED_AT,
        proposed_tasks=tasks,
        proposed_strata=strata,
        proposed_repetitions=repetitions,
        proposed_provider_seeds=tuple(
            ProposedProviderSeedEntryV1(
                repetition=repetition, provider_seed=STAGE_C_SEED_BASE + repetition
            )
            for repetition in range(count)
        ),
        proposed_positions=positions,
        proposed_runtime_configuration=ProposedRuntimeConfigurationV1(
            registration_expected_runtime_snapshots=tuple(
                _stage_c_snapshot(p, m) for p, m in pairs
            )
        ),
        proposed_randomization_mc_samples=randomization_mc_samples,
    )


def _stage_c_channel(index: int, status: str) -> InfrastructureSymmetryChannelV1:
    """The channel configuration that derives ``status`` for ``predicates[1]``."""

    if status == STATUS_PASS:
        checked, asymmetry = True, False
    elif status == STATUS_FAIL:
        checked, asymmetry = (index == 0), (index == 0)
    else:
        checked, asymmetry = False, False
    if checked:
        return InfrastructureSymmetryChannelV1(
            channel_id=CHANNEL_IDS[index],
            check_status="CHECKED",
            symmetry_result="ASYMMETRY_FOUND" if asymmetry else "NO_ASYMMETRY_FOUND",
            evidence_refs=(
                EvidenceReferenceV1(
                    evidence_kind="REPOSITORY_PATH",
                    locator=f"docs/synthetic-channel-{index}.md",
                    content_digest=STAGE_C_EVIDENCE_DIGEST,
                ),
            ),
        )
    return InfrastructureSymmetryChannelV1(
        channel_id=CHANNEL_IDS[index],
        check_status="NOT_CHECKED",
        symmetry_result="SYMMETRY_NOT_ASSESSED",
        evidence_refs=(),
    )


def _stage_c_record(
    pair: tuple[str, str], runtime_digest: str, statuses: tuple[str, ...]
) -> EligibilityStratumRecordV1:
    """One synthetic Stage-B record, built through Work Unit 2's public types."""

    predicates = tuple(
        EligibilityPredicateRecordV1(
            predicate_id=PREDICATE_IDS[index],
            status=status,
            evidence_refs=(
                ()
                if index == 1 or status == STATUS_UNASSESSED
                else (
                    EvidenceReferenceV1(
                        evidence_kind="REPOSITORY_PATH",
                        locator=f"docs/synthetic-predicate-{index}.md",
                        content_digest=STAGE_C_EVIDENCE_DIGEST,
                    ),
                )
            ),
        )
        for index, status in enumerate(statuses)
    )
    return EligibilityStratumRecordV1(
        provider=pair[0],
        model=pair[1],
        predicates=predicates,
        infrastructure_symmetry_audit=InfrastructureSymmetryAuditV1(
            channels=tuple(
                _stage_c_channel(index, statuses[1]) for index in range(len(CHANNEL_IDS))
            )
        ),
        runtime_identity_digest=runtime_digest,
    )


def _stage_c_runtime_digests(draft: RegistrationDraft) -> tuple[str, ...]:
    return tuple(
        snapshot.runtime_identity_digest
        for snapshot in (
            draft.proposed_runtime_configuration.registration_expected_runtime_snapshots
        )
    )


def _stage_c_eligibility(
    draft: RegistrationDraft, *statuses: tuple[str, ...]
) -> EligibilityManifestV1:
    """A synthetic Stage-B manifest, frozen through Work Unit 2's public API."""

    digests = _stage_c_runtime_digests(draft)
    per_stratum = statuses or (ALL_PASS,) * len(draft.proposed_strata)
    return freeze_eligibility(
        registration_draft=draft,
        created_at=STAGE_C_CREATED_AT,
        eligibility_records=tuple(
            _stage_c_record(
                (stratum.provider, stratum.model), digests[index], per_stratum[index]
            )
            for index, stratum in enumerate(draft.proposed_strata)
        ),
    )


class StageCChain(NamedTuple):
    """A complete synthetic Stage-A/Stage-B/Stage-C triple."""

    draft: RegistrationDraft
    eligibility: EligibilityManifestV1
    manifest: RegistrationManifest


def _stage_c_chain(
    *statuses: tuple[str, ...],
    pairs: tuple[tuple[str, str], ...] | None = None,
    tasks: tuple[str, ...] = (STAGE_C_TASK,),
    count: int = 1,
    design_id: str = STAGE_C_DESIGN_ID,
    randomization_mc_samples: int | None = None,
) -> StageCChain:
    """Freeze a Stage-C manifest over an invented, fully synthetic chain."""

    stratum_pairs = pairs if pairs is not None else tuple(
        _stage_c_pair(index) for index in range(len(statuses) or 1)
    )
    draft = _stage_c_draft(
        *stratum_pairs,
        tasks=tasks,
        count=count,
        design_id=design_id,
        randomization_mc_samples=randomization_mc_samples,
    )
    eligibility = _stage_c_eligibility(draft, *statuses)
    manifest = freeze_final_registration(
        registration_draft=draft, eligibility_manifest=eligibility
    )
    return StageCChain(draft, eligibility, manifest)


def _mixed_chain() -> StageCChain:
    """One ``CONFIRMATORY_ELIGIBLE`` stratum and five distinct descriptive reasons."""

    return _stage_c_chain(ALL_PASS, *DESCRIPTIVE_STATUS_PATTERNS)


def _simple_chain() -> StageCChain:
    """One eligible stratum and one descriptive-only stratum."""

    return _stage_c_chain(ALL_PASS, DESCRIPTIVE_STATUS_PATTERNS[2])


def _expected_matrix_digest(artifact: dict[str, Any]) -> str:
    """The §9.2 digest, recomputed here from the five persisted values alone."""

    preimage = {key: artifact[key] for key in MATRIX_PREIMAGE_KEYS}
    return hashlib.sha256(canonical_json_bytes(preimage)).hexdigest()


def _expected_position_id(identity: dict[str, Any]) -> str:
    """The §7.1 digest, recomputed here from the six identity fields alone."""

    return hashlib.sha256(canonical_json_bytes(identity)).hexdigest()


def _identity_of(record: dict[str, Any]) -> dict[str, Any]:
    return {key: record[key] for key in POSITION_IDENTITY_KEYS}


def _stage_c_artifact(
    manifest: RegistrationManifest,
    *mutations: Callable[[dict[str, Any]], None],
    reseal_matrix: bool = True,
    reseal_self: bool = True,
) -> dict[str, Any]:
    """A hand-built Stage-C artifact, optionally resealed after the mutations."""

    artifact = manifest.to_artifact()
    for mutate in mutations:
        mutate(artifact)
    if reseal_matrix and "matrix_digest" in artifact:
        artifact["matrix_digest"] = _expected_matrix_digest(artifact)
    if reseal_self and SELF_DIGEST_FIELD in artifact:
        artifact = attach_self_digest(artifact)
    return artifact


def _persist_stage_c(artifact: dict[str, Any], path: Path) -> Path:
    """Persist an artifact verbatim, digests and all, without re-verifying them."""

    path.write_bytes(canonical_json_bytes(artifact) + b"\n")
    return path


def _load_stage_c(
    artifact: dict[str, Any], chain: StageCChain, tmp_path: Path, name: str = "m.json"
) -> RegistrationManifest:
    return load_registration_manifest(
        _persist_stage_c(artifact, tmp_path / name),
        registration_draft=chain.draft,
        eligibility_manifest=chain.eligibility,
    )


def _written_chain(tmp_path: Path, chain: StageCChain) -> Path:
    """Write the Stage-A and Stage-B artifacts a Stage-C write must bind to."""

    write_registration_draft(chain.draft, confirmatory_root=tmp_path)
    write_eligibility_manifest(chain.eligibility, confirmatory_root=tmp_path)
    return tmp_path


def _registration_module_source() -> str:
    return Path(registration_module.__file__).read_text(encoding="utf-8")


def _dotted(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_dotted(node.value)}.{node.attr}"
    return ""


def _function_node(name: str) -> ast.FunctionDef:
    for node in ast.walk(ast.parse(_registration_module_source())):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} is not defined in the module")


def _calls_within(name: str) -> set[str]:
    """Every function invoked anywhere inside ``name``'s body."""

    return {
        _dotted(node.func)
        for node in ast.walk(_function_node(name))
        if isinstance(node, ast.Call)
    }


def _rule_call_sequence(function_name: str) -> list[int]:
    """The ``_validate_fN`` calls an orchestrator makes, in source order."""

    numbers: list[int] = []
    for statement in _function_node(function_name).body:
        if isinstance(statement, ast.Expr):
            value: ast.expr | None = statement.value
        elif isinstance(statement, ast.Assign):
            value = statement.value
        else:
            value = None
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id.startswith("_validate_f")
            and value.func.id[len("_validate_f") :].isdigit()
        ):
            numbers.append(int(value.func.id[len("_validate_f") :]))
    return numbers


def _module_string_constants() -> set[str]:
    """Every string literal the module *uses*, with docstrings excluded.

    Checked against the syntax tree rather than by substring, so a prose mention
    in a docstring cannot fail a rule and a real literal cannot hide behind one.
    """

    tree = ast.parse(_registration_module_source())
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                docstrings.add(id(first.value))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    }


def _module_imports() -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(_registration_module_source())):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(alias.name for alias in node.names)
            if node.module:
                names.add(node.module)
    return names


# --- S: basic round trip ----------------------------------------------------


def test_stage_c_freezes_a_valid_synthetic_chain() -> None:
    """§4 — a valid Stage-A plus Stage-B chain freezes into a Stage-C manifest."""

    chain = _simple_chain()
    manifest = chain.manifest
    assert isinstance(manifest, RegistrationManifest)
    assert manifest.design_id == STAGE_C_DESIGN_ID
    assert manifest.K == 1
    assert manifest.randomization_mode == RANDOMIZATION_MODE_EXACT_ENUMERATION
    assert len(manifest.confirmatory_strata) == 1
    assert len(manifest.descriptive_only_strata) == 1
    assert len(manifest.confirmatory_positions) == 2
    assert len(manifest.descriptive_positions) == 2


def test_registration_manifest_round_trips_through_canonical_serialization(
    tmp_path: Path,
) -> None:
    """§17.1 — write, read, and rebuild reproduce the identical typed manifest."""

    chain = _mixed_chain()
    _written_chain(tmp_path, chain)
    path = write_registration_manifest(chain.manifest, confirmatory_root=tmp_path)
    assert path.read_bytes().endswith(b"}\n")
    assert not path.read_bytes().endswith(b"}\n\n")
    loaded = load_registration_manifest(
        path,
        registration_draft=chain.draft,
        eligibility_manifest=chain.eligibility,
    )
    assert loaded == chain.manifest
    assert loaded.to_artifact() == chain.manifest.to_artifact()
    assert chain.manifest._freeze_provenance == (
        chain.manifest.created_at,
        chain.manifest.self_digest,
    )
    assert loaded._freeze_provenance is None


def test_registration_manifest_has_exactly_sixteen_top_level_keys() -> None:
    """§4.1 F1 — exactly sixteen keys, no optional key, no alternative shape."""

    artifact = _mixed_chain().manifest.to_artifact()
    assert set(artifact) == STAGE_C_TOP_LEVEL_KEYS
    assert len(artifact) == 16
    assert "_freeze_provenance" not in artifact


def test_freeze_provenance_is_private_nonpersisted_and_not_caller_settable() -> None:
    provenance_field = next(
        item
        for item in dataclass_fields(RegistrationManifest)
        if item.name == "_freeze_provenance"
    )
    assert provenance_field.init is False
    assert provenance_field.repr is False
    assert provenance_field.compare is False
    assert provenance_field.name not in inspect.signature(RegistrationManifest).parameters
    assert provenance_field.name not in _simple_chain().manifest.to_artifact()


def test_stage_c_frozen_literals_are_exact() -> None:
    """§4.1, §5 F2-F4 — the three stamped literals, verbatim."""

    manifest = _simple_chain().manifest
    assert REGISTRATION_MANIFEST_SCHEMA_VERSION == "RegistrationManifestV1"
    assert REGISTRATION_STATE_FINAL_REGISTRATION_FROZEN == "FINAL_REGISTRATION_FROZEN"
    assert manifest.schema_version == REGISTRATION_MANIFEST_SCHEMA_VERSION
    assert manifest.registration_state == REGISTRATION_STATE_FINAL_REGISTRATION_FROZEN
    assert manifest.confirmatory_profile == "post_phaseP_confirmatory_randomization_v1"
    assert REGISTRATION_MANIFEST_FILENAME == "registration_manifest.json"


def test_manifest_stores_no_same_object_final_registration_digest_alias() -> None:
    """§4.4, §4.5 — one digest of itself, and the downstream name is never a field."""

    artifact = _mixed_chain().manifest.to_artifact()
    assert "final_registration_digest" not in artifact
    assert "registration_manifest_digest" not in artifact
    assert artifact[SELF_DIGEST_FIELD] != artifact["matrix_digest"]
    digest_keys = {key for key in artifact if key.endswith("_digest")}
    assert digest_keys == {
        "eligibility_manifest_digest",
        "matrix_digest",
        "registration_draft_digest",
        SELF_DIGEST_FIELD,
    }


@pytest.mark.parametrize(
    "forbidden",
    [
        "assignment_digest",
        "b_k",
        "bits",
        "captured_at",
        "exact_support_size",
        "failure_class",
        "final_registration_digest",
        "generated_at",
        "observation_status",
        "qa_mode",
        "randomization_mc_provenance_digest",
        "registered_k",
        "seed_hex",
        "task_assignment_bit",
        "task_order",
    ],
)
def test_manifest_carries_no_assignment_seed_or_execution_key(forbidden: str) -> None:
    """§4.6, §16.4 — none of Stage C's forbidden names exists at any depth."""

    def keys(value: Any) -> set[str]:
        found: set[str] = set()
        if isinstance(value, dict):
            for key, item in value.items():
                found.add(key)
                found |= keys(item)
        elif isinstance(value, list):
            for item in value:
                found |= keys(item)
        return found

    assert forbidden not in keys(_mixed_chain().manifest.to_artifact())
    assert forbidden in REGISTRATION_MANIFEST_FORBIDDEN_KEY_NAMES


def test_upstream_digest_chain_is_bound_exactly() -> None:
    """§21, F26/F34/F35 — the two upstream references are the verified self digests."""

    chain = _mixed_chain()
    assert chain.manifest.registration_draft_digest == chain.draft.self_digest
    assert chain.manifest.eligibility_manifest_digest == chain.eligibility.self_digest
    assert chain.eligibility.registration_draft_digest == chain.draft.self_digest
    assert chain.draft.registration_state == REGISTRATION_STATE_DRAFT
    assert chain.eligibility.registration_state == REGISTRATION_STATE_ELIGIBILITY_FROZEN
    assert (
        chain.manifest.registration_state == REGISTRATION_STATE_FINAL_REGISTRATION_FROZEN
    )
    assert chain.draft.design_id == chain.eligibility.design_id
    assert chain.eligibility.design_id == chain.manifest.design_id
    assert chain.draft.confirmatory_profile == chain.manifest.confirmatory_profile


@pytest.mark.parametrize(
    ("field_name", "value", "match"),
    [
        ("registration_draft_digest", "1" * 64, "registration_draft_digest"),
        ("eligibility_manifest_digest", "2" * 64, "eligibility_manifest_digest"),
    ],
)
def test_broken_upstream_digest_binding_is_an_integrity_rejection(
    field_name: str, value: str, match: str, tmp_path: Path
) -> None:
    """§21 — a broken chain is refused, never converted to descriptive-only status."""

    chain = _mixed_chain()
    artifact = _stage_c_artifact(
        chain.manifest, lambda item: item.__setitem__(field_name, value)
    )
    with pytest.raises(ConfirmatoryRegistrationError, match=match):
        _load_stage_c(artifact, chain, tmp_path)


# ===========================================================================
# T. §13 The partition — deterministic, total, disjoint, never reassessed
# ===========================================================================


def test_partition_sends_the_eligible_stratum_confirmatory_and_the_rest_descriptive() -> None:
    """§13.1 — one ``CONFIRMATORY_ELIGIBLE`` stratum, five distinct descriptive reasons."""

    chain = _mixed_chain()
    dispositions = {
        record.identity: record.disposition
        for record in chain.eligibility.eligibility_records
    }
    eligible = {
        key
        for key, value in dispositions.items()
        if value == DISPOSITION_CONFIRMATORY_ELIGIBLE
    }
    descriptive = set(dispositions) - eligible
    assert len(eligible) == 1
    assert len(descriptive) == len(DESCRIPTIVE_STATUS_PATTERNS)
    # Every descriptive-only reason is exercised, not just one.
    assert len({dispositions[key] for key in descriptive}) == len(descriptive)
    assert {stratum.identity for stratum in chain.manifest.confirmatory_strata} == eligible
    assert {
        stratum.identity for stratum in chain.manifest.descriptive_only_strata
    } == descriptive


def test_partition_positions_follow_their_own_stratum() -> None:
    """§13.1 step 2 — a position's side is decided solely by its own stratum."""

    chain = _mixed_chain()
    confirmatory = {stratum.identity for stratum in chain.manifest.confirmatory_strata}
    descriptive = {
        stratum.identity for stratum in chain.manifest.descriptive_only_strata
    }
    for position in chain.manifest.confirmatory_positions:
        assert (position.provider, position.model) in confirmatory
    for position in chain.manifest.descriptive_positions:
        assert (position.provider, position.model) in descriptive


def test_partition_is_an_exact_cover_of_stage_a_with_no_overlap() -> None:
    """§13.2, §13.3 — total, disjoint, no foreign, no missing, no duplicate item."""

    chain = _mixed_chain()
    manifest = chain.manifest
    stratum_keys = [stratum.identity for stratum in chain.draft.proposed_strata]
    merged_strata = sorted(
        [stratum.identity for stratum in manifest.confirmatory_strata]
        + [stratum.identity for stratum in manifest.descriptive_only_strata]
    )
    assert merged_strata == sorted(stratum_keys)
    assert len(merged_strata) == len(set(merged_strata)) == len(stratum_keys)

    placements = [position.placement for position in chain.draft.proposed_positions]
    merged_positions = sorted(
        [position.placement for position in manifest.confirmatory_positions]
        + [position.placement for position in manifest.descriptive_positions]
    )
    assert merged_positions == sorted(placements)
    assert len(merged_positions) == len(set(merged_positions)) == len(placements)


def test_partition_output_is_sorted_without_ever_sorting() -> None:
    """§8.4 — the frozen order is emitted by stably filtering a sorted input."""

    manifest = _mixed_chain().manifest
    for strata in (manifest.confirmatory_strata, manifest.descriptive_only_strata):
        keys = [stratum.identity for stratum in strata]
        assert keys == sorted(keys)
        assert len(keys) == len(set(keys))
    for positions in (manifest.confirmatory_positions, manifest.descriptive_positions):
        placements = [position.placement for position in positions]
        assert placements == sorted(placements)
        assert len(placements) == len(set(placements))
    assert "sorted" not in _calls_within("_derive_stage_c_partition")


def test_partition_never_recomputes_a_stage_b_disposition() -> None:
    """§13.1 — the frozen token is read; no predicate or audit is re-derived here."""

    invoked = _calls_within("_derive_stage_c_partition") | _calls_within("_validate_f36")
    assert "derive_disposition" not in invoked
    assert "derive_infrastructure_symmetry_status" not in invoked
    imported = _module_imports()
    assert "derive_disposition" not in imported
    assert "derive_infrastructure_symmetry_status" not in imported


def test_stage_c_disposition_literal_belongs_to_the_work_unit_2_vocabulary() -> None:
    """§16 F36 — the partition token is cross-checked, never assumed."""

    assert DISPOSITION_CONFIRMATORY_ELIGIBLE in DISPOSITIONS
    assert DISPOSITION_CONFIRMATORY_ELIGIBLE == "CONFIRMATORY_ELIGIBLE"
    descriptive = set(DISPOSITIONS) - {DISPOSITION_CONFIRMATORY_ELIGIBLE}
    assert len(descriptive) == 5
    assert all(token.startswith("DESCRIPTIVE_ONLY_") for token in descriptive)


def test_a_stratum_placed_on_the_wrong_side_is_rejected_at_f36(tmp_path: Path) -> None:
    """§13.3, F36 — the persisted partition must agree with the frozen dispositions."""

    chain = _stage_c_chain(ALL_PASS, DESCRIPTIVE_STATUS_PATTERNS[0])
    digests = _stage_c_runtime_digests(chain.draft)

    def swap(artifact: dict[str, Any]) -> None:
        confirmatory = artifact["confirmatory_strata"]
        descriptive = artifact["descriptive_only_strata"]
        artifact["confirmatory_strata"] = [
            {
                "model": descriptive[0]["model"],
                "provider": descriptive[0]["provider"],
                "runtime_identity_digest": digests[1],
            }
        ]
        artifact["descriptive_only_strata"] = [
            {"model": confirmatory[0]["model"], "provider": confirmatory[0]["provider"]}
        ]
        artifact["confirmatory_positions"], artifact["descriptive_positions"] = (
            artifact["descriptive_positions"],
            artifact["confirmatory_positions"],
        )

    artifact = _stage_c_artifact(chain.manifest, swap)
    with pytest.raises(ConfirmatoryRegistrationError, match="CONFIRMATORY_ELIGIBLE"):
        _load_stage_c(artifact, chain, tmp_path)


def test_a_position_placed_opposite_its_own_stratum_is_rejected_at_f17(
    tmp_path: Path,
) -> None:
    """§13.3, F17 — every position must sit on its own stratum's side."""

    chain = _simple_chain()

    def move(artifact: dict[str, Any]) -> None:
        artifact["descriptive_positions"] = sorted(
            artifact["descriptive_positions"] + [artifact["confirmatory_positions"][0]],
            key=lambda item: tuple(item[key] for key in POSITION_IDENTITY_KEYS[:3])
            + (item["repetition"], item["slot"]),
        )
        artifact["confirmatory_positions"] = artifact["confirmatory_positions"][1:]

    artifact = _stage_c_artifact(chain.manifest, move)
    with pytest.raises(ConfirmatoryRegistrationError, match="descriptive_only_strata"):
        _load_stage_c(artifact, chain, tmp_path)


def test_no_stratum_or_position_may_appear_on_both_sides(tmp_path: Path) -> None:
    """§13.3, F11/F15 — the two sides are disjoint, structurally."""

    chain = _simple_chain()

    def duplicate_stratum(artifact: dict[str, Any]) -> None:
        artifact["descriptive_only_strata"] = sorted(
            artifact["descriptive_only_strata"]
            + [
                {
                    "model": artifact["confirmatory_strata"][0]["model"],
                    "provider": artifact["confirmatory_strata"][0]["provider"],
                }
            ],
            key=lambda item: (item["provider"], item["model"]),
        )

    artifact = _stage_c_artifact(chain.manifest, duplicate_stratum)
    with pytest.raises(ConfirmatoryRegistrationError, match="disjoint"):
        _load_stage_c(artifact, chain, tmp_path)


def test_stratum_records_carry_no_disposition_or_eligibility_evidence() -> None:
    """§8.1 — no disposition, predicate, audit, or evidence is copied into Stage C."""

    manifest = _mixed_chain().manifest
    for stratum in manifest.confirmatory_strata:
        assert set(stratum.to_dict()) == {
            "model",
            "provider",
            "runtime_identity_digest",
        }
    for descriptive in manifest.descriptive_only_strata:
        assert set(descriptive.to_dict()) == {"model", "provider"}


# ===========================================================================
# U. §7.1, §14 position_id — six identity fields, and nothing else
# ===========================================================================


def test_position_id_is_sha256_over_the_canonical_six_field_identity() -> None:
    """§7.1 — the shared canonical helper, over exactly the six identity fields."""

    manifest = _mixed_chain().manifest
    for position in manifest.confirmatory_positions + manifest.descriptive_positions:
        record = position.to_dict()
        assert set(record) == {
            "baseline_label",
            "model",
            "position_id",
            "provider",
            "provider_seed",
            "repetition",
            "slot",
            "task_id",
        }
        identity = _identity_of(record)
        assert set(identity) == set(POSITION_IDENTITY_KEYS)
        assert position.position_id == _expected_position_id(identity)
        assert len(position.position_id) == 64
        assert position.position_id == position.position_id.lower()


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("task_id", "synthetic-task-other"),
        ("provider", "synthetic-provider-other"),
        ("model", "synthetic-model-other"),
        ("repetition", 7),
        ("provider_seed", 999),
        ("slot", 2),
    ],
)
def test_changing_any_identity_field_changes_the_position_id(
    field_name: str, value: Any
) -> None:
    """§7.1 — every one of the six fields is inside the preimage."""

    base = _identity_of(_simple_chain().manifest.confirmatory_positions[0].to_dict())
    assert base[field_name] != value
    changed = dict(base, **{field_name: value})
    assert _expected_position_id(changed) != _expected_position_id(base)


def test_baseline_label_alone_does_not_change_the_position_id() -> None:
    """§7.1 — the label is excluded, so identity cannot leak assignment information."""

    position = _simple_chain().manifest.confirmatory_positions[0]
    record = position.to_dict()
    assert record["baseline_label"] == BASELINE_LABEL_OFF
    flipped = dict(record, baseline_label=BASELINE_LABEL_FULL)
    assert _identity_of(flipped) == _identity_of(record)
    assert _expected_position_id(_identity_of(flipped)) == position.position_id
    for excluded in ("baseline_label", "treatment", "qa_mode", "task_assignment_bit", "b_k"):
        assert excluded not in _identity_of(record)


def test_a_persisted_position_id_mismatch_is_rejected_at_f16(tmp_path: Path) -> None:
    """§14.2, F16 — a record cannot merely *claim* an identity."""

    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item["confirmatory_positions"][0].__setitem__(
            "position_id", "0" * 64
        ),
    )
    with pytest.raises(ConfirmatoryRegistrationError, match="position_id mismatch"):
        _load_stage_c(artifact, chain, tmp_path)


def test_a_duplicate_position_id_across_the_two_arrays_is_rejected_at_f15(
    tmp_path: Path,
) -> None:
    """§8.2, F15 — ``position_id`` is unique across the union of both arrays."""

    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item["descriptive_positions"][0].__setitem__(
            "position_id", item["confirmatory_positions"][0]["position_id"]
        ),
    )
    with pytest.raises(ConfirmatoryRegistrationError, match="unique across the union"):
        _load_stage_c(artifact, chain, tmp_path)


def test_position_id_derivation_uses_the_shared_canonical_helper() -> None:
    """§7.1 — no second serializer, no randomness, no assignment input."""

    invoked = _calls_within("_derive_position_id") | _calls_within(
        "_final_position_record"
    )
    assert "canonical_json_bytes" in invoked
    assert "hashlib.sha256" in invoked
    for forbidden in (
        "resolve_label",
        "complement",
        "secrets.randbits",
        "secrets.token_bytes",
        "os.urandom",
        "random.getrandbits",
    ):
        assert forbidden not in invoked


# ===========================================================================
# V. §10 Runtime identity — copied, cross-checked, never recaptured
# ===========================================================================


def test_confirmatory_strata_carry_the_exact_stage_a_and_stage_b_runtime_digest() -> None:
    """§10.1, §10.4 — one copied field, equal to both authenticated sources."""

    chain = _mixed_chain()
    runtime = chain.draft.proposed_runtime_configuration
    stage_b = {
        record.identity: record.runtime_identity_digest
        for record in chain.eligibility.eligibility_records
    }
    assert chain.manifest.confirmatory_strata
    for stratum in chain.manifest.confirmatory_strata:
        expected = runtime.registration_expected_runtime_identity_digest(
            stratum.provider, stratum.model
        )
        assert stratum.runtime_identity_digest == expected
        assert stratum.runtime_identity_digest == stage_b[stratum.identity]


def test_descriptive_only_strata_carry_no_runtime_identity_digest() -> None:
    """§10.2 — the extra key exists only where a frozen consumer reads it."""

    manifest = _mixed_chain().manifest
    assert manifest.descriptive_only_strata
    for stratum in manifest.descriptive_only_strata:
        assert not hasattr(stratum, "runtime_identity_digest")
        assert "runtime_identity_digest" not in stratum.to_dict()


def test_a_stage_a_runtime_identity_mismatch_is_rejected_at_f32(tmp_path: Path) -> None:
    """F32 — an integrity failure of the whole manifest, never an eligibility finding."""

    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item["confirmatory_strata"][0].__setitem__(
            "runtime_identity_digest", "f" * 64
        ),
    )
    with pytest.raises(
        ConfirmatoryRegistrationError, match="registration-expected digest"
    ):
        _load_stage_c(artifact, chain, tmp_path)


def test_a_stage_b_runtime_identity_mismatch_is_rejected_at_f37() -> None:
    """F37 — the copy is checked against the eligibility manifest as well as the draft."""

    chain = _simple_chain()
    artifact = chain.manifest.to_artifact()
    record = chain.eligibility.eligibility_records[0]
    forged_record = _forge_like(record, runtime_identity_digest="e" * 64)
    forged_manifest = _forge_like(
        chain.eligibility, eligibility_records=(forged_record,) + tuple(
            chain.eligibility.eligibility_records[1:]
        )
    )
    with pytest.raises(ConfirmatoryRegistrationError, match="eligibility manifest"):
        registration_module._validate_f37(artifact, forged_manifest)


def test_a_runtime_identity_digest_on_a_descriptive_stratum_is_rejected_at_f10(
    tmp_path: Path,
) -> None:
    """§10.2, F10 — exactly two keys on a descriptive-only stratum record."""

    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item["descriptive_only_strata"][0].__setitem__(
            "runtime_identity_digest", "b" * 64
        ),
    )
    with pytest.raises(ConfirmatoryRegistrationError, match="unexpected keys"):
        _load_stage_c(artifact, chain, tmp_path)


def test_stage_c_never_recaptures_a_runtime_snapshot_or_contacts_a_provider() -> None:
    """§10.3 — no capture, no provider call, no network, no ``captured_at`` compare."""

    for function_name in (
        "freeze_final_registration",
        "_derive_stage_c_partition",
        "_final_position_record",
        "_validate_f32",
        "_validate_f37",
    ):
        invoked = _calls_within(function_name)
        assert "RuntimeSnapshotV1" not in invoked
        assert "_runtime_snapshot_from_mapping" not in invoked
    imported = _module_imports()
    for network in ("http", "http.client", "requests", "socket", "urllib", "urllib.request"):
        assert network not in imported
    manifest_keys = set(_mixed_chain().manifest.to_artifact())
    assert "captured_at" not in manifest_keys


# ===========================================================================
# W. §15 K, randomization_mode, and the bidirectional M gate
# ===========================================================================


def test_k_is_zero_and_the_mode_is_exact_when_every_stratum_is_descriptive_only() -> None:
    """§8.3 item 4-5 — ``K = 0`` is legal and no minimum-``K`` rule is invented."""

    chain = _stage_c_chain(DESCRIPTIVE_STATUS_PATTERNS[0], DESCRIPTIVE_STATUS_PATTERNS[3])
    manifest = chain.manifest
    assert manifest.K == 0
    assert manifest.confirmatory_strata == ()
    assert manifest.confirmatory_positions == ()
    assert manifest.descriptive_only_strata
    assert manifest.descriptive_positions
    assert manifest.randomization_mode == RANDOMIZATION_MODE_EXACT_ENUMERATION
    assert manifest.registered_statistical_configuration.randomization_mc_samples is None


@pytest.mark.parametrize(
    ("task_count", "expected_mode", "mc_samples"),
    [
        (1, RANDOMIZATION_MODE_EXACT_ENUMERATION, None),
        (RANDOMIZATION_EXACT_ENUMERATION_MAX_K, RANDOMIZATION_MODE_EXACT_ENUMERATION, None),
        (RANDOMIZATION_EXACT_ENUMERATION_MAX_K + 1, RANDOMIZATION_MODE_MONTE_CARLO, 10_000),
    ],
)
def test_registered_k_and_mode_at_the_frozen_threshold(
    task_count: int, expected_mode: str, mc_samples: int | None
) -> None:
    """§15 — ``K <= 16`` enumerates exactly, ``K > 16`` uses Monte Carlo."""

    chain = _stage_c_chain(
        ALL_PASS, tasks=_stage_c_tasks(task_count), randomization_mc_samples=mc_samples
    )
    assert chain.manifest.K == task_count
    assert chain.manifest.randomization_mode == expected_mode
    assert RANDOMIZATION_MODES == (
        RANDOMIZATION_MODE_EXACT_ENUMERATION,
        RANDOMIZATION_MODE_MONTE_CARLO,
    )


def test_registered_k_counts_distinct_tasks_not_physical_positions() -> None:
    """§15, §6.4 — never a position, stratum, or repetition count."""

    chain = _stage_c_chain(ALL_PASS, ALL_PASS, tasks=_stage_c_tasks(3), count=2)
    manifest = chain.manifest
    assert manifest.K == 3
    assert len(manifest.confirmatory_positions) == 3 * 2 * 2 * 2
    assert len(manifest.confirmatory_strata) == 2
    assert manifest.K != len(manifest.confirmatory_positions)
    assert manifest.K != len(manifest.confirmatory_strata)
    assert manifest.K == len(
        {position.task_id for position in manifest.confirmatory_positions}
    )


def test_registered_k_is_persisted_under_the_exact_key_k() -> None:
    """§6.4 — the field is ``K``; ``registered_k`` is forbidden everywhere."""

    artifact = _simple_chain().manifest.to_artifact()
    assert artifact["K"] == 1
    assert "registered_k" not in artifact
    assert "registered_k" in REGISTRATION_MANIFEST_FORBIDDEN_KEY_NAMES
    # ``"K"`` sorts before every lowercase key under the frozen canonicalization.
    assert canonical_json_bytes(artifact).startswith(b'{"K":')


def test_exact_enumeration_with_a_positive_m_refuses_to_freeze() -> None:
    """§15 — the registered value is neither discarded, ignored, nor reinterpreted."""

    draft = _stage_c_draft(_stage_c_pair(0), randomization_mc_samples=5_000)
    eligibility = _stage_c_eligibility(draft, ALL_PASS)
    with pytest.raises(ConfirmatoryRegistrationError, match="EXACT_ENUMERATION"):
        freeze_final_registration(
            registration_draft=draft, eligibility_manifest=eligibility
        )


def test_monte_carlo_with_a_null_m_refuses_to_freeze() -> None:
    """§15 — final registration refuses; Stage C never selects ``M``."""

    tasks = _stage_c_tasks(RANDOMIZATION_EXACT_ENUMERATION_MAX_K + 1)
    draft = _stage_c_draft(_stage_c_pair(0), tasks=tasks, randomization_mc_samples=None)
    eligibility = _stage_c_eligibility(draft, ALL_PASS)
    with pytest.raises(ConfirmatoryRegistrationError, match="MONTE_CARLO"):
        freeze_final_registration(
            registration_draft=draft, eligibility_manifest=eligibility
        )


def test_monte_carlo_with_a_positive_m_carries_the_stage_a_value_forward() -> None:
    """§15, §11.4 — the registered ``M`` is Stage A's, in exactly one location."""

    tasks = _stage_c_tasks(RANDOMIZATION_EXACT_ENUMERATION_MAX_K + 1)
    chain = _stage_c_chain(ALL_PASS, tasks=tasks, randomization_mc_samples=7)
    manifest = chain.manifest
    assert manifest.randomization_mode == RANDOMIZATION_MODE_MONTE_CARLO
    assert manifest.registered_statistical_configuration.randomization_mc_samples == 7
    artifact = manifest.to_artifact()
    assert artifact["registered_statistical_configuration"]["randomization_mc_samples"] == 7
    assert "randomization_mc_samples" not in set(artifact) - {
        "registered_statistical_configuration"
    }


@pytest.mark.parametrize(
    ("mode", "samples", "match"),
    [
        (RANDOMIZATION_MODE_EXACT_ENUMERATION, 3, "EXACT_ENUMERATION"),
        (RANDOMIZATION_MODE_MONTE_CARLO, None, "MONTE_CARLO"),
    ],
)
def test_a_persisted_mode_m_violation_is_rejected_at_f22(
    mode: str, samples: int | None, match: str, tmp_path: Path
) -> None:
    """F22 — the gate is enforced on load as well as at construction."""

    tasks = (
        _stage_c_tasks(RANDOMIZATION_EXACT_ENUMERATION_MAX_K + 1)
        if mode == RANDOMIZATION_MODE_MONTE_CARLO
        else (STAGE_C_TASK,)
    )
    chain = _stage_c_chain(
        ALL_PASS,
        tasks=tasks,
        randomization_mc_samples=7 if mode == RANDOMIZATION_MODE_MONTE_CARLO else None,
    )

    def mutate(artifact: dict[str, Any]) -> None:
        artifact["registered_statistical_configuration"][
            "randomization_mc_samples"
        ] = samples

    artifact = _stage_c_artifact(chain.manifest, mutate)
    with pytest.raises(ConfirmatoryRegistrationError, match=match):
        _load_stage_c(artifact, chain, tmp_path)


@pytest.mark.parametrize(
    ("path_keys", "match"),
    [
        (("K",), "K"),
        (("confirmatory_positions", 0, "repetition"), "repetition"),
        (("confirmatory_positions", 0, "provider_seed"), "provider_seed"),
        (("confirmatory_positions", 0, "slot"), "slot"),
        (
            ("registered_statistical_configuration", "randomization_mc_samples"),
            "randomization_mc_samples",
        ),
    ],
)
def test_a_bool_is_never_accepted_where_a_json_integer_is_required(
    path_keys: tuple[Any, ...], match: str, tmp_path: Path
) -> None:
    """§7.2, §11.2 — ``bool`` is a subclass of ``int`` and is refused everywhere."""

    chain = _simple_chain()

    def mutate(artifact: dict[str, Any]) -> None:
        target: Any = artifact
        for key in path_keys[:-1]:
            target = target[key]
        target[path_keys[-1]] = True

    artifact = _stage_c_artifact(chain.manifest, mutate)
    with pytest.raises(ConfirmatoryRegistrationError, match=match):
        _load_stage_c(artifact, chain, tmp_path)


def test_stage_c_consults_no_entropy_source_anywhere() -> None:
    """§14.1, §44 — no randomness, no seed, no assignment surface exists."""

    imported = _module_imports()
    for entropy in ("secrets", "random", "numpy", "numpy.random", "os"):
        assert entropy not in imported
    source_names = {
        node.id
        for node in ast.walk(ast.parse(_registration_module_source()))
        if isinstance(node, ast.Name)
    }
    for forbidden in (
        "AssignmentRandomSource",
        "SecretsAssignmentRandomSource",
        "DeterministicAssignmentRandomSource",
        "resolve_label",
        "complement",
        "PCG64",
    ):
        assert forbidden not in source_names
    assert not any(
        name.startswith(("assignment", "randomization_mc_provenance"))
        for name in registration_module.__all__
    )


# ===========================================================================
# X. §9 matrix_digest — the exact five-key preimage
# ===========================================================================


def test_matrix_digest_preimage_is_exactly_the_five_frozen_keys() -> None:
    """§9.2 — no more, no fewer, each the identical value persisted under that key."""

    manifest = _mixed_chain().manifest
    artifact = manifest.to_artifact()
    preimage = manifest.matrix_preimage()
    assert set(preimage) == set(MATRIX_PREIMAGE_KEYS)
    assert len(preimage) == 5
    for key in MATRIX_PREIMAGE_KEYS:
        assert preimage[key] == artifact[key]
    assert manifest.matrix_digest == _expected_matrix_digest(artifact)
    assert (
        manifest.matrix_digest
        == hashlib.sha256(canonical_json_bytes(preimage)).hexdigest()
    )


@pytest.mark.parametrize(
    "excluded",
    [
        "created_at",
        "descriptive_only_strata",
        "descriptive_positions",
        "design_id",
        "eligibility_manifest_digest",
        "matrix_digest",
        "registration_draft_digest",
        "registration_state",
        "schema_version",
        "confirmatory_profile",
        SELF_DIGEST_FIELD,
    ],
)
def test_matrix_digest_preimage_excludes_every_non_matrix_field(excluded: str) -> None:
    """§9.4 — each exclusion is deliberate, including ``self_digest`` and ``created_at``."""

    assert excluded not in _mixed_chain().manifest.matrix_preimage()


def test_matrix_digest_is_stable_for_the_same_semantic_matrix() -> None:
    """§9.6 — the preimage is fully determined before hashing, with no freedom."""

    first = _mixed_chain().manifest
    second = _mixed_chain().manifest
    assert first.matrix_digest == second.matrix_digest
    reordered = dict(reversed(list(first.matrix_preimage().items())))
    assert hashlib.sha256(canonical_json_bytes(reordered)).hexdigest() == (
        first.matrix_digest
    )


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda item: item["confirmatory_positions"][0].__setitem__(
                "provider_seed", 4242
            ),
            id="confirmatory-position",
        ),
        pytest.param(
            lambda item: item["confirmatory_strata"][0].__setitem__(
                "runtime_identity_digest", "d" * 64
            ),
            id="confirmatory-runtime-identity",
        ),
        pytest.param(
            lambda item: item["confirmatory_positions"][0].__setitem__(
                "baseline_label", BASELINE_LABEL_FULL
            ),
            id="baseline-label",
        ),
        pytest.param(lambda item: item.__setitem__("K", 9), id="registered-k"),
        pytest.param(
            lambda item: item.__setitem__(
                "randomization_mode", RANDOMIZATION_MODE_MONTE_CARLO
            ),
            id="randomization-mode",
        ),
        pytest.param(
            lambda item: item["registered_statistical_configuration"].__setitem__(
                "randomization_mc_samples", 99
            ),
            id="registered-statistical-object",
        ),
    ],
)
def test_changing_confirmatory_matrix_material_changes_the_matrix_digest(
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    """§9.3, §9.5 — every registered matrix row is inside the preimage."""

    manifest = _simple_chain().manifest
    artifact = manifest.to_artifact()
    before = _expected_matrix_digest(artifact)
    assert before == manifest.matrix_digest
    mutate(artifact)
    assert _expected_matrix_digest(artifact) != before


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda item: item["descriptive_positions"][0].__setitem__(
                "provider_seed", 4242
            ),
            id="descriptive-position",
        ),
        pytest.param(
            lambda item: item["descriptive_only_strata"].append(
                {"model": "zzz-model", "provider": "zzz-provider"}
            ),
            id="descriptive-stratum",
        ),
        pytest.param(
            lambda item: item.__setitem__("created_at", "2001-02-03T04:05:06Z"),
            id="created-at",
        ),
        pytest.param(
            lambda item: item.__setitem__("design_id", "synthetic-other-design"),
            id="design-id",
        ),
        pytest.param(
            lambda item: item.__setitem__(SELF_DIGEST_FIELD, "0" * 64),
            id="self-digest",
        ),
    ],
)
def test_changing_non_matrix_material_leaves_the_matrix_digest_unchanged(
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    """§9.4 — descriptive reporting material and metadata are outside the preimage."""

    artifact = _mixed_chain().manifest.to_artifact()
    before = _expected_matrix_digest(artifact)
    mutate(artifact)
    assert _expected_matrix_digest(artifact) == before


def test_a_tampered_matrix_digest_is_rejected_at_f23(tmp_path: Path) -> None:
    """F23 — the digest is recomputed from the manifest's own persisted values."""

    chain = _mixed_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item.__setitem__("matrix_digest", "c" * 64),
        reseal_matrix=False,
    )
    with pytest.raises(ConfirmatoryRegistrationError, match="matrix_digest mismatch"):
        _load_stage_c(artifact, chain, tmp_path)


def test_matrix_digest_uses_the_shared_canonical_helper_only() -> None:
    """§9.7 — the algorithm is Work Unit 1's by reference; no second serializer."""

    invoked = _calls_within("_matrix_digest_from_values")
    assert "canonical_json_bytes" in invoked
    assert "hashlib.sha256" in invoked
    assert "json.dumps" not in invoked


def test_self_digest_is_computed_after_and_covers_matrix_digest() -> None:
    """§9.7 steps 3-4, §17.1 — only ``self_digest`` is removed before hashing."""

    manifest = _simple_chain().manifest
    artifact = manifest.to_artifact()
    assert manifest.self_digest == compute_self_digest(artifact)
    verify_self_digest(artifact)
    without_matrix = {
        key: value for key, value in artifact.items() if key != "matrix_digest"
    }
    assert compute_self_digest(without_matrix) != manifest.self_digest
    assert manifest.self_digest == compute_self_digest(manifest.canonical_payload())


def test_a_stale_self_digest_is_rejected_at_f24(tmp_path: Path) -> None:
    """F24 — a content edit that did not recompute the digest is caught, not repaired."""

    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item.__setitem__(SELF_DIGEST_FIELD, "9" * 64),
        reseal_matrix=False,
        reseal_self=False,
    )
    with pytest.raises(ConfirmatoryRegistrationError, match="self_digest mismatch"):
        _load_stage_c(artifact, chain, tmp_path)


# ===========================================================================
# Y. §11 Statistical carry-forward — exact parsed-object equality
# ===========================================================================


def test_registered_statistical_configuration_is_the_exact_stage_a_object() -> None:
    """§11.2 — the same eleven-key object, re-registered, never re-minted."""

    chain = _mixed_chain()
    registered = chain.manifest.to_artifact()["registered_statistical_configuration"]
    proposed = chain.draft.proposed_statistical_configuration.to_dict()
    assert registered == proposed
    assert len(registered) == 11
    assert registered["schema_version"] == PROPOSED_STATISTICAL_CONFIGURATION_SCHEMA_VERSION
    assert registered["schema_version"] == "ProposedStatisticalConfigurationV1"
    assert registered["statistic_spec_id"] == STATISTIC_SPEC_ID
    assert registered["alpha"] == ALPHA
    assert registered["multiplicity_architecture"] == MULTIPLICITY_ARCHITECTURE
    assert registered["primary_endpoint"] == PRIMARY_ENDPOINT
    assert registered["secondary_endpoint_sequence"] == list(SECONDARY_ENDPOINT_SEQUENCE)
    assert registered["primary_estimand_architecture"] == PRIMARY_ESTIMAND_ARCHITECTURE
    assert registered["aggregation_rule"] == AGGREGATION_RULE
    assert registered["treatment_contrast_orientation"] == TREATMENT_CONTRAST_ORIENTATION
    assert (
        registered["randomization_exact_enumeration_max_k"]
        == RANDOMIZATION_EXACT_ENUMERATION_MAX_K
    )
    assert "randomization_mode" not in registered


def test_no_registered_statistical_configuration_schema_literal_is_minted() -> None:
    """§11.3 — no ``RegisteredStatisticalConfigurationV1`` exists anywhere."""

    assert "RegisteredStatisticalConfigurationV1" not in _module_string_constants()
    assert isinstance(
        _simple_chain().manifest.registered_statistical_configuration,
        ProposedStatisticalConfigurationV1,
    )


def test_statistic_spec_id_appears_exactly_once_and_never_at_the_top_level() -> None:
    """§11.4 — one location only; a top-level copy is forbidden."""

    artifact = _simple_chain().manifest.to_artifact()
    assert "statistic_spec_id" not in artifact
    assert (
        artifact["registered_statistical_configuration"]["statistic_spec_id"]
        == STATISTIC_SPEC_ID
    )


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        pytest.param(
            lambda item: item.__setitem__("randomization_mc_samples", 250),
            "randomization_mc_samples",
            id="changed-m",
        ),
        pytest.param(
            lambda item: item.__setitem__("alpha", "0.10"), "alpha", id="changed-alpha"
        ),
        pytest.param(
            lambda item: item.__setitem__(
                "secondary_endpoint_sequence",
                list(reversed(list(SECONDARY_ENDPOINT_SEQUENCE))),
            ),
            "secondary_endpoint_sequence",
            id="reordered-endpoint-sequence",
        ),
        pytest.param(
            lambda item: item.__setitem__("aggregation_rule", "UNWEIGHTED_POOLED"),
            "aggregation_rule",
            id="changed-aggregation-rule",
        ),
        pytest.param(
            lambda item: item.__setitem__("twelfth_key", "synthetic"),
            "unexpected keys",
            id="extra-twelfth-key",
        ),
        pytest.param(
            lambda item: item.pop("treatment_contrast_orientation"),
            "missing keys",
            id="missing-key",
        ),
        pytest.param(
            lambda item: item.__setitem__(
                "schema_version", "RegisteredStatisticalConfigurationV1"
            ),
            "schema_version",
            id="re-minted-schema-literal",
        ),
    ],
)
def test_statistical_carry_forward_rejects_any_difference(
    mutate: Callable[[dict[str, Any]], None], match: str, tmp_path: Path
) -> None:
    """§11.2.1 S1-S7, F21/F33 — no missing, extra, reordered, or altered value."""

    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: mutate(item["registered_statistical_configuration"]),
    )
    with pytest.raises(ConfirmatoryRegistrationError, match=match):
        _load_stage_c(artifact, chain, tmp_path)


def test_statistical_carry_forward_is_never_a_source_byte_comparison(
    tmp_path: Path,
) -> None:
    """§11.2.2, §19 case 70 — a noncanonical draft serialization stays admissible."""

    chain = _simple_chain()
    draft_path = registration_draft_path(tmp_path, chain.draft.design_id)
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_bytes(
        json.dumps(
            chain.draft.to_artifact(), indent=3, sort_keys=False, ensure_ascii=True
        ).encode("utf-8")
        + b"\n"
    )
    reloaded_draft = load_registration_draft(draft_path)
    assert reloaded_draft == chain.draft
    loaded = load_registration_manifest(
        _persist_stage_c(chain.manifest.to_artifact(), tmp_path / "m.json"),
        registration_draft=reloaded_draft,
        eligibility_manifest=chain.eligibility,
    )
    assert loaded == chain.manifest
    assert "_source_bytes" not in _registration_module_source()
    assert "read_bytes" not in _calls_within("_validate_f33")


# ===========================================================================
# Z. §4.4.1 created_at — FREEZE_CAPTURE_METADATA, captured internally
# ===========================================================================


def test_freeze_final_registration_exposes_no_timestamp_or_clock_parameter() -> None:
    """T2 — there is no interface through which a caller could backdate the freeze."""

    parameters = inspect.signature(freeze_final_registration).parameters
    assert set(parameters) == {"registration_draft", "eligibility_manifest"}
    for name in parameters:
        assert not any(
            token in name
            for token in ("created", "clock", "as_of", "timestamp", "now", "time")
        )
    for parameter in parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    # §19 case 67 — a backdating call is not representable: it does not typecheck,
    # and it does not run either.  Routed through ``**kwargs`` only so the static
    # check of this module can still be clean while the runtime refusal is proved.
    backdating_call: dict[str, Any] = {
        "registration_draft": _stage_c_draft(_stage_c_pair(0)),
        "eligibility_manifest": _stage_c_eligibility(
            _stage_c_draft(_stage_c_pair(0)), ALL_PASS
        ),
        "created_at": datetime(2020, 1, 1, tzinfo=UTC),
    }
    with pytest.raises(TypeError, match="created_at"):
        freeze_final_registration(**backdating_call)


def test_created_at_is_captured_internally_in_the_frozen_grammar() -> None:
    """T1, T3 — one internal capture, whole-second UTC with a mandatory ``Z``."""

    before = datetime.now(tz=UTC).replace(microsecond=0)
    manifest = _simple_chain().manifest
    after = datetime.now(tz=UTC)
    assert manifest.created_at.endswith("Z")
    assert len(manifest.created_at) == 20
    captured = datetime.strptime(manifest.created_at, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=UTC
    )
    assert before - timedelta(seconds=1) <= captured <= after + timedelta(seconds=1)
    assert captured.microsecond == 0
    assert "_capture_created_at" in _calls_within("freeze_final_registration")


def test_created_at_is_inside_self_digest_and_outside_matrix_digest() -> None:
    """T5, T6 — authenticated by ``self_digest``; two matrices frozen apart are equal."""

    manifest = _mixed_chain().manifest
    artifact = manifest.to_artifact()
    assert "created_at" in manifest.canonical_payload()
    assert "created_at" not in manifest.matrix_preimage()
    rebranded = dict(artifact, created_at="2001-02-03T04:05:06Z")
    assert compute_self_digest(rebranded) != manifest.self_digest
    assert _expected_matrix_digest(rebranded) == manifest.matrix_digest


def test_created_at_is_never_a_cross_artifact_equality_invariant(tmp_path: Path) -> None:
    """T7 — no rule compares it against the draft's or the eligibility manifest's."""

    chain = _mixed_chain()
    assert chain.draft.created_at == chain.eligibility.created_at
    loaded = _load_stage_c(chain.manifest.to_artifact(), chain, tmp_path)
    assert loaded == chain.manifest
    for number in range(1, 40):
        reads = {
            _dotted(node)
            for node in ast.walk(_function_node(f"_validate_f{number}"))
            if isinstance(node, ast.Attribute)
        }
        assert "registration_draft.created_at" not in reads
        assert "eligibility_manifest.created_at" not in reads


@pytest.mark.parametrize(
    "value",
    [
        "2026-08-27T12:00:00",
        "2026-08-27T12:00:00+00:00",
        "2026-08-27T12:00:00.500Z",
        "2026-08-27 12:00:00Z",
        "not-a-timestamp",
        "2026-13-01T00:00:00Z",
    ],
)
def test_a_malformed_persisted_created_at_is_rejected_at_f6(
    value: str, tmp_path: Path
) -> None:
    """F6 — a persisted-grammar check, and nothing more."""

    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest, lambda item: item.__setitem__("created_at", value)
    )
    with pytest.raises(ConfirmatoryRegistrationError, match="created_at"):
        _load_stage_c(artifact, chain, tmp_path)


def test_created_at_is_the_only_timestamp_field_at_any_depth() -> None:
    """§3, §12 — ``FREEZE_CAPTURE_METADATA`` has exactly one member."""

    def keys(value: Any) -> set[str]:
        found: set[str] = set()
        if isinstance(value, dict):
            for key, item in value.items():
                found.add(key)
                found |= keys(item)
        elif isinstance(value, list):
            for item in value:
                found |= keys(item)
        return found

    present = keys(_mixed_chain().manifest.to_artifact())
    assert "created_at" in present
    for other in ("frozen_at", "sealed_at", "registered_at", "assessed_at", "captured_at"):
        assert other not in present


# ===========================================================================
# AA. §16 F1-F39 — numbered order and observable first-failure precedence
# ===========================================================================


def test_tier_one_applies_f1_through_f25_in_numbered_order() -> None:
    """§16.1 — the order is contractually observable, so it is mechanically fixed."""

    assert _rule_call_sequence("_validate_tier_one") == list(range(1, 26))


def test_tier_two_applies_f26_through_f33_in_numbered_order() -> None:
    """§16.2 — Tier 2 runs only after Tier 1, and in its own numbered order."""

    assert _rule_call_sequence("_validate_tier_two") == list(range(26, 34))


def test_tier_three_applies_f34_through_f37_in_numbered_order() -> None:
    """§16.3 — Tier 3 runs only after Tier 2, and in its own numbered order."""

    assert _rule_call_sequence("_validate_tier_three") == list(range(34, 38))


def test_every_numbered_rule_has_its_own_validator() -> None:
    """§16 — thirty-nine rules, thirty-nine functions, no rule folded into another."""

    namespace = vars(registration_module)
    for number in range(1, 40):
        assert callable(namespace[f"_validate_f{number}"])
    assert "_validate_f40" not in namespace
    assert "_validate_f38a" not in namespace
    assert "_validate_f38b" not in namespace


def test_f38_is_one_rule_with_two_conjuncts_before_f39() -> None:
    """§26 — ``F38a``/``F38b`` are labels, not independent validation positions."""

    write_calls = _calls_within("write_registration_manifest")
    assert "_validate_f38" in write_calls
    assert "_validate_f39" in write_calls
    body = _function_node("write_registration_manifest").body
    order = [
        statement.value.func.id
        for statement in body
        if isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and isinstance(statement.value.func, ast.Name)
        and statement.value.func.id.startswith("_validate_f")
    ]
    assert order == ["_validate_f38", "_validate_f39"]
    inner = _calls_within("_validate_f38")
    assert {"_validate_tier_one", "_validate_tier_two", "_validate_tier_three"} <= inner


def test_the_chain_runs_the_three_tiers_in_order() -> None:
    """§16 — F1-F37 against the complete bound chain, lowest-numbered tier first."""

    body = _function_node("_validate_chain").body
    order = [
        statement.value.func.id
        for statement in body
        if isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and isinstance(statement.value.func, ast.Name)
    ]
    assert order == [
        "_validate_tier_one",
        "_validate_tier_two",
        "_validate_tier_three",
    ]


def test_the_raw_parser_does_not_pre_verify_the_self_digest() -> None:
    """F24 must not run before F1: the envelope parse stops short of verification."""

    parse = vars(registration_module)["_parse_registration_manifest_bytes"]
    artifact = _simple_chain().manifest.to_artifact()
    artifact[SELF_DIGEST_FIELD] = "0" * 64
    parsed = parse(canonical_json_bytes(artifact) + b"\n")
    assert parsed[SELF_DIGEST_FIELD] == "0" * 64
    assert "verify_self_digest" not in _calls_within(
        "_parse_registration_manifest_bytes"
    )
    assert "parse_artifact" not in _calls_within("load_registration_manifest")


def test_no_digest_verification_runs_before_its_own_numbered_rule() -> None:
    """§22 — ``matrix_digest`` is F23 and ``self_digest`` is F24, never earlier."""

    for number in range(1, 23):
        invoked = _calls_within(f"_validate_f{number}")
        assert "_matrix_digest_from_values" not in invoked
        assert "verify_self_digest" not in invoked
        assert "compute_self_digest" not in invoked
    assert "_matrix_digest_from_values" in _calls_within("_validate_f23")
    assert "verify_self_digest" in _calls_within("_validate_f24")
    assert "verify_self_digest" not in _calls_within("_validate_f23")


def test_tier_one_constructs_no_stage_c_dataclass() -> None:
    """§22 — a ``__post_init__`` must not decide which rule a bad artifact fails."""

    for number in list(range(1, 26)) + [0]:
        name = "_validate_tier_one" if number == 0 else f"_validate_f{number}"
        invoked = _calls_within(name)
        for constructor in (
            "RegistrationManifest",
            "ConfirmatoryPositionV1",
            "ConfirmatoryStratumV1",
            "_manifest_from_validated",
            "_position_from_validated",
        ):
            assert constructor not in invoked


def test_upstream_loaders_do_not_run_before_their_numbered_tier() -> None:
    """§16.2, §16.3 — Tier 1 never reads the draft or the eligibility manifest."""

    for number in list(range(1, 26)) + [0]:
        name = "_validate_tier_one" if number == 0 else f"_validate_f{number}"
        invoked = _calls_within(name)
        for loader in (
            "_bound_stage_a_draft",
            "_bound_stage_b_manifest",
            "load_registration_draft",
            "load_eligibility_manifest",
            "freeze_eligibility",
            "_draft_from_artifact",
            "_revalidate_bound_eligibility",
        ):
            assert loader not in invoked
    assert "_draft_from_artifact" in _calls_within("_validate_f26")
    assert "_revalidate_bound_eligibility" in _calls_within("_validate_f34")
    assert "freeze_eligibility" in _calls_within("_revalidate_bound_eligibility")


# --- multi-defect artifacts: the lowest-numbered applicable rule wins -------


def _case_f1_vs_f24() -> tuple[StageCChain, dict[str, Any], str]:
    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item.__setitem__("seventeenth_key", "synthetic"),
        reseal_matrix=False,
        reseal_self=False,
    )
    return chain, artifact, "unexpected keys"


def _case_f2_vs_f23() -> tuple[StageCChain, dict[str, Any], str]:
    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item.__setitem__("schema_version", "ForeignManifestV9"),
        lambda item: item.__setitem__("matrix_digest", "0" * 64),
        reseal_matrix=False,
    )
    return chain, artifact, "schema_version"


def _case_f5_vs_f12() -> tuple[StageCChain, dict[str, Any], str]:
    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item.__setitem__("design_id", "nested/child"),
        lambda item: item["confirmatory_positions"][0].pop("task_id"),
    )
    return chain, artifact, "design_id"


def _case_f6_vs_f23() -> tuple[StageCChain, dict[str, Any], str]:
    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item.__setitem__("created_at", "2026-08-27T12:00:00"),
        lambda item: item.__setitem__("matrix_digest", "0" * 64),
        reseal_matrix=False,
    )
    return chain, artifact, "created_at"


def _case_f9_vs_f19() -> tuple[StageCChain, dict[str, Any], str]:
    chain = _stage_c_chain(ALL_PASS, ALL_PASS)
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item.__setitem__(
            "confirmatory_strata", list(reversed(item["confirmatory_strata"]))
        ),
        lambda item: item.__setitem__("K", 4),
    )
    return chain, artifact, "sorted ascending"


def _case_f12_vs_f16() -> tuple[StageCChain, dict[str, Any], str]:
    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item["confirmatory_positions"][0].__setitem__("slot", 3),
        lambda item: item["confirmatory_positions"][0].__setitem__(
            "position_id", "0" * 64
        ),
    )
    return chain, artifact, "slot"


def _case_f19_vs_f20() -> tuple[StageCChain, dict[str, Any], str]:
    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item.__setitem__("K", 5),
        lambda item: item.__setitem__(
            "randomization_mode", RANDOMIZATION_MODE_MONTE_CARLO
        ),
    )
    return chain, artifact, "K is recorded"


def _case_f21_vs_f22() -> tuple[StageCChain, dict[str, Any], str]:
    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item["registered_statistical_configuration"].__setitem__(
            "alpha", "0.10"
        ),
        lambda item: item["registered_statistical_configuration"].__setitem__(
            "randomization_mc_samples", 5
        ),
    )
    return chain, artifact, "alpha"


def _case_f23_vs_f24() -> tuple[StageCChain, dict[str, Any], str]:
    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item.__setitem__("matrix_digest", "0" * 64),
        reseal_matrix=False,
        reseal_self=False,
    )
    return chain, artifact, "matrix_digest mismatch"


def _case_tier_one_vs_f26() -> tuple[StageCChain, dict[str, Any], str]:
    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item.__setitem__("schema_version", "ForeignManifestV9"),
        lambda item: item.__setitem__("registration_draft_digest", "1" * 64),
    )
    return chain, artifact, "schema_version"


def _case_f26_vs_f34() -> tuple[StageCChain, dict[str, Any], str]:
    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item.__setitem__("registration_draft_digest", "1" * 64),
        lambda item: item.__setitem__("eligibility_manifest_digest", "2" * 64),
    )
    return chain, artifact, "registration_draft_digest"


def _case_f29_vs_f36() -> tuple[StageCChain, dict[str, Any], str]:
    chain = _stage_c_chain(ALL_PASS, DESCRIPTIVE_STATUS_PATTERNS[0])
    digests = _stage_c_runtime_digests(chain.draft)

    def swap_and_drop(artifact: dict[str, Any]) -> None:
        descriptive = artifact["descriptive_only_strata"]
        artifact["confirmatory_strata"] = [
            {
                "model": descriptive[0]["model"],
                "provider": descriptive[0]["provider"],
                "runtime_identity_digest": digests[1],
            }
        ]
        artifact["descriptive_only_strata"] = []
        artifact["confirmatory_positions"] = artifact["descriptive_positions"]
        artifact["descriptive_positions"] = []

    artifact = _stage_c_artifact(chain.manifest, swap_and_drop)
    return chain, artifact, "cover"


def _case_f32_vs_f37() -> tuple[StageCChain, dict[str, Any], str]:
    chain = _simple_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item["confirmatory_strata"][0].__setitem__(
            "runtime_identity_digest", "f" * 64
        ),
    )
    return chain, artifact, "registration-expected digest"


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(_case_f1_vs_f24, id="f1-beats-f24"),
        pytest.param(_case_f2_vs_f23, id="f2-beats-f23"),
        pytest.param(_case_f5_vs_f12, id="f5-beats-f12"),
        pytest.param(_case_f6_vs_f23, id="f6-beats-f23"),
        pytest.param(_case_f9_vs_f19, id="f9-beats-f19"),
        pytest.param(_case_f12_vs_f16, id="f12-beats-f16"),
        pytest.param(_case_f19_vs_f20, id="f19-beats-f20"),
        pytest.param(_case_f21_vs_f22, id="f21-beats-f22"),
        pytest.param(_case_f23_vs_f24, id="f23-beats-f24"),
        pytest.param(_case_tier_one_vs_f26, id="tier-one-beats-f26"),
        pytest.param(_case_f26_vs_f34, id="f26-beats-f34"),
        pytest.param(_case_f29_vs_f36, id="f29-beats-f36"),
        pytest.param(_case_f32_vs_f37, id="f32-beats-f37"),
    ],
)
def test_a_multi_defect_manifest_fails_at_its_lowest_numbered_rule(
    case: Callable[[], tuple[StageCChain, dict[str, Any], str]], tmp_path: Path
) -> None:
    """§16 — for any malformed manifest, the rule that fires is the lowest-numbered."""

    chain, artifact, match = case()
    with pytest.raises(ConfirmatoryRegistrationError, match=match):
        _load_stage_c(artifact, chain, tmp_path)


# ===========================================================================
# AB. §16.5, §17.2 Immutable write-once persistence
# ===========================================================================


def test_registration_manifest_path_is_design_id_scoped(tmp_path: Path) -> None:
    """§17 — one artifact per ``design_id``, inside ``confirmatory_root``."""

    path = registration_manifest_path(tmp_path, STAGE_C_DESIGN_ID)
    assert path == tmp_path / STAGE_C_DESIGN_ID / REGISTRATION_MANIFEST_FILENAME
    assert path.name == "registration_manifest.json"
    assert path.is_relative_to(tmp_path)


@pytest.mark.parametrize(
    "design_id",
    ["..", "../escape", "..\\escape", "nested/child", "nested\\child", "C:", "with\x00null"],
)
def test_registration_manifest_path_rejects_unsafe_design_ids(
    design_id: str, tmp_path: Path
) -> None:
    """§29, G7 — the safe single-segment discipline, reused unchanged."""

    with pytest.raises(ConfirmatoryRegistrationError):
        registration_manifest_path(tmp_path, design_id)


def test_a_valid_write_succeeds_once_and_the_second_write_is_refused(
    tmp_path: Path,
) -> None:
    """F39, §17.2 — never replaced, never truncated, never edited in place."""

    chain = _mixed_chain()
    _written_chain(tmp_path, chain)
    path = write_registration_manifest(chain.manifest, confirmatory_root=tmp_path)
    original = path.read_bytes()
    with pytest.raises(ConfirmatoryRegistrationError, match="immutable"):
        write_registration_manifest(chain.manifest, confirmatory_root=tmp_path)
    assert path.read_bytes() == original


def test_a_second_write_of_a_different_manifest_leaves_the_first_bytes_intact(
    tmp_path: Path,
) -> None:
    """§17.2 — an existing manifest for a ``design_id`` is never superseded in place."""

    chain = _mixed_chain()
    _written_chain(tmp_path, chain)
    path = write_registration_manifest(chain.manifest, confirmatory_root=tmp_path)
    original = path.read_bytes()
    second = freeze_final_registration(
        registration_draft=chain.draft, eligibility_manifest=chain.eligibility
    )
    with pytest.raises(ConfirmatoryRegistrationError, match="immutable"):
        write_registration_manifest(second, confirmatory_root=tmp_path)
    assert path.read_bytes() == original


def test_an_invalid_manifest_creates_no_file(tmp_path: Path) -> None:
    """§16.5 — the full contract runs before any byte reaches disk."""

    chain = _simple_chain()
    _written_chain(tmp_path, chain)
    forged = _forge_like(chain.manifest, self_digest="0" * 64)
    with pytest.raises(ConfirmatoryRegistrationError):
        write_registration_manifest(forged, confirmatory_root=tmp_path)
    assert not (
        tmp_path / STAGE_C_DESIGN_ID / REGISTRATION_MANIFEST_FILENAME
    ).exists()


def test_an_invalid_manifest_creates_no_directory(tmp_path: Path) -> None:
    """§16.5 — path calculation and ``mkdir`` come after every validation."""

    chain = _simple_chain()
    root = tmp_path / "empty-root"
    root.mkdir()
    assert not (root / STAGE_C_DESIGN_ID).exists()
    with pytest.raises(ConfirmatoryRegistrationError, match="registration draft"):
        write_registration_manifest(chain.manifest, confirmatory_root=root)
    assert not (root / STAGE_C_DESIGN_ID).exists()
    assert list(root.iterdir()) == []


def test_direct_registration_manifest_construction_is_not_writable(
    tmp_path: Path,
) -> None:
    chain = _simple_chain()
    _written_chain(tmp_path, chain)
    constructor_values: dict[str, Any] = {
        item.name: getattr(chain.manifest, item.name)
        for item in dataclass_fields(RegistrationManifest)
        if item.init
    }
    direct = RegistrationManifest(**constructor_values)
    assert direct._freeze_provenance is None
    with pytest.raises(ConfirmatoryRegistrationError, match="freeze provenance"):
        write_registration_manifest(direct, confirmatory_root=tmp_path)
    assert not (
        tmp_path / STAGE_C_DESIGN_ID / REGISTRATION_MANIFEST_FILENAME
    ).exists()

    caller_sealed_values = dict(
        constructor_values,
        _freeze_provenance=(direct.created_at, direct.self_digest),
    )
    with pytest.raises(TypeError, match="_freeze_provenance"):
        RegistrationManifest(**caller_sealed_values)


def test_digest_valid_backdated_replace_is_rejected_without_filesystem_mutation(
    tmp_path: Path,
) -> None:
    chain = _simple_chain()
    _written_chain(tmp_path, chain)
    backdated_created_at = "2001-02-03T04:05:06Z"
    backdated_payload = chain.manifest.canonical_payload()
    backdated_payload["created_at"] = backdated_created_at
    backdated = replace(
        chain.manifest,
        created_at=backdated_created_at,
        self_digest=compute_self_digest(backdated_payload),
    )

    verify_self_digest(backdated.to_artifact())
    assert backdated._freeze_provenance is None
    assert replace(chain.manifest)._freeze_provenance is None
    before = {path.relative_to(tmp_path) for path in tmp_path.rglob("*")}
    with pytest.raises(ConfirmatoryRegistrationError, match="freeze provenance"):
        write_registration_manifest(backdated, confirmatory_root=tmp_path)
    after = {path.relative_to(tmp_path) for path in tmp_path.rglob("*")}
    assert after == before
    assert not (
        tmp_path / STAGE_C_DESIGN_ID / REGISTRATION_MANIFEST_FILENAME
    ).exists()


def test_f24_defect_precedes_missing_f38_freeze_provenance(tmp_path: Path) -> None:
    chain = _simple_chain()
    _written_chain(tmp_path, chain)
    digest_invalid_and_unproven = replace(chain.manifest, self_digest="0" * 64)
    assert digest_invalid_and_unproven._freeze_provenance is None
    with pytest.raises(ConfirmatoryRegistrationError, match="self_digest mismatch"):
        write_registration_manifest(
            digest_invalid_and_unproven, confirmatory_root=tmp_path
        )
    assert not (
        tmp_path / STAGE_C_DESIGN_ID / REGISTRATION_MANIFEST_FILENAME
    ).exists()


def test_an_unsafe_design_id_is_rejected_before_any_filesystem_mutation(
    tmp_path: Path,
) -> None:
    """F5 — Tier 1 proves the segment safe before it is used to locate anything."""

    chain = _simple_chain()
    forged = _forge_like(chain.manifest, design_id="nested/child")
    resealed = _forge_like(
        forged, self_digest=compute_self_digest(forged.canonical_payload())
    )
    with pytest.raises(ConfirmatoryRegistrationError, match="design_id"):
        write_registration_manifest(resealed, confirmatory_root=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_final_registration_before_eligibility_is_frozen_is_refused(
    tmp_path: Path,
) -> None:
    """F38a — ``ELIGIBILITY_FROZEN`` strictly precedes ``FINAL_REGISTRATION_FROZEN``."""

    chain = _simple_chain()
    write_registration_draft(chain.draft, confirmatory_root=tmp_path)
    assert not (
        tmp_path / STAGE_C_DESIGN_ID / ELIGIBILITY_MANIFEST_FILENAME
    ).exists()
    with pytest.raises(ConfirmatoryRegistrationError, match="F38"):
        write_registration_manifest(chain.manifest, confirmatory_root=tmp_path)
    assert not (
        tmp_path / STAGE_C_DESIGN_ID / REGISTRATION_MANIFEST_FILENAME
    ).exists()


def test_the_write_is_an_exclusive_create_and_no_update_api_exists() -> None:
    """F39 — ``open("xb")`` only; there is no in-place update surface."""

    modes = {
        node.args[0].value
        for node in ast.walk(_function_node("write_registration_manifest"))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "open"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }
    assert modes == {"xb"}
    for forbidden in ("update", "overwrite", "replace", "truncate", "amend", "promote"):
        assert not any(forbidden in name for name in registration_module.__all__)


def test_written_stage_c_artifacts_stay_inside_the_temporary_directory(
    tmp_path: Path,
) -> None:
    """§31 — no real confirmatory artifact is created anywhere."""

    chain = _simple_chain()
    _written_chain(tmp_path, chain)
    path = write_registration_manifest(chain.manifest, confirmatory_root=tmp_path)
    assert path.is_relative_to(tmp_path)
    assert path.parent.name == STAGE_C_DESIGN_ID
    assert not Path("results/confirmatory").exists()


# ===========================================================================
# AC. §17.1, §17.3 The semantic recanonicalizing reader
# ===========================================================================


def _noncanonical_bytes(artifact: dict[str, Any]) -> bytes:
    """Vary object whitespace and key ordering only — never a registered array."""

    shuffled = dict(reversed(list(artifact.items())))
    return json.dumps(shuffled, indent=3, sort_keys=False, ensure_ascii=True).encode(
        "utf-8"
    ) + b"\n"


def test_semantically_equivalent_noncanonical_manifest_bytes_are_accepted(
    tmp_path: Path,
) -> None:
    """§17.1, §19 case 66 — no byte-for-byte canonical-input gate is added."""

    chain = _mixed_chain()
    artifact = chain.manifest.to_artifact()
    path = tmp_path / "noncanonical.json"
    path.write_bytes(_noncanonical_bytes(artifact))
    assert path.read_bytes() != canonical_json_bytes(artifact) + b"\n"
    loaded = load_registration_manifest(
        path,
        registration_draft=chain.draft,
        eligibility_manifest=chain.eligibility,
    )
    assert loaded == chain.manifest
    assert loaded.matrix_digest == chain.manifest.matrix_digest
    assert loaded.self_digest == chain.manifest.self_digest


def test_a_noncanonical_serialization_keeps_every_registered_array_order(
    tmp_path: Path,
) -> None:
    """§17.1 — array order is a schema precondition, never a serialization artifact."""

    chain = _mixed_chain()
    artifact = chain.manifest.to_artifact()
    path = tmp_path / "noncanonical.json"
    path.write_bytes(_noncanonical_bytes(artifact))
    parsed = json.loads(path.read_text(encoding="utf-8"))
    for key in ("confirmatory_strata", "descriptive_only_strata"):
        assert parsed[key] == artifact[key]
    loaded = load_registration_manifest(
        path,
        registration_draft=chain.draft,
        eligibility_manifest=chain.eligibility,
    )
    assert loaded.confirmatory_positions == chain.manifest.confirmatory_positions
    assert loaded.descriptive_positions == chain.manifest.descriptive_positions


def test_a_semantically_malformed_manifest_stays_rejected_however_it_is_serialized(
    tmp_path: Path,
) -> None:
    """§17.3 — a loader never repairs, normalizes, re-sorts, or reserializes around."""

    chain = _mixed_chain()
    artifact = _stage_c_artifact(
        chain.manifest,
        lambda item: item.__setitem__(
            "confirmatory_positions", list(reversed(item["confirmatory_positions"]))
        ),
    )
    path = tmp_path / "noncanonical.json"
    path.write_bytes(_noncanonical_bytes(artifact))
    with pytest.raises(ConfirmatoryRegistrationError, match="sorted ascending"):
        load_registration_manifest(
            path,
            registration_draft=chain.draft,
            eligibility_manifest=chain.eligibility,
        )
    assert json.loads(path.read_text(encoding="utf-8"))["confirmatory_positions"] == (
        artifact["confirmatory_positions"]
    )


def test_an_unsorted_or_duplicated_persisted_array_is_refused_not_repaired(
    tmp_path: Path,
) -> None:
    """§8.4, F14 — never re-sorted, never deduplicated, never repaired."""

    chain = _mixed_chain()
    duplicated = _stage_c_artifact(
        chain.manifest,
        lambda item: item.__setitem__(
            "descriptive_positions",
            [item["descriptive_positions"][0]] + item["descriptive_positions"],
        ),
    )
    with pytest.raises(ConfirmatoryRegistrationError, match="duplicates"):
        _load_stage_c(duplicated, chain, tmp_path, name="duplicated.json")


def test_stage_c_reuses_the_work_unit_1_and_work_unit_2_surfaces() -> None:
    """§43 — one canonical profile, one Stage-B contract, no fork of either."""

    imported = _module_imports()
    assert "iqa_soa.experiment.confirmatory_eligibility" in imported
    assert {"freeze_eligibility", "load_eligibility_manifest"} <= imported
    assert {"DISPOSITIONS", "REGISTRATION_STATE_ELIGIBILITY_FROZEN"} <= imported
    for e_rule in range(1, 27):
        assert f"_validate_e{e_rule}" not in vars(registration_module)
    invoked = _calls_within("_validate_f21")
    assert "_statistical_from_mapping" in invoked
