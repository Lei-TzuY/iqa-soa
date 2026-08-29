"""Stage-A confirmatory registration draft, the canonical digest profile, Stage C.

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

This module also owns the third work unit, Stage C
``FINAL_REGISTRATION_FROZEN`` (§5.A, §16 step 3), as the persisted representation
is frozen by
``docs/post_phaseP_confirmatory_final_registration_schema_clarification.md``
(``STAGE_C_SCHEMA_FROZEN``): the sixteen-key ``RegistrationManifestV1`` schema,
the deterministic partition of the Stage-A matrix by the frozen Stage-B
dispositions, ``position_id``, ``K``, ``randomization_mode``, the five-key
``matrix_digest`` preimage, the thirty-nine fail-closed rules ``F1``-``F39``, and
immutable ``registration_manifest.json`` persistence.  Stage C draws **no**
randomization bit, generates **no** Monte Carlo seed or provenance, contacts
**no** provider, recaptures **no** runtime snapshot, executes nothing, analyses
nothing, and assesses no eligibility.

Every verification failure fails closed.  This module raises; it never repairs a
malformed artifact, never normalizes an invalid one into validity, and never
reserializes around a mismatch.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from pathlib import Path, PureWindowsPath
import re
from typing import TYPE_CHECKING, Any, Sequence

from iqa_soa.types import QAMode

if TYPE_CHECKING:  # pragma: no cover - typing only, and never at runtime
    # Work Unit 2 imports *this* module, so the Stage-B type is referenced
    # under ``TYPE_CHECKING`` and imported inside the Stage-C functions that
    # need it at runtime.  Stage C reuses Work Unit 2's public surface; it
    # never reimplements ``E1``-``E26``.
    from iqa_soa.experiment.confirmatory_eligibility import EligibilityManifestV1

__all__ = [
    "AGGREGATION_RULE",
    "ALPHA",
    "BACKOFF_KINDS",
    "BASELINE_LABELS",
    "BASELINE_LABEL_FULL",
    "BASELINE_LABEL_OFF",
    "CONFIRMATORY_PROFILE",
    "ConfirmatoryPositionV1",
    "ConfirmatoryRegistrationError",
    "ConfirmatoryStratumV1",
    "DISPOSITION_CONFIRMATORY_ELIGIBLE",
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
    "RANDOMIZATION_MODES",
    "RANDOMIZATION_MODE_EXACT_ENUMERATION",
    "RANDOMIZATION_MODE_MONTE_CARLO",
    "REGISTRATION_DRAFT_FILENAME",
    "REGISTRATION_DRAFT_SCHEMA_VERSION",
    "REGISTRATION_MANIFEST_FILENAME",
    "REGISTRATION_MANIFEST_FORBIDDEN_KEY_NAMES",
    "REGISTRATION_MANIFEST_SCHEMA_VERSION",
    "REGISTRATION_STATE_DRAFT",
    "REGISTRATION_STATE_FINAL_REGISTRATION_FROZEN",
    "RUNTIME_SNAPSHOT_SCHEMA_VERSION",
    "RegistrationDraft",
    "RegistrationManifest",
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
    "freeze_final_registration",
    "load_registration_draft",
    "load_registration_manifest",
    "parse_artifact",
    "registration_draft_path",
    "registration_manifest_path",
    "serialize_artifact",
    "verify_self_digest",
    "write_registration_draft",
    "write_registration_manifest",
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

#: The one nested key of ``proposed_runtime_configuration`` (eligibility
#: clarification §12.3, §12.4).  The configuration-level ``timeout_seconds`` and
#: ``retry_policy`` are retired as duplicates: both survive verbatim per stratum
#: inside each ``RuntimeSnapshotV1``, already bound into its
#: ``runtime_identity_digest`` preimage.  Their absence here is what makes the
#: old three-key nested shape fail closed rather than load silently.
_RUNTIME_KEYS: frozenset[str] = frozenset({"registration_expected_runtime_snapshots"})

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
    """One registration-expected ``RuntimeSnapshotV1`` per proposed stratum.

    ``proposed_strata`` carries no upper bound, and every stratum names its own
    provider, model, and endpoint — all of which live inside a snapshot's
    ``runtime_identity_digest`` preimage.  One snapshot for a whole draft
    therefore leaves every stratum but at most one without a well-defined
    expected identity, so this object binds a **collection**: exactly one
    complete snapshot per stratum (eligibility clarification §12.3).

    ``__post_init__`` enforces RC-1 (non-empty), RC-3 (sorted ascending by
    ``(provider_name, model)``), and RC-4 (unique on that key).  RC-2 — that
    every element is a complete snapshot whose two digests verify — is enforced
    by ``RuntimeSnapshotV1.__post_init__``, which is unchanged.  RC-5, the exact
    element-wise cover of ``proposed_strata``, needs both objects and lives in
    :func:`_validate_stratum_runtime_cover`.

    There is no configuration-level ``timeout_seconds`` or ``retry_policy``
    (§12.4).  Both remain mandatory and digest-authenticated inside **each**
    snapshot, where they may legitimately differ between heterogeneous provider
    runtimes; nothing here requires strata to share them.
    """

    registration_expected_runtime_snapshots: tuple[RuntimeSnapshotV1, ...]

    def __post_init__(self) -> None:
        context = (
            "proposed_runtime_configuration.registration_expected_runtime_snapshots"
        )
        snapshots = self.registration_expected_runtime_snapshots
        if not isinstance(snapshots, tuple):
            raise ConfirmatoryRegistrationError(f"{context} must be a tuple")
        for index, snapshot in enumerate(snapshots):
            if not isinstance(snapshot, RuntimeSnapshotV1):
                raise ConfirmatoryRegistrationError(
                    f"{context}[{index}] must be a RuntimeSnapshotV1"
                )
        # RC-1, RC-4, and RC-3 in one place: non-empty, unique on
        # ``(provider_name, model)``, and already sorted by it.  Nothing is
        # sorted or deduplicated on the caller's behalf.
        _require_sorted_unique(
            [(snapshot.provider_name, snapshot.model) for snapshot in snapshots],
            context,
        )

    def registration_expected_runtime_identity_digest(
        self, provider: str, model: str
    ) -> str:
        """The identity later capture points must reproduce, for one stratum.

        Lookup is by the exact ``(provider, model)`` pair, never by position and
        never by fallback: an unbound stratum raises rather than quietly
        yielding some other stratum's digest (§12.3).
        """

        for snapshot in self.registration_expected_runtime_snapshots:
            if snapshot.provider_name == provider and snapshot.model == model:
                return snapshot.runtime_identity_digest
        raise ConfirmatoryRegistrationError(
            "proposed_runtime_configuration binds no registration-expected "
            f"RuntimeSnapshotV1 for stratum {(provider, model)!r}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "registration_expected_runtime_snapshots": [
                snapshot.to_dict()
                for snapshot in self.registration_expected_runtime_snapshots
            ]
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
    _validate_stratum_runtime_cover(strata, proposed_runtime_configuration)
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


def _validate_stratum_runtime_cover(
    proposed_strata: tuple[ProposedStratumV1, ...],
    proposed_runtime_configuration: ProposedRuntimeConfigurationV1,
) -> None:
    """Enforce RC-5: the runtime collection exactly covers ``proposed_strata``.

    The cross-check needs both objects, so it is a separate helper rather than a
    new parameter on :func:`_validate_proposed_matrix`: on the load path the
    runtime object is parsed *after* that call, and reordering existing checks
    would widen the repair (eligibility clarification §18.1).

    RC-5 is the whole of the mapping between the two spellings of one concept —
    the stratum vocabulary ``(provider, model)`` and the snapshot vocabulary
    ``(provider_name, model)``.  Equal lengths and index-wise equality make a
    missing, foreign, duplicated, misordered, or extra snapshot all rejections,
    with no normalization and no repair.
    """

    snapshots = proposed_runtime_configuration.registration_expected_runtime_snapshots
    _require_exact_cover(
        [(snapshot.provider_name, snapshot.model) for snapshot in snapshots],
        [stratum.identity for stratum in proposed_strata],
        "proposed_runtime_configuration.registration_expected_runtime_snapshots",
        "(provider, model) of proposed_strata",
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
    _validate_stratum_runtime_cover(strata, runtime)
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
    """Parse the one-key nested shape (§12.3); the legacy three-key one fails.

    Every element goes through the **unchanged** ``_runtime_snapshot_from_mapping``,
    so RC-2 — twenty frozen fields, ``runtime_identity_digest`` and
    ``self_digest`` both verified — is enforced exactly as before, per snapshot.
    """

    _require_exact_keys(mapping, _RUNTIME_KEYS, context)
    key = "registration_expected_runtime_snapshots"
    return ProposedRuntimeConfigurationV1(
        registration_expected_runtime_snapshots=tuple(
            _runtime_snapshot_from_mapping(item, f"{context}.{key}[{index}]")
            for index, item in enumerate(_require_array_field(mapping, key, context))
        ),
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


# ===========================================================================
# Stage C — FINAL_REGISTRATION_FROZEN
#
# The persisted representation is fixed by the binding final-registration schema
# clarification (``docs/post_phaseP_confirmatory_final_registration_schema_
# clarification.md``), whose decision is ``STAGE_C_SCHEMA_FROZEN``.  Unqualified
# section references below are that document's.
#
# Stage C performs **no** assignment, draws **no** task bit, generates **no**
# Monte Carlo seed or provenance, contacts **no** provider, recaptures **no**
# runtime snapshot, executes nothing, and analyses nothing.  It turns an
# ``ELIGIBILITY_FROZEN`` chain into a ``FINAL_REGISTRATION_FROZEN`` one and stops.
# ===========================================================================


#: §5 — the Stage-C schema literal.  There is no alias and no alternative.
REGISTRATION_MANIFEST_SCHEMA_VERSION = "RegistrationManifestV1"

#: §4.1 — the Stage-C lifecycle state, carried under the same
#: ``registration_state`` field name both sibling artifacts already use.
REGISTRATION_STATE_FINAL_REGISTRATION_FROZEN = "FINAL_REGISTRATION_FROZEN"

#: §17 — the Stage-C artifact file name: one per ``design_id``, written once.
REGISTRATION_MANIFEST_FILENAME = "registration_manifest.json"

#: §15 — the two randomization modes, derived from ``K`` and never caller-selected.
RANDOMIZATION_MODE_EXACT_ENUMERATION = "EXACT_ENUMERATION"
RANDOMIZATION_MODE_MONTE_CARLO = "MONTE_CARLO"
RANDOMIZATION_MODES: tuple[str, ...] = (
    RANDOMIZATION_MODE_EXACT_ENUMERATION,
    RANDOMIZATION_MODE_MONTE_CARLO,
)

#: §13.1 — the single Stage-B disposition token that sends a proposed stratum to
#: the confirmatory side of the partition.  It is named here because the
#: partition reads it; the token's *vocabulary* stays Work Unit 2's, and §16 F36
#: cross-checks this literal against that vocabulary rather than assuming it.
DISPOSITION_CONFIRMATORY_ELIGIBLE = "CONFIRMATORY_ELIGIBLE"

#: §4.1 — exactly sixteen top-level keys, no more, no fewer, no optional key.
_MANIFEST_KEYS: frozenset[str] = frozenset(
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
        SELF_DIGEST_FIELD,
    }
)

#: §8.1 — a confirmatory stratum carries the runtime identity its positions must
#: reproduce; a descriptive-only stratum is never executed and carries none.  The
#: two-key shape is the persisted ``ProposedStratumV1`` shape unchanged.
_CONFIRMATORY_STRATUM_KEYS: frozenset[str] = frozenset(
    {"model", "provider", "runtime_identity_digest"}
)

#: §7.2 — the eight-key Stage-C position record: the Stage-A seven plus the one
#: derived field ``position_id``.  Both position arrays use it identically (§7.3).
_CONFIRMATORY_POSITION_KEYS: frozenset[str] = frozenset(
    _POSITION_KEYS | {"position_id"}
)

#: §8.2 — the frozen position ordering/uniqueness key, identical to Stage A's.
_POSITION_PLACEMENT_KEYS: tuple[str, ...] = (
    "task_id",
    "provider",
    "model",
    "repetition",
    "slot",
)

#: §9.2 — the ``matrix_digest`` preimage: exactly five named components, no more,
#: no fewer, each taken as the identical value persisted under the same key.
_MATRIX_PREIMAGE_KEYS: tuple[str, ...] = (
    "K",
    "confirmatory_positions",
    "confirmatory_strata",
    "randomization_mode",
    "registered_statistical_configuration",
)

#: §16.4 — forbidden **key names**, at any depth.  This is a key-name
#: prohibition, never a raw-substring search, so a legitimate string *value*
#: containing one of these words can never trip it.  ``statistic_spec_id`` is
#: position-sensitive and lives in :data:`_TOP_LEVEL_ONLY_FORBIDDEN_KEY_NAMES`
#: instead: it is required inside ``registered_statistical_configuration`` and
#: forbidden at the top level (§11.4).  ``registered_k`` is forbidden everywhere,
#: the registered value being carried by ``K`` (§6.4).
REGISTRATION_MANIFEST_FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset(
    {
        # same-object digest aliases (§4.5)
        "final_registration_digest",
        "registration_manifest_digest",
        # downstream artifacts that do not exist yet (§4.6)
        "assignment_digest",
        "randomization_mc_provenance_digest",
        # assignment material — no assignment bit exists at Stage C
        "b_k",
        "bits",
        "task_assignment_bit",
        "task_order",
        # Monte Carlo seed / provenance material (implementation design §5.L)
        "entropy_bytes",
        "exact_support_size",
        "generated_at",
        "numpy_version",
        "rng_bit_generator",
        "rng_library",
        "seed_encoding",
        "seed_hex",
        "source_api",
        "source_kind",
        # realized execution values (implementation design §5.C)
        "error",
        "failure_class",
        "observation_status",
        "qa_mode",
        "runtime_snapshot_digest",
        # capture metadata (implementation design §5.I.2)
        "captured_at",
        # Stage-B assessment material (§4.6)
        "assessed_at",
        "disposition",
        "eligibility_records",
        "eligibility_state",
        "evidence_refs",
        "infrastructure_symmetry_audit",
        "isolation_evidence",
        "predicates",
        # Stage-A proposal names (§4.6)
        "proposed_positions",
        "proposed_provider_seeds",
        "proposed_repetitions",
        "proposed_runtime_configuration",
        "proposed_statistical_configuration",
        "proposed_strata",
        "proposed_tasks",
        # no runtime-snapshot duplication (§10.3)
        "registration_expected_runtime_snapshot",
        "registration_expected_runtime_snapshots",
        # redundant derivations that earn no field under C7 (§6)
        "confirmatory_tasks",
        "descriptive_tasks",
        "provider_seeds",
        "registered_provider_seeds",
        "registered_repetitions",
        "registered_tasks",
        "repetition_counts",
        "repetitions",
        "seeds",
        "task_membership",
        # the registered value is ``K`` (§6.4)
        "registered_k",
    }
)

#: §16.4 — forbidden at the top level only.  ``statistic_spec_id`` appears exactly
#: once in this artifact, inside ``registered_statistical_configuration`` (§11.4).
_TOP_LEVEL_ONLY_FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset({"statistic_spec_id"})


# ---------------------------------------------------------------------------
# Stage-C records (§7, §8.1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConfirmatoryStratumV1:
    """One confirmatory stratum: three keys, no more, no fewer (§8.1).

    ``runtime_identity_digest`` is **copied verbatim** from the bound draft's
    registration-expected snapshot for this exact ``(provider, model)`` pair.  It
    is never recomputed, never recaptured, and no ``RuntimeSnapshotV1`` is
    constructed, hashed, or read from a live provider at Stage C (§10.3).

    Descriptive-only strata deliberately keep the unchanged two-key
    :class:`ProposedStratumV1` shape instead: the extra key exists exactly where a
    frozen consumer reads it, and nowhere else (§10.2).  No ``disposition`` is
    copied into Stage C — the confirmatory/descriptive split *is* the disposition,
    coarsened to the only distinction Stage C consumes, and the exact per-stratum
    reason token stays authenticated in ``eligibility_manifest.json`` (§8.1).
    """

    provider: str
    model: str
    runtime_identity_digest: str

    def __post_init__(self) -> None:
        _require_nonempty_text(self.provider, "confirmatory_strata[].provider")
        _require_nonempty_text(self.model, "confirmatory_strata[].model")
        _require_digest(
            self.runtime_identity_digest,
            "confirmatory_strata[].runtime_identity_digest",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "provider": self.provider,
            "runtime_identity_digest": self.runtime_identity_digest,
        }

    @property
    def identity(self) -> tuple[str, str]:
        """The ``(provider, model)`` ordering, uniqueness, and join key (§8.1)."""

        return (self.provider, self.model)


@dataclass(frozen=True, slots=True)
class ConfirmatoryPositionV1:
    """One registered position: exactly eight keys, no more, no fewer (§7.2).

    The record is the seven-field Stage-A :class:`ProposedPositionV1` copied
    verbatim plus exactly one derived field, ``position_id``, which first exists
    at Stage C.  ``position_id`` is SHA-256 over the canonical JSON of exactly the
    **six** identity fields (§7.1); ``baseline_label`` is deliberately outside that
    preimage, because a position's identity must not depend on which label it
    receives or the identity would leak assignment information (§7.1).

    **No assignment-dependent field exists on this record, at Stage C or ever** —
    no ``treatment``, ``qa_mode``, ``task_assignment_bit``, ``b_k``, or realized
    label.  ``baseline_label`` is not assignment-dependent: it is the deterministic
    counterbalancing output already recorded at Stage A, strictly before any bit is
    drawn, and it is copied here, never recomputed (§14.3).

    Both ``confirmatory_positions`` and ``descriptive_positions`` use this exact
    shape: membership is carried by which array an element is in, and by nothing
    else (§7.3).
    """

    position_id: str
    task_id: str
    provider: str
    model: str
    repetition: int
    provider_seed: int
    slot: int
    baseline_label: str

    def __post_init__(self) -> None:
        _require_digest(self.position_id, "positions[].position_id")
        _require_nonempty_text(self.task_id, "positions[].task_id")
        _require_nonempty_text(self.provider, "positions[].provider")
        _require_nonempty_text(self.model, "positions[].model")
        _require_integer(self.repetition, "positions[].repetition", minimum=0)
        _require_integer(self.provider_seed, "positions[].provider_seed")
        _require_integer(self.slot, "positions[].slot")
        if self.slot not in _SLOTS:
            raise ConfirmatoryRegistrationError(
                f"positions[].slot must be one of {list(_SLOTS)}, got {self.slot!r}"
            )
        if self.baseline_label not in BASELINE_LABELS:
            raise ConfirmatoryRegistrationError(
                f"positions[].baseline_label must be one of {list(BASELINE_LABELS)}, "
                f"got {self.baseline_label!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_label": self.baseline_label,
            "model": self.model,
            "position_id": self.position_id,
            "provider": self.provider,
            "provider_seed": self.provider_seed,
            "repetition": self.repetition,
            "slot": self.slot,
            "task_id": self.task_id,
        }

    def identity_payload(self) -> dict[str, Any]:
        """Exactly the six §7.1 identity fields — the ``position_id`` preimage."""

        return {
            "model": self.model,
            "provider": self.provider,
            "provider_seed": self.provider_seed,
            "repetition": self.repetition,
            "slot": self.slot,
            "task_id": self.task_id,
        }

    @property
    def placement(self) -> tuple[str, str, str, int, int]:
        """The ``(task_id, provider, model, repetition, slot)`` sort key (§8.2)."""

        return (
            self.task_id,
            self.provider,
            self.model,
            self.repetition,
            self.slot,
        )


@dataclass(frozen=True, slots=True)
class RegistrationManifest:
    """The Stage-C ``FINAL_REGISTRATION_FROZEN`` artifact: exactly sixteen keys (§4.1).

    Construct through :func:`freeze_final_registration`, which derives every value
    from the two bound immutable upstream artifacts and seals the result.  **No
    field of this record is caller-selectable** (§12): each is a Stage-A copy, a
    deterministic derivation, a global frozen literal, or — for ``created_at``
    alone — the freeze instant captured internally by the sealing operation
    (§4.4.1).

    The record stores exactly one digest of itself, ``self_digest``, and never a
    ``final_registration_digest`` alias: that name is what *downstream* artifacts
    call this object's ``self_digest`` (§4.5).  ``matrix_digest`` is ordinary
    content computed first, so ``self_digest`` covers it and never the reverse
    (§9.7).
    """

    schema_version: str
    registration_state: str
    confirmatory_profile: str
    design_id: str
    created_at: str
    registration_draft_digest: str
    eligibility_manifest_digest: str
    confirmatory_strata: tuple[ConfirmatoryStratumV1, ...]
    descriptive_only_strata: tuple[ProposedStratumV1, ...]
    confirmatory_positions: tuple[ConfirmatoryPositionV1, ...]
    descriptive_positions: tuple[ConfirmatoryPositionV1, ...]
    K: int
    randomization_mode: str
    registered_statistical_configuration: ProposedStatisticalConfigurationV1
    matrix_digest: str
    self_digest: str
    _freeze_provenance: tuple[str, str] | None = field(
        init=False, repr=False, compare=False, default=None
    )

    def canonical_payload(self) -> dict[str, Any]:
        """The ``self_digest`` input: the whole artifact except its own digest.

        Every array preserves registered order; canonicalization never reorders or
        deduplicates one.  The §8.1/§8.2 sorting and uniqueness rules are
        schema-level preconditions applied before canonicalization, never
        canonicalization-time transformations (§17.1).
        """

        return {
            "K": self.K,
            "confirmatory_positions": [
                position.to_dict() for position in self.confirmatory_positions
            ],
            "confirmatory_profile": self.confirmatory_profile,
            "confirmatory_strata": [
                stratum.to_dict() for stratum in self.confirmatory_strata
            ],
            "created_at": self.created_at,
            "descriptive_only_strata": [
                stratum.to_dict() for stratum in self.descriptive_only_strata
            ],
            "descriptive_positions": [
                position.to_dict() for position in self.descriptive_positions
            ],
            "design_id": self.design_id,
            "eligibility_manifest_digest": self.eligibility_manifest_digest,
            "matrix_digest": self.matrix_digest,
            "randomization_mode": self.randomization_mode,
            "registered_statistical_configuration": (
                self.registered_statistical_configuration.to_dict()
            ),
            "registration_draft_digest": self.registration_draft_digest,
            "registration_state": self.registration_state,
            "schema_version": self.schema_version,
        }

    def to_artifact(self) -> dict[str, Any]:
        """The full persisted object: the canonical payload plus ``self_digest``."""

        artifact = self.canonical_payload()
        artifact[SELF_DIGEST_FIELD] = self.self_digest
        return artifact

    def matrix_preimage(self) -> dict[str, Any]:
        """The §9.2 five-key ``matrix_digest`` preimage, from this artifact's values.

        Nothing is projected, stripped, re-keyed, re-ordered, or recomputed on the
        way in: each value is the identical value persisted under the same key.
        """

        return _matrix_preimage_from_values(self.canonical_payload())


# ---------------------------------------------------------------------------
# Stage-C deterministic derivations (§9, §13, §14, §15)
#
# Every function below is pure and total.  None consults a clock, an
# environment, a provider, a configuration file, or any entropy source; none
# draws a bit, derives a seed, or resolves a treatment label.
# ---------------------------------------------------------------------------


def _stratum_key(mapping: dict[str, Any]) -> tuple[str, str]:
    """The ``(provider, model)`` key of a persisted stratum record (§8.1)."""

    return (mapping["provider"], mapping["model"])


def _position_placement(mapping: dict[str, Any]) -> tuple[Any, ...]:
    """The ``(task_id, provider, model, repetition, slot)`` key of a record (§8.2)."""

    return tuple(mapping[key] for key in _POSITION_PLACEMENT_KEYS)


def _position_identity_payload(mapping: dict[str, Any]) -> dict[str, Any]:
    """Exactly the six §7.1 identity fields of a persisted position record."""

    return {key: mapping[key] for key in _POSITION_IDENTITY_KEYS}


def _derive_position_id(identity_payload: dict[str, Any]) -> str:
    """``position_id`` — ordinary SHA-256 over the canonical six-key payload (§7.1).

    The canonicalization is Work Unit 1's single frozen algorithm, reused by
    reference; no second serializer, option set, or hash exists.  The derivation
    consults **no randomness** and no input other than the six identity fields.
    """

    return hashlib.sha256(canonical_json_bytes(identity_payload)).hexdigest()


def _final_position_record(position: ProposedPositionV1) -> ConfirmatoryPositionV1:
    """§14.1 — the total, pure, deterministic Stage-A to Stage-C transformation.

    All seven Stage-A fields are copied verbatim, with no coercion, re-typing,
    normalization, or case change.  ``position_id`` is the one derived field.
    ``resolve_label``, ``complement``, and ``qa_mode`` do not appear: no treatment
    transformation happens here, and ``baseline_label`` is copied, never mapped.
    """

    return ConfirmatoryPositionV1(
        position_id=_derive_position_id(position.identity_payload()),
        task_id=position.task_id,
        provider=position.provider,
        model=position.model,
        repetition=position.repetition,
        provider_seed=position.provider_seed,
        slot=position.slot,
        baseline_label=position.baseline_label,
    )


def _derive_registered_k(positions: Sequence[Any]) -> int:
    """§15 — ``K`` is the number of **distinct ``task_id`` values**, not positions.

    Never a position count, never a stratum count, never a repetition count, and
    never ``K_plus``, which is an analysis-time reporting derivation that can
    never affect matrix membership or ``K``.
    """

    return len({_task_id_of(position) for position in positions})


def _task_id_of(position: Any) -> str:
    task_id = (
        position["task_id"]
        if isinstance(position, dict)
        else position.task_id
    )
    text: str = task_id
    return text


def _derive_randomization_mode(registered_k: int) -> str:
    """§15 — the mode as a deterministic function of ``K``, with no caller choice.

    ``K <= 16`` enumerates exactly; ``K > 16`` uses Monte Carlo.  No randomness is
    drawn, no seed is generated, and no provenance artifact is produced here.
    """

    if registered_k <= RANDOMIZATION_EXACT_ENUMERATION_MAX_K:
        return RANDOMIZATION_MODE_EXACT_ENUMERATION
    return RANDOMIZATION_MODE_MONTE_CARLO


def _require_mode_sample_gate(mode: str, randomization_mc_samples: Any) -> None:
    """§15 — the bidirectional mode/``M`` gate, a hard refusal in both directions.

    Stage C never selects ``M``: the carried-forward Stage-A value is neither
    discarded, ignored, reinterpreted, defaulted, nor repaired.  An inconsistent
    pair abandons the whole registration; the remedy is a **new** ``design_id``.
    """

    if mode == RANDOMIZATION_MODE_EXACT_ENUMERATION:
        if randomization_mc_samples is not None:
            raise ConfirmatoryRegistrationError(
                "randomization_mode EXACT_ENUMERATION requires "
                "registered_statistical_configuration.randomization_mc_samples to be "
                f"null, got {randomization_mc_samples!r}; the final registration is "
                "refused rather than reinterpreting the registered value"
            )
        return
    if randomization_mc_samples is None:
        raise ConfirmatoryRegistrationError(
            "randomization_mode MONTE_CARLO requires "
            "registered_statistical_configuration.randomization_mc_samples to be a "
            "positive JSON integer, got null; final registration refuses to freeze "
            "and Stage C does not select M"
        )


def _matrix_preimage_from_values(values: dict[str, Any]) -> dict[str, Any]:
    """§9.2 — the exact five-key preimage object, taken from the artifact's values."""

    return {key: values[key] for key in _MATRIX_PREIMAGE_KEYS}


def _matrix_digest_from_values(values: dict[str, Any]) -> str:
    """§9.7 — SHA-256, lowercase hex, over the canonical five-key preimage.

    The algorithm is Work Unit 1's by reference; no ``self_digest``-removal step
    applies, because the preimage object has no ``self_digest`` field to remove.
    """

    return hashlib.sha256(
        canonical_json_bytes(_matrix_preimage_from_values(values))
    ).hexdigest()


def _capture_created_at() -> str:
    """§4.4.1 T1-T3 — the freeze instant, captured internally, exactly once.

    There is **no** ``created_at`` parameter, no clock parameter, no "as-of"
    parameter, and no override of any name anywhere on the Stage-C surface: a
    caller cannot backdate what it cannot reach (T2).  Sub-second precision is
    truncated by this capture, at the point of capture, as part of rendering the
    instant the operation captured (T3).
    """

    return datetime.now(tz=timezone.utc).strftime(_CREATED_AT_FORMAT)


def _require_sorted_unique_allowing_empty(values: Sequence[Any], context: str) -> None:
    """§8.3 — Stage-C arrays may be empty; otherwise sorted and unique as frozen.

    Nothing is re-sorted, deduplicated, or repaired on the caller's behalf.
    """

    items = list(values)
    if not items:
        return
    _require_sorted_unique(items, context)


def _merge_sorted_disjoint(
    left: Sequence[Any],
    right: Sequence[Any],
    key: Any,
    context: str,
) -> list[Any]:
    """§13.3 — a two-pointer merge of two arrays each sorted and unique under ``key``.

    The merge is well-defined and total only if the two sides are disjoint, so a
    shared key is a hard failure here rather than a silently masked duplicate.
    No set arithmetic is used, exactly so a duplicate cannot be absorbed.
    """

    merged: list[Any] = []
    left_index = 0
    right_index = 0
    while left_index < len(left) and right_index < len(right):
        left_key = key(left[left_index])
        right_key = key(right[right_index])
        if left_key == right_key:
            raise ConfirmatoryRegistrationError(
                f"{context}: {left_key!r} appears on both sides of the partition"
            )
        if left_key < right_key:
            merged.append(left[left_index])
            left_index += 1
        else:
            merged.append(right[right_index])
            right_index += 1
    merged.extend(left[left_index:])
    merged.extend(right[right_index:])
    return merged


# ---------------------------------------------------------------------------
# §16.1 Tier 1 — F1 through F25, in numbered order, over the RAW artifact
#
# Each rule is its own function so the order is mechanically obvious and so no
# later-numbered rule can execute before an earlier one has completed.  Nothing
# in this section constructs a Stage-C dataclass: a ``__post_init__`` must not be
# able to decide which rule a malformed artifact fails.  Nothing here normalizes,
# repairs, sorts, deduplicates, default-fills, or partially accepts.
# ---------------------------------------------------------------------------


def _validate_f1(artifact: dict[str, Any]) -> None:
    """F1 — exactly the sixteen top-level keys of §4.1, no missing, no extra."""

    _require_exact_keys(artifact, _MANIFEST_KEYS, REGISTRATION_MANIFEST_FILENAME)


def _validate_f2(artifact: dict[str, Any]) -> None:
    """F2 — ``schema_version`` is exactly ``"RegistrationManifestV1"`` (§5)."""

    _require_literal(artifact, "schema_version", REGISTRATION_MANIFEST_SCHEMA_VERSION)


def _validate_f3(artifact: dict[str, Any]) -> None:
    """F3 — ``registration_state`` is exactly ``"FINAL_REGISTRATION_FROZEN"``."""

    _require_literal(
        artifact, "registration_state", REGISTRATION_STATE_FINAL_REGISTRATION_FROZEN
    )


def _validate_f4(artifact: dict[str, Any]) -> None:
    """F4 — ``confirmatory_profile`` is exactly the frozen design family (§4.1)."""

    _require_literal(artifact, "confirmatory_profile", CONFIRMATORY_PROFILE)


def _validate_f5(artifact: dict[str, Any]) -> None:
    """F5 — ``design_id`` is a non-empty string and a single safe path segment."""

    _require_design_id(artifact["design_id"])


def _validate_f6(artifact: dict[str, Any]) -> None:
    """F6 — the **persisted** ``created_at`` grammar, and nothing more (§4.4.1).

    This is a syntax/type validation of the persisted value.  It does not, and
    cannot, establish that the persisted instant is the true wall-clock moment of
    the freeze: that guarantee is structural and lives at construction/write time
    (T1-T4, F38).  No rule here compares ``created_at`` against any other
    artifact's timestamp (T7).
    """

    _require_created_at_text(_require_text_field(artifact, "created_at"))


def _validate_f7(artifact: dict[str, Any]) -> None:
    """F7 — ``registration_draft_digest`` grammar: lowercase 64-character hex."""

    _require_digest(artifact["registration_draft_digest"], "registration_draft_digest")


def _validate_f8(artifact: dict[str, Any]) -> None:
    """F8 — ``eligibility_manifest_digest`` grammar: lowercase 64-character hex."""

    _require_digest(
        artifact["eligibility_manifest_digest"], "eligibility_manifest_digest"
    )


def _validate_f9(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    """F9 — ``confirmatory_strata`` schema, order, and uniqueness (§8.1)."""

    context = "confirmatory_strata"
    records: list[dict[str, Any]] = []
    for index, item in enumerate(_require_array_field(artifact, context)):
        item_context = f"{context}[{index}]"
        mapping = _require_object(item, item_context)
        _require_exact_keys(mapping, _CONFIRMATORY_STRATUM_KEYS, item_context)
        _require_text_field(mapping, "provider", item_context)
        _require_text_field(mapping, "model", item_context)
        _require_digest(
            mapping["runtime_identity_digest"],
            f"{item_context}.runtime_identity_digest",
        )
        records.append(mapping)
    _require_sorted_unique_allowing_empty(
        [_stratum_key(record) for record in records], context
    )
    return records


def _validate_f10(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    """F10 — ``descriptive_only_strata`` schema, order, and uniqueness (§8.1).

    Exactly two keys: a descriptive-only stratum is never executed under this
    profile and carries **no** ``runtime_identity_digest`` (§10.2).
    """

    context = "descriptive_only_strata"
    records: list[dict[str, Any]] = []
    for index, item in enumerate(_require_array_field(artifact, context)):
        item_context = f"{context}[{index}]"
        mapping = _require_object(item, item_context)
        _require_exact_keys(mapping, _STRATUM_KEYS, item_context)
        _require_text_field(mapping, "provider", item_context)
        _require_text_field(mapping, "model", item_context)
        records.append(mapping)
    _require_sorted_unique_allowing_empty(
        [_stratum_key(record) for record in records], context
    )
    return records


def _validate_f11(
    confirmatory_strata: list[dict[str, Any]],
    descriptive_only_strata: list[dict[str, Any]],
) -> None:
    """F11 — the two stratum arrays are disjoint, and their union is non-empty."""

    shared = sorted(
        {_stratum_key(record) for record in confirmatory_strata}
        & {_stratum_key(record) for record in descriptive_only_strata}
    )
    if shared:
        raise ConfirmatoryRegistrationError(
            "confirmatory_strata and descriptive_only_strata must be disjoint on "
            f"(provider, model); both carry {shared!r}"
        )
    if not confirmatory_strata and not descriptive_only_strata:
        raise ConfirmatoryRegistrationError(
            "confirmatory_strata and descriptive_only_strata must not both be "
            "empty: a valid Stage-A draft has a non-empty proposed_strata and the "
            "Stage-C partition is total"
        )


def _validate_position_array(
    artifact: dict[str, Any], key: str
) -> list[dict[str, Any]]:
    """The shared eight-key position element schema of F12 and F13 (§7.2, §7.3)."""

    records: list[dict[str, Any]] = []
    for index, item in enumerate(_require_array_field(artifact, key)):
        context = f"{key}[{index}]"
        mapping = _require_object(item, context)
        _require_exact_keys(mapping, _CONFIRMATORY_POSITION_KEYS, context)
        _require_digest(mapping["position_id"], f"{context}.position_id")
        _require_text_field(mapping, "task_id", context)
        _require_text_field(mapping, "provider", context)
        _require_text_field(mapping, "model", context)
        _require_integer_field(mapping, "repetition", context, minimum=0)
        _require_integer_field(mapping, "provider_seed", context)
        slot = _require_integer_field(mapping, "slot", context)
        if slot not in _SLOTS:
            raise ConfirmatoryRegistrationError(
                f"{context}.slot must be one of {list(_SLOTS)}, got {slot!r}"
            )
        if mapping["baseline_label"] not in BASELINE_LABELS:
            raise ConfirmatoryRegistrationError(
                f"{context}.baseline_label must be one of {list(BASELINE_LABELS)}, "
                f"got {mapping['baseline_label']!r}"
            )
        records.append(mapping)
    return records


def _validate_f12(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    """F12 — ``confirmatory_positions`` element schema and frozen types (§7.2)."""

    return _validate_position_array(artifact, "confirmatory_positions")


def _validate_f13(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    """F13 — ``descriptive_positions`` satisfies the identical element schema (§7.3)."""

    return _validate_position_array(artifact, "descriptive_positions")


def _validate_f14(
    confirmatory_positions: list[dict[str, Any]],
    descriptive_positions: list[dict[str, Any]],
) -> None:
    """F14 — each position array is sorted and unique on the frozen key (§8.2)."""

    for key, records in (
        ("confirmatory_positions", confirmatory_positions),
        ("descriptive_positions", descriptive_positions),
    ):
        _require_sorted_unique_allowing_empty(
            [_position_placement(record) for record in records], key
        )


def _validate_f15(
    confirmatory_positions: list[dict[str, Any]],
    descriptive_positions: list[dict[str, Any]],
) -> None:
    """F15 — ``position_id`` and placement uniqueness across the **union** (§8.2)."""

    union = list(confirmatory_positions) + list(descriptive_positions)
    identifiers = [record["position_id"] for record in union]
    if len(set(identifiers)) != len(identifiers):
        duplicates = sorted(
            {value for value in identifiers if identifiers.count(value) > 1}
        )
        raise ConfirmatoryRegistrationError(
            "position_id must be unique across the union of confirmatory_positions "
            f"and descriptive_positions; duplicated {duplicates!r}"
        )
    shared = sorted(
        {_position_placement(record) for record in confirmatory_positions}
        & {_position_placement(record) for record in descriptive_positions}
    )
    if shared:
        raise ConfirmatoryRegistrationError(
            "confirmatory_positions and descriptive_positions must be disjoint on "
            f"(task_id, provider, model, repetition, slot); both carry {shared!r}"
        )


def _validate_f16(
    confirmatory_positions: list[dict[str, Any]],
    descriptive_positions: list[dict[str, Any]],
) -> None:
    """F16 — every record's six identity fields reproduce its claimed ``position_id``.

    A record cannot merely *claim* an identity: it is recomputed from the record's
    own fields, in both arrays, and a mismatch is refused (§14.2).
    """

    for key, records in (
        ("confirmatory_positions", confirmatory_positions),
        ("descriptive_positions", descriptive_positions),
    ):
        for index, record in enumerate(records):
            recomputed = _derive_position_id(_position_identity_payload(record))
            if not hmac.compare_digest(recomputed, record["position_id"]):
                raise ConfirmatoryRegistrationError(
                    f"{key}[{index}].position_id mismatch: claimed "
                    f"{record['position_id']}, recomputed {recomputed}"
                )


def _validate_f17(
    confirmatory_positions: list[dict[str, Any]],
    descriptive_positions: list[dict[str, Any]],
    confirmatory_strata: list[dict[str, Any]],
    descriptive_only_strata: list[dict[str, Any]],
) -> None:
    """F17 — every position sits on its own ``(provider, model)`` stratum's side."""

    for key, records, strata, side in (
        (
            "confirmatory_positions",
            confirmatory_positions,
            confirmatory_strata,
            "confirmatory_strata",
        ),
        (
            "descriptive_positions",
            descriptive_positions,
            descriptive_only_strata,
            "descriptive_only_strata",
        ),
    ):
        keys = {_stratum_key(record) for record in strata}
        for index, record in enumerate(records):
            if _stratum_key(record) not in keys:
                raise ConfirmatoryRegistrationError(
                    f"{key}[{index}] belongs to stratum "
                    f"{_stratum_key(record)!r}, which is not in {side}"
                )


def _validate_f18(
    confirmatory_strata: list[dict[str, Any]],
    descriptive_only_strata: list[dict[str, Any]],
    confirmatory_positions: list[dict[str, Any]],
    descriptive_positions: list[dict[str, Any]],
) -> None:
    """F18 — emptiness is coupled in both directions (§8.3 item 3)."""

    if bool(confirmatory_positions) != bool(confirmatory_strata):
        raise ConfirmatoryRegistrationError(
            "confirmatory_positions is empty if and only if confirmatory_strata is "
            f"empty; got {len(confirmatory_positions)} positions and "
            f"{len(confirmatory_strata)} strata"
        )
    if bool(descriptive_positions) != bool(descriptive_only_strata):
        raise ConfirmatoryRegistrationError(
            "descriptive_positions is empty if and only if descriptive_only_strata "
            f"is empty; got {len(descriptive_positions)} positions and "
            f"{len(descriptive_only_strata)} strata"
        )


def _validate_f19(
    artifact: dict[str, Any], confirmatory_positions: list[dict[str, Any]]
) -> None:
    """F19 — ``K`` is recorded **and** recomputed; a difference is refused (§6.4).

    ``K = 0`` is legal and no minimum-``K`` rule exists (§8.3 item 4).
    """

    registered_k = _require_integer_field(artifact, "K", minimum=0)
    recomputed = _derive_registered_k(confirmatory_positions)
    if registered_k != recomputed:
        raise ConfirmatoryRegistrationError(
            f"K is recorded as {registered_k!r} but confirmatory_positions span "
            f"{recomputed!r} distinct task_id values"
        )


def _validate_f20(artifact: dict[str, Any]) -> None:
    """F20 — ``randomization_mode`` is recorded **and** recomputed from ``K`` (§15)."""

    mode = artifact["randomization_mode"]
    if mode not in RANDOMIZATION_MODES:
        raise ConfirmatoryRegistrationError(
            f"randomization_mode must be one of {list(RANDOMIZATION_MODES)}, got "
            f"{mode!r}"
        )
    derived = _derive_randomization_mode(artifact["K"])
    if mode != derived:
        raise ConfirmatoryRegistrationError(
            f"randomization_mode is recorded as {mode!r} but K={artifact['K']!r} "
            f"derives {derived!r}; it is never caller-selected"
        )


def _validate_f21(artifact: dict[str, Any]) -> None:
    """F21 — the eleven-key statistical object and its ten stamped literals (§11.2).

    The check is the committed Stage-A one, reused: no second statistical schema
    is defined here and no ``RegisteredStatisticalConfigurationV1`` is minted
    (§11.3).
    """

    _statistical_from_mapping(
        _require_object_field(artifact, "registered_statistical_configuration"),
        "registered_statistical_configuration",
    )


def _validate_f22(artifact: dict[str, Any]) -> None:
    """F22 — the bidirectional mode/``M`` gate of §15 holds."""

    _require_mode_sample_gate(
        artifact["randomization_mode"],
        artifact["registered_statistical_configuration"]["randomization_mc_samples"],
    )


def _validate_f23(artifact: dict[str, Any]) -> None:
    """F23 — ``matrix_digest`` equals the digest of the rebuilt five-key preimage.

    The preimage is rebuilt from this manifest's own persisted values (§9.2) and
    hashed with Work Unit 1's frozen algorithm.  This is separate from, and
    additional to, ``self_digest`` verification at F24 (§9.7).
    """

    claimed = artifact["matrix_digest"]
    _require_digest(claimed, "matrix_digest")
    recomputed = _matrix_digest_from_values(artifact)
    if not hmac.compare_digest(recomputed, claimed):
        raise ConfirmatoryRegistrationError(
            f"matrix_digest mismatch: claimed {claimed}, recomputed {recomputed}"
        )


def _validate_f24(artifact: dict[str, Any]) -> None:
    """F24 — ``self_digest`` verifies under §5.B.2's unchanged procedure.

    ``matrix_digest`` is **not** removed before hashing: only ``self_digest`` is,
    so ``self_digest`` covers ``matrix_digest`` and ``created_at`` (§17.1, T5).
    """

    verify_self_digest(artifact)


def _require_no_forbidden_keys(value: Any, path: str) -> None:
    """Walk object **keys** only — never string values — refusing forbidden names."""

    if isinstance(value, dict):
        for key, item in value.items():
            if key in REGISTRATION_MANIFEST_FORBIDDEN_KEY_NAMES:
                raise ConfirmatoryRegistrationError(
                    f"{path}: {key!r} is a forbidden key name in "
                    f"{REGISTRATION_MANIFEST_FILENAME}"
                )
            _require_no_forbidden_keys(item, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_no_forbidden_keys(item, f"{path}[{index}]")


def _validate_f25(artifact: dict[str, Any]) -> None:
    """F25 — the frozen forbidden-key contract of §16.4, restated for auditors.

    Two entries are position-sensitive: ``statistic_spec_id`` is forbidden at the
    top level and required inside ``registered_statistical_configuration``, and
    ``registered_k`` is forbidden everywhere because ``K`` carries the value.
    """

    for key in sorted(_TOP_LEVEL_ONLY_FORBIDDEN_KEY_NAMES):
        if key in artifact:
            raise ConfirmatoryRegistrationError(
                f"{REGISTRATION_MANIFEST_FILENAME}: {key!r} is forbidden at the top "
                "level; it is carried inside registered_statistical_configuration"
            )
    _require_no_forbidden_keys(artifact, REGISTRATION_MANIFEST_FILENAME)


def _validate_tier_one(artifact: dict[str, Any]) -> None:
    """§16.1 — F1 through F25, in numbered order, aborting on the first failure."""

    _validate_f1(artifact)
    _validate_f2(artifact)
    _validate_f3(artifact)
    _validate_f4(artifact)
    _validate_f5(artifact)
    _validate_f6(artifact)
    _validate_f7(artifact)
    _validate_f8(artifact)
    confirmatory_strata = _validate_f9(artifact)
    descriptive_only_strata = _validate_f10(artifact)
    _validate_f11(confirmatory_strata, descriptive_only_strata)
    confirmatory_positions = _validate_f12(artifact)
    descriptive_positions = _validate_f13(artifact)
    _validate_f14(confirmatory_positions, descriptive_positions)
    _validate_f15(confirmatory_positions, descriptive_positions)
    _validate_f16(confirmatory_positions, descriptive_positions)
    _validate_f17(
        confirmatory_positions,
        descriptive_positions,
        confirmatory_strata,
        descriptive_only_strata,
    )
    _validate_f18(
        confirmatory_strata,
        descriptive_only_strata,
        confirmatory_positions,
        descriptive_positions,
    )
    _validate_f19(artifact, confirmatory_positions)
    _validate_f20(artifact)
    _validate_f21(artifact)
    _validate_f22(artifact)
    _validate_f23(artifact)
    _validate_f24(artifact)
    _validate_f25(artifact)


# ---------------------------------------------------------------------------
# §16.2 Tier 2 — F26 through F33, against the bound registration draft
#
# A manifest may be *parsed* standalone but is never *accepted* without both
# bound upstream artifacts, so these run only after every Tier-1 rule has passed.
# ---------------------------------------------------------------------------


def _validate_f26(artifact: dict[str, Any], registration_draft: RegistrationDraft) -> None:
    """F26 — the bound draft loads through its own frozen loader and binds here.

    The draft is put through the committed Stage-A rebuild (V1-V11, RC-1…RC-5)
    and Work Unit 1's own ``self_digest`` verification, not a locally recreated
    hash, and this manifest's ``registration_draft_digest`` must equal that
    verified digest.
    """

    if not isinstance(registration_draft, RegistrationDraft):
        raise ConfirmatoryRegistrationError(
            "registration_draft must be a RegistrationDraft"
        )
    draft_artifact = registration_draft.to_artifact()
    verify_self_digest(draft_artifact)
    _draft_from_artifact(draft_artifact)
    if not hmac.compare_digest(
        artifact["registration_draft_digest"], registration_draft.self_digest
    ):
        raise ConfirmatoryRegistrationError(
            f"registration_draft_digest {artifact['registration_draft_digest']} does "
            f"not equal the bound draft's self_digest "
            f"{registration_draft.self_digest}"
        )


def _validate_f27(registration_draft: RegistrationDraft) -> None:
    """F27 — the bound artifact is a Stage-A draft, not some other stage's."""

    if registration_draft.registration_state != REGISTRATION_STATE_DRAFT:
        raise ConfirmatoryRegistrationError(
            "the bound registration draft's registration_state must be "
            f"{REGISTRATION_STATE_DRAFT!r}, got "
            f"{registration_draft.registration_state!r}"
        )


def _validate_f28(artifact: dict[str, Any], registration_draft: RegistrationDraft) -> None:
    """F28 — ``design_id`` and ``confirmatory_profile`` equal the draft's exactly."""

    if artifact["design_id"] != registration_draft.design_id:
        raise ConfirmatoryRegistrationError(
            f"design_id {artifact['design_id']!r} does not equal the bound draft's "
            f"{registration_draft.design_id!r}"
        )
    if artifact["confirmatory_profile"] != registration_draft.confirmatory_profile:
        raise ConfirmatoryRegistrationError(
            f"confirmatory_profile {artifact['confirmatory_profile']!r} does not "
            f"equal the bound draft's {registration_draft.confirmatory_profile!r}"
        )


def _validate_f29(artifact: dict[str, Any], registration_draft: RegistrationDraft) -> None:
    """F29 — exact element-wise stratum cover of ``draft.proposed_strata`` (§13.3).

    This is the single rule that rejects a missing, duplicate, foreign, or
    both-sides stratum, by equal total length plus index-wise equality after the
    ascending merge.  No set arithmetic can mask a duplicate.
    """

    confirmatory_strata = artifact["confirmatory_strata"]
    descriptive_only_strata = artifact["descriptive_only_strata"]
    expected = registration_draft.proposed_strata
    if len(confirmatory_strata) + len(descriptive_only_strata) != len(expected):
        raise ConfirmatoryRegistrationError(
            "confirmatory_strata and descriptive_only_strata must together cover "
            f"the draft's {len(expected)} proposed_strata exactly once each, got "
            f"{len(confirmatory_strata)} + {len(descriptive_only_strata)}"
        )
    merged = _merge_sorted_disjoint(
        confirmatory_strata,
        descriptive_only_strata,
        _stratum_key,
        "confirmatory_strata/descriptive_only_strata",
    )
    for index, stratum in enumerate(expected):
        if _stratum_key(merged[index]) != stratum.identity:
            raise ConfirmatoryRegistrationError(
                f"merged Stage-C stratum {index} is "
                f"{_stratum_key(merged[index])!r} but the bound draft's "
                f"proposed_strata[{index}] is {stratum.identity!r}"
            )


def _validate_f30(
    artifact: dict[str, Any], registration_draft: RegistrationDraft
) -> list[dict[str, Any]]:
    """F30 — exact element-wise position cover on all seven Stage-A fields (§13.3).

    This is the single rule that rejects a missing, duplicate, or foreign
    position.  Every one of the seven registered Stage-A fields is compared
    positionally against the proposed position at the same merged index, so a
    faithful ``position_id`` over fabricated fields cannot pass.
    """

    confirmatory_positions = artifact["confirmatory_positions"]
    descriptive_positions = artifact["descriptive_positions"]
    expected = registration_draft.proposed_positions
    if len(confirmatory_positions) + len(descriptive_positions) != len(expected):
        raise ConfirmatoryRegistrationError(
            "confirmatory_positions and descriptive_positions must together cover "
            f"the draft's {len(expected)} proposed_positions exactly once each, got "
            f"{len(confirmatory_positions)} + {len(descriptive_positions)}"
        )
    merged = _merge_sorted_disjoint(
        confirmatory_positions,
        descriptive_positions,
        _position_placement,
        "confirmatory_positions/descriptive_positions",
    )
    for index, position in enumerate(expected):
        record = merged[index]
        for name, value in (
            ("task_id", position.task_id),
            ("provider", position.provider),
            ("model", position.model),
            ("repetition", position.repetition),
            ("provider_seed", position.provider_seed),
            ("slot", position.slot),
            ("baseline_label", position.baseline_label),
        ):
            if record[name] != value:
                raise ConfirmatoryRegistrationError(
                    f"merged Stage-C position {index} has {name}={record[name]!r} "
                    f"but the bound draft's proposed_positions[{index}] has "
                    f"{name}={value!r}"
                )
    return merged


def _validate_f31(
    merged_positions: list[dict[str, Any]], registration_draft: RegistrationDraft
) -> None:
    """F31 — ``baseline_label`` equals the draft's, positionally, on both sides.

    Implied by F30 and stated separately because it is the binding ``S_k``
    equality the Stage-A clarification froze by name (§14.3).  Stage C copies the
    label; it never recomputes one, reruns an ordering procedure, chooses a new
    schedule, or alters a label because eligibility results are now known.
    """

    for index, position in enumerate(registration_draft.proposed_positions):
        recorded = merged_positions[index]["baseline_label"]
        if recorded != position.baseline_label:
            raise ConfirmatoryRegistrationError(
                f"merged Stage-C position {index} has baseline_label {recorded!r} "
                f"but the bound draft's proposed_positions[{index}] has "
                f"{position.baseline_label!r}"
            )


def _validate_f32(artifact: dict[str, Any], registration_draft: RegistrationDraft) -> None:
    """F32 — each confirmatory stratum's runtime identity equals Stage A's (§10.4).

    The lookup is by the exact ``(provider, model)`` pair, never by position and
    never by fallback.  Equality is exact string equality of two 64-hex values:
    no partial match, no prefix comparison, no normalization.  **Nothing is
    recaptured**: no ``RuntimeSnapshotV1`` is built, no provider is contacted, no
    live runtime is read, and no ``captured_at`` is compared (§10.3).
    """

    runtime = registration_draft.proposed_runtime_configuration
    for index, stratum in enumerate(artifact["confirmatory_strata"]):
        expected = runtime.registration_expected_runtime_identity_digest(
            stratum["provider"], stratum["model"]
        )
        if not hmac.compare_digest(stratum["runtime_identity_digest"], expected):
            raise ConfirmatoryRegistrationError(
                f"confirmatory_strata[{index}].runtime_identity_digest "
                f"{stratum['runtime_identity_digest']} does not equal the bound "
                f"draft's registration-expected digest {expected} for stratum "
                f"{_stratum_key(stratum)!r}"
            )


def _validate_f33(artifact: dict[str, Any], registration_draft: RegistrationDraft) -> None:
    """F33 — exact **parsed-object** equality with the draft's proposed object.

    §11.2.1 S1-S7: the same eleven keys, the same JSON value for every key,
    arrays in the same registered order, no missing key, no extra key, no
    normalized or reinterpreted value, and no caller-selected replacement.  The
    comparison is over parsed objects; it is **never** a comparison of the
    draft's incidental serialized bytes, and no byte-canonicality reader gate is
    added (§11.2.2).
    """

    registered = artifact["registered_statistical_configuration"]
    proposed = registration_draft.proposed_statistical_configuration.to_dict()
    if registered == proposed:
        return
    missing = sorted(set(proposed) - set(registered))
    unexpected = sorted(set(registered) - set(proposed))
    differing = sorted(
        key
        for key in set(proposed) & set(registered)
        if registered[key] != proposed[key]
    )
    raise ConfirmatoryRegistrationError(
        "registered_statistical_configuration must equal the bound draft's "
        "proposed_statistical_configuration by exact parsed-object equality; "
        f"missing={missing!r} unexpected={unexpected!r} differing={differing!r}"
    )


def _validate_tier_two(
    artifact: dict[str, Any], registration_draft: RegistrationDraft
) -> None:
    """§16.2 — F26 through F33, in numbered order, aborting on the first failure."""

    _validate_f26(artifact, registration_draft)
    _validate_f27(registration_draft)
    _validate_f28(artifact, registration_draft)
    _validate_f29(artifact, registration_draft)
    merged_positions = _validate_f30(artifact, registration_draft)
    _validate_f31(merged_positions, registration_draft)
    _validate_f32(artifact, registration_draft)
    _validate_f33(artifact, registration_draft)


# ---------------------------------------------------------------------------
# §16.3 Tier 3 — F34 through F37, against the bound eligibility manifest
#
# Stage C never re-evaluates a predicate, never re-derives a disposition, and
# never reimplements ``E1``-``E26``: it calls Work Unit 2's own public validation
# surface and reads the frozen result.
# ---------------------------------------------------------------------------


def _require_eligibility_manifest(eligibility_manifest: Any) -> None:
    from iqa_soa.experiment.confirmatory_eligibility import EligibilityManifestV1 as _M

    if not isinstance(eligibility_manifest, _M):
        raise ConfirmatoryRegistrationError(
            "eligibility_manifest must be an EligibilityManifestV1"
        )


def _revalidate_bound_eligibility(
    eligibility_manifest: EligibilityManifestV1,
    registration_draft: RegistrationDraft,
) -> None:
    """Put the bound manifest through Work Unit 2's own frozen ``E1``-``E26`` contract.

    ``freeze_eligibility`` applies the identical ordered contract the Stage-B
    loader applies, against this exact draft, and seals the result; requiring the
    bound object to be reproduced by it proves the manifest satisfies ``E1``-``E26``
    without a single Stage-B rule being restated here.
    """

    from iqa_soa.experiment.confirmatory_eligibility import (
        ConfirmatoryEligibilityError,
        freeze_eligibility,
    )

    _require_created_at_text(
        _require_nonempty_text(
            eligibility_manifest.created_at, "eligibility_manifest.created_at"
        )
    )
    captured = datetime.strptime(
        eligibility_manifest.created_at, _CREATED_AT_FORMAT
    ).replace(tzinfo=timezone.utc)
    try:
        rebuilt = freeze_eligibility(
            registration_draft=registration_draft,
            created_at=captured,
            eligibility_records=eligibility_manifest.eligibility_records,
        )
    except ConfirmatoryEligibilityError as error:
        raise ConfirmatoryRegistrationError(
            "the bound eligibility manifest does not satisfy the frozen Stage-B "
            f"E1-E26 contract against this draft: {error}"
        ) from error
    if rebuilt != eligibility_manifest:
        raise ConfirmatoryRegistrationError(
            "the bound eligibility manifest is not reproduced by the frozen Stage-B "
            "contract applied to its own records and this draft"
        )


def _validate_f34(
    artifact: dict[str, Any],
    registration_draft: RegistrationDraft,
    eligibility_manifest: EligibilityManifestV1,
) -> None:
    """F34 — the bound manifest loads through its own frozen loader and binds here."""

    _require_eligibility_manifest(eligibility_manifest)
    verify_self_digest(eligibility_manifest.to_artifact())
    _revalidate_bound_eligibility(eligibility_manifest, registration_draft)
    if not hmac.compare_digest(
        artifact["eligibility_manifest_digest"], eligibility_manifest.self_digest
    ):
        raise ConfirmatoryRegistrationError(
            f"eligibility_manifest_digest {artifact['eligibility_manifest_digest']} "
            "does not equal the bound eligibility manifest's self_digest "
            f"{eligibility_manifest.self_digest}"
        )


def _validate_f35(
    artifact: dict[str, Any], eligibility_manifest: EligibilityManifestV1
) -> None:
    """F35 — Stage-B state, and the design/profile/draft chain, agree across all three.

    An eligibility manifest assessed against a *different* draft can never be
    admitted, so a broken chain is an integrity rejection and is **never**
    converted into descriptive-only status.
    """

    from iqa_soa.experiment.confirmatory_eligibility import (
        REGISTRATION_STATE_ELIGIBILITY_FROZEN,
    )

    if eligibility_manifest.registration_state != REGISTRATION_STATE_ELIGIBILITY_FROZEN:
        raise ConfirmatoryRegistrationError(
            "the bound eligibility manifest's registration_state must be "
            f"{REGISTRATION_STATE_ELIGIBILITY_FROZEN!r}, got "
            f"{eligibility_manifest.registration_state!r}"
        )
    if eligibility_manifest.design_id != artifact["design_id"]:
        raise ConfirmatoryRegistrationError(
            f"the bound eligibility manifest's design_id "
            f"{eligibility_manifest.design_id!r} does not equal this manifest's "
            f"{artifact['design_id']!r}"
        )
    if eligibility_manifest.confirmatory_profile != artifact["confirmatory_profile"]:
        raise ConfirmatoryRegistrationError(
            "the bound eligibility manifest's confirmatory_profile "
            f"{eligibility_manifest.confirmatory_profile!r} does not equal this "
            f"manifest's {artifact['confirmatory_profile']!r}"
        )
    if not hmac.compare_digest(
        eligibility_manifest.registration_draft_digest,
        artifact["registration_draft_digest"],
    ):
        raise ConfirmatoryRegistrationError(
            "the bound eligibility manifest's registration_draft_digest "
            f"{eligibility_manifest.registration_draft_digest} does not equal this "
            f"manifest's {artifact['registration_draft_digest']}"
        )


def _validate_f36(
    artifact: dict[str, Any], eligibility_manifest: EligibilityManifestV1
) -> None:
    """F36 — the partition agrees with the frozen Stage-B dispositions (§13.3).

    **No disposition is recomputed from predicates**, no predicate is evaluated,
    and no evidence is read: the frozen token is read, and only which side each
    stratum landed on is checked.
    """

    from iqa_soa.experiment.confirmatory_eligibility import DISPOSITIONS

    if DISPOSITION_CONFIRMATORY_ELIGIBLE not in DISPOSITIONS:
        raise ConfirmatoryRegistrationError(
            f"{DISPOSITION_CONFIRMATORY_ELIGIBLE!r} is not one of the frozen Stage-B "
            f"dispositions {list(DISPOSITIONS)!r}"
        )
    dispositions = {
        record.identity: record.disposition
        for record in eligibility_manifest.eligibility_records
    }
    for index, stratum in enumerate(artifact["confirmatory_strata"]):
        key = _stratum_key(stratum)
        disposition = dispositions.get(key)
        if disposition is None:
            raise ConfirmatoryRegistrationError(
                f"confirmatory_strata[{index}] {key!r} has no eligibility record in "
                "the bound eligibility manifest"
            )
        if disposition != DISPOSITION_CONFIRMATORY_ELIGIBLE:
            raise ConfirmatoryRegistrationError(
                f"confirmatory_strata[{index}] {key!r} is recorded "
                f"{disposition!r} in the bound eligibility manifest, not "
                f"{DISPOSITION_CONFIRMATORY_ELIGIBLE!r}"
            )
    for index, stratum in enumerate(artifact["descriptive_only_strata"]):
        key = _stratum_key(stratum)
        disposition = dispositions.get(key)
        if disposition is None:
            raise ConfirmatoryRegistrationError(
                f"descriptive_only_strata[{index}] {key!r} has no eligibility record "
                "in the bound eligibility manifest"
            )
        if disposition not in DISPOSITIONS:
            raise ConfirmatoryRegistrationError(
                f"descriptive_only_strata[{index}] {key!r} carries the unknown "
                f"disposition {disposition!r}"
            )
        if disposition == DISPOSITION_CONFIRMATORY_ELIGIBLE:
            raise ConfirmatoryRegistrationError(
                f"descriptive_only_strata[{index}] {key!r} is recorded "
                f"{DISPOSITION_CONFIRMATORY_ELIGIBLE!r} in the bound eligibility "
                "manifest and belongs on the confirmatory side"
            )


def _validate_f37(
    artifact: dict[str, Any], eligibility_manifest: EligibilityManifestV1
) -> None:
    """F37 — each confirmatory runtime identity equals Stage B's copy (§10.4)."""

    digests = {
        record.identity: record.runtime_identity_digest
        for record in eligibility_manifest.eligibility_records
    }
    for index, stratum in enumerate(artifact["confirmatory_strata"]):
        key = _stratum_key(stratum)
        expected = digests.get(key)
        if expected is None:
            raise ConfirmatoryRegistrationError(
                f"confirmatory_strata[{index}] {key!r} has no eligibility record in "
                "the bound eligibility manifest"
            )
        if not hmac.compare_digest(stratum["runtime_identity_digest"], expected):
            raise ConfirmatoryRegistrationError(
                f"confirmatory_strata[{index}].runtime_identity_digest "
                f"{stratum['runtime_identity_digest']} does not equal the bound "
                f"eligibility manifest's {expected} for stratum {key!r}"
            )


def _validate_tier_three(
    artifact: dict[str, Any],
    registration_draft: RegistrationDraft,
    eligibility_manifest: EligibilityManifestV1,
) -> None:
    """§16.3 — F34 through F37, in numbered order, aborting on the first failure."""

    _validate_f34(artifact, registration_draft, eligibility_manifest)
    _validate_f35(artifact, eligibility_manifest)
    _validate_f36(artifact, eligibility_manifest)
    _validate_f37(artifact, eligibility_manifest)


def _validate_chain(
    artifact: dict[str, Any],
    registration_draft: RegistrationDraft,
    eligibility_manifest: EligibilityManifestV1,
) -> None:
    """F1 through F37 against the complete bound chain, in numbered order."""

    _validate_tier_one(artifact)
    _validate_tier_two(artifact, registration_draft)
    _validate_tier_three(artifact, registration_draft, eligibility_manifest)


# ---------------------------------------------------------------------------
# §13 The partition — deterministic construction, never caller-supplied
# ---------------------------------------------------------------------------


def _derive_stage_c_partition(
    registration_draft: RegistrationDraft,
    eligibility_manifest: EligibilityManifestV1,
) -> tuple[
    tuple[ConfirmatoryStratumV1, ...],
    tuple[ProposedStratumV1, ...],
    tuple[ConfirmatoryPositionV1, ...],
    tuple[ConfirmatoryPositionV1, ...],
]:
    """§13.1 — the total, deterministic, stable element-wise partition.

    Both steps iterate an already-sorted, already-unique immutable Stage-A array
    **in order** and append without reordering, so each output is a stable filter
    of a sorted array and is therefore sorted and unique under the same key.
    **There is no ``sorted()`` call anywhere in the construction**, no
    normalization of the input, and no interface through which a caller could
    supply an order or an array at all (§8.4).

    ``record.disposition`` is **read**, never recomputed: Stage B already
    cross-checked the persisted token against its own derivation at E19.  Stage C
    re-derives no disposition from predicates, evaluates no predicate, reads no
    evidence, promotes no ``UNASSESSED`` stratum, and never infers eligibility
    from a provider type.  A position's side is decided solely by its own
    ``(provider, model)`` stratum's disposition.
    """

    strata = registration_draft.proposed_strata
    records = eligibility_manifest.eligibility_records
    if len(records) != len(strata):
        raise ConfirmatoryRegistrationError(
            f"the bound eligibility manifest carries {len(records)} records for the "
            f"draft's {len(strata)} proposed_strata"
        )
    confirmatory_strata: list[ConfirmatoryStratumV1] = []
    descriptive_only_strata: list[ProposedStratumV1] = []
    confirmatory_keys: set[tuple[str, str]] = set()
    runtime = registration_draft.proposed_runtime_configuration
    for index, stratum in enumerate(strata):
        record = records[index]
        if record.identity != stratum.identity:
            raise ConfirmatoryRegistrationError(
                f"eligibility_records[{index}] {record.identity!r} is not aligned "
                f"with proposed_strata[{index}] {stratum.identity!r}"
            )
        if record.disposition == DISPOSITION_CONFIRMATORY_ELIGIBLE:
            expected = runtime.registration_expected_runtime_identity_digest(
                stratum.provider, stratum.model
            )
            if not hmac.compare_digest(record.runtime_identity_digest, expected):
                raise ConfirmatoryRegistrationError(
                    f"eligibility_records[{index}] carries runtime_identity_digest "
                    f"{record.runtime_identity_digest} for stratum "
                    f"{stratum.identity!r} but the bound draft expects {expected}"
                )
            confirmatory_strata.append(
                ConfirmatoryStratumV1(
                    provider=stratum.provider,
                    model=stratum.model,
                    runtime_identity_digest=expected,
                )
            )
            confirmatory_keys.add(stratum.identity)
        else:
            descriptive_only_strata.append(
                ProposedStratumV1(provider=stratum.provider, model=stratum.model)
            )
    confirmatory_positions: list[ConfirmatoryPositionV1] = []
    descriptive_positions: list[ConfirmatoryPositionV1] = []
    for position in registration_draft.proposed_positions:
        record_position = _final_position_record(position)
        if (position.provider, position.model) in confirmatory_keys:
            confirmatory_positions.append(record_position)
        else:
            descriptive_positions.append(record_position)
    return (
        tuple(confirmatory_strata),
        tuple(descriptive_only_strata),
        tuple(confirmatory_positions),
        tuple(descriptive_positions),
    )


def _bind_upstream_chain(
    registration_draft: RegistrationDraft,
    eligibility_manifest: EligibilityManifestV1,
) -> None:
    """Every failure-prone upstream check, run **before** the ``created_at`` capture.

    T4 requires construction to perform all failure-prone pre-capture validation
    it can, so a construction that fails never captures an instant and a captured
    instant never exists without a sealed artifact.  This is the F26/F27 draft
    binding and the F34/F35 eligibility binding, applied to the in-memory objects
    the same way the numbered rules apply them to a persisted manifest.
    """

    if not isinstance(registration_draft, RegistrationDraft):
        raise ConfirmatoryRegistrationError(
            "registration_draft must be a RegistrationDraft"
        )
    draft_artifact = registration_draft.to_artifact()
    verify_self_digest(draft_artifact)
    _draft_from_artifact(draft_artifact)
    _validate_f27(registration_draft)
    _require_eligibility_manifest(eligibility_manifest)
    verify_self_digest(eligibility_manifest.to_artifact())
    _revalidate_bound_eligibility(eligibility_manifest, registration_draft)


def freeze_final_registration(
    *,
    registration_draft: RegistrationDraft,
    eligibility_manifest: EligibilityManifestV1,
) -> RegistrationManifest:
    """Freeze ``ELIGIBILITY_FROZEN`` into ``FINAL_REGISTRATION_FROZEN`` (§4-§17).

    Every Stage-C value is **derived, never accepted**: the partition, the
    position records, ``position_id``, the confirmatory runtime identities, ``K``,
    ``randomization_mode``, ``matrix_digest``, and ``self_digest`` all follow from
    the two bound immutable upstream artifacts under already-frozen rules.  There
    is no matrix parameter, no ordering parameter, and no statistical parameter.

    **``created_at`` is not caller-selectable** (§4.4.1).  There is deliberately
    no ``created_at`` parameter, no clock parameter, no "as-of" parameter, and no
    override of any name: the freeze instant is captured internally, exactly once,
    on the successful sealing path, after every check that does not depend on it
    and strictly before ``self_digest`` is computed and before any byte reaches
    disk.  Backdating is prevented structurally — a caller cannot backdate what it
    cannot reach.

    **This function assigns nothing.**  It draws no randomization bit, generates
    no Monte Carlo seed and no provenance artifact, selects no ``M``, contacts no
    provider, recaptures no ``RuntimeSnapshotV1``, executes nothing, analyses
    nothing, and assesses no eligibility.  It records the consequence of an
    assessment that Stage B already froze, and no caller in this repository has
    performed a real one.
    """

    # 1-2. Bind and validate both upstream artifacts (pre-capture, T4).
    _bind_upstream_chain(registration_draft, eligibility_manifest)
    # 3-5. Derive the partition, the position records, and the runtime identities.
    (
        confirmatory_strata,
        descriptive_only_strata,
        confirmatory_positions,
        descriptive_positions,
    ) = _derive_stage_c_partition(registration_draft, eligibility_manifest)
    # 6. Carry the already-authenticated statistical object forward unchanged.
    statistical = registration_draft.proposed_statistical_configuration
    # 7-9. Derive K, derive the mode from K, and enforce the mode/M gate.
    registered_k = _derive_registered_k(confirmatory_positions)
    randomization_mode = _derive_randomization_mode(registered_k)
    _require_mode_sample_gate(
        randomization_mode, statistical.randomization_mc_samples
    )
    # 10-12. Every failure-prone check is behind us; capture the freeze instant.
    created_at = _capture_created_at()
    # 13. Seal the sixteen-key artifact with matrix_digest and self_digest unset.
    body: dict[str, Any] = {
        "K": registered_k,
        "confirmatory_positions": [
            position.to_dict() for position in confirmatory_positions
        ],
        "confirmatory_profile": CONFIRMATORY_PROFILE,
        "confirmatory_strata": [
            stratum.to_dict() for stratum in confirmatory_strata
        ],
        "created_at": created_at,
        "descriptive_only_strata": [
            stratum.to_dict() for stratum in descriptive_only_strata
        ],
        "descriptive_positions": [
            position.to_dict() for position in descriptive_positions
        ],
        "design_id": registration_draft.design_id,
        "eligibility_manifest_digest": eligibility_manifest.self_digest,
        "randomization_mode": randomization_mode,
        "registered_statistical_configuration": statistical.to_dict(),
        "registration_draft_digest": registration_draft.self_digest,
        "registration_state": REGISTRATION_STATE_FINAL_REGISTRATION_FROZEN,
        "schema_version": REGISTRATION_MANIFEST_SCHEMA_VERSION,
    }
    # 14. matrix_digest from the artifact's own already-final values (§9.7 step 3).
    matrix_digest = _matrix_digest_from_values(body)
    body["matrix_digest"] = matrix_digest
    # 15. self_digest strictly after, so it covers matrix_digest and never the
    #     reverse (§9.7 step 4).
    self_digest = compute_self_digest(body)
    sealed = RegistrationManifest(
        schema_version=REGISTRATION_MANIFEST_SCHEMA_VERSION,
        registration_state=REGISTRATION_STATE_FINAL_REGISTRATION_FROZEN,
        confirmatory_profile=CONFIRMATORY_PROFILE,
        design_id=registration_draft.design_id,
        created_at=created_at,
        registration_draft_digest=registration_draft.self_digest,
        eligibility_manifest_digest=eligibility_manifest.self_digest,
        confirmatory_strata=confirmatory_strata,
        descriptive_only_strata=descriptive_only_strata,
        confirmatory_positions=confirmatory_positions,
        descriptive_positions=descriptive_positions,
        K=registered_k,
        randomization_mode=randomization_mode,
        registered_statistical_configuration=statistical,
        matrix_digest=matrix_digest,
        self_digest=self_digest,
    )
    # 16. The complete frozen semantic contract, so construction cannot mint
    #     anything a load would refuse.
    _validate_chain(sealed.to_artifact(), registration_draft, eligibility_manifest)
    object.__setattr__(
        sealed, "_freeze_provenance", (sealed.created_at, sealed.self_digest)
    )
    return sealed


# ---------------------------------------------------------------------------
# Reconstruction — only after F1-F37 have all passed
# ---------------------------------------------------------------------------


def _position_from_validated(mapping: dict[str, Any]) -> ConfirmatoryPositionV1:
    return ConfirmatoryPositionV1(
        position_id=mapping["position_id"],
        task_id=mapping["task_id"],
        provider=mapping["provider"],
        model=mapping["model"],
        repetition=mapping["repetition"],
        provider_seed=mapping["provider_seed"],
        slot=mapping["slot"],
        baseline_label=mapping["baseline_label"],
    )


def _manifest_from_validated(artifact: dict[str, Any]) -> RegistrationManifest:
    return RegistrationManifest(
        schema_version=REGISTRATION_MANIFEST_SCHEMA_VERSION,
        registration_state=REGISTRATION_STATE_FINAL_REGISTRATION_FROZEN,
        confirmatory_profile=CONFIRMATORY_PROFILE,
        design_id=artifact["design_id"],
        created_at=artifact["created_at"],
        registration_draft_digest=artifact["registration_draft_digest"],
        eligibility_manifest_digest=artifact["eligibility_manifest_digest"],
        confirmatory_strata=tuple(
            ConfirmatoryStratumV1(
                provider=mapping["provider"],
                model=mapping["model"],
                runtime_identity_digest=mapping["runtime_identity_digest"],
            )
            for mapping in artifact["confirmatory_strata"]
        ),
        descriptive_only_strata=tuple(
            ProposedStratumV1(provider=mapping["provider"], model=mapping["model"])
            for mapping in artifact["descriptive_only_strata"]
        ),
        confirmatory_positions=tuple(
            _position_from_validated(mapping)
            for mapping in artifact["confirmatory_positions"]
        ),
        descriptive_positions=tuple(
            _position_from_validated(mapping)
            for mapping in artifact["descriptive_positions"]
        ),
        K=artifact["K"],
        randomization_mode=artifact["randomization_mode"],
        registered_statistical_configuration=ProposedStatisticalConfigurationV1(
            randomization_mc_samples=(
                artifact["registered_statistical_configuration"][
                    "randomization_mc_samples"
                ]
            ),
        ),
        matrix_digest=artifact["matrix_digest"],
        self_digest=artifact[SELF_DIGEST_FIELD],
    )


# ---------------------------------------------------------------------------
# Immutable persistence and fail-closed load (§16.5, §17)
# ---------------------------------------------------------------------------


def registration_manifest_path(confirmatory_root: Path, design_id: str) -> Path:
    """``<confirmatory_root>/<design_id>/registration_manifest.json`` (§17).

    ``design_id`` goes through the Work Unit 1 single-safe-segment discipline and
    the resolved path is required to stay inside ``confirmatory_root``, so no
    design id can steer a write outside the confirmatory tree.
    """

    safe_design_id = _require_design_id(design_id)
    root = Path(confirmatory_root)
    path = root / safe_design_id / REGISTRATION_MANIFEST_FILENAME
    resolved_root = root.resolve(strict=False)
    resolved_path = path.resolve(strict=False)
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as error:
        raise ConfirmatoryRegistrationError(
            f"registration manifest path escapes confirmatory_root: {path}"
        ) from error
    return path


def _bound_stage_a_draft(confirmatory_root: Path, design_id: str) -> RegistrationDraft:
    """Load the Stage-A draft this manifest must bind to, failing closed."""

    draft_path = registration_draft_path(confirmatory_root, design_id)
    if not draft_path.is_file():
        raise ConfirmatoryRegistrationError(
            "the bound registration draft does not exist; Stage C occurs strictly "
            f"after registration_draft.json: {draft_path}"
        )
    return load_registration_draft(draft_path)


def _bound_stage_b_manifest(
    confirmatory_root: Path, design_id: str, registration_draft: RegistrationDraft
) -> EligibilityManifestV1:
    """Load the Stage-B manifest through Work Unit 2's own frozen ``E1``-``E26`` loader.

    An absent manifest is F38's Stage-B prerequisite failing: ``ELIGIBILITY_FROZEN``
    strictly precedes ``FINAL_REGISTRATION_FROZEN`` and there is no path that
    freezes a final registration first.
    """

    from iqa_soa.experiment.confirmatory_eligibility import (
        ConfirmatoryEligibilityError,
        eligibility_manifest_path,
        load_eligibility_manifest,
    )

    try:
        manifest_path = eligibility_manifest_path(confirmatory_root, design_id)
        if not manifest_path.is_file():
            raise ConfirmatoryRegistrationError(
                "F38: the bound eligibility manifest does not exist; "
                "ELIGIBILITY_FROZEN strictly precedes FINAL_REGISTRATION_FROZEN: "
                f"{manifest_path}"
            )
        return load_eligibility_manifest(
            manifest_path, registration_draft=registration_draft
        )
    except ConfirmatoryEligibilityError as error:
        raise ConfirmatoryRegistrationError(
            f"F38: the bound eligibility manifest is not valid Stage-B: {error}"
        ) from error


def _validate_f38(
    artifact: dict[str, Any],
    *,
    manifest: RegistrationManifest,
    confirmatory_root: Path,
) -> None:
    """F38 — the write prerequisite: **one rule, two required conjuncts** (§16.5).

    ``F38a``/``F38b`` are labels for the two conjuncts of this single rule, not new
    independent validation positions, so the observable sequence stays
    ``F1 … F37 -> F38 -> F39``.

    **(a) Stage-B prerequisite.** ``eligibility_manifest.json`` must already exist
    for this ``design_id`` and load and validate through ``E1``-``E26``, and the
    artifact about to be written must pass ``F1``-``F37`` against it and the bound
    draft.

    **(b) ``created_at`` capture prerequisite.** The sealed ``created_at`` must be
    the value captured internally by this :func:`freeze_final_registration`
    invocation.  A private, non-persisted provenance tuple binds that value and
    the completed ``self_digest``.  Direct construction and
    :func:`dataclasses.replace` leave the manifest unproven, while loading proves
    artifact integrity and semantics without fabricating historical wall-clock
    provenance.
    """

    # (a) — F1-F25 first, so design_id is a proven safe segment before it is used
    # to locate either upstream artifact.
    _validate_tier_one(artifact)
    registration_draft = _bound_stage_a_draft(confirmatory_root, artifact["design_id"])
    _validate_tier_two(artifact, registration_draft)
    eligibility_manifest = _bound_stage_b_manifest(
        confirmatory_root, artifact["design_id"], registration_draft
    )
    _validate_tier_three(artifact, registration_draft, eligibility_manifest)
    # (b) — F6 and F24 have already checked the persisted grammar and digest.
    # Only this invocation's successfully sealed result carries usable provenance.
    expected_provenance = (manifest.created_at, manifest.self_digest)
    if manifest._freeze_provenance != expected_provenance:
        raise ConfirmatoryRegistrationError(
            "F38: created_at and self_digest lack matching freeze provenance from "
            "this freeze_final_registration invocation"
        )


def _validate_f39(path: Path) -> None:
    """F39 — the write is an exclusive create; an existing manifest is never touched.

    ``registration_manifest.json`` for a given ``design_id`` is written once.  It is
    never overwritten, truncated, replaced, or updated in place; the remedy for a
    superseded design is a **new** ``design_id`` (§17.2).
    """

    if path.exists():
        raise ConfirmatoryRegistrationError(
            f"registration manifest already exists and is immutable: {path}"
        )


def write_registration_manifest(
    manifest: RegistrationManifest, *, confirmatory_root: Path
) -> Path:
    """Write ``registration_manifest.json`` exactly once, and never again.

    The complete ``F1``-``F37`` contract runs against the sealed artifact, and F38's
    two conjuncts after it, **before** path calculation, ``mkdir``, and
    ``open("xb")`` — so an invalid manifest creates no directory and no file, and a
    manifest with several simultaneous defects is refused for the lowest-numbered
    one.  The persisted form is canonical JSON including ``self_digest`` followed
    by exactly one LF, appended after every digest is computed and so never part
    of one.
    """

    if not isinstance(manifest, RegistrationManifest):
        raise ConfirmatoryRegistrationError("manifest must be a RegistrationManifest")
    try:
        artifact = manifest.to_artifact()
    except (AttributeError, TypeError, ValueError) as error:
        raise ConfirmatoryRegistrationError(
            f"registration manifest cannot be represented by the frozen schema: "
            f"{error}"
        ) from error
    _validate_f38(
        artifact, manifest=manifest, confirmatory_root=confirmatory_root
    )
    payload = serialize_artifact(artifact)
    path = registration_manifest_path(confirmatory_root, manifest.design_id)
    _validate_f39(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
    except FileExistsError as error:
        raise ConfirmatoryRegistrationError(
            f"registration manifest already exists and is immutable: {path}"
        ) from error
    return path


def _parse_registration_manifest_bytes(data: bytes) -> dict[str, Any]:
    """The file envelope only: strip one LF, decode UTF-8, parse, require an object.

    This deliberately stops **short** of ``self_digest`` verification.  §16 fixes
    F1-F39 in numbered order and aborts on the first failure, so F24 must not run
    before F1: a manifest missing a top-level key fails F1, not F24.  Work Unit
    1's :func:`parse_artifact` verifies the digest as part of parsing, which is
    correct for a Stage-A draft but would invert this contract, so only its
    envelope is reproduced here.

    **Nothing is canonicalized and nothing is hashed.**  §17.1's reader semantics
    are otherwise unchanged — at most one trailing LF is stripped, the parse is
    semantic, and **no byte-for-byte canonical-input gate is introduced**.
    """

    if data.endswith(b"\n"):
        data = data[:-1]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ConfirmatoryRegistrationError(
            f"registration manifest bytes are not valid UTF-8: {error}"
        ) from error
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise ConfirmatoryRegistrationError(
            f"registration manifest is not valid JSON: {error}"
        ) from error
    if not isinstance(parsed, dict):
        raise ConfirmatoryRegistrationError(
            f"registration manifest must be a JSON object, got {type(parsed).__name__}"
        )
    artifact: dict[str, Any] = parsed
    return artifact


def load_registration_manifest(
    path: Path,
    *,
    registration_draft: RegistrationDraft,
    eligibility_manifest: EligibilityManifestV1,
) -> RegistrationManifest:
    """Read, verify, and rebuild a persisted registration manifest, failing closed.

    Both bound upstream artifacts are required, because a Stage-C manifest may be
    *parsed* standalone but is never *accepted* without the complete chain it
    claims.  The frozen F1-F37 contract is applied in numbered order and aborts on
    the first failure: ``matrix_digest`` verification is F23 and ``self_digest``
    verification is F24, each at its own numbered position, neither a
    precondition of parsing.

    Reader semantics are §5.B.2's, unchanged: at most one trailing LF is stripped,
    the parse is semantic, and each digest is recomputed over the recanonicalized
    content.  **No byte-for-byte canonical-input gate is added**, so semantically
    equivalent noncanonical JSON that parses to the same authenticated object
    remains acceptable (§17.1).

    Nothing is normalized, repaired, sorted, deduplicated, default-filled, or
    partially accepted.  A persisted manifest is never re-sorted or re-deduplicated
    on the caller's behalf.
    """

    artifact = _parse_registration_manifest_bytes(Path(path).read_bytes())
    _validate_chain(artifact, registration_draft, eligibility_manifest)
    return _manifest_from_validated(artifact)
