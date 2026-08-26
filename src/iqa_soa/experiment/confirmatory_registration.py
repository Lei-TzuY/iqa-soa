"""Stage-A confirmatory registration draft and the frozen canonical digest profile.

This module implements the first work unit of the frozen post-Phase-P
confirmatory randomization implementation design
(``docs/post_phaseP_confirmatory_randomization_implementation_design.md``): the
Stage-A ``REGISTRATION_DRAFT`` schema (§5.A), the canonical JSON profile and the
``self_digest`` construction/verification procedure (§5.B.2), and the immutable
``registration_draft.json`` persistence/load behaviour (§5.B, §6).

Nothing here selects a real task, provider, model, repetition, ordinary seed, or
``design_id``, and nothing here writes under ``results/``.  A draft records a
*proposed* design only: it authorizes no eligibility assessment, no
randomization, no assignment, and no execution (§5.A Stage A).  Its sole role is
to be the fixed input that eligibility is later assessed against.

Three rules from §5.B are load-bearing and are implemented literally:

* Canonicalization is exactly ``json.dumps(obj, sort_keys=True,
  separators=(",", ":"), ensure_ascii=False, allow_nan=False)`` encoded as
  UTF-8.  No other serializer, library, or option set is authorized.
* An artifact stores exactly one digest of itself, ``self_digest``, computed
  over the artifact with only that field removed.  Same-object alias fields such
  as ``registration_draft_digest`` are never written here; that name belongs to
  *downstream* artifacts referencing this one's ``self_digest`` (§5.B.1).
* The persisted bytes are the canonical JSON *including* ``self_digest``
  followed by exactly one LF.  That LF is appended after every digest has
  already been computed, so it is never part of any digest, and a reader strips
  at most one trailing LF before doing anything else with the bytes.

Every verification failure fails closed.  This module raises; it never repairs a
malformed artifact, never normalizes an invalid one into validity, and never
reserializes around a mismatch.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
import hashlib
import hmac
import json
from pathlib import Path, PureWindowsPath
import re
from typing import Any, Sequence

from iqa_soa.types import QAMode

__all__ = [
    "AGGREGATION_RULE",
    "ALPHA",
    "BACKOFF_KINDS",
    "BASELINE_LABELS",
    "BASELINE_LABEL_FULL",
    "BASELINE_LABEL_OFF",
    "CONFIRMATORY_PROFILE",
    "ConfirmatoryRegistrationError",
    "MULTIPLICITY_ARCHITECTURE",
    "PRIMARY_ENDPOINT",
    "PRIMARY_ESTIMAND_ARCHITECTURE",
    "PROPOSED_STATISTICAL_CONFIGURATION_SCHEMA_VERSION",
    "ProposedPositionV1",
    "ProposedProviderSeedEntryV1",
    "ProposedRepetitionsEntryV1",
    "ProposedRuntimeConfigurationV1",
    "ProposedStatisticalConfigurationV1",
    "ProposedStratumV1",
    "RANDOMIZATION_EXACT_ENUMERATION_MAX_K",
    "REGISTRATION_DRAFT_FILENAME",
    "REGISTRATION_DRAFT_SCHEMA_VERSION",
    "REGISTRATION_STATE_DRAFT",
    "RUNTIME_SNAPSHOT_SCHEMA_VERSION",
    "RegistrationDraft",
    "RetryPolicyV1",
    "RuntimeSnapshotV1",
    "SECONDARY_ENDPOINT_SEQUENCE",
    "SELF_DIGEST_FIELD",
    "STATISTIC_SPEC_ID",
    "TREATMENT_CONTRAST_ORIENTATION",
    "attach_self_digest",
    "canonical_json_bytes",
    "compute_self_digest",
    "draft_registration",
    "load_registration_draft",
    "parse_artifact",
    "registration_draft_path",
    "serialize_artifact",
    "verify_self_digest",
    "write_registration_draft",
]


class ConfirmatoryRegistrationError(ValueError):
    """A confirmatory registration artifact is malformed, mismatched, or immutable."""


#: The frozen confirmatory design family this registration chain belongs to
#: (implementation design §5.C).  Assignment generation refuses a test-only
#: random source under exactly this profile (§5.M), so the profile is stamped at
#: Stage A rather than first appearing on an execution row.
CONFIRMATORY_PROFILE = "post_phaseP_confirmatory_randomization_v1"

#: The frozen lifecycle state a Stage-A draft carries (§5.A, §6).
REGISTRATION_STATE_DRAFT = "REGISTRATION_DRAFT"

#: Schema identity of this artifact shape, following the document's own ``V1``
#: record-naming convention (``ConfirmatoryPositionV1``, ``RuntimeSnapshotV1``).
REGISTRATION_DRAFT_SCHEMA_VERSION = "RegistrationDraftV1"

#: The record identity frozen by implementation design §5.I.
RUNTIME_SNAPSHOT_SCHEMA_VERSION = "RuntimeSnapshotV1"

#: The single opaque versioned statistic identifier frozen by §5.K.  A change to
#: the statistic's implementation requires minting a new literal id; this value
#: is stamped by :func:`draft_registration` rather than accepted from a caller,
#: so a draft always records the id this implementation actually realizes.
STATISTIC_SPEC_ID = "confirmatory_task_sign_flip_v1"

#: The one and only digest field an artifact stores about itself (§5.B.1).
SELF_DIGEST_FIELD = "self_digest"

#: Persisted Stage-A artifact name under ``<confirmatory_root>/<design_id>/``.
REGISTRATION_DRAFT_FILENAME = "registration_draft.json"

#: Schema identity of the Stage-A statistical object (clarification §7.1-§7.2).
PROPOSED_STATISTICAL_CONFIGURATION_SCHEMA_VERSION = (
    "ProposedStatisticalConfigurationV1"
)

#: Two-sided alpha, a canonical decimal string because ``0.05`` has no exact
#: binary floating-point representation (clarification §7.2, §7.4).  Two-
#: sidedness is carried by the absolute-value statistic itself, so there is no
#: separate sidedness key.
ALPHA = "0.05"

#: Frozen multiplicity architecture (clarification §7.2; analysis contract §16.1).
MULTIPLICITY_ARCHITECTURE = "FIXED_SEQUENCE_GATEKEEPING"

#: Frozen primary endpoint (clarification §7.2; analysis contract §6.1).
PRIMARY_ENDPOINT = "unsafe_action_executed"

#: The frozen fixed-sequence gate order S-1 -> S-5.  This array is **ordered,
#: not sorted**: its order is semantic, and canonicalization preserves
#: registered order (clarification §7.2, §7.4).
SECONDARY_ENDPOINT_SEQUENCE: tuple[str, ...] = (
    "safety_security_violation",
    "unsafe_action_proposed",
    "constraint_violation",
    "privacy_leak",
    "attack_success",
)

#: Frozen primary estimand architecture (clarification §7.2).
PRIMARY_ESTIMAND_ARCHITECTURE = (
    "SCHEDULED_ATTEMPT_PRIMARY_WITH_MECHANISM_SECONDARIES"
)

#: Frozen aggregation rule (clarification §7.2).
AGGREGATION_RULE = "NESTED_EQUAL_WEIGHT_FIXED_PRE_RUN"

#: Frozen contrast orientation for ``D_k`` (clarification §7.2).
TREATMENT_CONTRAST_ORIENTATION = "FULL_MINUS_OFF"

#: Frozen exact-enumeration ceiling on ``K`` (clarification §7.2).  Recorded for
#: auditability only; Stage A never derives ``K`` or ``randomization_mode`` from
#: it — both are Stage-C deterministic derivations (clarification §8.2, §10.2).
RANDOMIZATION_EXACT_ENUMERATION_MAX_K = 16

#: The baseline-schedule label vocabulary.  These are the repository's existing
#: canonical ``QAMode`` serializations, not a new vocabulary (clarification
#: §5.3): the confirmatory contrast is exactly OFF versus FULL, so
#: ``QAMode.PARTIAL`` and ``QAMode.ABLATION`` are outside this design.
BASELINE_LABEL_OFF = QAMode.OFF.value
BASELINE_LABEL_FULL = QAMode.FULL.value
BASELINE_LABELS: tuple[str, ...] = (BASELINE_LABEL_OFF, BASELINE_LABEL_FULL)

#: The two physical call slots of a matched contrast (design decision §4.A).
_SLOTS: tuple[int, ...] = (1, 2)

#: Frozen ``retry_policy.backoff_kind`` domain (§5.I.4).
BACKOFF_KINDS: tuple[str, ...] = ("NONE", "FIXED", "EXPONENTIAL")

#: ``created_at`` is an RFC 3339 UTC instant with a mandatory ``Z`` designator,
#: second precision, no fractional seconds, no non-``Z`` offset (clarification
#: §4.3).
_CREATED_AT_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_CREATED_AT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

#: Digest representation frozen by §5.B.2: lowercase 64-character hexadecimal.
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")

#: Canonical decimal string frozen by §5.B.2: base-10, no exponent form, no
#: leading zeros other than a single ``0`` before a decimal point, no trailing
#: bare decimal point, no ``+`` sign.
_CANONICAL_DECIMAL_PATTERN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")

#: Characters that are path syntax rather than portable single-segment content.
_DESIGN_ID_FORBIDDEN = ("/", "\\", ":", "\x00")

_WINDOWS_RESERVED_NAMES: frozenset[str] = frozenset(
    {
        "AUX",
        "CON",
        "NUL",
        "PRN",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
)

#: The exact key set of ``registration_draft.json``.  A persisted draft with a
#: missing or extra key is malformed, which is also what structurally forbids a
#: same-object ``registration_draft_digest`` alias from ever loading (§5.B.1).
_DRAFT_KEYS: frozenset[str] = frozenset(
    {
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
        SELF_DIGEST_FIELD,
    }
)

_STRATUM_KEYS: frozenset[str] = frozenset({"model", "provider"})

_REPETITIONS_ENTRY_KEYS: frozenset[str] = frozenset(
    {"model", "provider", "repetition_count", "task_id"}
)

_PROVIDER_SEED_ENTRY_KEYS: frozenset[str] = frozenset(
    {"provider_seed", "repetition"}
)

#: The seven Stage-A proposed-position fields (clarification §5.2): the six
#: identity fields plus ``baseline_label``.
_POSITION_KEYS: frozenset[str] = frozenset(
    {
        "baseline_label",
        "model",
        "provider",
        "provider_seed",
        "repetition",
        "slot",
        "task_id",
    }
)

#: The six identity fields Stage C hashes into ``position_id`` (clarification
#: §5.1).  ``baseline_label`` is deliberately absent.
_POSITION_IDENTITY_KEYS: tuple[str, ...] = (
    "task_id",
    "provider",
    "model",
    "repetition",
    "provider_seed",
    "slot",
)

_RETRY_POLICY_KEYS: frozenset[str] = frozenset(
    {
        "backoff_kind",
        "initial_delay_seconds",
        "max_attempts",
        "max_delay_seconds",
        "retryable_error_classes",
    }
)

_RUNTIME_KEYS: frozenset[str] = frozenset(
    {
        "registration_expected_runtime_snapshot",
        "retry_policy",
        "timeout_seconds",
    }
)

_RUNTIME_SNAPSHOT_KEYS: frozenset[str] = frozenset(
    {
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
)

#: The eleven Stage-A statistical-configuration keys (clarification §7.1).
_STATISTICAL_KEYS: frozenset[str] = frozenset(
    {
        "aggregation_rule",
        "alpha",
        "multiplicity_architecture",
        "primary_endpoint",
        "primary_estimand_architecture",
        "randomization_exact_enumeration_max_k",
        "randomization_mc_samples",
        "schema_version",
        "secondary_endpoint_sequence",
        "statistic_spec_id",
        "treatment_contrast_orientation",
    }
)

#: The ten stamped statistical literals, each checked on load so a tampered
#: draft fails V9 rather than being silently accepted (clarification §7.2, §7.3).
_STATISTICAL_STRING_LITERALS: tuple[tuple[str, str], ...] = (
    ("schema_version", PROPOSED_STATISTICAL_CONFIGURATION_SCHEMA_VERSION),
    ("statistic_spec_id", STATISTIC_SPEC_ID),
    ("alpha", ALPHA),
    ("multiplicity_architecture", MULTIPLICITY_ARCHITECTURE),
    ("primary_endpoint", PRIMARY_ENDPOINT),
    ("primary_estimand_architecture", PRIMARY_ESTIMAND_ARCHITECTURE),
    ("aggregation_rule", AGGREGATION_RULE),
    ("treatment_contrast_orientation", TREATMENT_CONTRAST_ORIENTATION),
)


# ---------------------------------------------------------------------------
# Canonical JSON profile and self-digest construction (§5.B.2)
# ---------------------------------------------------------------------------


def canonical_json_bytes(payload: Any) -> bytes:
    """Canonical UTF-8 bytes of ``payload`` under the one frozen algorithm.

    The option set is fixed by §5.B.2 and is not configurable: ``sort_keys``
    orders object keys by ordinary code-point ordering, ``separators`` removes
    every insignificant space, ``ensure_ascii=False`` keeps Unicode verbatim,
    and ``allow_nan=False`` makes ``NaN``/``Infinity``/``-Infinity`` a hard
    construction error rather than a representable value.
    """

    _require_string_keys(payload, path="<artifact>")
    try:
        text = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ConfirmatoryRegistrationError(
            f"value is not canonically serializable: {error}"
        ) from error
    return text.encode("utf-8")


def compute_self_digest(payload: dict[str, Any]) -> str:
    """SHA-256, lowercase hex, over canonical bytes of ``payload`` sans ``self_digest``.

    Only the object's own ``self_digest`` is removed before hashing (§5.B.2 step
    2).  No other field is stripped, because per §5.B.1 no same-object alias of
    that value exists on any artifact to strip.
    """

    body = {key: value for key, value in payload.items() if key != SELF_DIGEST_FIELD}
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def attach_self_digest(payload: dict[str, Any]) -> dict[str, Any]:
    """Return ``payload`` with a freshly computed ``self_digest`` attached."""

    body = {key: value for key, value in payload.items() if key != SELF_DIGEST_FIELD}
    sealed = dict(body)
    sealed[SELF_DIGEST_FIELD] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    return sealed


def verify_self_digest(artifact: dict[str, Any]) -> None:
    """Fail closed unless ``artifact`` carries a valid, matching ``self_digest``.

    Implements §5.B.2 steps 3-7 for an already-parsed object: the claimed digest
    must be present, must be lowercase 64-character hexadecimal, and must equal
    SHA-256 over the recanonicalized remainder.  A content edit that did not
    recompute the digest and a digest edit that did not follow a content change
    are both caught here, and neither is repaired.
    """

    claimed = artifact.get(SELF_DIGEST_FIELD)
    if claimed is None:
        raise ConfirmatoryRegistrationError(
            f"artifact is missing its {SELF_DIGEST_FIELD} field"
        )
    if not isinstance(claimed, str) or not _DIGEST_PATTERN.fullmatch(claimed):
        raise ConfirmatoryRegistrationError(
            f"{SELF_DIGEST_FIELD} is not a lowercase 64-character SHA-256 hex digest: "
            f"{claimed!r}"
        )
    recomputed = compute_self_digest(artifact)
    if not hmac.compare_digest(recomputed, claimed):
        raise ConfirmatoryRegistrationError(
            f"{SELF_DIGEST_FIELD} mismatch: claimed {claimed}, recomputed {recomputed}"
        )


def serialize_artifact(artifact: dict[str, Any]) -> bytes:
    """Persisted bytes: canonical JSON including ``self_digest``, then one LF.

    The digest is verified before serialization, so a hand-mutated artifact can
    never reach disk under a stale digest.  The trailing LF is appended last and
    is a pure file-formatting convenience, never part of any digest (§5.B.2).
    """

    verify_self_digest(artifact)
    return canonical_json_bytes(artifact) + b"\n"


def parse_artifact(data: bytes) -> dict[str, Any]:
    """Parse persisted artifact bytes and verify the claimed ``self_digest``.

    Implements §5.B.2's verification procedure end to end: strip at most one
    trailing LF, decode UTF-8, parse JSON, then verify.  Malformed bytes,
    malformed JSON, a non-object payload, a missing or ill-formed digest, and a
    digest mismatch are all hard failures.
    """

    if data.endswith(b"\n"):
        data = data[:-1]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ConfirmatoryRegistrationError(
            f"artifact bytes are not valid UTF-8: {error}"
        ) from error
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise ConfirmatoryRegistrationError(
            f"artifact is not valid JSON: {error}"
        ) from error
    if not isinstance(parsed, dict):
        raise ConfirmatoryRegistrationError(
            f"artifact must be a JSON object, got {type(parsed).__name__}"
        )
    artifact: dict[str, Any] = parsed
    verify_self_digest(artifact)
    return artifact


def _require_string_keys(value: Any, *, path: str) -> None:
    """Reject non-string object keys anywhere in a canonical payload (§5.B.2)."""

    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ConfirmatoryRegistrationError(
                    f"{path}: JSON object keys must be strings, got "
                    f"{type(key).__name__}"
                )
            _require_string_keys(item, path=f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _require_string_keys(item, path=f"{path}[{index}]")


# ---------------------------------------------------------------------------
# Stage-A proposed-design records (§5.A Stage A, §5.C identity fields, §5.I.4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProposedStratumV1:
    """One proposed provider/model stratum of the draft matrix (§5.A Stage A)."""

    provider: str
    model: str

    def __post_init__(self) -> None:
        _require_nonempty_text(self.provider, "proposed_strata[].provider")
        _require_nonempty_text(self.model, "proposed_strata[].model")

    def to_dict(self) -> dict[str, Any]:
        return {"model": self.model, "provider": self.provider}

    @property
    def identity(self) -> tuple[str, str]:
        return (self.provider, self.model)


@dataclass(frozen=True, slots=True)
class ProposedRepetitionsEntryV1:
    """Proposed repetition count for one ``(task, provider, model)`` cell.

    The granularity is per ``(task_cluster, model_stratum)`` because that is the
    granularity of the frozen target estimand's inner average ``Sched(k, m)``
    (clarification §4.3).  A uniform count across every cell is a permitted
    special case of this schema, not a separate one.
    """

    task_id: str
    provider: str
    model: str
    repetition_count: int

    def __post_init__(self) -> None:
        _require_nonempty_text(self.task_id, "proposed_repetitions[].task_id")
        _require_nonempty_text(self.provider, "proposed_repetitions[].provider")
        _require_nonempty_text(self.model, "proposed_repetitions[].model")
        _require_integer(
            self.repetition_count,
            "proposed_repetitions[].repetition_count",
            minimum=1,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "provider": self.provider,
            "repetition_count": self.repetition_count,
            "task_id": self.task_id,
        }

    @property
    def cell(self) -> tuple[str, str, str]:
        """The ``(task_id, provider, model)`` cell this entry counts."""

        return (self.task_id, self.provider, self.model)


@dataclass(frozen=True, slots=True)
class ProposedProviderSeedEntryV1:
    """The ordinary provider seed proposed for one repetition index.

    Keyed on ``repetition`` alone because the ordinary provider seed is already
    frozen as a function of the repetition index — seed and repetition are
    collinear, and the seed is a matched-contrast property, not a treatment
    property (clarification §4.3).

    These are **ordinary provider seeds only**.  They are not, and can never
    become, randomization bits, assignment material, or Monte Carlo seed
    material.
    """

    repetition: int
    provider_seed: int

    def __post_init__(self) -> None:
        _require_integer(
            self.repetition, "proposed_provider_seeds[].repetition", minimum=0
        )
        _require_integer(
            self.provider_seed, "proposed_provider_seeds[].provider_seed"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_seed": self.provider_seed,
            "repetition": self.repetition,
        }


@dataclass(frozen=True, slots=True)
class ProposedPositionV1:
    """One proposed fixed position: the six identity fields plus its baseline label.

    The Stage-A record is a strict superset of the §5.C identity payload by
    exactly one field, ``baseline_label`` (clarification §5.2).  The label is
    carried by the record and **never** by the identity payload: a position's
    identity must not depend on which label it ends up receiving, or the
    identity would leak assignment information and could not be registered
    before ``b_k`` is drawn (§5.C).

    ``position_id`` is *not* computed here.  It first exists at Stage C, derived
    from :meth:`identity_payload` of the immutable proposed position
    (clarification §5.1, §5.2).
    """

    task_id: str
    provider: str
    model: str
    repetition: int
    provider_seed: int
    slot: int
    baseline_label: str

    def __post_init__(self) -> None:
        _require_nonempty_text(self.task_id, "proposed_positions[].task_id")
        _require_nonempty_text(self.provider, "proposed_positions[].provider")
        _require_nonempty_text(self.model, "proposed_positions[].model")
        _require_integer(self.repetition, "proposed_positions[].repetition", minimum=0)
        _require_integer(self.provider_seed, "proposed_positions[].provider_seed")
        _require_integer(self.slot, "proposed_positions[].slot")
        if self.slot not in _SLOTS:
            raise ConfirmatoryRegistrationError(
                f"proposed_positions[].slot must be one of {list(_SLOTS)}, got "
                f"{self.slot!r}"
            )
        if self.baseline_label not in BASELINE_LABELS:
            raise ConfirmatoryRegistrationError(
                f"proposed_positions[].baseline_label must be one of "
                f"{list(BASELINE_LABELS)}, got {self.baseline_label!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        payload = self.identity_payload()
        payload["baseline_label"] = self.baseline_label
        return payload

    def identity_payload(self) -> dict[str, Any]:
        """Exactly the six identity fields Stage C hashes (clarification §5.1).

        ``baseline_label`` is deliberately excluded.  Nothing here hashes this
        payload: deriving ``position_id`` is Stage-C work.
        """

        return {
            "model": self.model,
            "provider": self.provider,
            "provider_seed": self.provider_seed,
            "repetition": self.repetition,
            "slot": self.slot,
            "task_id": self.task_id,
        }

    @property
    def identity(self) -> tuple[str, str, str, int, int, int]:
        """The six frozen identity fields, in the §5.C field order."""

        return (
            self.task_id,
            self.provider,
            self.model,
            self.repetition,
            self.provider_seed,
            self.slot,
        )

    @property
    def placement(self) -> tuple[str, str, str, int, int]:
        """The ``(task_id, provider, model, repetition, slot)`` ordering key."""

        return (
            self.task_id,
            self.provider,
            self.model,
            self.repetition,
            self.slot,
        )

    @property
    def group(self) -> tuple[str, str, str, int]:
        """The ``(task_id, provider, model, repetition)`` matched-contrast group."""

        return (self.task_id, self.provider, self.model, self.repetition)


@dataclass(frozen=True, slots=True)
class RetryPolicyV1:
    """The complete retry configuration, schema frozen by §5.I.4.

    ``initial_delay_seconds``/``max_delay_seconds`` are canonical decimal
    strings rather than binary floats so the persisted value is exact.
    ``retryable_error_classes`` must arrive already sorted and unique: the frozen
    rule makes deduplication a schema-level precondition applied *before*
    canonicalization, so an out-of-order or duplicated list is rejected here
    rather than silently normalized into validity.  A zero-retry configuration is
    recorded verbatim, never omitted or left implicit.
    """

    max_attempts: int
    backoff_kind: str
    initial_delay_seconds: str
    max_delay_seconds: str
    retryable_error_classes: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_integer(self.max_attempts, "retry_policy.max_attempts", minimum=1)
        if self.backoff_kind not in BACKOFF_KINDS:
            raise ConfirmatoryRegistrationError(
                f"retry_policy.backoff_kind must be one of {list(BACKOFF_KINDS)}, got "
                f"{self.backoff_kind!r}"
            )
        _require_canonical_decimal(
            self.initial_delay_seconds, "retry_policy.initial_delay_seconds"
        )
        _require_canonical_decimal(
            self.max_delay_seconds, "retry_policy.max_delay_seconds"
        )
        classes = self.retryable_error_classes
        if not isinstance(classes, tuple):
            raise ConfirmatoryRegistrationError(
                "retry_policy.retryable_error_classes must be a tuple"
            )
        for item in classes:
            _require_nonempty_text(item, "retry_policy.retryable_error_classes[]")
        if list(classes) != sorted(set(classes)):
            raise ConfirmatoryRegistrationError(
                "retry_policy.retryable_error_classes must be sorted and unique"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "backoff_kind": self.backoff_kind,
            "initial_delay_seconds": self.initial_delay_seconds,
            "max_attempts": self.max_attempts,
            "max_delay_seconds": self.max_delay_seconds,
            "retryable_error_classes": list(self.retryable_error_classes),
        }


@dataclass(frozen=True, slots=True)
class RuntimeSnapshotV1:
    """The complete two-layer runtime snapshot frozen by §5.I.

    Callers supply the captured invariant fields and capture timestamp.  Both
    digests are derived here: ``runtime_identity_digest`` hashes exactly the
    invariant field set from §5.I.1, while ``self_digest`` additionally binds the
    identity digest and ``captured_at`` as required by §5.I.2.  Neither digest is
    accepted as free-standing caller input.
    """

    provider_name: str
    model: str
    endpoint: str
    provider_config_digest: str
    provider_parameters_digest: str
    timeout_seconds: str
    retry_policy: RetryPolicyV1
    tool_contract_policy: str
    native_tool_adapter_version: str
    package_source_sha256: str
    python_version: str
    artifact_version: str
    prompt_digest: str
    experiment_config_digest: str
    models_config_digest: str
    environment_fingerprint: str
    captured_at: str
    schema_version: str = field(
        init=False, default=RUNTIME_SNAPSHOT_SCHEMA_VERSION
    )
    runtime_identity_digest: str = field(init=False)
    self_digest: str = field(init=False)

    def __post_init__(self) -> None:
        for name in (
            "provider_name",
            "model",
            "endpoint",
            "tool_contract_policy",
            "native_tool_adapter_version",
            "python_version",
            "artifact_version",
        ):
            _require_nonempty_text(getattr(self, name), f"runtime_snapshot.{name}")
        for name in (
            "provider_config_digest",
            "provider_parameters_digest",
            "package_source_sha256",
            "prompt_digest",
            "experiment_config_digest",
            "models_config_digest",
            "environment_fingerprint",
        ):
            _require_digest(getattr(self, name), f"runtime_snapshot.{name}")
        _require_canonical_decimal(
            self.timeout_seconds, "runtime_snapshot.timeout_seconds"
        )
        if not isinstance(self.retry_policy, RetryPolicyV1):
            raise ConfirmatoryRegistrationError(
                "runtime_snapshot.retry_policy must be a RetryPolicyV1"
            )
        _require_aware_datetime(
            _parse_timestamp(self.captured_at, "runtime_snapshot.captured_at"),
            "runtime_snapshot.captured_at",
        )
        identity_digest = hashlib.sha256(
            canonical_json_bytes(self.identity_payload())
        ).hexdigest()
        object.__setattr__(self, "runtime_identity_digest", identity_digest)
        object.__setattr__(
            self,
            SELF_DIGEST_FIELD,
            hashlib.sha256(canonical_json_bytes(self.canonical_payload())).hexdigest(),
        )

    def identity_payload(self) -> dict[str, Any]:
        """Exactly the invariant field set hashed by §5.I.1."""

        return {
            "artifact_version": self.artifact_version,
            "endpoint": self.endpoint,
            "environment_fingerprint": self.environment_fingerprint,
            "experiment_config_digest": self.experiment_config_digest,
            "model": self.model,
            "models_config_digest": self.models_config_digest,
            "native_tool_adapter_version": self.native_tool_adapter_version,
            "package_source_sha256": self.package_source_sha256,
            "prompt_digest": self.prompt_digest,
            "provider_config_digest": self.provider_config_digest,
            "provider_name": self.provider_name,
            "provider_parameters_digest": self.provider_parameters_digest,
            "python_version": self.python_version,
            "retry_policy": self.retry_policy.to_dict(),
            "schema_version": self.schema_version,
            "timeout_seconds": self.timeout_seconds,
            "tool_contract_policy": self.tool_contract_policy,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Snapshot digest input: identity fields plus capture metadata."""

        payload = self.identity_payload()
        payload["captured_at"] = self.captured_at
        payload["runtime_identity_digest"] = self.runtime_identity_digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = self.canonical_payload()
        payload[SELF_DIGEST_FIELD] = self.self_digest
        return payload


@dataclass(frozen=True, slots=True)
class ProposedRuntimeConfigurationV1:
    """The proposed runtime configuration bound into the draft (§5.I.4, §5.I.5).

    The complete registration-expected ``RuntimeSnapshotV1`` is embedded here,
    so Stage A binds both the expected identity and the capture record before
    eligibility/final registration.  The explicit timeout/retry values must
    equal the snapshot fields; a caller cannot pair one proposed configuration
    with an unrelated identity digest.
    """

    timeout_seconds: str
    retry_policy: RetryPolicyV1
    registration_expected_runtime_snapshot: RuntimeSnapshotV1

    def __post_init__(self) -> None:
        _require_canonical_decimal(
            self.timeout_seconds, "proposed_runtime_configuration.timeout_seconds"
        )
        if not isinstance(self.retry_policy, RetryPolicyV1):
            raise ConfirmatoryRegistrationError(
                "proposed_runtime_configuration.retry_policy must be a RetryPolicyV1"
            )
        snapshot = self.registration_expected_runtime_snapshot
        if not isinstance(snapshot, RuntimeSnapshotV1):
            raise ConfirmatoryRegistrationError(
                "proposed_runtime_configuration.registration_expected_runtime_snapshot "
                "must be a RuntimeSnapshotV1"
            )
        if self.timeout_seconds != snapshot.timeout_seconds:
            raise ConfirmatoryRegistrationError(
                "proposed_runtime_configuration.timeout_seconds must match the "
                "registration-expected RuntimeSnapshotV1"
            )
        if self.retry_policy != snapshot.retry_policy:
            raise ConfirmatoryRegistrationError(
                "proposed_runtime_configuration.retry_policy must match the "
                "registration-expected RuntimeSnapshotV1"
            )

    @property
    def registration_expected_runtime_identity_digest(self) -> str:
        """The derived identity later capture points must reproduce."""

        return self.registration_expected_runtime_snapshot.runtime_identity_digest

    def to_dict(self) -> dict[str, Any]:
        return {
            "registration_expected_runtime_snapshot": (
                self.registration_expected_runtime_snapshot.to_dict()
            ),
            "retry_policy": self.retry_policy.to_dict(),
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class ProposedStatisticalConfigurationV1:
    """The Stage-A statistical configuration: exactly eleven keys (clarification §7).

    Exactly one key is caller-proposed, ``randomization_mc_samples``.  The other
    ten are global frozen constants stamped by implementation and therefore
    declared ``init=False`` — a caller cannot supply a wrong value, and a
    persisted draft whose stamped key does not equal its frozen literal fails
    V9 on load.  Recording a constant is an auditability act, never a caller
    choice: it is what lets a later analyzer detect a mismatch rather than
    silently assume agreement (clarification §7.3).

    ``randomization_mc_samples`` is the proposed ``M``.  The key is present in
    every draft, and ``null`` means "no Monte Carlo sample count has been
    prospectively proposed for this draft" — not zero, not "decide later", not
    "inapplicable".  Absence of the key is never a valid encoding of that
    statement (clarification §8.1).

    ``K`` and ``randomization_mode`` are deliberately absent: both are Stage-C
    deterministic derivations, and neither may be proposed or hinted at here
    (clarification §8.2, §10.2).  The bidirectional mode/``M`` gate of
    clarification §8.3 likewise belongs to final registration, not to Stage A.
    """

    randomization_mc_samples: int | None = None
    schema_version: str = field(
        init=False, default=PROPOSED_STATISTICAL_CONFIGURATION_SCHEMA_VERSION
    )
    statistic_spec_id: str = field(init=False, default=STATISTIC_SPEC_ID)
    alpha: str = field(init=False, default=ALPHA)
    multiplicity_architecture: str = field(
        init=False, default=MULTIPLICITY_ARCHITECTURE
    )
    primary_endpoint: str = field(init=False, default=PRIMARY_ENDPOINT)
    secondary_endpoint_sequence: tuple[str, ...] = field(
        init=False, default=SECONDARY_ENDPOINT_SEQUENCE
    )
    primary_estimand_architecture: str = field(
        init=False, default=PRIMARY_ESTIMAND_ARCHITECTURE
    )
    aggregation_rule: str = field(init=False, default=AGGREGATION_RULE)
    treatment_contrast_orientation: str = field(
        init=False, default=TREATMENT_CONTRAST_ORIENTATION
    )
    randomization_exact_enumeration_max_k: int = field(
        init=False, default=RANDOMIZATION_EXACT_ENUMERATION_MAX_K
    )

    def __post_init__(self) -> None:
        if self.randomization_mc_samples is not None:
            _require_integer(
                self.randomization_mc_samples,
                "proposed_statistical_configuration.randomization_mc_samples",
                minimum=1,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "aggregation_rule": self.aggregation_rule,
            "alpha": self.alpha,
            "multiplicity_architecture": self.multiplicity_architecture,
            "primary_endpoint": self.primary_endpoint,
            "primary_estimand_architecture": self.primary_estimand_architecture,
            "randomization_exact_enumeration_max_k": (
                self.randomization_exact_enumeration_max_k
            ),
            "randomization_mc_samples": self.randomization_mc_samples,
            "schema_version": self.schema_version,
            "secondary_endpoint_sequence": list(self.secondary_endpoint_sequence),
            "statistic_spec_id": self.statistic_spec_id,
            "treatment_contrast_orientation": self.treatment_contrast_orientation,
        }


@dataclass(frozen=True, slots=True)
class RegistrationDraft:
    """The Stage-A ``REGISTRATION_DRAFT`` artifact (§5.A Stage A).

    Construct through :func:`draft_registration`, which validates the proposed
    design and seals it with a ``self_digest``.  The record stores exactly one
    digest of itself and never a ``registration_draft_digest`` alias — that name
    is what *downstream* artifacts call this object's ``self_digest`` (§5.B.1).
    """

    schema_version: str
    registration_state: str
    confirmatory_profile: str
    design_id: str
    created_at: str
    proposed_tasks: tuple[str, ...]
    proposed_strata: tuple[ProposedStratumV1, ...]
    proposed_repetitions: tuple[ProposedRepetitionsEntryV1, ...]
    proposed_provider_seeds: tuple[ProposedProviderSeedEntryV1, ...]
    proposed_positions: tuple[ProposedPositionV1, ...]
    proposed_runtime_configuration: ProposedRuntimeConfigurationV1
    proposed_statistical_configuration: ProposedStatisticalConfigurationV1
    self_digest: str

    def canonical_payload(self) -> dict[str, Any]:
        """The digest input: the whole artifact except its own ``self_digest``.

        Every array preserves registered order; the canonicalization step never
        reorders or deduplicates one (§5.B.2).  The sorting and uniqueness rules
        of clarification §4.3 are schema-level preconditions enforced before
        canonicalization, never canonicalization-time transformations.
        """

        return {
            "confirmatory_profile": self.confirmatory_profile,
            "created_at": self.created_at,
            "design_id": self.design_id,
            "proposed_positions": [
                position.to_dict() for position in self.proposed_positions
            ],
            "proposed_provider_seeds": [
                entry.to_dict() for entry in self.proposed_provider_seeds
            ],
            "proposed_repetitions": [
                entry.to_dict() for entry in self.proposed_repetitions
            ],
            "proposed_runtime_configuration": (
                self.proposed_runtime_configuration.to_dict()
            ),
            "proposed_statistical_configuration": (
                self.proposed_statistical_configuration.to_dict()
            ),
            "proposed_strata": [stratum.to_dict() for stratum in self.proposed_strata],
            "proposed_tasks": list(self.proposed_tasks),
            "registration_state": self.registration_state,
            "schema_version": self.schema_version,
        }

    def to_artifact(self) -> dict[str, Any]:
        """The full persisted object: the canonical payload plus ``self_digest``."""

        artifact = self.canonical_payload()
        artifact[SELF_DIGEST_FIELD] = self.self_digest
        return artifact


# ---------------------------------------------------------------------------
# Stage-A construction boundary (§5.A Stage A)
# ---------------------------------------------------------------------------


def draft_registration(
    *,
    design_id: str,
    created_at: datetime,
    proposed_tasks: Sequence[str],
    proposed_strata: Sequence[ProposedStratumV1],
    proposed_repetitions: Sequence[ProposedRepetitionsEntryV1],
    proposed_provider_seeds: Sequence[ProposedProviderSeedEntryV1],
    proposed_positions: Sequence[ProposedPositionV1],
    proposed_runtime_configuration: ProposedRuntimeConfigurationV1,
    proposed_randomization_mc_samples: int | None = None,
) -> RegistrationDraft:
    """Build and seal a Stage-A registration draft from a proposed design.

    ``schema_version``, ``registration_state``, ``confirmatory_profile``, and
    every stamped statistical constant are taken from this module's frozen
    literals rather than from the caller, so a draft always records the
    lifecycle stage and statistical identity this implementation realizes.

    ``created_at`` must be a timezone-aware UTC instant at whole-second
    precision; it is supplied rather than read from a clock so construction
    stays deterministic and testable.

    The complete collection of ``(identity fields, baseline_label)`` over
    ``proposed_positions`` **is** the proposed baseline schedule ``S_k``, bound
    prospectively here (clarification §6.1).  Binding it draws no randomness and
    generates no assignment bit: the labels transcribe an already-deterministic
    frozen counterbalancing function (clarification §6.2).

    The draft is sealed with its ``self_digest`` before it is returned.  It
    authorizes nothing: no eligibility disposition, no assignment, no execution.
    """

    _require_design_id(design_id)
    created_at_text = _require_created_at_instant(created_at)
    tasks = tuple(proposed_tasks)
    strata = tuple(proposed_strata)
    repetitions = tuple(proposed_repetitions)
    provider_seeds = tuple(proposed_provider_seeds)
    positions = tuple(proposed_positions)
    _validate_proposed_matrix(
        proposed_tasks=tasks,
        proposed_strata=strata,
        proposed_repetitions=repetitions,
        proposed_provider_seeds=provider_seeds,
        proposed_positions=positions,
    )
    if not isinstance(proposed_runtime_configuration, ProposedRuntimeConfigurationV1):
        raise ConfirmatoryRegistrationError(
            "proposed_runtime_configuration must be a ProposedRuntimeConfigurationV1"
        )
    unsealed = RegistrationDraft(
        schema_version=REGISTRATION_DRAFT_SCHEMA_VERSION,
        registration_state=REGISTRATION_STATE_DRAFT,
        confirmatory_profile=CONFIRMATORY_PROFILE,
        design_id=design_id,
        created_at=created_at_text,
        proposed_tasks=tasks,
        proposed_strata=strata,
        proposed_repetitions=repetitions,
        proposed_provider_seeds=provider_seeds,
        proposed_positions=positions,
        proposed_runtime_configuration=proposed_runtime_configuration,
        proposed_statistical_configuration=ProposedStatisticalConfigurationV1(
            randomization_mc_samples=proposed_randomization_mc_samples,
        ),
        self_digest="",
    )
    return replace(
        unsealed,
        self_digest=hashlib.sha256(
            canonical_json_bytes(unsealed.canonical_payload())
        ).hexdigest(),
    )


def _validate_proposed_matrix(
    *,
    proposed_tasks: tuple[str, ...],
    proposed_strata: tuple[ProposedStratumV1, ...],
    proposed_repetitions: tuple[ProposedRepetitionsEntryV1, ...],
    proposed_provider_seeds: tuple[ProposedProviderSeedEntryV1, ...],
    proposed_positions: tuple[ProposedPositionV1, ...],
) -> None:
    """Enforce clarification §4.5 rules V3-V8 over the proposed matrix.

    Nothing here sorts, repairs, fills, or deduplicates.  A draft whose arrays
    are out of order, incompletely covered, duplicated, or internally
    inconsistent is rejected, both at construction and on load; the ordering
    rules are schema-level preconditions, not transformations this code applies
    on the caller's behalf.
    """

    # V3 — proposed_tasks non-empty, sorted ascending, unique.
    _require_sorted_unique(proposed_tasks, "proposed_tasks")
    for index, task_id in enumerate(proposed_tasks):
        _require_nonempty_text(task_id, f"proposed_tasks[{index}]")

    # V4 — proposed_strata non-empty, sorted ascending by (provider, model),
    # unique.
    stratum_keys = tuple(stratum.identity for stratum in proposed_strata)
    _require_sorted_unique(stratum_keys, "proposed_strata")

    # V5 — proposed_repetitions covers proposed_tasks x proposed_strata exactly
    # once each, sorted ascending by (task_id, provider, model).  Iterating tasks
    # outermost over the two already-sorted arrays yields exactly that order.
    expected_cells = [
        (task_id, provider, model)
        for task_id in proposed_tasks
        for provider, model in stratum_keys
    ]
    _require_exact_cover(
        [entry.cell for entry in proposed_repetitions],
        expected_cells,
        "proposed_repetitions",
        "(task_id, provider, model)",
    )

    # V6 — proposed_positions is exactly two positions, slot 1 and slot 2, for
    # every repetition index of every repetitions entry.
    expected_placements = [
        (entry.task_id, entry.provider, entry.model, repetition, slot)
        for entry in proposed_repetitions
        for repetition in range(entry.repetition_count)
        for slot in _SLOTS
    ]
    _require_exact_cover(
        [position.placement for position in proposed_positions],
        expected_placements,
        "proposed_positions",
        "(task_id, provider, model, repetition, slot)",
    )

    # V7 — every matched-contrast group carries exactly one "off" and one
    # "full".  V6 already fixed each group at two positions, so this fixes the
    # label multiset, which is what makes OFF/FULL balance structural under
    # complementation rather than merely asserted (clarification §6.2).
    labels_by_group: dict[tuple[str, str, str, int], list[str]] = {}
    for position in proposed_positions:
        labels_by_group.setdefault(position.group, []).append(position.baseline_label)
    expected_labels = sorted(BASELINE_LABELS)
    for group, labels in labels_by_group.items():
        if sorted(labels) != expected_labels:
            raise ConfirmatoryRegistrationError(
                f"proposed_positions group {group!r} must carry exactly one "
                f"{BASELINE_LABEL_OFF!r} and one {BASELINE_LABEL_FULL!r} "
                f"baseline_label, got {sorted(labels)!r}"
            )

    # V8 — the seed table covers exactly the repetition indices the positions
    # use, sorted and unique, and every position agrees with its entry.
    _require_exact_cover(
        [entry.repetition for entry in proposed_provider_seeds],
        sorted({position.repetition for position in proposed_positions}),
        "proposed_provider_seeds",
        "repetition",
    )
    seed_for_repetition = {
        entry.repetition: entry.provider_seed for entry in proposed_provider_seeds
    }
    for index, position in enumerate(proposed_positions):
        expected_seed = seed_for_repetition[position.repetition]
        if position.provider_seed != expected_seed:
            raise ConfirmatoryRegistrationError(
                f"proposed_positions[{index}].provider_seed {position.provider_seed!r} "
                f"does not match the proposed seed {expected_seed!r} registered for "
                f"repetition {position.repetition!r}"
            )


def _require_sorted_unique(values: Sequence[Any], context: str) -> None:
    """Reject an empty, unsorted, or duplicated registered array."""

    if not values:
        raise ConfirmatoryRegistrationError(f"{context} must not be empty")
    items = list(values)
    if len(set(items)) != len(items):
        raise ConfirmatoryRegistrationError(f"{context} must not contain duplicates")
    if items != sorted(items):
        raise ConfirmatoryRegistrationError(
            f"{context} must be sorted ascending; it is not re-sorted on your behalf"
        )


def _require_exact_cover(
    actual: Sequence[Any], expected: Sequence[Any], context: str, key_name: str
) -> None:
    """Reject anything but an exact, correctly ordered cover of ``expected``.

    Reported as three distinct failures — coverage, duplication, ordering — so a
    malformed draft names which rule it broke rather than only that it differed.
    """

    actual_items = list(actual)
    expected_items = list(expected)
    missing = sorted(set(expected_items) - set(actual_items), key=repr)
    unexpected = sorted(set(actual_items) - set(expected_items), key=repr)
    if missing or unexpected:
        raise ConfirmatoryRegistrationError(
            f"{context} must cover every {key_name} exactly once; "
            f"missing={missing!r} unexpected={unexpected!r}"
        )
    if len(set(actual_items)) != len(actual_items):
        raise ConfirmatoryRegistrationError(
            f"{context} must not contain a duplicate {key_name}"
        )
    if actual_items != expected_items:
        raise ConfirmatoryRegistrationError(
            f"{context} must be sorted ascending by {key_name}; it is not "
            "re-sorted on your behalf"
        )


# ---------------------------------------------------------------------------
# Immutable persistence and fail-closed load (§5.B, §6)
# ---------------------------------------------------------------------------


def registration_draft_path(confirmatory_root: Path, design_id: str) -> Path:
    """``<confirmatory_root>/<design_id>/registration_draft.json`` (§5.B layout)."""

    safe_design_id = _require_design_id(design_id)
    root = Path(confirmatory_root)
    path = root / safe_design_id / REGISTRATION_DRAFT_FILENAME
    resolved_root = root.resolve(strict=False)
    resolved_path = path.resolve(strict=False)
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as error:
        raise ConfirmatoryRegistrationError(
            f"registration draft path escapes confirmatory_root: {path}"
        ) from error
    return path


def _validated_draft_artifact_for_write(
    draft: RegistrationDraft,
) -> dict[str, Any]:
    """Revalidate the complete persisted contract before any filesystem mutation."""

    if not isinstance(draft, RegistrationDraft):
        raise ConfirmatoryRegistrationError(
            "draft must be a RegistrationDraft"
        )
    try:
        artifact = draft.to_artifact()
    except (AttributeError, TypeError, ValueError) as error:
        raise ConfirmatoryRegistrationError(
            f"registration draft cannot be represented by the frozen schema: {error}"
        ) from error
    # Rebuild through the same exact-key, literal, type, membership, runtime,
    # statistical, and digest checks used by the fail-closed loader.  This is
    # deliberately before path calculation, mkdir, and open("xb").
    _draft_from_artifact(artifact)
    return artifact


def write_registration_draft(
    draft: RegistrationDraft, *, confirmatory_root: Path
) -> Path:
    """Write ``registration_draft.json`` once, under the draft's own design id.

    The write is an exclusive create, so an existing draft is never replaced,
    truncated, or edited in place: a draft may be superseded only by a **new**
    draft under a **new** ``design_id`` (§6).  The digest is verified before any
    byte reaches disk, and the persisted form is canonical JSON including
    ``self_digest`` followed by exactly one LF.
    """

    artifact = _validated_draft_artifact_for_write(draft)
    payload = serialize_artifact(artifact)
    path = registration_draft_path(confirmatory_root, draft.design_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
    except FileExistsError as error:
        raise ConfirmatoryRegistrationError(
            f"registration draft already exists and is immutable: {path}"
        ) from error
    return path


def load_registration_draft(path: Path) -> RegistrationDraft:
    """Read, verify, and rebuild a persisted registration draft, failing closed.

    The claimed ``self_digest`` is verified against the recanonicalized content
    before any field is interpreted, the key set must be exactly the frozen one,
    and the rebuilt record must re-derive the same digest — so a typed draft is
    never returned for bytes it does not faithfully represent.
    """

    artifact = parse_artifact(Path(path).read_bytes())
    return _draft_from_artifact(artifact)


def _draft_from_artifact(artifact: dict[str, Any]) -> RegistrationDraft:
    _require_exact_keys(artifact, _DRAFT_KEYS, REGISTRATION_DRAFT_FILENAME)
    _require_literal(artifact, "schema_version", REGISTRATION_DRAFT_SCHEMA_VERSION)
    _require_literal(artifact, "registration_state", REGISTRATION_STATE_DRAFT)
    _require_literal(artifact, "confirmatory_profile", CONFIRMATORY_PROFILE)
    design_id = _require_text_field(artifact, "design_id")
    _require_design_id(design_id)
    created_at = _require_text_field(artifact, "created_at")
    _require_created_at_text(created_at)
    tasks = tuple(
        _require_text_item(item, f"proposed_tasks[{index}]")
        for index, item in enumerate(_require_array_field(artifact, "proposed_tasks"))
    )
    strata = tuple(
        _stratum_from_mapping(item, f"proposed_strata[{index}]")
        for index, item in enumerate(_require_array_field(artifact, "proposed_strata"))
    )
    repetitions = tuple(
        _repetitions_entry_from_mapping(item, f"proposed_repetitions[{index}]")
        for index, item in enumerate(
            _require_array_field(artifact, "proposed_repetitions")
        )
    )
    provider_seeds = tuple(
        _provider_seed_entry_from_mapping(item, f"proposed_provider_seeds[{index}]")
        for index, item in enumerate(
            _require_array_field(artifact, "proposed_provider_seeds")
        )
    )
    positions = tuple(
        _position_from_mapping(item, f"proposed_positions[{index}]")
        for index, item in enumerate(
            _require_array_field(artifact, "proposed_positions")
        )
    )
    _validate_proposed_matrix(
        proposed_tasks=tasks,
        proposed_strata=strata,
        proposed_repetitions=repetitions,
        proposed_provider_seeds=provider_seeds,
        proposed_positions=positions,
    )
    runtime = _runtime_from_mapping(
        _require_object_field(artifact, "proposed_runtime_configuration"),
        "proposed_runtime_configuration",
    )
    statistical = _statistical_from_mapping(
        _require_object_field(artifact, "proposed_statistical_configuration"),
        "proposed_statistical_configuration",
    )
    draft = RegistrationDraft(
        schema_version=REGISTRATION_DRAFT_SCHEMA_VERSION,
        registration_state=REGISTRATION_STATE_DRAFT,
        confirmatory_profile=CONFIRMATORY_PROFILE,
        design_id=design_id,
        created_at=created_at,
        proposed_tasks=tasks,
        proposed_strata=strata,
        proposed_repetitions=repetitions,
        proposed_provider_seeds=provider_seeds,
        proposed_positions=positions,
        proposed_runtime_configuration=runtime,
        proposed_statistical_configuration=statistical,
        self_digest=_require_text_field(artifact, SELF_DIGEST_FIELD),
    )
    rebuilt = hashlib.sha256(canonical_json_bytes(draft.canonical_payload())).hexdigest()
    if not hmac.compare_digest(rebuilt, draft.self_digest):
        raise ConfirmatoryRegistrationError(
            "rebuilt registration draft does not reproduce the persisted "
            f"{SELF_DIGEST_FIELD}"
        )
    return draft


def _stratum_from_mapping(value: Any, context: str) -> ProposedStratumV1:
    mapping = _require_object(value, context)
    _require_exact_keys(mapping, _STRATUM_KEYS, context)
    return ProposedStratumV1(
        provider=_require_text_field(mapping, "provider", context),
        model=_require_text_field(mapping, "model", context),
    )


def _repetitions_entry_from_mapping(
    value: Any, context: str
) -> ProposedRepetitionsEntryV1:
    mapping = _require_object(value, context)
    _require_exact_keys(mapping, _REPETITIONS_ENTRY_KEYS, context)
    return ProposedRepetitionsEntryV1(
        task_id=_require_text_field(mapping, "task_id", context),
        provider=_require_text_field(mapping, "provider", context),
        model=_require_text_field(mapping, "model", context),
        repetition_count=_require_integer_field(
            mapping, "repetition_count", context, minimum=1
        ),
    )


def _provider_seed_entry_from_mapping(
    value: Any, context: str
) -> ProposedProviderSeedEntryV1:
    mapping = _require_object(value, context)
    _require_exact_keys(mapping, _PROVIDER_SEED_ENTRY_KEYS, context)
    return ProposedProviderSeedEntryV1(
        repetition=_require_integer_field(mapping, "repetition", context, minimum=0),
        provider_seed=_require_integer_field(mapping, "provider_seed", context),
    )


def _position_from_mapping(value: Any, context: str) -> ProposedPositionV1:
    mapping = _require_object(value, context)
    _require_exact_keys(mapping, _POSITION_KEYS, context)
    return ProposedPositionV1(
        task_id=_require_text_field(mapping, "task_id", context),
        provider=_require_text_field(mapping, "provider", context),
        model=_require_text_field(mapping, "model", context),
        repetition=_require_integer_field(mapping, "repetition", context, minimum=0),
        provider_seed=_require_integer_field(mapping, "provider_seed", context),
        slot=_require_integer_field(mapping, "slot", context),
        baseline_label=_require_text_field(mapping, "baseline_label", context),
    )


def _retry_policy_from_mapping(value: Any, context: str) -> RetryPolicyV1:
    mapping = _require_object(value, context)
    _require_exact_keys(mapping, _RETRY_POLICY_KEYS, context)
    classes = _require_array_field(mapping, "retryable_error_classes", context)
    return RetryPolicyV1(
        max_attempts=_require_integer_field(mapping, "max_attempts", context, minimum=1),
        backoff_kind=_require_text_field(mapping, "backoff_kind", context),
        initial_delay_seconds=_require_text_field(
            mapping, "initial_delay_seconds", context
        ),
        max_delay_seconds=_require_text_field(mapping, "max_delay_seconds", context),
        retryable_error_classes=tuple(
            _require_text_item(item, f"{context}.retryable_error_classes[{index}]")
            for index, item in enumerate(classes)
        ),
    )


def _runtime_snapshot_from_mapping(value: Any, context: str) -> RuntimeSnapshotV1:
    mapping = _require_object(value, context)
    _require_exact_keys(mapping, _RUNTIME_SNAPSHOT_KEYS, context)
    _require_literal(mapping, "schema_version", RUNTIME_SNAPSHOT_SCHEMA_VERSION)
    snapshot = RuntimeSnapshotV1(
        provider_name=_require_text_field(mapping, "provider_name", context),
        model=_require_text_field(mapping, "model", context),
        endpoint=_require_text_field(mapping, "endpoint", context),
        provider_config_digest=_require_text_field(
            mapping, "provider_config_digest", context
        ),
        provider_parameters_digest=_require_text_field(
            mapping, "provider_parameters_digest", context
        ),
        timeout_seconds=_require_text_field(mapping, "timeout_seconds", context),
        retry_policy=_retry_policy_from_mapping(
            mapping["retry_policy"], f"{context}.retry_policy"
        ),
        tool_contract_policy=_require_text_field(
            mapping, "tool_contract_policy", context
        ),
        native_tool_adapter_version=_require_text_field(
            mapping, "native_tool_adapter_version", context
        ),
        package_source_sha256=_require_text_field(
            mapping, "package_source_sha256", context
        ),
        python_version=_require_text_field(mapping, "python_version", context),
        artifact_version=_require_text_field(mapping, "artifact_version", context),
        prompt_digest=_require_text_field(mapping, "prompt_digest", context),
        experiment_config_digest=_require_text_field(
            mapping, "experiment_config_digest", context
        ),
        models_config_digest=_require_text_field(
            mapping, "models_config_digest", context
        ),
        environment_fingerprint=_require_text_field(
            mapping, "environment_fingerprint", context
        ),
        captured_at=_require_text_field(mapping, "captured_at", context),
    )
    claimed_identity = _require_digest(
        _require_text_field(mapping, "runtime_identity_digest", context),
        f"{context}.runtime_identity_digest",
    )
    if not hmac.compare_digest(
        claimed_identity, snapshot.runtime_identity_digest
    ):
        raise ConfirmatoryRegistrationError(
            f"{context}.runtime_identity_digest does not match the frozen identity fields"
        )
    claimed_self = _require_digest(
        _require_text_field(mapping, SELF_DIGEST_FIELD, context),
        f"{context}.{SELF_DIGEST_FIELD}",
    )
    if not hmac.compare_digest(claimed_self, snapshot.self_digest):
        raise ConfirmatoryRegistrationError(
            f"{context}.{SELF_DIGEST_FIELD} does not match the runtime snapshot"
        )
    return snapshot


def _runtime_from_mapping(
    mapping: dict[str, Any], context: str
) -> ProposedRuntimeConfigurationV1:
    _require_exact_keys(mapping, _RUNTIME_KEYS, context)
    snapshot = _runtime_snapshot_from_mapping(
        mapping["registration_expected_runtime_snapshot"],
        f"{context}.registration_expected_runtime_snapshot",
    )
    return ProposedRuntimeConfigurationV1(
        timeout_seconds=_require_text_field(mapping, "timeout_seconds", context),
        retry_policy=_retry_policy_from_mapping(
            mapping["retry_policy"], f"{context}.retry_policy"
        ),
        registration_expected_runtime_snapshot=snapshot,
    )


def _statistical_from_mapping(
    mapping: dict[str, Any], context: str
) -> ProposedStatisticalConfigurationV1:
    """Rebuild the statistical object, enforcing V9 (clarification §4.5, §7.2).

    Each of the ten stamped constants is compared against its frozen literal
    rather than trusted, so a tampered draft is refused instead of loading with
    a foreign alpha, endpoint order, or contrast orientation.
    """

    _require_exact_keys(mapping, _STATISTICAL_KEYS, context)
    for key, expected in _STATISTICAL_STRING_LITERALS:
        if mapping[key] != expected:
            raise ConfirmatoryRegistrationError(
                f"{context}.{key} must be {expected!r}, got {mapping[key]!r}"
            )
    sequence = _require_array_field(mapping, "secondary_endpoint_sequence", context)
    if tuple(sequence) != SECONDARY_ENDPOINT_SEQUENCE:
        raise ConfirmatoryRegistrationError(
            f"{context}.secondary_endpoint_sequence must be "
            f"{list(SECONDARY_ENDPOINT_SEQUENCE)!r} in that frozen gate order, got "
            f"{sequence!r}"
        )
    max_k = _require_integer_field(
        mapping, "randomization_exact_enumeration_max_k", context
    )
    if max_k != RANDOMIZATION_EXACT_ENUMERATION_MAX_K:
        raise ConfirmatoryRegistrationError(
            f"{context}.randomization_exact_enumeration_max_k must be "
            f"{RANDOMIZATION_EXACT_ENUMERATION_MAX_K!r}, got {max_k!r}"
        )
    raw_samples = mapping["randomization_mc_samples"]
    samples: int | None = None
    if raw_samples is not None:
        samples = _require_integer_item(
            raw_samples, f"{context}.randomization_mc_samples", minimum=1
        )
    return ProposedStatisticalConfigurationV1(randomization_mc_samples=samples)


# ---------------------------------------------------------------------------
# Explicit validation helpers
# ---------------------------------------------------------------------------


def _require_nonempty_text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ConfirmatoryRegistrationError(
            f"{context} must be a non-empty string, got {value!r}"
        )
    return value


def _require_integer(value: Any, context: str, *, minimum: int | None = None) -> int:
    # ``bool`` is a subclass of ``int``, and ``True`` would serialize as JSON
    # ``true`` rather than an integer, so it is refused here: §5.B.2 keeps
    # integer-valued schema fields ordinary JSON integers.
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfirmatoryRegistrationError(
            f"{context} must be a JSON integer, got {value!r}"
        )
    number: int = value
    if minimum is not None and number < minimum:
        raise ConfirmatoryRegistrationError(
            f"{context} must be >= {minimum}, got {number!r}"
        )
    return number


def _require_digest(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _DIGEST_PATTERN.fullmatch(value):
        raise ConfirmatoryRegistrationError(
            f"{context} must be a lowercase 64-character SHA-256 hex digest, got "
            f"{value!r}"
        )
    return value


def _require_canonical_decimal(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _CANONICAL_DECIMAL_PATTERN.fullmatch(value):
        raise ConfirmatoryRegistrationError(
            f"{context} must be a canonical base-10 decimal string, got {value!r}"
        )
    return value


def _require_design_id(design_id: Any) -> str:
    text = _require_nonempty_text(design_id, "design_id")
    windows_path = PureWindowsPath(text)
    windows_stem = text.rstrip(" .").split(".", 1)[0].upper()
    if (
        text in {".", ".."}
        or any(bad in text for bad in _DESIGN_ID_FORBIDDEN)
        or windows_path.drive
        or windows_path.root
        or windows_stem in _WINDOWS_RESERVED_NAMES
        or text.endswith((" ", "."))
    ):
        raise ConfirmatoryRegistrationError(
            f"design_id must be a single safe path segment, got {text!r}"
        )
    return text


def _require_aware_datetime(value: datetime, context: str) -> str:
    if not isinstance(value, datetime):
        raise ConfirmatoryRegistrationError(
            f"{context} must be a datetime, got {value!r}"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ConfirmatoryRegistrationError(f"{context} must be timezone-aware")
    return value.isoformat()


def _require_created_at_instant(value: datetime) -> str:
    """Render ``created_at`` in the one frozen form (clarification §4.3).

    The frozen form is ``YYYY-MM-DDTHH:MM:SSZ``: RFC 3339, UTC, mandatory ``Z``
    designator, whole-second precision.  A non-UTC offset or a sub-second
    component is refused rather than converted or truncated — ``created_at`` is
    a registered, digest-authenticated value, so silently rewriting what the
    caller passed would register something they did not propose.
    """

    _require_aware_datetime(value, "created_at")
    if value.utcoffset() != timedelta(0):
        raise ConfirmatoryRegistrationError(
            "created_at must be a UTC instant with a zero offset; it is not "
            f"converted on your behalf, got offset {value.utcoffset()!r}"
        )
    if value.microsecond:
        raise ConfirmatoryRegistrationError(
            "created_at must have whole-second precision with no fractional "
            f"seconds; it is not truncated on your behalf, got {value!r}"
        )
    return value.strftime(_CREATED_AT_FORMAT)


def _require_created_at_text(value: str) -> None:
    """Reject any persisted ``created_at`` outside the frozen form."""

    if not _CREATED_AT_PATTERN.fullmatch(value):
        raise ConfirmatoryRegistrationError(
            "created_at must be an RFC 3339 UTC instant of the form "
            f"YYYY-MM-DDTHH:MM:SSZ, got {value!r}"
        )
    try:
        datetime.strptime(value, _CREATED_AT_FORMAT)
    except ValueError as error:
        raise ConfirmatoryRegistrationError(
            f"created_at is not a real instant: {value!r}"
        ) from error


def _parse_timestamp(value: str, context: str = "created_at") -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise ConfirmatoryRegistrationError(
            f"{context} is not an ISO-8601 timestamp: {value!r}"
        ) from error


def _require_exact_keys(
    mapping: dict[str, Any], expected: frozenset[str], context: str
) -> None:
    present = set(mapping)
    missing = sorted(expected - present)
    unexpected = sorted(present - expected)
    if missing and unexpected:
        # Report both halves together: a renamed key is the common case, and
        # naming only the missing half hides which key replaced it.
        raise ConfirmatoryRegistrationError(
            f"{context} is missing keys: {missing} and carries unexpected keys: "
            f"{unexpected}"
        )
    if missing:
        raise ConfirmatoryRegistrationError(f"{context} is missing keys: {missing}")
    if unexpected:
        raise ConfirmatoryRegistrationError(
            f"{context} carries unexpected keys: {unexpected}"
        )


def _require_literal(mapping: dict[str, Any], key: str, expected: str) -> None:
    if mapping[key] != expected:
        raise ConfirmatoryRegistrationError(
            f"{key} must be {expected!r}, got {mapping[key]!r}"
        )


def _require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfirmatoryRegistrationError(
            f"{context} must be a JSON object, got {type(value).__name__}"
        )
    mapping: dict[str, Any] = value
    return mapping


def _require_object_field(
    mapping: dict[str, Any], key: str, context: str | None = None
) -> dict[str, Any]:
    return _require_object(mapping[key], _field_context(key, context))


def _require_array_field(
    mapping: dict[str, Any], key: str, context: str | None = None
) -> list[Any]:
    value = mapping[key]
    if not isinstance(value, list):
        raise ConfirmatoryRegistrationError(
            f"{_field_context(key, context)} must be a JSON array, got "
            f"{type(value).__name__}"
        )
    items: list[Any] = value
    return items


def _require_text_field(
    mapping: dict[str, Any], key: str, context: str | None = None
) -> str:
    return _require_nonempty_text(mapping[key], _field_context(key, context))


def _require_integer_field(
    mapping: dict[str, Any],
    key: str,
    context: str | None = None,
    *,
    minimum: int | None = None,
) -> int:
    return _require_integer(mapping[key], _field_context(key, context), minimum=minimum)


def _require_text_item(value: Any, context: str) -> str:
    return _require_nonempty_text(value, context)


def _require_integer_item(
    value: Any, context: str, *, minimum: int | None = None
) -> int:
    return _require_integer(value, context, minimum=minimum)


def _field_context(key: str, context: str | None) -> str:
    return key if context is None else f"{context}.{key}"
