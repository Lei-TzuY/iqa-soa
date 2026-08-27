"""Focused tests for the Stage-A registration draft and canonical digest profile.

Every artifact these tests write lives in a pytest ``tmp_path``.  No real
``design_id``, task, provider, model, seed, or endpoint appears anywhere here,
nothing is written under ``results/``, and no randomness, provider, or network is
touched: the code implementation authorization keeps
``ACTUAL_CONFIRMATORY_REGISTRATION_AUTHORIZED: NO``, so these are synthetic test
artifacts and nothing more.

The proposed baseline labels below are likewise synthetic: they exercise the
schema's structural balance rule, and no assignment bit is drawn anywhere in
this module.
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields, replace
from datetime import UTC, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from iqa_soa.experiment.confirmatory_registration import (
    AGGREGATION_RULE,
    ALPHA,
    BASELINE_LABEL_FULL,
    BASELINE_LABEL_OFF,
    BASELINE_LABELS,
    CONFIRMATORY_PROFILE,
    ConfirmatoryRegistrationError,
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
    REGISTRATION_DRAFT_FILENAME,
    REGISTRATION_DRAFT_SCHEMA_VERSION,
    REGISTRATION_STATE_DRAFT,
    RegistrationDraft,
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
    load_registration_draft,
    parse_artifact,
    registration_draft_path,
    serialize_artifact,
    verify_self_digest,
    write_registration_draft,
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
