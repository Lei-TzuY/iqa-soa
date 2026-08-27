"""Focused Work Unit 4 tests over synthetic temporary registration roots only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import inspect
import json
import os
from pathlib import Path
import secrets
from typing import Any, Callable

import numpy as np
import pytest

import iqa_soa.experiment.confirmatory_assignment as assignment
from iqa_soa.experiment.confirmatory_assignment import (
    ASSIGNMENT_MANIFEST_FILENAME,
    ASSIGNMENT_MANIFEST_SCHEMA_VERSION,
    MC_PROVENANCE_SCHEMA_VERSION,
    AssignmentIntegrityError,
    ConfirmatoryAssignmentError,
    DeterministicAssignmentRandomSource,
    DuplicateAssignmentError,
    DuplicateMcProvenanceError,
    McProvenanceIntegrityError,
    assignment_manifest_path,
    assignment_pending_path,
    load_assignment_manifest,
    load_randomization_mc_provenance,
    persist_assignment,
    persist_randomization_mc_provenance,
    randomization_mc_provenance_path,
)
from iqa_soa.experiment.confirmatory_eligibility import (
    CHANNEL_IDS,
    PREDICATE_IDS,
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
    BASELINE_LABEL_FULL,
    BASELINE_LABEL_OFF,
    CONFIRMATORY_PROFILE,
    ConfirmatoryRegistrationError,
    ProposedPositionV1,
    ProposedProviderSeedEntryV1,
    ProposedRepetitionsEntryV1,
    ProposedRuntimeConfigurationV1,
    ProposedStratumV1,
    RegistrationDraft,
    RegistrationManifest,
    RetryPolicyV1,
    RuntimeSnapshotV1,
    attach_self_digest,
    canonical_json_bytes,
    compute_self_digest,
    draft_registration,
    freeze_final_registration,
    registration_manifest_path,
    write_registration_draft,
    write_registration_manifest,
)


SYNTHETIC_CREATED_AT = datetime(2026, 8, 28, 1, 2, 3, tzinfo=timezone.utc)
SYNTHETIC_PROVIDER = "synthetic-provider"
SYNTHETIC_MODEL = "synthetic-model"
SYNTHETIC_DESIGN_PREFIX = "synthetic-wu4"
SYNTHETIC_EVIDENCE_DIGEST = "e" * 64
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
ALL_PASS = (STATUS_PASS,) * 4
DESCRIPTIVE = (STATUS_FAIL, STATUS_PASS, STATUS_PASS, STATUS_PASS)


@dataclass(frozen=True, slots=True)
class SyntheticChain:
    root: Path
    draft: RegistrationDraft
    eligibility: EligibilityManifestV1
    registration: RegistrationManifest


def _snapshot() -> RuntimeSnapshotV1:
    return RuntimeSnapshotV1(
        provider_name=SYNTHETIC_PROVIDER,
        model=SYNTHETIC_MODEL,
        endpoint="https://synthetic-provider.invalid/v1",
        provider_config_digest="0" * 64,
        provider_parameters_digest="1" * 64,
        timeout_seconds="30",
        retry_policy=RetryPolicyV1(
            max_attempts=1,
            backoff_kind="NONE",
            initial_delay_seconds="0",
            max_delay_seconds="0",
            retryable_error_classes=("SYNTHETIC_ERROR",),
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
        captured_at=SYNTHETIC_CREATED_AT.isoformat(),
    )


def _channel(index: int) -> InfrastructureSymmetryChannelV1:
    return InfrastructureSymmetryChannelV1(
        channel_id=CHANNEL_IDS[index],
        check_status="CHECKED",
        symmetry_result="NO_ASYMMETRY_FOUND",
        evidence_refs=(
            EvidenceReferenceV1(
                evidence_kind="REPOSITORY_PATH",
                locator=f"docs/synthetic-channel-{index}.md",
                content_digest=SYNTHETIC_EVIDENCE_DIGEST,
            ),
        ),
    )


def _eligibility_record(
    runtime_identity_digest: str, statuses: tuple[str, str, str, str]
) -> EligibilityStratumRecordV1:
    predicates = tuple(
        EligibilityPredicateRecordV1(
            predicate_id=PREDICATE_IDS[index],
            status=status,
            evidence_refs=(
                ()
                if index == 1
                else (
                    EvidenceReferenceV1(
                        evidence_kind="REPOSITORY_PATH",
                        locator=f"docs/synthetic-predicate-{index}.md",
                        content_digest=SYNTHETIC_EVIDENCE_DIGEST,
                    ),
                )
            ),
        )
        for index, status in enumerate(statuses)
    )
    return EligibilityStratumRecordV1(
        provider=SYNTHETIC_PROVIDER,
        model=SYNTHETIC_MODEL,
        predicates=predicates,
        infrastructure_symmetry_audit=InfrastructureSymmetryAuditV1(
            channels=tuple(_channel(index) for index in range(len(CHANNEL_IDS)))
        ),
        runtime_identity_digest=runtime_identity_digest,
    )


def _synthetic_chain(
    tmp_path: Path,
    K: int,
    *,
    design_suffix: str = "design",
) -> SyntheticChain:
    """Persist a complete invented Stage-A/B/C chain with registered K."""

    design_id = f"{SYNTHETIC_DESIGN_PREFIX}-{design_suffix}"
    proposed_tasks = (
        tuple(f"synthetic-task-{index:02d}" for index in range(K))
        if K > 0
        else ("synthetic-descriptive-task",)
    )
    stratum = ProposedStratumV1(
        provider=SYNTHETIC_PROVIDER, model=SYNTHETIC_MODEL
    )
    repetitions = tuple(
        ProposedRepetitionsEntryV1(
            task_id=task_id,
            provider=SYNTHETIC_PROVIDER,
            model=SYNTHETIC_MODEL,
            repetition_count=1,
        )
        for task_id in proposed_tasks
    )
    positions = tuple(
        ProposedPositionV1(
            task_id=task_id,
            provider=SYNTHETIC_PROVIDER,
            model=SYNTHETIC_MODEL,
            repetition=0,
            provider_seed=101,
            slot=slot,
            baseline_label=label,
        )
        for task_id in proposed_tasks
        for slot, label in ((1, BASELINE_LABEL_OFF), (2, BASELINE_LABEL_FULL))
    )
    snapshot = _snapshot()
    draft = draft_registration(
        design_id=design_id,
        created_at=SYNTHETIC_CREATED_AT,
        proposed_tasks=proposed_tasks,
        proposed_strata=(stratum,),
        proposed_repetitions=repetitions,
        proposed_provider_seeds=(
            ProposedProviderSeedEntryV1(repetition=0, provider_seed=101),
        ),
        proposed_positions=positions,
        proposed_runtime_configuration=ProposedRuntimeConfigurationV1(
            registration_expected_runtime_snapshots=(snapshot,)
        ),
        proposed_randomization_mc_samples=1001 if K > 16 else None,
    )
    eligibility = freeze_eligibility(
        registration_draft=draft,
        created_at=SYNTHETIC_CREATED_AT,
        eligibility_records=(
            _eligibility_record(
                snapshot.runtime_identity_digest,
                ALL_PASS if K > 0 else DESCRIPTIVE,
            ),
        ),
    )
    registration = freeze_final_registration(
        registration_draft=draft, eligibility_manifest=eligibility
    )
    write_registration_draft(draft, confirmatory_root=tmp_path)
    write_eligibility_manifest(eligibility, confirmatory_root=tmp_path)
    write_registration_manifest(registration, confirmatory_root=tmp_path)
    assert registration.K == K
    return SyntheticChain(tmp_path, draft, eligibility, registration)


def _write_artifact(path: Path, artifact: dict[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(artifact) + b"\n")


def _mutate_and_reseal(
    path: Path, mutation: Callable[[dict[str, Any]], None]
) -> dict[str, Any]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(artifact, dict)
    mutation(artifact)
    sealed = attach_self_digest(artifact)
    _write_artifact(path, sealed)
    return sealed


def _provenance(chain: SyntheticChain) -> assignment.RandomizationMcProvenanceV1:
    return persist_randomization_mc_provenance(
        confirmatory_root=chain.root, design_id=chain.registration.design_id
    )


def _assignment(chain: SyntheticChain) -> assignment.AssignmentManifestV1:
    return persist_assignment(
        confirmatory_root=chain.root, design_id=chain.registration.design_id
    )


def test_k_zero_exact_provenance_is_mandatory_and_has_ten_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 0)
    monkeypatch.setattr(
        secrets,
        "token_bytes",
        lambda count: pytest.fail(f"exact mode requested {count} entropy bytes"),
    )
    provenance = _provenance(chain)
    artifact = provenance.to_artifact()
    assert len(artifact) == 10
    assert artifact["K"] == 0
    assert artifact["exact_support_size"] == 1
    assert "seed_hex" not in artifact
    assert "generated_at" not in artifact
    assert load_randomization_mc_provenance(
        randomization_mc_provenance_path(tmp_path, chain.registration.design_id)
    ) == provenance


def test_k_sixteen_exact_provenance_has_full_support_and_zero_entropy_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 16)
    calls = 0

    def token_bytes(count: int) -> bytes:
        nonlocal calls
        calls += 1
        return bytes(count)

    monkeypatch.setattr(secrets, "token_bytes", token_bytes)
    provenance = _provenance(chain)
    assert provenance.exact_support_size == 65536
    assert calls == 0


def test_k_seventeen_mc_uses_one_32_byte_draw_and_captures_numpy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 17)
    calls: list[int] = []
    raw = bytes(range(32))

    def token_bytes(count: int) -> bytes:
        calls.append(count)
        return raw

    monkeypatch.setattr(secrets, "token_bytes", token_bytes)
    provenance = _provenance(chain)
    artifact = provenance.to_artifact()
    assert len(artifact) == 19
    assert calls == [32]
    assert provenance.seed_hex == raw.hex()
    assert provenance.numpy_version == np.__version__
    assert provenance.randomization_mc_samples == 1001
    assert provenance.exact_support_size is None


def test_leading_zero_seed_bytes_are_preserved_and_seed_int_is_big_endian(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 17)
    raw = b"\x00\x01" + b"\xaa" * 30
    observed_seed_ints: list[int] = []
    real_pcg64 = np.random.PCG64

    def pcg64(seed: int) -> Any:
        observed_seed_ints.append(seed)
        return real_pcg64(seed)

    monkeypatch.setattr(secrets, "token_bytes", lambda count: raw)
    monkeypatch.setattr(np.random, "PCG64", pcg64)
    provenance = _provenance(chain)
    assert provenance.seed_hex == raw.hex()
    assert provenance.seed_hex.startswith("0001")
    assert len(provenance.seed_hex) == 64
    assert observed_seed_ints == [int.from_bytes(raw, "big", signed=False)]


@pytest.mark.parametrize(
    "seed_hex",
    ["0" * 62, "A" * 64, "0x" + "0" * 64, "g" * 64, "0" * 65],
)
def test_seed_hex_grammar_is_exactly_lowercase_64_hex(
    tmp_path: Path, seed_hex: str
) -> None:
    chain = _synthetic_chain(tmp_path, 17)
    _provenance(chain)
    path = randomization_mc_provenance_path(tmp_path, chain.registration.design_id)
    _mutate_and_reseal(path, lambda artifact: artifact.__setitem__("seed_hex", seed_hex))
    with pytest.raises(McProvenanceIntegrityError, match=r"^P13:"):
        load_randomization_mc_provenance(path)


def test_wrong_or_missing_branch_fields_fail_at_p3(tmp_path: Path) -> None:
    exact = _synthetic_chain(tmp_path, 2, design_suffix="exact-fields")
    _provenance(exact)
    exact_path = randomization_mc_provenance_path(tmp_path, exact.registration.design_id)
    artifact = json.loads(exact_path.read_text(encoding="utf-8"))
    artifact["seed_hex"] = "0" * 64
    _write_artifact(exact_path, artifact)
    with pytest.raises(McProvenanceIntegrityError, match=r"^P3:"):
        load_randomization_mc_provenance(exact_path)

    mc = _synthetic_chain(tmp_path, 17, design_suffix="mc-fields")
    _provenance(mc)
    mc_path = randomization_mc_provenance_path(tmp_path, mc.registration.design_id)
    artifact = json.loads(mc_path.read_text(encoding="utf-8"))
    artifact.pop("seed_hex")
    _write_artifact(mc_path, artifact)
    with pytest.raises(McProvenanceIntegrityError, match=r"^P3:"):
        load_randomization_mc_provenance(mc_path)


def test_empty_numpy_version_is_rejected_at_p14_and_generation_captures_current(
    tmp_path: Path,
) -> None:
    chain = _synthetic_chain(tmp_path, 17)
    provenance = _provenance(chain)
    assert provenance.numpy_version == np.__version__
    path = randomization_mc_provenance_path(tmp_path, chain.registration.design_id)
    _mutate_and_reseal(
        path, lambda artifact: artifact.__setitem__("numpy_version", "")
    )
    with pytest.raises(McProvenanceIntegrityError, match=r"^P14:"):
        load_randomization_mc_provenance(path)


def test_duplicate_mc_persistence_draws_no_second_entropy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 17)
    calls = 0

    def token_bytes(count: int) -> bytes:
        nonlocal calls
        calls += 1
        return bytes([calls]) * count

    monkeypatch.setattr(secrets, "token_bytes", token_bytes)
    _provenance(chain)
    with pytest.raises(DuplicateMcProvenanceError):
        _provenance(chain)
    assert calls == 1


def test_failed_mc_persistence_cannot_redraw_entropy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 17)
    calls = 0

    def token_bytes(count: int) -> bytes:
        nonlocal calls
        calls += 1
        return b"\x11" * count

    def fail_fsync(descriptor: int) -> None:
        raise OSError("synthetic fsync failure")

    monkeypatch.setattr(secrets, "token_bytes", token_bytes)
    monkeypatch.setattr(os, "fsync", fail_fsync)
    with pytest.raises(OSError, match="synthetic fsync failure"):
        _provenance(chain)
    assert randomization_mc_provenance_path(
        tmp_path, chain.registration.design_id
    ).exists()
    with pytest.raises(DuplicateMcProvenanceError):
        _provenance(chain)
    assert calls == 1


def test_mc_loader_first_failure_order_is_observable(tmp_path: Path) -> None:
    chain = _synthetic_chain(tmp_path, 2)
    _provenance(chain)
    path = randomization_mc_provenance_path(tmp_path, chain.registration.design_id)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["randomization_mode"] = "UNKNOWN"
    artifact.pop("created_at")
    _write_artifact(path, artifact)
    with pytest.raises(McProvenanceIntegrityError, match=r"^P2:"):
        load_randomization_mc_provenance(path)

    artifact["randomization_mode"] = "EXACT_ENUMERATION"
    artifact["schema_version"] = "Wrong"
    _write_artifact(path, artifact)
    with pytest.raises(McProvenanceIntegrityError, match=r"^P3:"):
        load_randomization_mc_provenance(path)


def test_mc_self_digest_and_upstream_binding_fail_at_p17_then_p19(
    tmp_path: Path,
) -> None:
    chain = _synthetic_chain(tmp_path, 2)
    _provenance(chain)
    path = randomization_mc_provenance_path(tmp_path, chain.registration.design_id)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["created_at"] = "2020-01-01T00:00:00Z"
    _write_artifact(path, artifact)
    with pytest.raises(McProvenanceIntegrityError, match=r"^P17:"):
        load_randomization_mc_provenance(path)

    artifact = attach_self_digest(artifact)
    artifact["final_registration_digest"] = "f" * 64
    artifact = attach_self_digest(artifact)
    _write_artifact(path, artifact)
    with pytest.raises(McProvenanceIntegrityError, match=r"^P19:"):
        load_randomization_mc_provenance(path)


def test_bad_registration_chain_causes_zero_mc_entropy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 17)
    registration_manifest_path(tmp_path, chain.registration.design_id).write_bytes(
        b"not-json"
    )
    monkeypatch.setattr(
        secrets,
        "token_bytes",
        lambda count: pytest.fail(f"bad upstream chain drew {count} entropy bytes"),
    )
    with pytest.raises(McProvenanceIntegrityError, match=r"^P18:") as raised:
        _provenance(chain)
    assert isinstance(raised.value.__cause__, ConfirmatoryRegistrationError)


def test_provenance_semantic_reader_accepts_noncanonical_authenticated_json(
    tmp_path: Path,
) -> None:
    chain = _synthetic_chain(tmp_path, 2)
    provenance = _provenance(chain)
    path = randomization_mc_provenance_path(tmp_path, chain.registration.design_id)
    path.write_text(
        json.dumps(provenance.to_artifact(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    assert load_randomization_mc_provenance(path) == provenance


def test_k_zero_assignment_draws_zero_bits_and_persists_empty_arrays(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 0)
    _provenance(chain)
    monkeypatch.setattr(
        secrets,
        "randbits",
        lambda width: pytest.fail(f"K=0 attempted randbits({width})"),
    )
    manifest = _assignment(chain)
    assert manifest.task_order == ()
    assert manifest.bits == ()
    assert len(manifest.to_artifact()) == 13
    assert assignment_manifest_path(tmp_path, chain.registration.design_id).is_file()


def test_assignment_draws_exactly_k_bits_in_sorted_task_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 3)
    _provenance(chain)
    returned = iter((1, 0, 1))
    widths: list[int] = []

    def randbits(width: int) -> int:
        widths.append(width)
        return next(returned)

    monkeypatch.setattr(secrets, "randbits", randbits)
    manifest = _assignment(chain)
    expected = tuple(sorted({p.task_id for p in chain.registration.confirmatory_positions}))
    assert manifest.task_order == expected
    assert manifest.bits == (1, 0, 1)
    assert widths == [1, 1, 1]
    for position in chain.registration.confirmatory_positions:
        assert manifest.bit_for_task(position.task_id) == manifest.bits[
            manifest.task_order.index(position.task_id)
        ]


@pytest.mark.parametrize("bad_bit", [True, 2])
def test_assignment_loader_rejects_bool_and_two_at_a11(
    tmp_path: Path, bad_bit: Any
) -> None:
    chain = _synthetic_chain(tmp_path, 1)
    _provenance(chain)
    _assignment(chain)
    path = assignment_manifest_path(tmp_path, chain.registration.design_id)
    _mutate_and_reseal(path, lambda artifact: artifact["bits"].__setitem__(0, bad_bit))
    with pytest.raises(AssignmentIntegrityError, match=r"^A11:"):
        load_assignment_manifest(path)


@pytest.mark.parametrize("variant", ["missing", "extra", "duplicate", "reordered"])
def test_assignment_task_order_must_be_exact_registered_cover(
    tmp_path: Path, variant: str
) -> None:
    chain = _synthetic_chain(tmp_path, 2)
    _provenance(chain)
    _assignment(chain)
    path = assignment_manifest_path(tmp_path, chain.registration.design_id)

    def mutate(artifact: dict[str, Any]) -> None:
        if variant == "missing":
            artifact["task_order"].pop()
            artifact["bits"].pop()
        elif variant == "extra":
            artifact["task_order"].append("zz-foreign-task")
            artifact["bits"].append(0)
        elif variant == "duplicate":
            artifact["task_order"][1] = artifact["task_order"][0]
        else:
            artifact["task_order"].reverse()
            artifact["bits"].reverse()

    _mutate_and_reseal(path, mutate)
    expected_rule = "A10" if variant in {"duplicate", "reordered"} else "A21"
    with pytest.raises(AssignmentIntegrityError, match=rf"^{expected_rule}:"):
        load_assignment_manifest(path)


def test_assignment_wrong_upstream_digests_fail_at_a17_and_a20(tmp_path: Path) -> None:
    first = _synthetic_chain(tmp_path, 1, design_suffix="wrong-registration")
    _provenance(first)
    _assignment(first)
    first_path = assignment_manifest_path(tmp_path, first.registration.design_id)
    _mutate_and_reseal(
        first_path,
        lambda artifact: artifact.__setitem__("final_registration_digest", "f" * 64),
    )
    with pytest.raises(AssignmentIntegrityError, match=r"^A17:"):
        load_assignment_manifest(first_path)

    second = _synthetic_chain(tmp_path, 1, design_suffix="wrong-provenance")
    _provenance(second)
    _assignment(second)
    second_path = assignment_manifest_path(tmp_path, second.registration.design_id)
    _mutate_and_reseal(
        second_path,
        lambda artifact: artifact.__setitem__(
            "randomization_mc_provenance_digest", "f" * 64
        ),
    )
    with pytest.raises(AssignmentIntegrityError, match=r"^A20:"):
        load_assignment_manifest(second_path)


def test_missing_provenance_causes_zero_assignment_draws(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 1)
    calls = 0

    def randbits(width: int) -> int:
        nonlocal calls
        calls += 1
        return 0

    monkeypatch.setattr(secrets, "randbits", randbits)
    with pytest.raises(AssignmentIntegrityError, match=r"^A19:") as raised:
        _assignment(chain)
    assert isinstance(raised.value.__cause__, McProvenanceIntegrityError)
    assert calls == 0


def test_corrupt_provenance_causes_zero_assignment_draws(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 1)
    _provenance(chain)
    randomization_mc_provenance_path(
        tmp_path, chain.registration.design_id
    ).write_bytes(b"not-json")
    monkeypatch.setattr(
        secrets,
        "randbits",
        lambda width: pytest.fail(f"corrupt provenance drew randbits({width})"),
    )
    with pytest.raises(AssignmentIntegrityError, match=r"^A19:") as raised:
        _assignment(chain)
    assert isinstance(raised.value.__cause__, McProvenanceIntegrityError)


def test_duplicate_final_assignment_causes_zero_additional_draws(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 1)
    _provenance(chain)
    calls = 0

    def randbits(width: int) -> int:
        nonlocal calls
        calls += 1
        return 1

    monkeypatch.setattr(secrets, "randbits", randbits)
    _assignment(chain)
    with pytest.raises(DuplicateAssignmentError):
        _assignment(chain)
    assert calls == 1


def test_pending_without_final_refuses_before_any_draw(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 1)
    _provenance(chain)
    pending = assignment_pending_path(tmp_path, chain.registration.design_id)
    pending.write_bytes(assignment.ASSIGNMENT_RESERVATION_MARKER)
    calls = 0

    def randbits(width: int) -> int:
        nonlocal calls
        calls += 1
        return 0

    monkeypatch.setattr(secrets, "randbits", randbits)
    with pytest.raises(AssignmentIntegrityError, match=r"^R1:"):
        _assignment(chain)
    assert calls == 0


def test_deterministic_source_is_test_only_and_cannot_reach_persistence() -> None:
    source = DeterministicAssignmentRandomSource((1, 0))
    assert assignment._draw_assignment_bits(
        source,
        ("a", "b"),
        confirmatory_profile=CONFIRMATORY_PROFILE,
        persisting=False,
    ) == (1, 0)
    with pytest.raises(ConfirmatoryAssignmentError, match="deterministic"):
        assignment._draw_assignment_bits(
            DeterministicAssignmentRandomSource((1,)),
            ("a",),
            confirmatory_profile=CONFIRMATORY_PROFILE,
            persisting=True,
        )


def test_production_randomness_and_timestamp_injection_surfaces_do_not_exist() -> None:
    for operation in (persist_randomization_mc_provenance, persist_assignment):
        signature = inspect.signature(operation)
        assert set(signature.parameters) == {"confirmatory_root", "design_id"}
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in signature.parameters.values()
        )
    forbidden = {
        "seed",
        "seed_hex",
        "bits",
        "timestamp",
        "clock",
        "random_source",
        "numpy_version",
        "python_version",
    }
    assert forbidden.isdisjoint(inspect.signature(persist_assignment).parameters)
    assert forbidden.isdisjoint(
        inspect.signature(persist_randomization_mc_provenance).parameters
    )


def test_assignment_a1_a16_a19_are_wrapped_with_required_causes(tmp_path: Path) -> None:
    malformed_path = tmp_path / "malformed" / ASSIGNMENT_MANIFEST_FILENAME
    malformed_path.parent.mkdir()
    malformed_path.write_bytes(b"not-json")
    with pytest.raises(AssignmentIntegrityError, match=r"^A1:"):
        load_assignment_manifest(malformed_path)

    a16_chain = _synthetic_chain(tmp_path, 1, design_suffix="a16")
    _provenance(a16_chain)
    _assignment(a16_chain)
    registration_manifest_path(
        tmp_path, a16_chain.registration.design_id
    ).write_bytes(b"not-json")
    with pytest.raises(AssignmentIntegrityError, match=r"^A16:") as a16:
        load_assignment_manifest(
            assignment_manifest_path(tmp_path, a16_chain.registration.design_id)
        )
    assert isinstance(a16.value.__cause__, ConfirmatoryRegistrationError)

    a19_chain = _synthetic_chain(tmp_path, 1, design_suffix="a19")
    _provenance(a19_chain)
    _assignment(a19_chain)
    randomization_mc_provenance_path(
        tmp_path, a19_chain.registration.design_id
    ).write_bytes(b"not-json")
    with pytest.raises(AssignmentIntegrityError, match=r"^A19:") as a19:
        load_assignment_manifest(
            assignment_manifest_path(tmp_path, a19_chain.registration.design_id)
        )
    assert isinstance(a19.value.__cause__, McProvenanceIntegrityError)


def test_assignment_local_first_failure_precedes_digest_and_dependency_failures(
    tmp_path: Path,
) -> None:
    a2_chain = _synthetic_chain(tmp_path, 1, design_suffix="a2-precedence")
    _provenance(a2_chain)
    _assignment(a2_chain)
    a2_path = assignment_manifest_path(tmp_path, a2_chain.registration.design_id)
    artifact = json.loads(a2_path.read_text(encoding="utf-8"))
    artifact.pop("source_api")
    artifact["schema_version"] = "Wrong"
    _write_artifact(a2_path, artifact)
    registration_manifest_path(tmp_path, a2_chain.registration.design_id).write_bytes(
        b"not-json"
    )
    with pytest.raises(AssignmentIntegrityError, match=r"^A2:"):
        load_assignment_manifest(a2_path)

    a15_chain = _synthetic_chain(tmp_path, 1, design_suffix="a15-precedence")
    _provenance(a15_chain)
    _assignment(a15_chain)
    a15_path = assignment_manifest_path(tmp_path, a15_chain.registration.design_id)
    artifact = json.loads(a15_path.read_text(encoding="utf-8"))
    artifact["generation_started_at"] = "2020-01-01T00:00:00Z"
    artifact["generation_completed_at"] = "2020-01-01T00:00:00Z"
    _write_artifact(a15_path, artifact)
    registration_manifest_path(
        tmp_path, a15_chain.registration.design_id
    ).write_bytes(b"not-json")
    with pytest.raises(AssignmentIntegrityError, match=r"^A15:"):
        load_assignment_manifest(a15_path)


def test_assignment_semantic_reader_accepts_noncanonical_authenticated_json(
    tmp_path: Path,
) -> None:
    chain = _synthetic_chain(tmp_path, 1)
    _provenance(chain)
    manifest = _assignment(chain)
    path = assignment_manifest_path(tmp_path, chain.registration.design_id)
    path.write_text(
        json.dumps(manifest.to_artifact(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    assert load_assignment_manifest(path) == manifest


def test_pending_reservation_is_durable_and_visible_before_first_draw(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 1)
    _provenance(chain)
    pending = assignment_pending_path(tmp_path, chain.registration.design_id)

    def randbits(width: int) -> int:
        assert width == 1
        assert pending.read_bytes() == assignment.ASSIGNMENT_RESERVATION_MARKER
        return 0

    monkeypatch.setattr(secrets, "randbits", randbits)
    _assignment(chain)


def test_failure_after_draw_retains_no_redraw_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 2)
    _provenance(chain)
    calls = 0

    def randbits(width: int) -> int:
        nonlocal calls
        calls += 1
        return calls % 2

    def fail_stage(path: Path, payload: bytes) -> None:
        raise OSError("synthetic post-draw staging failure")

    monkeypatch.setattr(secrets, "randbits", randbits)
    monkeypatch.setattr(assignment, "_stage_assignment", fail_stage)
    with pytest.raises(OSError, match="post-draw staging failure"):
        _assignment(chain)
    pending = assignment_pending_path(tmp_path, chain.registration.design_id)
    final = assignment_manifest_path(tmp_path, chain.registration.design_id)
    assert pending.exists()
    assert not final.exists()
    with pytest.raises(AssignmentIntegrityError, match=r"^R1:"):
        _assignment(chain)
    assert calls == 2


def test_publication_uses_no_clobber_link_and_never_streams_to_final() -> None:
    module_source = inspect.getsource(assignment)
    persist_source = inspect.getsource(persist_assignment)
    publish_source = inspect.getsource(assignment._publish_assignment_no_clobber)
    assert "os.replace" not in module_source
    assert "os.link" in publish_source
    assert ".open(" not in persist_source


def test_no_clobber_publication_preserves_existing_final(tmp_path: Path) -> None:
    pending = tmp_path / "assignment_manifest.json.pending"
    final = tmp_path / ASSIGNMENT_MANIFEST_FILENAME
    pending.write_bytes(b"new")
    final.write_bytes(b"old")
    with pytest.raises(FileExistsError):
        assignment._publish_assignment_no_clobber(pending, final)
    assert final.read_bytes() == b"old"
    assert pending.read_bytes() == b"new"


def test_r5_r5prime_r6_order_is_literal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 1)
    _provenance(chain)
    events: list[str] = []

    def reserve(path: Path) -> None:
        events.append("reserve")
        path.write_bytes(assignment.ASSIGNMENT_RESERVATION_MARKER)

    def draw(width: int) -> int:
        events.append("draw")
        return 0

    def stage(path: Path, payload: bytes) -> None:
        events.append("stage")
        path.write_bytes(payload)

    def publish(pending: Path, final: Path) -> None:
        events.append("R5")
        os.link(pending, final)

    def sync(directory: Path) -> None:
        assert (directory / ASSIGNMENT_MANIFEST_FILENAME).exists()
        events.append("R5prime")

    def unlink(path: Path) -> None:
        events.append("R6")
        path.unlink()

    monkeypatch.setattr(assignment, "_reserve_assignment", reserve)
    monkeypatch.setattr(secrets, "randbits", draw)
    monkeypatch.setattr(assignment, "_stage_assignment", stage)
    monkeypatch.setattr(assignment, "_publish_assignment_no_clobber", publish)
    monkeypatch.setattr(assignment, "_sync_directory_metadata", sync)
    monkeypatch.setattr(
        assignment, "_unlink_pending_after_durable_publication", unlink
    )
    _assignment(chain)
    assert events == ["reserve", "draw", "stage", "R5", "R5prime", "R6"]


def test_r5prime_failure_retains_pending_and_prevents_redraw(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 1)
    _provenance(chain)
    real_sync = assignment._sync_directory_metadata
    draws = 0

    def randbits(width: int) -> int:
        nonlocal draws
        draws += 1
        return 1

    def fail_after_final(directory: Path) -> None:
        if (directory / ASSIGNMENT_MANIFEST_FILENAME).exists():
            raise OSError("synthetic R5-prime failure")
        real_sync(directory)

    monkeypatch.setattr(secrets, "randbits", randbits)
    monkeypatch.setattr(assignment, "_sync_directory_metadata", fail_after_final)
    with pytest.raises(OSError, match="R5-prime failure"):
        _assignment(chain)
    final = assignment_manifest_path(tmp_path, chain.registration.design_id)
    pending = assignment_pending_path(tmp_path, chain.registration.design_id)
    assert final.exists()
    assert pending.exists()
    with pytest.raises(DuplicateAssignmentError):
        _assignment(chain)
    assert draws == 1


def test_final_plus_pending_is_final_authoritative_and_never_redraws(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chain = _synthetic_chain(tmp_path, 1)
    _provenance(chain)
    _assignment(chain)
    pending = assignment_pending_path(tmp_path, chain.registration.design_id)
    pending.write_bytes(assignment.ASSIGNMENT_RESERVATION_MARKER)
    monkeypatch.setattr(
        secrets,
        "randbits",
        lambda width: pytest.fail("final + pending attempted redraw"),
    )
    with pytest.raises(DuplicateAssignmentError):
        _assignment(chain)


def test_pending_never_enters_scientific_schema_or_digest(tmp_path: Path) -> None:
    chain = _synthetic_chain(tmp_path, 1)
    _provenance(chain)
    manifest = _assignment(chain)
    artifact = manifest.to_artifact()
    assert len(artifact) == 13
    assert set(artifact) == assignment._ASSIGNMENT_KEYS
    assert all("pending" not in key for key in artifact)
    assert artifact["schema_version"] == ASSIGNMENT_MANIFEST_SCHEMA_VERSION
    assert artifact["self_digest"] == compute_self_digest(artifact)
    assert not assignment_pending_path(tmp_path, chain.registration.design_id).exists()


def test_schema_literals_and_file_names_are_exact(tmp_path: Path) -> None:
    chain = _synthetic_chain(tmp_path, 1)
    provenance = _provenance(chain)
    manifest = _assignment(chain)
    assert provenance.schema_version == MC_PROVENANCE_SCHEMA_VERSION
    assert manifest.schema_version == ASSIGNMENT_MANIFEST_SCHEMA_VERSION
    assert randomization_mc_provenance_path(
        tmp_path, chain.registration.design_id
    ).name == "randomization_mc_provenance.json"
    assert assignment_manifest_path(
        tmp_path, chain.registration.design_id
    ).name == "assignment_manifest.json"
