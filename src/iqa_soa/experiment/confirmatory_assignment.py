"""Work Unit 4 confirmatory provenance and assignment persistence.

This module implements the two immutable artifacts that follow a validated
``FINAL_REGISTRATION_FROZEN`` chain:

* ``randomization_mc_provenance.json`` in its exact ten-key or Monte-Carlo
  nineteen-key tagged shape; and
* ``assignment_manifest.json`` with one production bit per registered task.

The public production operations accept only the address of a design.  They
reload the complete registration chain from disk, capture every timestamp and
environment value internally, and return randomness only after it has been
persisted.  Canonical JSON and ``self_digest`` remain owned by
``confirmatory_registration`` and are reused here without a second algorithm.
"""

from __future__ import annotations

from collections.abc import Sequence
import ctypes
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import secrets
from typing import Any, Protocol, cast

import numpy as np

from iqa_soa.experiment.confirmatory_eligibility import (
    ConfirmatoryEligibilityError,
    EligibilityManifestV1,
    eligibility_manifest_path,
    load_eligibility_manifest,
)
from iqa_soa.experiment.confirmatory_registration import (
    CONFIRMATORY_PROFILE,
    RANDOMIZATION_MODE_EXACT_ENUMERATION,
    RANDOMIZATION_MODE_MONTE_CARLO,
    STATISTIC_SPEC_ID,
    ConfirmatoryRegistrationError,
    RegistrationDraft,
    RegistrationManifest,
    attach_self_digest,
    load_registration_draft,
    load_registration_manifest,
    registration_draft_path,
    registration_manifest_path,
    serialize_artifact,
    verify_self_digest,
)
from iqa_soa.types import QAMode

__all__ = [
    "ASSIGNMENT_MANIFEST_FILENAME",
    "ASSIGNMENT_MANIFEST_SCHEMA_VERSION",
    "MC_PROVENANCE_SCHEMA_VERSION",
    "RANDOMIZATION_MC_PROVENANCE_FILENAME",
    "AssignmentIntegrityError",
    "AssignmentManifestV1",
    "AssignmentNotPersistedError",
    "AssignmentRandomSource",
    "ConfirmatoryAssignmentError",
    "DeterministicAssignmentRandomSource",
    "DuplicateAssignmentError",
    "DuplicateMcProvenanceError",
    "McProvenanceIntegrityError",
    "RandomizationMcProvenanceV1",
    "SecretsAssignmentRandomSource",
    "assignment_manifest_path",
    "assignment_pending_path",
    "complement",
    "load_assignment_manifest",
    "load_randomization_mc_provenance",
    "persist_assignment",
    "persist_randomization_mc_provenance",
    "randomization_mc_provenance_path",
    "resolve_label",
]


class ConfirmatoryAssignmentError(ValueError):
    """Base error for Work Unit 4 construction and integrity failures."""


class McProvenanceIntegrityError(ConfirmatoryAssignmentError):
    """The MC-provenance artifact is malformed, inconsistent, or wrongly bound."""


class DuplicateMcProvenanceError(ConfirmatoryAssignmentError):
    """MC provenance already exists for this design and must not be regenerated."""


class AssignmentIntegrityError(ConfirmatoryAssignmentError):
    """The assignment artifact or one of its required dependencies is invalid."""


class DuplicateAssignmentError(ConfirmatoryAssignmentError):
    """A final assignment manifest already exists for this design."""


class AssignmentNotPersistedError(ConfirmatoryAssignmentError):
    """Confirmatory execution was requested without a persisted assignment."""


RANDOMIZATION_MC_PROVENANCE_FILENAME = "randomization_mc_provenance.json"
ASSIGNMENT_MANIFEST_FILENAME = "assignment_manifest.json"
ASSIGNMENT_PENDING_SUFFIX = ".pending"
ASSIGNMENT_RESERVATION_MARKER = b"ASSIGNMENT_GENERATION_RESERVED_V1\n"

MC_PROVENANCE_SCHEMA_VERSION = "RandomizationMcProvenanceV1"
ASSIGNMENT_MANIFEST_SCHEMA_VERSION = "AssignmentManifestV1"

MC_SOURCE_KIND = "PYTHON_SECRETS_TOKEN_BYTES"
MC_SOURCE_API = "secrets.token_bytes"
MC_ENTROPY_BYTES = 32
MC_SEED_ENCODING = "uint256_big_endian"
MC_RNG_LIBRARY = "numpy"
MC_RNG_BIT_GENERATOR = "PCG64"

ASSIGNMENT_SOURCE_KIND = "PYTHON_SECRETS_RANDBITS"
ASSIGNMENT_SOURCE_API = "secrets.randbits"

_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SEED_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")

_MC_COMMON_KEYS = frozenset(
    {
        "schema_version",
        "confirmatory_profile",
        "design_id",
        "final_registration_digest",
        "randomization_mode",
        "created_at",
        "K",
        "statistic_spec_id",
        "self_digest",
    }
)
_MC_EXACT_KEYS = _MC_COMMON_KEYS | {"exact_support_size"}
_MC_MONTE_CARLO_KEYS = _MC_COMMON_KEYS | {
    "source_kind",
    "source_api",
    "entropy_bytes",
    "seed_hex",
    "seed_encoding",
    "rng_library",
    "rng_bit_generator",
    "numpy_version",
    "randomization_mc_samples",
    "generated_at",
}
_ASSIGNMENT_KEYS = frozenset(
    {
        "schema_version",
        "confirmatory_profile",
        "design_id",
        "final_registration_digest",
        "randomization_mc_provenance_digest",
        "task_order",
        "bits",
        "source_kind",
        "source_api",
        "python_version",
        "generation_started_at",
        "generation_completed_at",
        "self_digest",
    }
)


@dataclass(frozen=True, slots=True)
class RandomizationMcProvenanceV1:
    """The frozen ten-key / nineteen-key tagged provenance record."""

    schema_version: str
    confirmatory_profile: str
    design_id: str
    final_registration_digest: str
    randomization_mode: str
    created_at: str
    K: int
    statistic_spec_id: str
    self_digest: str
    exact_support_size: int | None
    source_kind: str | None
    source_api: str | None
    entropy_bytes: int | None
    seed_hex: str | None
    seed_encoding: str | None
    rng_library: str | None
    rng_bit_generator: str | None
    numpy_version: str | None
    randomization_mc_samples: int | None
    generated_at: str | None

    def to_artifact(self) -> dict[str, Any]:
        common: dict[str, Any] = {
            "K": self.K,
            "confirmatory_profile": self.confirmatory_profile,
            "created_at": self.created_at,
            "design_id": self.design_id,
            "final_registration_digest": self.final_registration_digest,
            "randomization_mode": self.randomization_mode,
            "schema_version": self.schema_version,
            "self_digest": self.self_digest,
            "statistic_spec_id": self.statistic_spec_id,
        }
        if self.randomization_mode == RANDOMIZATION_MODE_EXACT_ENUMERATION:
            common["exact_support_size"] = self.exact_support_size
            return common
        common.update(
            {
                "entropy_bytes": self.entropy_bytes,
                "generated_at": self.generated_at,
                "numpy_version": self.numpy_version,
                "randomization_mc_samples": self.randomization_mc_samples,
                "rng_bit_generator": self.rng_bit_generator,
                "rng_library": self.rng_library,
                "seed_encoding": self.seed_encoding,
                "seed_hex": self.seed_hex,
                "source_api": self.source_api,
                "source_kind": self.source_kind,
            }
        )
        return common


@dataclass(frozen=True, slots=True)
class AssignmentManifestV1:
    """The frozen thirteen-key task-level assignment record."""

    schema_version: str
    confirmatory_profile: str
    design_id: str
    final_registration_digest: str
    randomization_mc_provenance_digest: str
    task_order: tuple[str, ...]
    bits: tuple[int, ...]
    source_kind: str
    source_api: str
    python_version: str
    generation_started_at: str
    generation_completed_at: str
    self_digest: str

    def to_artifact(self) -> dict[str, Any]:
        return {
            "bits": list(self.bits),
            "confirmatory_profile": self.confirmatory_profile,
            "design_id": self.design_id,
            "final_registration_digest": self.final_registration_digest,
            "generation_completed_at": self.generation_completed_at,
            "generation_started_at": self.generation_started_at,
            "python_version": self.python_version,
            "randomization_mc_provenance_digest": (
                self.randomization_mc_provenance_digest
            ),
            "schema_version": self.schema_version,
            "self_digest": self.self_digest,
            "source_api": self.source_api,
            "source_kind": self.source_kind,
            "task_order": list(self.task_order),
        }

    def bit_for_task(self, task_id: str) -> int:
        """Return the one persisted bit shared by every position of ``task_id``."""

        try:
            index = self.task_order.index(task_id)
        except ValueError as error:
            raise AssignmentIntegrityError(
                f"task has no persisted assignment bit: {task_id!r}"
            ) from error
        return self.bits[index]


class AssignmentRandomSource(Protocol):
    """The frozen one-bit source boundary used by the internal draw helper."""

    def draw_bit(self) -> int:
        """Return one JSON-integer assignment bit."""


class SecretsAssignmentRandomSource:
    """The only source a production assignment persistence path constructs."""

    def draw_bit(self) -> int:
        return secrets.randbits(1)


class DeterministicAssignmentRandomSource:
    """A finite, deterministic bit sequence for focused tests only."""

    __slots__ = ("_bits", "_index")

    def __init__(self, bits: Sequence[int]) -> None:
        checked: list[int] = []
        for index, bit in enumerate(bits):
            if not _is_json_integer(bit) or bit not in (0, 1):
                raise ConfirmatoryAssignmentError(
                    f"deterministic test bit {index} must be integer 0 or 1, got "
                    f"{bit!r}"
                )
            checked.append(bit)
        self._bits = tuple(checked)
        self._index = 0

    def draw_bit(self) -> int:
        if self._index >= len(self._bits):
            raise ConfirmatoryAssignmentError(
                "deterministic assignment source is exhausted"
            )
        bit = self._bits[self._index]
        self._index += 1
        return bit


def complement(baseline_label: QAMode) -> QAMode:
    """The exact OFF/FULL complement; other modes are outside this design."""

    if baseline_label is QAMode.OFF:
        return QAMode.FULL
    if baseline_label is QAMode.FULL:
        return QAMode.OFF
    raise ConfirmatoryAssignmentError(
        "confirmatory baseline label must be QAMode.OFF or QAMode.FULL, got "
        f"{baseline_label!r}"
    )


def resolve_label(baseline_label: QAMode, b_k: int) -> QAMode:
    """Apply one task-level bit to one registered baseline label."""

    if not _is_json_integer(b_k) or b_k not in (0, 1):
        raise ConfirmatoryAssignmentError(
            f"b_k must be a JSON integer equal to 0 or 1, got {b_k!r}"
        )
    return baseline_label if b_k == 0 else complement(baseline_label)


def randomization_mc_provenance_path(
    confirmatory_root: Path, design_id: str
) -> Path:
    """Return the safe, design-scoped MC-provenance path."""

    try:
        design_directory = registration_manifest_path(
            Path(confirmatory_root), design_id
        ).parent
    except ConfirmatoryRegistrationError as error:
        raise ConfirmatoryAssignmentError(
            f"invalid MC-provenance path: {error}"
        ) from error
    return design_directory / RANDOMIZATION_MC_PROVENANCE_FILENAME


def assignment_manifest_path(confirmatory_root: Path, design_id: str) -> Path:
    """Return the safe, design-scoped scientific assignment path."""

    try:
        design_directory = registration_manifest_path(
            Path(confirmatory_root), design_id
        ).parent
    except ConfirmatoryRegistrationError as error:
        raise ConfirmatoryAssignmentError(
            f"invalid assignment-manifest path: {error}"
        ) from error
    return design_directory / ASSIGNMENT_MANIFEST_FILENAME


def assignment_pending_path(confirmatory_root: Path, design_id: str) -> Path:
    """Return the operational reservation/staging path; never a scientific path."""

    final_path = assignment_manifest_path(confirmatory_root, design_id)
    return final_path.with_name(final_path.name + ASSIGNMENT_PENDING_SUFFIX)


def _is_json_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _has_digest_grammar(value: Any) -> bool:
    return isinstance(value, str) and _DIGEST_PATTERN.fullmatch(value) is not None


def _timestamp_instant(value: Any) -> datetime | None:
    if not isinstance(value, str) or _TIMESTAMP_PATTERN.fullmatch(value) is None:
        return None
    try:
        return datetime.strptime(value, _TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _capture_timestamp() -> str:
    return datetime.now(tz=timezone.utc).strftime(_TIMESTAMP_FORMAT)


def _require_string_keys(value: Any) -> bool:
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _require_string_keys(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return all(_require_string_keys(item) for item in value)
    return True


def _mc_failure(rule: str, message: str) -> McProvenanceIntegrityError:
    return McProvenanceIntegrityError(f"{rule}: {message}")


def _assignment_failure(rule: str, message: str) -> AssignmentIntegrityError:
    return AssignmentIntegrityError(f"{rule}: {message}")


def _parse_mc_file(path: Path) -> dict[str, Any]:
    try:
        data = Path(path).read_bytes()
    except OSError as error:
        raise _mc_failure("P1", f"cannot read provenance file: {error}") from error
    if data.endswith(b"\n"):
        data = data[:-1]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _mc_failure("P1", f"provenance is not UTF-8: {error}") from error
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise _mc_failure("P1", f"provenance is not valid JSON: {error}") from error
    if not isinstance(parsed, dict) or not _require_string_keys(parsed):
        raise _mc_failure(
            "P1", "provenance must be a JSON object with string keys at every depth"
        )
    return cast(dict[str, Any], parsed)


def _parse_assignment_file(path: Path) -> dict[str, Any]:
    try:
        data = Path(path).read_bytes()
    except OSError as error:
        raise _assignment_failure(
            "A1", f"cannot read assignment manifest: {error}"
        ) from error
    if data.endswith(b"\n"):
        data = data[:-1]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _assignment_failure(
            "A1", f"assignment manifest is not UTF-8: {error}"
        ) from error
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise _assignment_failure(
            "A1", f"assignment manifest is not valid JSON: {error}"
        ) from error
    if not isinstance(parsed, dict) or not _require_string_keys(parsed):
        raise _assignment_failure(
            "A1",
            "assignment manifest must be a JSON object with string keys at every depth",
        )
    return cast(dict[str, Any], parsed)


def _validate_mc_tier_one(artifact: dict[str, Any]) -> str:
    # P2: the tag is intentionally the first interpreted field.
    mode = artifact.get("randomization_mode")
    if not isinstance(mode, str) or mode not in {
        RANDOMIZATION_MODE_EXACT_ENUMERATION,
        RANDOMIZATION_MODE_MONTE_CARLO,
    }:
        raise _mc_failure("P2", "randomization_mode is missing or unknown")

    # P3: exact branch key set, including complementary forbidden fields.
    expected_keys = (
        _MC_EXACT_KEYS
        if mode == RANDOMIZATION_MODE_EXACT_ENUMERATION
        else _MC_MONTE_CARLO_KEYS
    )
    if set(artifact) != expected_keys:
        raise _mc_failure(
            "P3",
            f"wrong top-level key set; expected={sorted(expected_keys)!r} "
            f"actual={sorted(artifact)!r}",
        )

    # P4-P6: literals and safe design-id grammar.
    if artifact["schema_version"] != MC_PROVENANCE_SCHEMA_VERSION:
        raise _mc_failure("P4", "wrong schema_version")
    if artifact["confirmatory_profile"] != CONFIRMATORY_PROFILE:
        raise _mc_failure("P5", "wrong confirmatory_profile")
    design_id = artifact["design_id"]
    if not isinstance(design_id, str) or not design_id:
        raise _mc_failure("P6", "design_id must be a non-empty safe string")
    try:
        registration_manifest_path(Path("."), design_id)
    except ConfirmatoryRegistrationError as error:
        raise _mc_failure("P6", f"unsafe design_id: {error}") from error

    # P7: every branch field has its frozen JSON type; bool is never an integer.
    string_fields = {
        "schema_version",
        "confirmatory_profile",
        "design_id",
        "final_registration_digest",
        "randomization_mode",
        "created_at",
        "statistic_spec_id",
        "self_digest",
    }
    integer_fields = {"K"}
    if mode == RANDOMIZATION_MODE_EXACT_ENUMERATION:
        integer_fields.add("exact_support_size")
    else:
        string_fields.update(
            {
                "source_kind",
                "source_api",
                "seed_hex",
                "seed_encoding",
                "rng_library",
                "rng_bit_generator",
                "numpy_version",
                "generated_at",
            }
        )
        integer_fields.update({"entropy_bytes", "randomization_mc_samples"})
    if any(not isinstance(artifact[field], str) for field in string_fields):
        raise _mc_failure("P7", "one or more string fields has the wrong JSON type")
    if any(not _is_json_integer(artifact[field]) for field in integer_fields):
        raise _mc_failure(
            "P7", "one or more integer fields is not a JSON integer (bool refused)"
        )

    # P8-P10: digest grammar, K/mode, and statistic literal.
    if not _has_digest_grammar(artifact["final_registration_digest"]) or not (
        _has_digest_grammar(artifact["self_digest"])
    ):
        raise _mc_failure("P8", "digest field has invalid lowercase SHA-256 grammar")
    K = cast(int, artifact["K"])
    if K < 0 or (
        mode == RANDOMIZATION_MODE_EXACT_ENUMERATION and K > 16
    ) or (mode == RANDOMIZATION_MODE_MONTE_CARLO and K <= 16):
        raise _mc_failure("P9", "K is negative or inconsistent with the branch")
    if artifact["statistic_spec_id"] != STATISTIC_SPEC_ID:
        raise _mc_failure("P10", "wrong statistic_spec_id")

    # P11-P14: branch-specific derivations, constants, and values.
    if mode == RANDOMIZATION_MODE_EXACT_ENUMERATION:
        if artifact["exact_support_size"] != 2**K:
            raise _mc_failure("P11", "exact_support_size is not 2 ** K")
    else:
        constants = {
            "source_kind": MC_SOURCE_KIND,
            "source_api": MC_SOURCE_API,
            "entropy_bytes": MC_ENTROPY_BYTES,
            "seed_encoding": MC_SEED_ENCODING,
            "rng_library": MC_RNG_LIBRARY,
            "rng_bit_generator": MC_RNG_BIT_GENERATOR,
        }
        if any(artifact[field] != expected for field, expected in constants.items()):
            raise _mc_failure("P12", "one or more Monte-Carlo literals is wrong")
        seed_hex = artifact["seed_hex"]
        if not isinstance(seed_hex, str) or _SEED_HEX_PATTERN.fullmatch(seed_hex) is None:
            raise _mc_failure("P13", "seed_hex must be exactly 64 lowercase hex chars")
        if not artifact["numpy_version"] or artifact["randomization_mc_samples"] < 1:
            raise _mc_failure("P14", "numpy_version is empty or M is not positive")

    # P15-P16: real whole-second UTC instants and non-strict order.
    created_at = _timestamp_instant(artifact["created_at"])
    if created_at is None:
        raise _mc_failure("P15", "created_at is not a real frozen-form instant")
    if mode == RANDOMIZATION_MODE_MONTE_CARLO:
        generated_at = _timestamp_instant(artifact["generated_at"])
        if generated_at is None:
            raise _mc_failure("P15", "generated_at is not a real frozen-form instant")
        if generated_at > created_at:
            raise _mc_failure("P16", "generated_at is after created_at")

    # P17: shared WU1 self-digest implementation, at its frozen position.
    try:
        verify_self_digest(artifact)
    except ConfirmatoryRegistrationError as error:
        raise _mc_failure("P17", f"self_digest does not verify: {error}") from error
    return mode


def _validate_mc_tier_two(
    artifact: dict[str, Any], registration: RegistrationManifest, mode: str
) -> None:
    # P19-P24. P18 is the already-completed full on-disk chain load.
    if artifact["final_registration_digest"] != registration.self_digest:
        raise _mc_failure("P19", "final_registration_digest does not match")
    if artifact["design_id"] != registration.design_id:
        raise _mc_failure("P20", "design_id does not match registration")
    if mode != registration.randomization_mode:
        raise _mc_failure("P21", "randomization_mode does not match registration")
    if artifact["K"] != registration.K:
        raise _mc_failure("P22", "K does not match registration")
    if (
        artifact["statistic_spec_id"]
        != registration.registered_statistical_configuration.statistic_spec_id
    ):
        raise _mc_failure("P23", "statistic_spec_id does not match registration")
    if mode == RANDOMIZATION_MODE_MONTE_CARLO and (
        artifact["randomization_mc_samples"]
        != registration.registered_statistical_configuration.randomization_mc_samples
    ):
        raise _mc_failure("P24", "randomization_mc_samples does not match registered M")


def _validate_assignment_tier_one(artifact: dict[str, Any]) -> None:
    # A2-A5: exact keys, literals, and safe design id.
    if set(artifact) != _ASSIGNMENT_KEYS:
        raise _assignment_failure(
            "A2",
            f"wrong top-level key set; expected={sorted(_ASSIGNMENT_KEYS)!r} "
            f"actual={sorted(artifact)!r}",
        )
    if artifact["schema_version"] != ASSIGNMENT_MANIFEST_SCHEMA_VERSION:
        raise _assignment_failure("A3", "wrong schema_version")
    if artifact["confirmatory_profile"] != CONFIRMATORY_PROFILE:
        raise _assignment_failure("A4", "wrong confirmatory_profile")
    design_id = artifact["design_id"]
    if not isinstance(design_id, str) or not design_id:
        raise _assignment_failure("A5", "design_id must be a non-empty safe string")
    try:
        registration_manifest_path(Path("."), design_id)
    except ConfirmatoryRegistrationError as error:
        raise _assignment_failure("A5", f"unsafe design_id: {error}") from error

    # A6-A9: field types, digest grammar, exact source literals, environment.
    if not isinstance(artifact["task_order"], list) or not isinstance(
        artifact["bits"], list
    ):
        raise _assignment_failure("A6", "task_order and bits must be arrays")
    scalar_fields = _ASSIGNMENT_KEYS - {"task_order", "bits"}
    if any(not isinstance(artifact[field], str) for field in scalar_fields):
        raise _assignment_failure("A6", "the other eleven fields must be strings")
    if any(
        not _has_digest_grammar(artifact[field])
        for field in (
            "final_registration_digest",
            "randomization_mc_provenance_digest",
            "self_digest",
        )
    ):
        raise _assignment_failure("A7", "digest field has invalid grammar")
    if artifact["source_kind"] != ASSIGNMENT_SOURCE_KIND or (
        artifact["source_api"] != ASSIGNMENT_SOURCE_API
    ):
        raise _assignment_failure("A8", "wrong production assignment source literal")
    if not artifact["python_version"]:
        raise _assignment_failure("A9", "python_version must be non-empty")

    # A10-A12: persisted order, bit domain, and parallel-array length.
    task_order = artifact["task_order"]
    if any(not isinstance(task, str) or not task for task in task_order) or any(
        cast(str, task_order[index - 1]) >= cast(str, task_order[index])
        for index in range(1, len(task_order))
    ):
        raise _assignment_failure(
            "A10", "task_order must contain non-empty strictly ascending strings"
        )
    bits = artifact["bits"]
    if any(not _is_json_integer(bit) or bit not in (0, 1) for bit in bits):
        raise _assignment_failure(
            "A11", "every bit must be JSON integer 0 or 1 (bool refused)"
        )
    if len(bits) != len(task_order):
        raise _assignment_failure("A12", "bits and task_order lengths differ")

    # A13-A14: real instants and non-strict order.
    started = _timestamp_instant(artifact["generation_started_at"])
    completed = _timestamp_instant(artifact["generation_completed_at"])
    if started is None or completed is None:
        raise _assignment_failure("A13", "assignment timestamp is not a real instant")
    if started > completed:
        raise _assignment_failure("A14", "generation_started_at is after completion")

    # A15: shared WU1 self-digest verification at its frozen position.
    try:
        verify_self_digest(artifact)
    except ConfirmatoryRegistrationError as error:
        raise _assignment_failure("A15", f"self_digest does not verify: {error}") from error


def _registered_task_order(registration: RegistrationManifest) -> tuple[str, ...]:
    return tuple(sorted({position.task_id for position in registration.confirmatory_positions}))


def _validate_assignment_tier_two(
    artifact: dict[str, Any], registration: RegistrationManifest
) -> None:
    # A17-A18. A16 is the already-completed full on-disk chain load.
    if artifact["final_registration_digest"] != registration.self_digest:
        raise _assignment_failure("A17", "final_registration_digest does not match")
    if artifact["design_id"] != registration.design_id:
        raise _assignment_failure("A18", "design_id does not match registration")


def _validate_assignment_tier_three(
    artifact: dict[str, Any],
    registration: RegistrationManifest,
    provenance: RandomizationMcProvenanceV1,
) -> None:
    # A20-A23. A19 is the already-completed provenance load through P1-P24.
    if artifact["randomization_mc_provenance_digest"] != provenance.self_digest:
        raise _assignment_failure(
            "A20", "randomization_mc_provenance_digest does not match"
        )
    if artifact["task_order"] != list(_registered_task_order(registration)):
        raise _assignment_failure("A21", "task_order is not the exact registered cover")
    if len(cast(list[Any], artifact["bits"])) != registration.K:
        raise _assignment_failure("A22", "bit count does not equal registered K")
    provenance_created = _timestamp_instant(provenance.created_at)
    generation_started = _timestamp_instant(artifact["generation_started_at"])
    if (
        provenance_created is None
        or generation_started is None
        or provenance_created > generation_started
    ):
        raise _assignment_failure("A23", "provenance was sealed after assignment start")


def _load_registration_chain(
    confirmatory_root: Path, design_id: str
) -> tuple[RegistrationDraft, EligibilityManifestV1, RegistrationManifest]:
    draft = load_registration_draft(registration_draft_path(confirmatory_root, design_id))
    eligibility = load_eligibility_manifest(
        eligibility_manifest_path(confirmatory_root, design_id),
        registration_draft=draft,
    )
    registration = load_registration_manifest(
        registration_manifest_path(confirmatory_root, design_id),
        registration_draft=draft,
        eligibility_manifest=eligibility,
    )
    return draft, eligibility, registration


def _mc_from_validated(
    artifact: dict[str, Any], mode: str
) -> RandomizationMcProvenanceV1:
    exact = mode == RANDOMIZATION_MODE_EXACT_ENUMERATION
    return RandomizationMcProvenanceV1(
        schema_version=cast(str, artifact["schema_version"]),
        confirmatory_profile=cast(str, artifact["confirmatory_profile"]),
        design_id=cast(str, artifact["design_id"]),
        final_registration_digest=cast(str, artifact["final_registration_digest"]),
        randomization_mode=mode,
        created_at=cast(str, artifact["created_at"]),
        K=cast(int, artifact["K"]),
        statistic_spec_id=cast(str, artifact["statistic_spec_id"]),
        self_digest=cast(str, artifact["self_digest"]),
        exact_support_size=(
            cast(int, artifact["exact_support_size"]) if exact else None
        ),
        source_kind=(None if exact else cast(str, artifact["source_kind"])),
        source_api=(None if exact else cast(str, artifact["source_api"])),
        entropy_bytes=(None if exact else cast(int, artifact["entropy_bytes"])),
        seed_hex=(None if exact else cast(str, artifact["seed_hex"])),
        seed_encoding=(None if exact else cast(str, artifact["seed_encoding"])),
        rng_library=(None if exact else cast(str, artifact["rng_library"])),
        rng_bit_generator=(
            None if exact else cast(str, artifact["rng_bit_generator"])
        ),
        numpy_version=(None if exact else cast(str, artifact["numpy_version"])),
        randomization_mc_samples=(
            None if exact else cast(int, artifact["randomization_mc_samples"])
        ),
        generated_at=(None if exact else cast(str, artifact["generated_at"])),
    )


def _assignment_from_validated(artifact: dict[str, Any]) -> AssignmentManifestV1:
    return AssignmentManifestV1(
        schema_version=cast(str, artifact["schema_version"]),
        confirmatory_profile=cast(str, artifact["confirmatory_profile"]),
        design_id=cast(str, artifact["design_id"]),
        final_registration_digest=cast(str, artifact["final_registration_digest"]),
        randomization_mc_provenance_digest=cast(
            str, artifact["randomization_mc_provenance_digest"]
        ),
        task_order=tuple(cast(list[str], artifact["task_order"])),
        bits=tuple(cast(list[int], artifact["bits"])),
        source_kind=cast(str, artifact["source_kind"]),
        source_api=cast(str, artifact["source_api"]),
        python_version=cast(str, artifact["python_version"]),
        generation_started_at=cast(str, artifact["generation_started_at"]),
        generation_completed_at=cast(str, artifact["generation_completed_at"]),
        self_digest=cast(str, artifact["self_digest"]),
    )


def load_randomization_mc_provenance(
    path: Path,
) -> RandomizationMcProvenanceV1:
    """Load one provenance artifact through P1-P24 in exact first-failure order."""

    artifact = _parse_mc_file(Path(path))  # P1
    mode = _validate_mc_tier_one(artifact)  # P2-P17
    confirmatory_root = Path(path).parent.parent
    try:
        _, _, registration = _load_registration_chain(
            confirmatory_root, cast(str, artifact["design_id"])
        )
    except (ConfirmatoryRegistrationError, ConfirmatoryEligibilityError, OSError) as error:
        raise _mc_failure("P18", f"bound registration chain failed: {error}") from error
    _validate_mc_tier_two(artifact, registration, mode)  # P19-P24
    return _mc_from_validated(artifact, mode)


def load_assignment_manifest(path: Path) -> AssignmentManifestV1:
    """Load one assignment through A1-A23 with a single assignment error surface."""

    artifact = _parse_assignment_file(Path(path))  # A1
    _validate_assignment_tier_one(artifact)  # A2-A15
    confirmatory_root = Path(path).parent.parent
    design_id = cast(str, artifact["design_id"])
    try:
        _, _, registration = _load_registration_chain(confirmatory_root, design_id)
    except (ConfirmatoryRegistrationError, ConfirmatoryEligibilityError, OSError) as error:
        raise _assignment_failure(
            "A16", f"bound registration chain failed: {error}"
        ) from error
    _validate_assignment_tier_two(artifact, registration)  # A17-A18
    try:
        provenance = load_randomization_mc_provenance(
            randomization_mc_provenance_path(confirmatory_root, design_id)
        )
    except McProvenanceIntegrityError as error:
        raise _assignment_failure("A19", f"bound provenance failed: {error}") from error
    _validate_assignment_tier_three(artifact, registration, provenance)  # A20-A23
    return _assignment_from_validated(artifact)


def _seal_with_shared_digest(body: dict[str, Any], error_kind: str) -> dict[str, Any]:
    try:
        return attach_self_digest(body)
    except ConfirmatoryRegistrationError as error:
        if error_kind == "mc":
            raise _mc_failure("P17", f"cannot seal provenance: {error}") from error
        raise _assignment_failure("A15", f"cannot seal assignment: {error}") from error


def persist_randomization_mc_provenance(
    *, confirmatory_root: Path, design_id: str
) -> RandomizationMcProvenanceV1:
    """Generate and exclusively persist mandatory provenance as one operation.

    No caller-provided seed, timestamp, NumPy version, M, mode, or randomness
    source is accepted.  The exact branch performs no entropy call; the MC branch
    calls ``secrets.token_bytes(32)`` exactly once and constructs
    ``Generator(PCG64(seed_int))`` before sealing the source provenance.
    """

    root = Path(confirmatory_root)
    try:
        _, _, registration = _load_registration_chain(root, design_id)
    except (ConfirmatoryRegistrationError, ConfirmatoryEligibilityError, OSError) as error:
        raise _mc_failure("P18", f"bound registration chain failed: {error}") from error
    try:
        path = randomization_mc_provenance_path(root, design_id)
    except ConfirmatoryAssignmentError as error:
        raise _mc_failure("P6", str(error)) from error
    if path.exists():
        raise DuplicateMcProvenanceError(
            f"randomization MC provenance already exists and is immutable: {path}"
        )

    mode = registration.randomization_mode
    branch: dict[str, Any]
    if mode == RANDOMIZATION_MODE_EXACT_ENUMERATION:
        branch = {"exact_support_size": 2**registration.K}
    else:
        generated_at = _capture_timestamp()
        raw_seed_bytes = secrets.token_bytes(MC_ENTROPY_BYTES)
        if len(raw_seed_bytes) != MC_ENTROPY_BYTES:
            raise _mc_failure(
                "P13", "secrets.token_bytes(32) did not return exactly 32 bytes"
            )
        seed_int = int.from_bytes(raw_seed_bytes, byteorder="big", signed=False)
        # Construction is part of the frozen provenance mechanism.  No values are
        # sampled here; analysis later recreates the generator from the persisted seed.
        np.random.Generator(np.random.PCG64(seed_int))
        registered_m = (
            registration.registered_statistical_configuration.randomization_mc_samples
        )
        branch = {
            "entropy_bytes": MC_ENTROPY_BYTES,
            "generated_at": generated_at,
            "numpy_version": np.__version__,
            "randomization_mc_samples": registered_m,
            "rng_bit_generator": MC_RNG_BIT_GENERATOR,
            "rng_library": MC_RNG_LIBRARY,
            "seed_encoding": MC_SEED_ENCODING,
            "seed_hex": raw_seed_bytes.hex(),
            "source_api": MC_SOURCE_API,
            "source_kind": MC_SOURCE_KIND,
        }

    body: dict[str, Any] = {
        "K": registration.K,
        "confirmatory_profile": CONFIRMATORY_PROFILE,
        "created_at": _capture_timestamp(),
        "design_id": registration.design_id,
        "final_registration_digest": registration.self_digest,
        "randomization_mode": mode,
        "schema_version": MC_PROVENANCE_SCHEMA_VERSION,
        "statistic_spec_id": STATISTIC_SPEC_ID,
        **branch,
    }
    artifact = _seal_with_shared_digest(body, "mc")
    validated_mode = _validate_mc_tier_one(artifact)
    _validate_mc_tier_two(artifact, registration, validated_mode)
    try:
        payload = serialize_artifact(artifact)
    except ConfirmatoryRegistrationError as error:
        raise _mc_failure("P17", f"cannot serialize provenance: {error}") from error

    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as error:
        raise DuplicateMcProvenanceError(
            f"randomization MC provenance already exists and is immutable: {path}"
        ) from error
    return _mc_from_validated(artifact, validated_mode)


def _draw_assignment_bits(
    source: AssignmentRandomSource,
    task_order: Sequence[str],
    *,
    confirmatory_profile: str,
    persisting: bool,
) -> tuple[int, ...]:
    """Draw once per task in order, with the frozen production-source refusal."""

    if persisting and confirmatory_profile == CONFIRMATORY_PROFILE:
        if isinstance(source, DeterministicAssignmentRandomSource):
            raise ConfirmatoryAssignmentError(
                "deterministic assignment randomness cannot reach production persistence"
            )
        if not isinstance(source, SecretsAssignmentRandomSource):
            raise ConfirmatoryAssignmentError(
                "production persistence requires SecretsAssignmentRandomSource"
            )
    drawn: list[int] = []
    for task_id in task_order:
        bit = source.draw_bit()
        if not _is_json_integer(bit) or bit not in (0, 1):
            raise ConfirmatoryAssignmentError(
                f"random source returned an invalid bit for {task_id!r}: {bit!r}"
            )
        drawn.append(bit)
    return tuple(drawn)


def _sync_windows_directory_metadata(directory: Path) -> None:
    """Flush one Windows directory handle, failing closed on unsupported semantics."""

    win_dll_factory = getattr(ctypes, "WinDLL", None)
    get_last_error = getattr(ctypes, "get_last_error", None)
    if win_dll_factory is None or get_last_error is None:
        raise OSError("Windows directory metadata durability API is unavailable")
    kernel32: Any = win_dll_factory("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    kernel32.CreateFileW.restype = ctypes.c_void_p
    kernel32.FlushFileBuffers.argtypes = [ctypes.c_void_p]
    kernel32.FlushFileBuffers.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int

    generic_write = 0x40000000
    share_read_write_delete = 0x00000007
    open_existing = 3
    backup_semantics = 0x02000000
    write_through = 0x80000000
    invalid_handle = ctypes.c_void_p(-1).value
    handle = kernel32.CreateFileW(
        str(directory),
        generic_write,
        share_read_write_delete,
        None,
        open_existing,
        backup_semantics | write_through,
        None,
    )
    if handle in (None, invalid_handle):
        error_code = int(get_last_error())
        raise OSError(
            error_code,
            "cannot open directory for durable metadata synchronization",
            str(directory),
        )
    try:
        if not kernel32.FlushFileBuffers(handle):
            error_code = int(get_last_error())
            raise OSError(
                error_code,
                "cannot durably synchronize directory metadata",
                str(directory),
            )
    finally:
        kernel32.CloseHandle(handle)


def _sync_directory_metadata(directory: Path) -> None:
    """Establish durable metadata for entries in ``directory`` or fail closed."""

    if os.name == "nt":
        _sync_windows_directory_metadata(directory)
        return
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(directory, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _reserve_assignment(pending_path: Path) -> None:
    """R2-R3: exclusively create and durably publish the pre-draw marker."""

    with pending_path.open("xb") as handle:
        handle.write(ASSIGNMENT_RESERVATION_MARKER)
        handle.flush()
        os.fsync(handle.fileno())
    _sync_directory_metadata(pending_path.parent)


def _stage_assignment(pending_path: Path, payload: bytes) -> None:
    """R4: replace reservation content with complete canonical bytes and sync it."""

    with pending_path.open("r+b") as handle:
        handle.seek(0)
        handle.write(payload)
        handle.truncate()
        handle.flush()
        os.fsync(handle.fileno())


def _publish_assignment_no_clobber(pending_path: Path, final_path: Path) -> None:
    """R5: atomically create the final entry from the complete staged inode."""

    os.link(pending_path, final_path)


def _unlink_pending_after_durable_publication(pending_path: Path) -> None:
    """R6: optional, non-authoritative cleanup after R5-prime has succeeded."""

    try:
        pending_path.unlink()
    except OSError:
        # The final artifact is already durably published and authoritative.
        pass


def persist_assignment(
    *, confirmatory_root: Path, design_id: str
) -> AssignmentManifestV1:
    """Draw and crash-safely publish one production assignment as one operation.

    The signature deliberately accepts no bits, timestamps, clock, Python
    version, or random source.  The complete registration/provenance chain is
    reloaded before R1 and before any reservation or draw.
    """

    root = Path(confirmatory_root)
    try:
        _, _, registration = _load_registration_chain(root, design_id)
    except (ConfirmatoryRegistrationError, ConfirmatoryEligibilityError, OSError) as error:
        raise _assignment_failure(
            "A16", f"bound registration chain failed: {error}"
        ) from error
    try:
        provenance = load_randomization_mc_provenance(
            randomization_mc_provenance_path(root, design_id)
        )
    except McProvenanceIntegrityError as error:
        raise _assignment_failure("A19", f"bound provenance failed: {error}") from error

    try:
        final_path = assignment_manifest_path(root, design_id)
        pending_path = assignment_pending_path(root, design_id)
    except ConfirmatoryAssignmentError as error:
        raise _assignment_failure("A5", str(error)) from error

    # R1 is intentionally final-first: final + pending means final authoritative.
    if final_path.exists():
        raise DuplicateAssignmentError(
            f"assignment manifest already exists and is immutable: {final_path}"
        )
    if pending_path.exists():
        raise _assignment_failure(
            "R1",
            "assignment final is absent but a prior .pending reservation exists",
        )

    task_order = _registered_task_order(registration)
    try:
        _reserve_assignment(pending_path)  # R2-R3, before timestamp or draw.
    except FileExistsError as error:
        if final_path.exists():
            raise DuplicateAssignmentError(
                f"assignment manifest already exists and is immutable: {final_path}"
            ) from error
        raise _assignment_failure(
            "R1", "a prior .pending reservation exists"
        ) from error

    generation_started_at = _capture_timestamp()
    source = SecretsAssignmentRandomSource()
    try:
        bits = _draw_assignment_bits(
            source,
            task_order,
            confirmatory_profile=CONFIRMATORY_PROFILE,
            persisting=True,
        )
    except ConfirmatoryAssignmentError as error:
        raise _assignment_failure("A11", str(error)) from error
    generation_completed_at = _capture_timestamp()

    body: dict[str, Any] = {
        "bits": list(bits),
        "confirmatory_profile": CONFIRMATORY_PROFILE,
        "design_id": registration.design_id,
        "final_registration_digest": registration.self_digest,
        "generation_completed_at": generation_completed_at,
        "generation_started_at": generation_started_at,
        "python_version": platform.python_version(),
        "randomization_mc_provenance_digest": provenance.self_digest,
        "schema_version": ASSIGNMENT_MANIFEST_SCHEMA_VERSION,
        "source_api": ASSIGNMENT_SOURCE_API,
        "source_kind": ASSIGNMENT_SOURCE_KIND,
        "task_order": list(task_order),
    }
    artifact = _seal_with_shared_digest(body, "assignment")
    _validate_assignment_tier_one(artifact)
    _validate_assignment_tier_two(artifact, registration)
    _validate_assignment_tier_three(artifact, registration, provenance)
    try:
        payload = serialize_artifact(artifact)
    except ConfirmatoryRegistrationError as error:
        raise _assignment_failure(
            "A15", f"cannot serialize assignment manifest: {error}"
        ) from error

    _stage_assignment(pending_path, payload)  # R4
    try:
        _publish_assignment_no_clobber(pending_path, final_path)  # R5
    except FileExistsError as error:
        raise DuplicateAssignmentError(
            f"assignment manifest already exists and is immutable: {final_path}"
        ) from error
    _sync_directory_metadata(final_path.parent)  # R5-prime; pending retained on fail.
    _unlink_pending_after_durable_publication(pending_path)  # R6, only after R5-prime.
    return _assignment_from_validated(artifact)
