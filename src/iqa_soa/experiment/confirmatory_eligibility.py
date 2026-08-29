"""Stage-B confirmatory eligibility: the ``ELIGIBILITY_FROZEN`` manifest schema.

This module implements the second work unit of the frozen post-Phase-P
confirmatory randomization implementation design
(``docs/post_phaseP_confirmatory_randomization_implementation_design.md`` §5.A
Stage B, §5.F, §5.I) as fixed by the binding eligibility schema clarification
(``docs/post_phaseP_confirmatory_eligibility_schema_clarification.md``): the
``EligibilityManifestV1`` schema (§4-§13), the total disposition derivation
(§8.2), the infrastructure-symmetry derivation (§10.4), the twenty-six
fail-closed rules ``E1``-``E26`` (§14), and immutable
``eligibility_manifest.json`` persistence (§15).

Stage B occurs strictly **after** ``registration_draft.json`` exists and strictly
**before** ``registration_manifest.json``.  The manifest binds to the draft's
``self_digest`` under the field name ``registration_draft_digest``.

**This module assesses nothing.**  It owns the schema and the validation
machinery only.  It does not read provider configuration, does not decide that
any configured provider/model is ``CONFIRMATORY_ELIGIBLE`` or any
``DESCRIPTIVE_ONLY_*`` state, contacts no provider, opens no network connection,
draws no randomness, and creates no real ``design_id``.
``CURRENT_PROVIDER_ELIGIBILITY: UNASSESSED`` remains true for every provider and
runtime configured in the repository (design decision §9).

Five rules are load-bearing and are implemented literally:

* **E1-E26 run in numbered order and abort on the first failure** (§14).  That
  order is contractually observable, so it is realized by the explicit
  ``_validate_e1`` … ``_validate_e26`` sequence in :func:`_validate_tier_one` and
  :func:`_validate_tier_two`, every one of which inspects the **raw** parsed
  artifact.  No frozen dataclass is constructed until E26 has passed, so no
  ``__post_init__`` can advance a later-numbered rule ahead of an earlier one.
* **Nothing is normalized or repaired.**  Sorting, uniqueness, evidence
  cardinality, and key sets are schema-level *preconditions*, refused rather
  than fixed up on the caller's behalf (§14).
* **All 81 status combinations are legal.**  A status combination is never
  itself a rejection ground (§7.4, E12).  The single-disposition guarantee comes
  from :func:`derive_disposition`'s precedence, never from narrowing what may be
  recorded, so ``PASS FAIL FAIL PASS`` is an admissible record.
* **No locator is ever dereferenced.**  Evidence validation is structural and
  offline: no file is opened, no URL is fetched, no remote digest is recomputed
  (§9.2).
* **The canonical JSON profile and the digest algorithm are not forked.**
  Canonicalization, ``self_digest`` construction/verification, and serialization
  are the Work Unit 1 helpers, imported unchanged and reached at E20, E22, and
  write time.  This module never spells a canonical artifact digest itself: it
  contains no ``hashlib``, no ``sha256``, and no serializer options.  The only
  local JSON work is the file-envelope *syntax* parse of
  :func:`_parse_eligibility_bytes`, which exists solely so E20 cannot run before
  E1 (§16 reader semantics are otherwise unchanged).

Every verification failure fails closed as :class:`ConfirmatoryEligibilityError`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
import hmac
import json
from pathlib import Path
import re
from typing import Any, Callable, Iterator, ParamSpec, Sequence, TypeVar

from iqa_soa.experiment.confirmatory_registration import (
    CONFIRMATORY_PROFILE,
    ConfirmatoryRegistrationError,
    REGISTRATION_STATE_DRAFT,
    RegistrationDraft,
    SELF_DIGEST_FIELD,
    compute_self_digest,
    load_registration_draft,
    registration_draft_path,
    serialize_artifact,
    verify_self_digest,
)

# The frozen digest/timestamp grammars, the exact-key check, the ``design_id``
# path discipline, and the sorted/cover rules are Work Unit 1's, reused rather
# than restated: a second copy of a frozen grammar is a second thing that can
# drift from it.  Every call goes through :func:`_reuse`, which restates a Work
# Unit 1 failure as this module's own error type, so the Stage-B surface raises
# exactly one exception class (§14).
from iqa_soa.experiment.confirmatory_registration import (
    _require_array_field,
    _require_created_at_instant,
    _require_created_at_text,
    _require_design_id,
    _require_digest,
    _require_exact_cover,
    _require_exact_keys,
    _require_literal,
    _require_nonempty_text,
    _require_object,
    _require_object_field,
    _require_sorted_unique,
    _require_text_field,
)

__all__ = [
    "CHANNEL_IDS",
    "CHECK_STATUSES",
    "DISPOSITIONS",
    "ELIGIBILITY_MANIFEST_FILENAME",
    "ELIGIBILITY_MANIFEST_SCHEMA_VERSION",
    "EVIDENCE_KINDS",
    "FORBIDDEN_KEY_NAMES",
    "PREDICATE_IDS",
    "PREDICATE_STATUSES",
    "REGISTRATION_STATE_ELIGIBILITY_FROZEN",
    "SYMMETRY_RESULTS",
    "ConfirmatoryEligibilityError",
    "EligibilityManifestV1",
    "EligibilityPredicateRecordV1",
    "EligibilityStratumRecordV1",
    "EvidenceReferenceV1",
    "InfrastructureSymmetryAuditV1",
    "InfrastructureSymmetryChannelV1",
    "derive_disposition",
    "derive_infrastructure_symmetry_status",
    "eligibility_manifest_path",
    "freeze_eligibility",
    "load_eligibility_manifest",
    "write_eligibility_manifest",
]


class ConfirmatoryEligibilityError(ValueError):
    """A confirmatory eligibility artifact is malformed, mismatched, or immutable."""


# ---------------------------------------------------------------------------
# Frozen literals (§4.1, §4.2, §7.2, §7.3, §8.1, §9.2, §10.2, §10.3, §14.3)
# ---------------------------------------------------------------------------

#: Schema identity of the Stage-B artifact (§4.1).
ELIGIBILITY_MANIFEST_SCHEMA_VERSION = "EligibilityManifestV1"

#: The lifecycle state a Stage-B manifest carries, under the same field name the
#: sibling artifacts use so one uniform check reads all three (§4.2).
#: ``eligibility_state`` is retired and is not a field of this artifact.
REGISTRATION_STATE_ELIGIBILITY_FROZEN = "ELIGIBILITY_FROZEN"

#: Persisted Stage-B artifact name under ``<confirmatory_root>/<design_id>/``.
ELIGIBILITY_MANIFEST_FILENAME = "eligibility_manifest.json"

#: The four frozen eligibility predicates, in design decision §9's order (§7.2).
#: ``predicates`` is a *semantic* array: this order is storage order and
#: disposition precedence, never assessment chronology (§7.4).
PREDICATE_IDS: tuple[str, ...] = (
    "POSITION_STATE_ISOLATION",
    "INFRASTRUCTURE_SYMMETRY",
    "TOTAL_OBSERVATION",
    "RUNTIME_CONFIGURATION_FROZEN",
)

#: Index of ``INFRASTRUCTURE_SYMMETRY``, whose status is derived from the audit
#: channels (§10.4) and whose predicate-level evidence is always empty (§9.5).
_SYMMETRY_INDEX = 1

_STATUS_PASS = "PASS"
_STATUS_FAIL = "FAIL"
_STATUS_UNASSESSED = "UNASSESSED"

#: Exactly three status tokens (§7.3).  There is no fourth, no ``null``, and an
#: absent ``status`` encodes nothing — it is malformed.
PREDICATE_STATUSES: tuple[str, ...] = (
    _STATUS_PASS,
    _STATUS_FAIL,
    _STATUS_UNASSESSED,
)

_DISPOSITION_ELIGIBLE = "CONFIRMATORY_ELIGIBLE"
_DISPOSITION_UNASSESSED = "DESCRIPTIVE_ONLY_UNASSESSED"

#: The earliest-failing predicate's reason, positionally aligned with
#: :data:`PREDICATE_IDS` (§8.2 step 1).
_FAILURE_DISPOSITIONS: tuple[str, ...] = (
    "DESCRIPTIVE_ONLY_STATE_NOT_ISOLATED",
    "DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY",
    "DESCRIPTIVE_ONLY_OBSERVABILITY_NOT_TOTAL",
    "DESCRIPTIVE_ONLY_RUNTIME_NOT_FROZEN",
)

#: Exactly six disposition tokens, quoted verbatim from design decision §9 (§8.1).
DISPOSITIONS: tuple[str, ...] = (
    _DISPOSITION_ELIGIBLE,
    *_FAILURE_DISPOSITIONS,
    _DISPOSITION_UNASSESSED,
)

#: An assignment/randomization-layer failure token (implementation design §11),
#: **not** an eligibility disposition.  Named here so its rejection is explicit
#: rather than an incidental consequence of a membership test (§8.1, E19).
_NON_ELIGIBILITY_DISPOSITION = "DESCRIPTIVE_ONLY_NO_CONFIRMATORY_RANDOMIZATION"

#: The four §5.F candidate leak paths, tokens minted by clarification §10.2.
#: ``channels`` is a *semantic* array carrying exactly these, positionally.
CHANNEL_IDS: tuple[str, ...] = (
    "PROMPT_SYSTEM_MESSAGE_CONTENT",
    "GATEWAY_PATH_LATENCY_SIGNATURE",
    "EVIDENCE_VOLUME",
    "PROVIDER_MODEL_SELECTION",
)

_CHECK_STATUS_CHECKED = "CHECKED"
_CHECK_STATUS_NOT_CHECKED = "NOT_CHECKED"

#: Implementation design §5.F's own two tokens, kept verbatim in their own field.
CHECK_STATUSES: tuple[str, ...] = (
    _CHECK_STATUS_CHECKED,
    _CHECK_STATUS_NOT_CHECKED,
)

_SYMMETRY_NO_ASYMMETRY_FOUND = "NO_ASYMMETRY_FOUND"
_SYMMETRY_ASYMMETRY_FOUND = "ASYMMETRY_FOUND"
_SYMMETRY_NOT_ASSESSED = "SYMMETRY_NOT_ASSESSED"

#: The separate field supplying §5.F's checked-and-no-asymmetry versus
#: checked-and-asymmetry-found distinction (§10.3).  ``SYMMETRY_NOT_ASSESSED`` is
#: deliberately spelled differently from the predicate status ``UNASSESSED`` so
#: every token identifies its own field unambiguously.
SYMMETRY_RESULTS: tuple[str, ...] = (
    _SYMMETRY_NO_ASYMMETRY_FOUND,
    _SYMMETRY_ASYMMETRY_FOUND,
    _SYMMETRY_NOT_ASSESSED,
)

_EVIDENCE_REPOSITORY_PATH = "REPOSITORY_PATH"
_EVIDENCE_DESIGN_ARTIFACT_FIELD = "DESIGN_ARTIFACT_FIELD"
_EVIDENCE_EXTERNAL_ATTESTATION = "EXTERNAL_ATTESTATION"

#: Exactly three evidence kinds, each with one locator grammar (§9.2).
EVIDENCE_KINDS: tuple[str, ...] = (
    _EVIDENCE_REPOSITORY_PATH,
    _EVIDENCE_DESIGN_ARTIFACT_FIELD,
    _EVIDENCE_EXTERNAL_ATTESTATION,
)

#: Repository-relative POSIX path: no leading ``/``, no backslash, no empty
#: segment.  ``.`` and ``..`` segments match this character class and are
#: rejected separately (§9.2).
_REPOSITORY_PATH_PATTERN = re.compile(r"^(?:[A-Za-z0-9._-]+/)*[A-Za-z0-9._-]+$")

#: ``registration_draft.json`` is the **only** admissible artifact filename: at
#: Stage B it is the only artifact of the chain that exists besides the manifest
#: being written.  The fragment is an RFC 6901 pointer of at least one segment.
_DESIGN_ARTIFACT_FIELD_PATTERN = re.compile(r"^registration_draft\.json#(?:/[^/]*)+$")

#: Absolute HTTPS URL only; ``http://`` is not an admissible attestation locator.
_EXTERNAL_ATTESTATION_PATTERN = re.compile(r"^https://[^\s]+$")

#: Path segments that are directory navigation rather than content (§9.2).
_FORBIDDEN_PATH_SEGMENTS = frozenset({".", ".."})

#: The exact eight top-level keys of ``eligibility_manifest.json`` (§4.3).  A
#: ninth key or a missing key is malformed, which is also what structurally
#: forbids ``assessed_at`` and the same-object ``eligibility_manifest_digest``
#: alias from ever loading (§4.5, §5).
_MANIFEST_KEYS: frozenset[str] = frozenset(
    {
        "confirmatory_profile",
        "created_at",
        "design_id",
        "eligibility_records",
        "registration_draft_digest",
        "registration_state",
        "schema_version",
        SELF_DIGEST_FIELD,
    }
)

#: The exact six keys of ``EligibilityStratumRecordV1`` (§6.1).  Per §3 C2 the
#: record carries no ``schema_version``: the manifest's single top-level one
#: versions every nested shape.
_STRATUM_RECORD_KEYS: frozenset[str] = frozenset(
    {
        "disposition",
        "infrastructure_symmetry_audit",
        "model",
        "predicates",
        "provider",
        "runtime_identity_digest",
    }
)

#: The exact three keys of ``EligibilityPredicateRecordV1`` (§7.2).
_PREDICATE_RECORD_KEYS: frozenset[str] = frozenset(
    {"evidence_refs", "predicate_id", "status"}
)

#: The exact three keys of ``EvidenceReferenceV1`` (§9.1).  There is no ``note``,
#: ``summary``, or ``author``: every field of this record is checkable offline.
_EVIDENCE_KEYS: frozenset[str] = frozenset({"content_digest", "evidence_kind", "locator"})

#: ``infrastructure_symmetry_audit`` is an object with exactly one key (§10.1).
_AUDIT_KEYS: frozenset[str] = frozenset({"channels"})

#: The exact four keys of ``InfrastructureSymmetryChannelV1`` (§10.3).
_CHANNEL_KEYS: frozenset[str] = frozenset(
    {"channel_id", "check_status", "evidence_refs", "symmetry_result"}
)

#: No JSON object key at any depth may be one of these (§14.3, E21).  This is a
#: **key-name** prohibition, not a raw-substring search, so it is exactly
#: checkable and cannot false-positive on a legitimate ``locator`` string that
#: happens to contain one of these words.
FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset(
    {
        # retired timestamp (§5) and same-object digest alias (§4.5)
        "assessed_at",
        "eligibility_manifest_digest",
        # not part of this schema (§9.4)
        "isolation_evidence",
        # Stage C only (F7)
        "position_id",
        # assignment material
        "b_k",
        "baseline_label",
        "bits",
        "qa_mode",
        "task_assignment_bit",
        # execution rows (§11)
        "failure_class",
        "observation_status",
        # downstream artifacts
        "assignment_digest",
        "final_registration_digest",
        "matrix_digest",
        "randomization_mc_provenance_digest",
        # Stage-C derivations (§4.6)
        "confirmatory_strata",
        "descriptive_only_strata",
        "descriptive_positions",
    }
)


# ---------------------------------------------------------------------------
# Work Unit 1 reuse boundary
# ---------------------------------------------------------------------------

_P = ParamSpec("_P")
_R = TypeVar("_R")


def _reuse(call: Callable[_P, _R], *args: _P.args, **kwargs: _P.kwargs) -> _R:
    """Run a Work Unit 1 helper, restating its failure as an eligibility failure.

    The frozen contract raises exactly one exception class from this module's
    surface (§14).  Reusing the committed helpers rather than reimplementing them
    keeps a single copy of every frozen grammar; this adapter is the whole cost
    of that reuse.
    """

    try:
        return call(*args, **kwargs)
    except ConfirmatoryRegistrationError as error:
        raise ConfirmatoryEligibilityError(str(error)) from error


def _require_member(value: Any, vocabulary: tuple[str, ...], context: str) -> str:
    """Reject anything outside a closed frozen vocabulary."""

    if not isinstance(value, str) or value not in vocabulary:
        raise ConfirmatoryEligibilityError(
            f"{context} must be one of {list(vocabulary)}, got {value!r}"
        )
    return value


# ---------------------------------------------------------------------------
# Shared field-level rules
#
# Each rule below has exactly one implementation, called from two places: the
# ordered raw-artifact validators of §14, and the frozen dataclasses'
# ``__post_init__``.  The dataclasses therefore cannot disagree with the loader,
# and the loader does not depend on them to realize E1-E21.
# ---------------------------------------------------------------------------


def _check_evidence_reference(
    evidence_kind: Any, locator: Any, content_digest: Any, context: str
) -> None:
    """§9.1, §9.2 — one evidence reference's kind, locator grammar, and digest.

    **No locator is dereferenced.**  Nothing here opens a file, fetches a URL, or
    recomputes anything from remote bytes, so Stage-B validation stays
    deterministic and offline forever, including after an external URL has
    rotted.
    """

    _require_member(evidence_kind, EVIDENCE_KINDS, f"{context}.evidence_kind")
    if not isinstance(locator, str) or not locator:
        raise ConfirmatoryEligibilityError(
            f"{context}.locator must be a non-empty string, got {locator!r}"
        )
    if evidence_kind == _EVIDENCE_REPOSITORY_PATH:
        if not _REPOSITORY_PATH_PATTERN.fullmatch(locator) or any(
            segment in _FORBIDDEN_PATH_SEGMENTS for segment in locator.split("/")
        ):
            raise ConfirmatoryEligibilityError(
                f"{context}: REPOSITORY_PATH locator must be a repository-relative "
                "POSIX path with no leading '/', no backslash, no empty segment, "
                f"and no '.' or '..' segment, got {locator!r}"
            )
    elif evidence_kind == _EVIDENCE_DESIGN_ARTIFACT_FIELD:
        if not _DESIGN_ARTIFACT_FIELD_PATTERN.fullmatch(locator):
            raise ConfirmatoryEligibilityError(
                f"{context}: DESIGN_ARTIFACT_FIELD locator must be "
                "'registration_draft.json#<RFC 6901 pointer>' with at least one "
                "pointer segment — no downstream artifact exists at Stage B — got "
                f"{locator!r}"
            )
    elif not _EXTERNAL_ATTESTATION_PATTERN.fullmatch(locator):
        raise ConfirmatoryEligibilityError(
            f"{context}: EXTERNAL_ATTESTATION locator must be an absolute HTTPS "
            f"URL, got {locator!r}"
        )
    _reuse(_require_digest, content_digest, f"{context}.content_digest")


def _check_evidence_order(keys: Sequence[tuple[str, str, str]], context: str) -> None:
    """§9.3 — sorted ascending by the frozen tuple, and unique on it.

    Out-of-order or duplicated entries are refused, never re-sorted or
    deduplicated on the caller's behalf.
    """

    items = list(keys)
    if len(set(items)) != len(items):
        raise ConfirmatoryEligibilityError(
            f"{context} must not contain a duplicate "
            "(evidence_kind, locator, content_digest)"
        )
    if items != sorted(items):
        raise ConfirmatoryEligibilityError(
            f"{context} must be sorted ascending by "
            "(evidence_kind, locator, content_digest); it is not re-sorted on your "
            "behalf"
        )


def _check_predicate_evidence_cardinality(
    predicate_id: str, status: str, count: int, context: str
) -> None:
    """§9.3, §9.5 — the evidence cardinality the accompanying status fixes.

    A recorded ``PASS``/``FAIL`` with no evidence is an unsupported assertion, and
    a recorded ``UNASSESSED`` carrying evidence contradicts its own status.
    ``INFRASTRUCTURE_SYMMETRY`` is the one exception: its evidence lives
    exclusively on the audit channels, so its predicate-level array is always
    exactly empty, in every status.
    """

    if predicate_id == PREDICATE_IDS[_SYMMETRY_INDEX]:
        if count:
            raise ConfirmatoryEligibilityError(
                f"{context} must be exactly [] in every status: "
                "INFRASTRUCTURE_SYMMETRY evidence lives exclusively on "
                "infrastructure_symmetry_audit.channels[*].evidence_refs"
            )
        return
    if status == _STATUS_UNASSESSED:
        if count:
            raise ConfirmatoryEligibilityError(
                f"{context} must be exactly [] when status is UNASSESSED; evidence "
                "contradicts the recorded status"
            )
        return
    if not count:
        raise ConfirmatoryEligibilityError(
            f"{context} must carry at least one reference when status is {status}; a "
            "recorded result with no evidence is an unsupported assertion"
        )


def _check_channel_coherence(
    channel_id: str, check_status: str, symmetry_result: str, count: int, context: str
) -> None:
    """§10.3 — the channel coherence rule, refused rather than repaired.

    A ``CHECKED`` channel carrying ``SYMMETRY_NOT_ASSESSED`` is a checked channel
    without a result, and a ``NOT_CHECKED`` channel claiming a result contradicts
    itself.  There is no ``null`` and no absent field in either direction.
    """

    if check_status == _CHECK_STATUS_CHECKED:
        if symmetry_result == _SYMMETRY_NOT_ASSESSED:
            raise ConfirmatoryEligibilityError(
                f"{context}: channel {channel_id} is CHECKED and must carry "
                f"{_SYMMETRY_NO_ASYMMETRY_FOUND!r} or {_SYMMETRY_ASYMMETRY_FOUND!r}, "
                f"not {_SYMMETRY_NOT_ASSESSED!r}"
            )
        if not count:
            raise ConfirmatoryEligibilityError(
                f"{context}.evidence_refs must carry at least one reference when the "
                "channel is CHECKED"
            )
        return
    if symmetry_result != _SYMMETRY_NOT_ASSESSED:
        raise ConfirmatoryEligibilityError(
            f"{context}: channel {channel_id} is NOT_CHECKED and must carry "
            f"{_SYMMETRY_NOT_ASSESSED!r}, got {symmetry_result!r}"
        )
    if count:
        raise ConfirmatoryEligibilityError(
            f"{context}.evidence_refs must be exactly [] when the channel is "
            "NOT_CHECKED"
        )


def _derived_symmetry_status(
    check_statuses: Sequence[str], symmetry_results: Sequence[str]
) -> str:
    """§10.4 — ``predicates[1].status`` as an exact function of the four channels.

    Any ``ASYMMETRY_FOUND`` is ``FAIL``, unconditionally on the other channels'
    ``check_status`` — an audit that found an asymmetry need not complete the
    remaining channels.  Otherwise ``PASS`` requires **every** channel
    ``CHECKED``, which is §5.F's frozen PASS condition verbatim; a partially
    audited stratum that has found nothing wrong yet is ``UNASSESSED``, never
    ``PASS``, and so can never reach ``CONFIRMATORY_ELIGIBLE``.
    """

    if any(result == _SYMMETRY_ASYMMETRY_FOUND for result in symmetry_results):
        return _STATUS_FAIL
    if all(status == _CHECK_STATUS_CHECKED for status in check_statuses):
        return _STATUS_PASS
    return _STATUS_UNASSESSED


def _require_disposition(value: Any, context: str) -> str:
    """§8.1 — exactly the six frozen eligibility tokens."""

    if value == _NON_ELIGIBILITY_DISPOSITION:
        raise ConfirmatoryEligibilityError(
            f"{context} must not be {_NON_ELIGIBILITY_DISPOSITION!r}: that is an "
            "assignment/randomization-layer token, not one of the six eligibility "
            "dispositions"
        )
    return _require_member(value, DISPOSITIONS, context)


def derive_disposition(statuses: Sequence[str]) -> str:
    """The exact, total §8.2 derivation from four recorded statuses to one token.

    Three mutually exclusive, jointly exhaustive steps over all 81 combinations:

    1. some predicate is ``FAIL`` — the **earliest** such predicate in the frozen
       order supplies the reason;
    2. no ``FAIL`` but some ``UNASSESSED`` — ``DESCRIPTIVE_ONLY_UNASSESSED``;
    3. otherwise all four ``PASS`` — ``CONFIRMATORY_ELIGIBLE``.

    ``FAIL`` outranks ``UNASSESSED`` at every position: a *discovered* defect is
    never buried behind an *un-looked-at* one, so ``UNASSESSED FAIL UNASSESSED
    UNASSESSED`` yields ``DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY``.  "Earliest" ranges
    over failing predicates only; unassessed positions consume no precedence.

    Every combination receives exactly one disposition — never zero, never two.
    """

    values = tuple(statuses)
    if len(values) != len(PREDICATE_IDS):
        raise ConfirmatoryEligibilityError(
            f"disposition derivation needs exactly {len(PREDICATE_IDS)} predicate "
            f"statuses, got {len(values)}"
        )
    for index, status in enumerate(values):
        _require_member(status, PREDICATE_STATUSES, f"predicates[{index}].status")
    for index, status in enumerate(values):
        if status == _STATUS_FAIL:
            return _FAILURE_DISPOSITIONS[index]
    if _STATUS_UNASSESSED in values:
        return _DISPOSITION_UNASSESSED
    return _DISPOSITION_ELIGIBLE


# ---------------------------------------------------------------------------
# The frozen record types (§6, §7, §9, §10)
#
# These are the in-memory representation.  They validate through the shared
# rules above so a directly constructed object cannot be weaker than a loaded
# one, but the §14 loader never depends on them: see :func:`_validate_tier_one`.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EvidenceReferenceV1:
    """One structured evidence reference: three keys, no more, no fewer (§9.1).

    Evidence references are never bare strings — a bare string would leave "what
    kind of thing is this" open, which is exactly the class of open choice the
    frozen schema exists to remove.

    The ``DESIGN_ARTIFACT_FIELD`` rule that ``content_digest`` equals the bound
    draft digest is a *manifest-level* cross-check: it needs the manifest's
    ``registration_draft_digest`` and lives in E14.
    """

    evidence_kind: str
    locator: str
    content_digest: str

    def __post_init__(self) -> None:
        _check_evidence_reference(
            self.evidence_kind, self.locator, self.content_digest, "evidence_refs[]"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "content_digest": self.content_digest,
            "evidence_kind": self.evidence_kind,
            "locator": self.locator,
        }

    @property
    def sort_key(self) -> tuple[str, str, str]:
        """The frozen ``(evidence_kind, locator, content_digest)`` ordering key."""

        return (self.evidence_kind, self.locator, self.content_digest)


def _require_evidence_array(value: Any, context: str) -> tuple[EvidenceReferenceV1, ...]:
    """Reject an evidence array that is not a sorted, unique tuple of records.

    ``evidence_refs`` is always present and always an array — never ``null``,
    never absent (§9.3).
    """

    if not isinstance(value, tuple):
        raise ConfirmatoryEligibilityError(f"{context} must be a tuple")
    for index, item in enumerate(value):
        if not isinstance(item, EvidenceReferenceV1):
            raise ConfirmatoryEligibilityError(
                f"{context}[{index}] must be an EvidenceReferenceV1"
            )
    refs: tuple[EvidenceReferenceV1, ...] = value
    _check_evidence_order([item.sort_key for item in refs], context)
    return refs


@dataclass(frozen=True, slots=True)
class EligibilityPredicateRecordV1:
    """One predicate's recorded state: three keys, no more, no fewer (§7.2).

    The four statuses of a stratum are **mutually unconstrained**: all
    ``3**4 = 81`` combinations are admissible records (§7.4).  A recorded ``FAIL``
    does not terminate the record, multiple ``FAIL`` values are legal, and a
    ``PASS`` or ``FAIL`` may follow either.  Nothing in this class, and nothing
    anywhere in this module, rejects a record for its status combination (E12) —
    the single-disposition guarantee is supplied by :func:`derive_disposition`
    instead.

    ``TOTAL_OBSERVATION`` at index 2 is an ordinary record like the others: its
    status is the **prospective** observability argument, and no realized
    endpoint, row count, or failure class exists at Stage B to inspect (§11).
    """

    predicate_id: str
    status: str
    evidence_refs: tuple[EvidenceReferenceV1, ...] = ()

    def __post_init__(self) -> None:
        _require_member(self.predicate_id, PREDICATE_IDS, "predicates[].predicate_id")
        _require_member(self.status, PREDICATE_STATUSES, "predicates[].status")
        context = f"predicates[{self.predicate_id}].evidence_refs"
        refs = _require_evidence_array(self.evidence_refs, context)
        _check_predicate_evidence_cardinality(
            self.predicate_id, self.status, len(refs), context
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_refs": [ref.to_dict() for ref in self.evidence_refs],
            "predicate_id": self.predicate_id,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class InfrastructureSymmetryChannelV1:
    """One audited leak path: four keys, no more, no fewer (§10.3).

    ``check_status`` keeps implementation design §5.F's own ``CHECKED``/
    ``NOT_CHECKED`` vocabulary literally, in its own field; ``symmetry_result`` is
    the separate field supplying the checked-and-no-asymmetry versus
    checked-and-asymmetry-found distinction §5.F requires but never named.
    """

    channel_id: str
    check_status: str
    symmetry_result: str
    evidence_refs: tuple[EvidenceReferenceV1, ...] = ()

    def __post_init__(self) -> None:
        _require_member(self.channel_id, CHANNEL_IDS, "channels[].channel_id")
        _require_member(self.check_status, CHECK_STATUSES, "channels[].check_status")
        _require_member(
            self.symmetry_result, SYMMETRY_RESULTS, "channels[].symmetry_result"
        )
        context = f"channels[{self.channel_id}]"
        refs = _require_evidence_array(self.evidence_refs, f"{context}.evidence_refs")
        _check_channel_coherence(
            self.channel_id, self.check_status, self.symmetry_result, len(refs), context
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "check_status": self.check_status,
            "evidence_refs": [ref.to_dict() for ref in self.evidence_refs],
            "symmetry_result": self.symmetry_result,
        }


@dataclass(frozen=True, slots=True)
class InfrastructureSymmetryAuditV1:
    """The one-key audit record over exactly four positional channels (§10.1, §10.2).

    It stays an object rather than a bare array because §5.F freezes it as an
    ``infrastructure_symmetry_audit`` *record*.  Per §3 C2 it carries no
    ``schema_version``.  No channel may be absent, duplicated, reordered, or
    unknown, and there is no fifth channel: §5.F froze the candidate set at
    exactly these four.
    """

    channels: tuple[InfrastructureSymmetryChannelV1, ...]

    def __post_init__(self) -> None:
        channels = self.channels
        if not isinstance(channels, tuple):
            raise ConfirmatoryEligibilityError(
                "infrastructure_symmetry_audit.channels must be a tuple"
            )
        if len(channels) != len(CHANNEL_IDS):
            raise ConfirmatoryEligibilityError(
                "infrastructure_symmetry_audit.channels must hold exactly "
                f"{len(CHANNEL_IDS)} channels, got {len(channels)}"
            )
        for index, channel in enumerate(channels):
            if not isinstance(channel, InfrastructureSymmetryChannelV1):
                raise ConfirmatoryEligibilityError(
                    f"infrastructure_symmetry_audit.channels[{index}] must be an "
                    "InfrastructureSymmetryChannelV1"
                )
            if channel.channel_id != CHANNEL_IDS[index]:
                raise ConfirmatoryEligibilityError(
                    f"infrastructure_symmetry_audit.channels[{index}].channel_id "
                    f"must be {CHANNEL_IDS[index]!r}, got {channel.channel_id!r}; the "
                    "array is positional and is not re-sorted on your behalf"
                )

    def to_dict(self) -> dict[str, Any]:
        return {"channels": [channel.to_dict() for channel in self.channels]}


def derive_infrastructure_symmetry_status(audit: InfrastructureSymmetryAuditV1) -> str:
    """``predicates[1].status`` derived from a typed audit record (§10.4)."""

    if not isinstance(audit, InfrastructureSymmetryAuditV1):
        raise ConfirmatoryEligibilityError(
            "infrastructure_symmetry_audit must be an InfrastructureSymmetryAuditV1"
        )
    return _derived_symmetry_status(
        [channel.check_status for channel in audit.channels],
        [channel.symmetry_result for channel in audit.channels],
    )


@dataclass(frozen=True, slots=True)
class EligibilityStratumRecordV1:
    """One proposed stratum's eligibility record: six keys, no more, no fewer (§6.1).

    The stratum is identified by exactly ``provider`` and ``model``, the Stage-A
    vocabulary unchanged: no composite ``stratum_id`` is minted and no digest of
    the pair is introduced (§6.2).

    ``runtime_identity_digest`` is **copied verbatim** from the bound draft's
    registration-expected snapshot for this stratum.  It is never recomputed,
    never recaptured, and no ``RuntimeSnapshotV1`` is constructed here (§13.1,
    §13.2); the copy equality itself is E25, checked against the draft.

    ``disposition`` is derived rather than accepted here, and the loader
    separately cross-checks the *persisted* token against the same derivation at
    E19 (§8.3) — recording a derivation so a mismatch is detectable, never
    trusting it.  ``predicates[1].status`` is likewise both recorded and
    recomputed (§10.4, E17).
    """

    provider: str
    model: str
    predicates: tuple[EligibilityPredicateRecordV1, ...]
    infrastructure_symmetry_audit: InfrastructureSymmetryAuditV1
    runtime_identity_digest: str
    disposition: str = field(init=False)

    def __post_init__(self) -> None:
        _reuse(_require_nonempty_text, self.provider, "eligibility_records[].provider")
        _reuse(_require_nonempty_text, self.model, "eligibility_records[].model")
        predicates = self.predicates
        if not isinstance(predicates, tuple):
            raise ConfirmatoryEligibilityError(
                "eligibility_records[].predicates must be a tuple"
            )
        if len(predicates) != len(PREDICATE_IDS):
            raise ConfirmatoryEligibilityError(
                "eligibility_records[].predicates must hold exactly "
                f"{len(PREDICATE_IDS)} records, got {len(predicates)}"
            )
        for index, predicate in enumerate(predicates):
            if not isinstance(predicate, EligibilityPredicateRecordV1):
                raise ConfirmatoryEligibilityError(
                    f"predicates[{index}] must be an EligibilityPredicateRecordV1"
                )
            if predicate.predicate_id != PREDICATE_IDS[index]:
                raise ConfirmatoryEligibilityError(
                    f"predicates[{index}].predicate_id must be "
                    f"{PREDICATE_IDS[index]!r}, got {predicate.predicate_id!r}; the "
                    "array is positional and is not re-sorted on your behalf"
                )
        derived_symmetry = derive_infrastructure_symmetry_status(
            self.infrastructure_symmetry_audit
        )
        recorded_symmetry = predicates[_SYMMETRY_INDEX].status
        if recorded_symmetry != derived_symmetry:
            raise ConfirmatoryEligibilityError(
                f"predicates[{_SYMMETRY_INDEX}].status is {recorded_symmetry!r} but "
                f"infrastructure_symmetry_audit.channels derive {derived_symmetry!r}"
            )
        _reuse(
            _require_digest,
            self.runtime_identity_digest,
            "eligibility_records[].runtime_identity_digest",
        )
        object.__setattr__(
            self,
            "disposition",
            derive_disposition([predicate.status for predicate in predicates]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "disposition": self.disposition,
            "infrastructure_symmetry_audit": (
                self.infrastructure_symmetry_audit.to_dict()
            ),
            "model": self.model,
            "predicates": [predicate.to_dict() for predicate in self.predicates],
            "provider": self.provider,
            "runtime_identity_digest": self.runtime_identity_digest,
        }

    @property
    def identity(self) -> tuple[str, str]:
        """The ``(provider, model)`` ordering and join key (§6.2, §6.3)."""

        return (self.provider, self.model)


@dataclass(frozen=True, slots=True)
class EligibilityManifestV1:
    """The Stage-B ``ELIGIBILITY_FROZEN`` artifact: exactly eight keys (§4.3).

    Construct through :func:`freeze_eligibility`, which validates the assessment
    against the bound draft and seals it with a ``self_digest``.  The record
    stores exactly one digest of itself and never an
    ``eligibility_manifest_digest`` alias — that name is what *downstream*
    artifacts call this object's ``self_digest`` (§4.5).

    There is exactly one timestamp, ``created_at``: the instant the assessment was
    finalized and sealed.  Because the manifest is written once and can never be
    edited or re-assessed in place, there is exactly one such instant per
    manifest, and it answers "when was this stratum assessed" for every stratum in
    it.  ``assessed_at`` is retired and is not a field at any depth (§5).
    """

    schema_version: str
    registration_state: str
    confirmatory_profile: str
    design_id: str
    created_at: str
    registration_draft_digest: str
    eligibility_records: tuple[EligibilityStratumRecordV1, ...]
    self_digest: str

    def canonical_payload(self) -> dict[str, Any]:
        """The digest input: the whole artifact except its own ``self_digest``.

        ``eligibility_records`` preserves registered order; canonicalization never
        reorders or deduplicates an array.  The sorting and uniqueness rules of
        §6.3 and §9.3 are schema-level preconditions enforced before
        canonicalization, never canonicalization-time transformations (§16).
        """

        return {
            "confirmatory_profile": self.confirmatory_profile,
            "created_at": self.created_at,
            "design_id": self.design_id,
            "eligibility_records": [
                record.to_dict() for record in self.eligibility_records
            ],
            "registration_draft_digest": self.registration_draft_digest,
            "registration_state": self.registration_state,
            "schema_version": self.schema_version,
        }

    def to_artifact(self) -> dict[str, Any]:
        """The full persisted object: the canonical payload plus ``self_digest``."""

        artifact = self.canonical_payload()
        artifact[SELF_DIGEST_FIELD] = self.self_digest
        return artifact


# ---------------------------------------------------------------------------
# §14 Tier 1 — E1 through E21, in numbered order, over the RAW artifact
#
# Each rule is its own function so the order is mechanically obvious and so no
# later-numbered rule can execute before an earlier one has completed.  Nothing
# in this section constructs a frozen dataclass: ``__post_init__`` ordering must
# not be able to decide which rule a malformed artifact fails.
# ---------------------------------------------------------------------------


def _validate_e1(artifact: dict[str, Any]) -> None:
    """E1 — exactly the eight top-level keys of §4.3, no missing, no extra."""

    _reuse(_require_exact_keys, artifact, _MANIFEST_KEYS, ELIGIBILITY_MANIFEST_FILENAME)


def _validate_e2(artifact: dict[str, Any]) -> None:
    """E2 — ``schema_version`` equals the frozen literal."""

    _reuse(
        _require_literal, artifact, "schema_version", ELIGIBILITY_MANIFEST_SCHEMA_VERSION
    )


def _validate_e3(artifact: dict[str, Any]) -> None:
    """E3 — ``registration_state`` equals ``ELIGIBILITY_FROZEN``."""

    _reuse(
        _require_literal,
        artifact,
        "registration_state",
        REGISTRATION_STATE_ELIGIBILITY_FROZEN,
    )


def _validate_e4(artifact: dict[str, Any]) -> None:
    """E4 — ``confirmatory_profile`` equals the frozen profile."""

    _reuse(_require_literal, artifact, "confirmatory_profile", CONFIRMATORY_PROFILE)


def _validate_e5(artifact: dict[str, Any]) -> None:
    """E5 — non-empty ``design_id``, under the Work Unit 1 path discipline."""

    _reuse(_require_design_id, _reuse(_require_text_field, artifact, "design_id"))


def _validate_e6(artifact: dict[str, Any]) -> None:
    """E6 — the one frozen ``created_at`` grammar; never converted or truncated."""

    _reuse(_require_created_at_text, _reuse(_require_text_field, artifact, "created_at"))


def _validate_e7(artifact: dict[str, Any]) -> None:
    """E7 — ``registration_draft_digest`` is lowercase 64-character hexadecimal."""

    _reuse(
        _require_digest,
        artifact["registration_draft_digest"],
        "registration_draft_digest",
    )


def _validate_e8(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    """E8 — a non-empty array whose elements are exactly-six-key record objects."""

    raw = _reuse(_require_array_field, artifact, "eligibility_records")
    if not raw:
        raise ConfirmatoryEligibilityError("eligibility_records must not be empty")
    records: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        context = f"eligibility_records[{index}]"
        mapping = _reuse(_require_object, item, context)
        _reuse(_require_exact_keys, mapping, _STRATUM_RECORD_KEYS, context)
        records.append(mapping)
    return records


def _validate_e9(records: list[dict[str, Any]]) -> None:
    """E9 — non-empty ``provider``/``model``, sorted ascending on the pair, unique."""

    identities: list[tuple[str, str]] = []
    for index, record in enumerate(records):
        context = f"eligibility_records[{index}]"
        identities.append(
            (
                _reuse(_require_text_field, record, "provider", context),
                _reuse(_require_text_field, record, "model", context),
            )
        )
    _reuse(_require_sorted_unique, identities, "eligibility_records")


def _validate_e10(records: list[dict[str, Any]]) -> None:
    """E10 — exactly four predicate objects carrying the frozen ids, positionally."""

    for index, record in enumerate(records):
        context = f"eligibility_records[{index}]"
        predicates = _reuse(_require_array_field, record, "predicates", context)
        if len(predicates) != len(PREDICATE_IDS):
            raise ConfirmatoryEligibilityError(
                f"{context}.predicates must hold exactly {len(PREDICATE_IDS)} records, "
                f"got {len(predicates)}"
            )
        for position, item in enumerate(predicates):
            predicate_context = f"{context}.predicates[{position}]"
            mapping = _reuse(_require_object, item, predicate_context)
            claimed = mapping.get("predicate_id")
            if claimed != PREDICATE_IDS[position]:
                raise ConfirmatoryEligibilityError(
                    f"{predicate_context}.predicate_id must be "
                    f"{PREDICATE_IDS[position]!r}, got {claimed!r}; predicates is a "
                    "positional semantic array in the frozen order and is not "
                    "re-sorted on your behalf"
                )


def _validate_e11(records: list[dict[str, Any]]) -> None:
    """E11 — exactly the three predicate keys, and a ``status`` in the vocabulary."""

    for index, record in enumerate(records):
        for position, mapping in enumerate(record["predicates"]):
            context = f"eligibility_records[{index}].predicates[{position}]"
            _reuse(_require_exact_keys, mapping, _PREDICATE_RECORD_KEYS, context)
            _require_member(
                mapping["status"], PREDICATE_STATUSES, f"{context}.status"
            )


def _validate_e12(records: list[dict[str, Any]]) -> None:
    """E12 — a status combination is **never** itself a rejection ground (§7.4).

    This is the one rule in the frozen contract that *forbids* a rejection rather
    than requiring one, so it deliberately raises nothing.  It is written,
    numbered, and called in sequence so the ordering is mechanically auditable and
    so no later reader mistakes the absence of a check for an oversight.

    After E11 every status is one of ``PASS``/``FAIL``/``UNASSESSED``, and all
    ``3**4 = 81`` combinations over the four frozen positions are admissible
    records: multiple ``FAIL`` values are legal, a ``PASS`` may follow a ``FAIL``,
    and a ``PASS`` or ``FAIL`` may follow an ``UNASSESSED``.  A loader that
    refuses ``PASS FAIL FAIL PASS`` is non-conformant.  Status legality is
    constrained only by E11, E13, E17, and E19.
    """


def _validate_e13(records: list[dict[str, Any]]) -> None:
    """E13 — the predicate evidence-attachment rule of §9.3, including §9.5."""

    for index, record in enumerate(records):
        for position, mapping in enumerate(record["predicates"]):
            context = f"eligibility_records[{index}].predicates[{position}]"
            refs = _reuse(_require_array_field, mapping, "evidence_refs", context)
            _check_predicate_evidence_cardinality(
                mapping["predicate_id"],
                mapping["status"],
                len(refs),
                f"{context}.evidence_refs",
            )


def _reachable_evidence_arrays(
    record: dict[str, Any], context: str
) -> Iterator[tuple[str, list[Any]]]:
    """Every ``evidence_refs`` array E14 can reach in one record.

    The predicate-level arrays are guaranteed arrays by E13.  The channel-level
    arrays sit inside ``infrastructure_symmetry_audit``, whose *structure* is
    E15's and E16's, so they are navigated defensively: E14 is a content rule
    over the references it can see, and an unreachable array is left for the
    later, structural rules to reject at their own numbered position.
    """

    for position, predicate in enumerate(record["predicates"]):
        yield (f"{context}.predicates[{position}].evidence_refs", predicate["evidence_refs"])
    audit = record.get("infrastructure_symmetry_audit")
    if not isinstance(audit, dict):
        return
    channels = audit.get("channels")
    if not isinstance(channels, list):
        return
    for position, channel in enumerate(channels):
        if not isinstance(channel, dict):
            continue
        refs = channel.get("evidence_refs")
        if isinstance(refs, list):
            yield (
                f"{context}.infrastructure_symmetry_audit.channels[{position}]"
                ".evidence_refs",
                refs,
            )


def _validate_e14(records: list[dict[str, Any]], registration_draft_digest: str) -> None:
    """E14 — every evidence reference's schema, grammar, digest, order, uniqueness.

    Includes the ``DESIGN_ARTIFACT_FIELD`` binding: when the registered draft
    itself *is* the evidence, the reference's ``content_digest`` is that
    artifact's ``self_digest``, which is exactly this manifest's
    ``registration_draft_digest`` (§9.2).  Nothing is opened to check it; the
    comparison is between two values the manifest already carries.
    """

    for index, record in enumerate(records):
        for context, refs in _reachable_evidence_arrays(
            record, f"eligibility_records[{index}]"
        ):
            keys: list[tuple[str, str, str]] = []
            for position, item in enumerate(refs):
                item_context = f"{context}[{position}]"
                mapping = _reuse(_require_object, item, item_context)
                _reuse(_require_exact_keys, mapping, _EVIDENCE_KEYS, item_context)
                evidence_kind = mapping["evidence_kind"]
                locator = mapping["locator"]
                content_digest = mapping["content_digest"]
                _check_evidence_reference(
                    evidence_kind, locator, content_digest, item_context
                )
                if evidence_kind == _EVIDENCE_DESIGN_ARTIFACT_FIELD and not (
                    hmac.compare_digest(content_digest, registration_draft_digest)
                ):
                    raise ConfirmatoryEligibilityError(
                        f"{item_context}: DESIGN_ARTIFACT_FIELD content_digest "
                        f"{content_digest} must equal the manifest's "
                        f"registration_draft_digest {registration_draft_digest}"
                    )
                keys.append((evidence_kind, locator, content_digest))
            _check_evidence_order(keys, context)


def _validate_e15(records: list[dict[str, Any]]) -> None:
    """E15 — the one-key audit object over exactly four positional channels."""

    for index, record in enumerate(records):
        record_context = f"eligibility_records[{index}]"
        context = f"{record_context}.infrastructure_symmetry_audit"
        audit = _reuse(
            _require_object_field,
            record,
            "infrastructure_symmetry_audit",
            record_context,
        )
        _reuse(_require_exact_keys, audit, _AUDIT_KEYS, context)
        channels = _reuse(_require_array_field, audit, "channels", context)
        if len(channels) != len(CHANNEL_IDS):
            raise ConfirmatoryEligibilityError(
                f"{context}.channels must hold exactly {len(CHANNEL_IDS)} records, got "
                f"{len(channels)}"
            )
        for position, item in enumerate(channels):
            channel_context = f"{context}.channels[{position}]"
            mapping = _reuse(_require_object, item, channel_context)
            claimed = mapping.get("channel_id")
            if claimed != CHANNEL_IDS[position]:
                raise ConfirmatoryEligibilityError(
                    f"{channel_context}.channel_id must be {CHANNEL_IDS[position]!r}, "
                    f"got {claimed!r}; channels is a positional semantic array in the "
                    "frozen §5.F order and is not re-sorted on your behalf"
                )


def _validate_e16(records: list[dict[str, Any]]) -> None:
    """E16 — exactly the four channel keys, the two vocabularies, and coherence."""

    for index, record in enumerate(records):
        channels = record["infrastructure_symmetry_audit"]["channels"]
        for position, mapping in enumerate(channels):
            context = (
                f"eligibility_records[{index}].infrastructure_symmetry_audit"
                f".channels[{position}]"
            )
            _reuse(_require_exact_keys, mapping, _CHANNEL_KEYS, context)
            check_status = _require_member(
                mapping["check_status"], CHECK_STATUSES, f"{context}.check_status"
            )
            symmetry_result = _require_member(
                mapping["symmetry_result"], SYMMETRY_RESULTS, f"{context}.symmetry_result"
            )
            refs = _reuse(_require_array_field, mapping, "evidence_refs", context)
            _check_channel_coherence(
                mapping["channel_id"], check_status, symmetry_result, len(refs), context
            )


def _validate_e17(records: list[dict[str, Any]]) -> None:
    """E17 — the recorded symmetry predicate status equals the §10.4 derivation."""

    for index, record in enumerate(records):
        channels = record["infrastructure_symmetry_audit"]["channels"]
        derived = _derived_symmetry_status(
            [channel["check_status"] for channel in channels],
            [channel["symmetry_result"] for channel in channels],
        )
        recorded = record["predicates"][_SYMMETRY_INDEX]["status"]
        if recorded != derived:
            raise ConfirmatoryEligibilityError(
                f"eligibility_records[{index}].predicates[{_SYMMETRY_INDEX}].status is "
                f"{recorded!r} but infrastructure_symmetry_audit.channels derive "
                f"{derived!r}"
            )


def _validate_e18(records: list[dict[str, Any]]) -> None:
    """E18 — ``runtime_identity_digest`` is lowercase 64-character hexadecimal."""

    for index, record in enumerate(records):
        _reuse(
            _require_digest,
            record["runtime_identity_digest"],
            f"eligibility_records[{index}].runtime_identity_digest",
        )


def _validate_e19(records: list[dict[str, Any]]) -> None:
    """E19 — the stored disposition is legal and equals the §8.2 derivation.

    The vocabulary half runs before the comparison, so an illegal token is
    reported as illegal rather than as a mismatch, and a recorded derivation is
    cross-checked rather than trusted (§8.3).
    """

    for index, record in enumerate(records):
        context = f"eligibility_records[{index}]"
        claimed = _require_disposition(record["disposition"], f"{context}.disposition")
        derived = derive_disposition(
            [predicate["status"] for predicate in record["predicates"]]
        )
        if claimed != derived:
            raise ConfirmatoryEligibilityError(
                f"{context}.disposition is {claimed!r} but the recorded predicate "
                f"statuses derive {derived!r}; a recorded derivation is cross-checked, "
                "never trusted"
            )


def _validate_e20(artifact: dict[str, Any]) -> None:
    """E20 — ``self_digest`` form and verification, through the Work Unit 1 helper.

    :func:`verify_self_digest` is §5.B.2's own procedure: recanonicalize the
    object with only ``self_digest`` removed, recompute SHA-256, compare.  This
    module never spells that computation itself.
    """

    _reuse(verify_self_digest, artifact)


def _validate_e21(artifact: dict[str, Any]) -> None:
    """E21 — no forbidden **key name** at any depth (§14.3).

    A key-name rule, never a raw-substring scan over values: an evidence
    ``locator`` that legitimately contains one of these words is not a violation.

    E1, E8, E11, E14, E15, and E16 exhaust the key set at every depth, so this
    rule is unreachable through a conforming loader — a forbidden name is caught
    earlier, at its own numbered position, by whichever exact-key rule owns that
    object.  It is implemented anyway, exactly as the frozen contract states,
    because it restates the prohibition so an auditor can check it directly and
    because it fails closed if any earlier key set is ever widened.
    """

    _require_no_forbidden_keys(artifact, ELIGIBILITY_MANIFEST_FILENAME)


def _require_no_forbidden_keys(value: Any, path: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in FORBIDDEN_KEY_NAMES:
                raise ConfirmatoryEligibilityError(
                    f"{path}.{key} is a forbidden key name in "
                    f"{ELIGIBILITY_MANIFEST_FILENAME}"
                )
            _require_no_forbidden_keys(item, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_no_forbidden_keys(item, f"{path}[{index}]")


def _validate_tier_one(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    """§14.1 — E1 through E21, in numbered order, aborting on the first failure.

    Returns the raw record objects so the Tier-2 rules and the reconstruction
    step can reuse them without re-walking the artifact.
    """

    _validate_e1(artifact)
    _validate_e2(artifact)
    _validate_e3(artifact)
    _validate_e4(artifact)
    _validate_e5(artifact)
    _validate_e6(artifact)
    _validate_e7(artifact)
    records = _validate_e8(artifact)
    _validate_e9(records)
    _validate_e10(records)
    _validate_e11(records)
    _validate_e12(records)
    _validate_e13(records)
    _validate_e14(records, artifact["registration_draft_digest"])
    _validate_e15(records)
    _validate_e16(records)
    _validate_e17(records)
    _validate_e18(records)
    _validate_e19(records)
    _validate_e20(artifact)
    _validate_e21(artifact)
    return records


# ---------------------------------------------------------------------------
# §14 Tier 2 — E22 through E26, against the bound registration draft
#
# A manifest may be *parsed* standalone but is never *accepted* without the bound
# draft, so these run only after every Tier-1 rule has passed (§14.2).
# ---------------------------------------------------------------------------


def _validate_e22(artifact: dict[str, Any], registration_draft: RegistrationDraft) -> None:
    """E22 — the bound draft's own ``self_digest`` verifies, and the binding matches.

    The draft's digest is verified with the authoritative Work Unit 1 procedure,
    not with a locally recreated hash of its canonical payload.
    """

    _reuse(verify_self_digest, registration_draft.to_artifact())
    if not hmac.compare_digest(
        artifact["registration_draft_digest"], registration_draft.self_digest
    ):
        raise ConfirmatoryEligibilityError(
            f"registration_draft_digest {artifact['registration_draft_digest']} does "
            f"not match the bound draft's {SELF_DIGEST_FIELD} "
            f"{registration_draft.self_digest}"
        )


def _validate_e23(artifact: dict[str, Any], registration_draft: RegistrationDraft) -> None:
    """E23 — ``design_id`` and ``confirmatory_profile`` agree with the draft."""

    if artifact["design_id"] != registration_draft.design_id:
        raise ConfirmatoryEligibilityError(
            f"design_id {artifact['design_id']!r} does not match the bound draft's "
            f"{registration_draft.design_id!r}"
        )
    if artifact["confirmatory_profile"] != registration_draft.confirmatory_profile:
        raise ConfirmatoryEligibilityError(
            f"confirmatory_profile {artifact['confirmatory_profile']!r} does not match "
            f"the bound draft's {registration_draft.confirmatory_profile!r}"
        )


def _validate_e24(
    records: list[dict[str, Any]], registration_draft: RegistrationDraft
) -> None:
    """E24 — an exact element-wise cover of ``proposed_strata``.

    No missing, no duplicate, no extra, no foreign stratum.  This is the single
    rule that makes implementation design §6's "refuse to finalize if any of the
    four predicates is missing a disposition for any proposed stratum" structural.
    """

    _reuse(
        _require_exact_cover,
        [(record["provider"], record["model"]) for record in records],
        [stratum.identity for stratum in registration_draft.proposed_strata],
        "eligibility_records",
        "(provider, model) of proposed_strata",
    )


def _validate_e25(
    records: list[dict[str, Any]], registration_draft: RegistrationDraft
) -> None:
    """E25 — each ``runtime_identity_digest`` is an exact copy from the draft.

    A copy mismatch is an integrity failure, not an eligibility finding: it means
    the manifest was assembled against a different runtime binding than the draft
    its own ``registration_draft_digest`` names.  The **whole manifest** is
    refused and no disposition is produced for any stratum — silently downgrading
    a corrupt chain to ``DESCRIPTIVE_ONLY_*`` would let it produce a
    usable-looking record (§13.3).
    """

    snapshots = (
        registration_draft.proposed_runtime_configuration
        .registration_expected_runtime_snapshots
    )
    if len(snapshots) != len(records):
        raise ConfirmatoryEligibilityError(
            f"the bound draft binds {len(snapshots)} registration-expected runtime "
            f"snapshots for {len(records)} eligibility records"
        )
    for index, record in enumerate(records):
        expected = snapshots[index].runtime_identity_digest
        if not hmac.compare_digest(record["runtime_identity_digest"], expected):
            raise ConfirmatoryEligibilityError(
                f"eligibility_records[{index}].runtime_identity_digest "
                f"{record['runtime_identity_digest']} is not an exact copy of the "
                f"bound draft's registration-expected {expected} for stratum "
                f"{(record['provider'], record['model'])!r}"
            )


def _validate_e26(registration_draft: RegistrationDraft) -> None:
    """E26 — the manifest is bound to a Stage-A artifact, not some other stage's."""

    if registration_draft.registration_state != REGISTRATION_STATE_DRAFT:
        raise ConfirmatoryEligibilityError(
            "the bound artifact's registration_state must be "
            f"{REGISTRATION_STATE_DRAFT!r}, got "
            f"{registration_draft.registration_state!r}"
        )


def _validate_tier_two(
    artifact: dict[str, Any],
    records: list[dict[str, Any]],
    registration_draft: RegistrationDraft,
) -> None:
    """§14.2 — E22 through E26, in numbered order, aborting on the first failure."""

    if not isinstance(registration_draft, RegistrationDraft):
        raise ConfirmatoryEligibilityError(
            "registration_draft must be a RegistrationDraft"
        )
    _validate_e22(artifact, registration_draft)
    _validate_e23(artifact, registration_draft)
    _validate_e24(records, registration_draft)
    _validate_e25(records, registration_draft)
    _validate_e26(registration_draft)


# ---------------------------------------------------------------------------
# Reconstruction — only after E1-E26 have all passed
# ---------------------------------------------------------------------------


def _evidence_from_validated(mapping: dict[str, Any]) -> EvidenceReferenceV1:
    return EvidenceReferenceV1(
        evidence_kind=mapping["evidence_kind"],
        locator=mapping["locator"],
        content_digest=mapping["content_digest"],
    )


def _record_from_validated(mapping: dict[str, Any]) -> EligibilityStratumRecordV1:
    return EligibilityStratumRecordV1(
        provider=mapping["provider"],
        model=mapping["model"],
        predicates=tuple(
            EligibilityPredicateRecordV1(
                predicate_id=predicate["predicate_id"],
                status=predicate["status"],
                evidence_refs=tuple(
                    _evidence_from_validated(ref) for ref in predicate["evidence_refs"]
                ),
            )
            for predicate in mapping["predicates"]
        ),
        infrastructure_symmetry_audit=InfrastructureSymmetryAuditV1(
            channels=tuple(
                InfrastructureSymmetryChannelV1(
                    channel_id=channel["channel_id"],
                    check_status=channel["check_status"],
                    symmetry_result=channel["symmetry_result"],
                    evidence_refs=tuple(
                        _evidence_from_validated(ref) for ref in channel["evidence_refs"]
                    ),
                )
                for channel in mapping["infrastructure_symmetry_audit"]["channels"]
            )
        ),
        runtime_identity_digest=mapping["runtime_identity_digest"],
    )


def _manifest_from_validated(
    artifact: dict[str, Any], records: list[dict[str, Any]]
) -> EligibilityManifestV1:
    """Rebuild the typed manifest from raw data that has already passed E1-E26.

    Every constructor below revalidates through the same shared rules the ordered
    passes used.  Because those passes have all succeeded, no constructor can
    raise here, so reconstruction cannot change which rule a malformed artifact
    is observed to fail.
    """

    manifest = EligibilityManifestV1(
        schema_version=ELIGIBILITY_MANIFEST_SCHEMA_VERSION,
        registration_state=REGISTRATION_STATE_ELIGIBILITY_FROZEN,
        confirmatory_profile=CONFIRMATORY_PROFILE,
        design_id=artifact["design_id"],
        created_at=artifact["created_at"],
        registration_draft_digest=artifact["registration_draft_digest"],
        eligibility_records=tuple(_record_from_validated(record) for record in records),
        self_digest=artifact[SELF_DIGEST_FIELD],
    )
    # A reconstruction guard, deliberately after the whole numbered contract so
    # it can never preempt a rule: the rebuilt record must reproduce the
    # persisted digest, or the typed object does not faithfully represent the
    # bytes it came from.  The digest itself is Work Unit 1's helper.
    if not hmac.compare_digest(
        compute_self_digest(manifest.canonical_payload()), manifest.self_digest
    ):
        raise ConfirmatoryEligibilityError(
            "rebuilt eligibility manifest does not reproduce the persisted "
            f"{SELF_DIGEST_FIELD}"
        )
    return manifest


# ---------------------------------------------------------------------------
# Stage-B construction boundary (§5.A Stage B)
# ---------------------------------------------------------------------------


def freeze_eligibility(
    *,
    registration_draft: RegistrationDraft,
    created_at: datetime,
    eligibility_records: Sequence[EligibilityStratumRecordV1],
) -> EligibilityManifestV1:
    """Build and seal a Stage-B eligibility manifest against a bound draft.

    ``schema_version``, ``registration_state``, and ``confirmatory_profile`` are
    taken from this module's frozen literals rather than from a caller, and
    ``design_id`` and ``registration_draft_digest`` are taken from the bound
    draft, so a manifest always records the lifecycle stage it realizes and the
    draft it was actually assessed against.

    ``created_at`` must be a timezone-aware UTC instant at whole-second precision;
    it is supplied rather than read from a clock so construction stays
    deterministic and testable.  It is refused rather than converted or truncated
    — a registered, digest-authenticated value is never silently rewritten (§5).

    The sealed artifact is put through the identical ordered E1-E26 contract the
    loader uses, so construction cannot mint anything a load would refuse.

    **This function assesses nothing.**  It records an assessment a caller
    already performed offline, and no caller in this repository performs one:
    every disposition it can seal today is a synthetic one.
    """

    if not isinstance(registration_draft, RegistrationDraft):
        raise ConfirmatoryEligibilityError(
            "registration_draft must be a RegistrationDraft"
        )
    created_at_text = _reuse(_require_created_at_instant, created_at)
    records = tuple(eligibility_records)
    for index, record in enumerate(records):
        if not isinstance(record, EligibilityStratumRecordV1):
            raise ConfirmatoryEligibilityError(
                f"eligibility_records[{index}] must be an EligibilityStratumRecordV1"
            )
    unsealed = EligibilityManifestV1(
        schema_version=ELIGIBILITY_MANIFEST_SCHEMA_VERSION,
        registration_state=REGISTRATION_STATE_ELIGIBILITY_FROZEN,
        confirmatory_profile=CONFIRMATORY_PROFILE,
        design_id=registration_draft.design_id,
        created_at=created_at_text,
        registration_draft_digest=registration_draft.self_digest,
        eligibility_records=records,
        self_digest="",
    )
    sealed = replace(
        unsealed, self_digest=compute_self_digest(unsealed.canonical_payload())
    )
    artifact = sealed.to_artifact()
    _validate_tier_two(artifact, _validate_tier_one(artifact), registration_draft)
    return sealed


# ---------------------------------------------------------------------------
# Immutable persistence and fail-closed load (§14, §15, §16)
# ---------------------------------------------------------------------------


def eligibility_manifest_path(confirmatory_root: Path, design_id: str) -> Path:
    """``<confirmatory_root>/<design_id>/eligibility_manifest.json`` (§5.B layout).

    ``design_id`` goes through the Work Unit 1 single-safe-segment discipline and
    the resolved path is required to stay inside ``confirmatory_root``, so no
    design id can steer a write outside the confirmatory tree.
    """

    safe_design_id = _reuse(_require_design_id, design_id)
    root = Path(confirmatory_root)
    path = root / safe_design_id / ELIGIBILITY_MANIFEST_FILENAME
    resolved_root = root.resolve(strict=False)
    resolved_path = path.resolve(strict=False)
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as error:
        raise ConfirmatoryEligibilityError(
            f"eligibility manifest path escapes confirmatory_root: {path}"
        ) from error
    return path


def _bound_registration_draft(
    confirmatory_root: Path, design_id: str
) -> RegistrationDraft:
    """Load the Stage-A draft this manifest must bind to, failing closed.

    Stage B occurs strictly *after* ``registration_draft.json`` exists (§5.A), so
    an absent draft is a lifecycle-order violation and is refused before any
    eligibility artifact is written.
    """

    draft_path = _reuse(registration_draft_path, confirmatory_root, design_id)
    if not draft_path.is_file():
        raise ConfirmatoryEligibilityError(
            "the bound registration draft does not exist; Stage B occurs strictly "
            f"after registration_draft.json: {draft_path}"
        )
    return _reuse(load_registration_draft, draft_path)


def _validated_manifest_artifact_for_write(
    manifest: EligibilityManifestV1, *, confirmatory_root: Path
) -> dict[str, Any]:
    """Revalidate the complete persisted contract before any filesystem mutation.

    A directly constructed manifest that bypassed :func:`freeze_eligibility`, even
    one carrying a correctly recomputed ``self_digest``, is put through the same
    ordered E1-E26 machinery the loader uses — deliberately before path
    calculation, ``mkdir``, and ``open("xb")``, so an invalid manifest creates no
    directory and no file, and a manifest with several simultaneous defects is
    refused for the lowest-numbered one (§21).

    Tier 1 runs before the bound draft is even read: E5 has already established
    that ``design_id`` is a safe single segment by the time it is used to locate
    ``registration_draft.json``.
    """

    if not isinstance(manifest, EligibilityManifestV1):
        raise ConfirmatoryEligibilityError("manifest must be an EligibilityManifestV1")
    try:
        artifact = manifest.to_artifact()
    except (AttributeError, TypeError, ValueError) as error:
        raise ConfirmatoryEligibilityError(
            f"eligibility manifest cannot be represented by the frozen schema: {error}"
        ) from error
    records = _validate_tier_one(artifact)
    draft = _bound_registration_draft(confirmatory_root, artifact["design_id"])
    _validate_tier_two(artifact, records, draft)
    return artifact


def write_eligibility_manifest(
    manifest: EligibilityManifestV1, *, confirmatory_root: Path
) -> Path:
    """Write ``eligibility_manifest.json`` exactly once, and never again.

    The write is an exclusive create, so an existing manifest is never replaced,
    truncated, or edited in place.  There is no overwrite, no in-place
    reassessment, no versioning in place, and no post-freeze promotion of any
    stratum's disposition — not before assignment, not after execution, not for
    any reason, ever.  Any reassessment is abandon-and-recreate under a **new**
    ``design_id``, which this module does not implement (§15).

    The digest is verified before any byte reaches disk, and the persisted form is
    canonical JSON including ``self_digest`` followed by exactly one LF, which is
    appended after every digest is computed and so is never part of one.
    """

    artifact = _validated_manifest_artifact_for_write(
        manifest, confirmatory_root=confirmatory_root
    )
    payload = _reuse(serialize_artifact, artifact)
    path = eligibility_manifest_path(confirmatory_root, manifest.design_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
    except FileExistsError as error:
        raise ConfirmatoryEligibilityError(
            f"eligibility manifest already exists and is immutable: {path}"
        ) from error
    return path


def _parse_eligibility_bytes(data: bytes) -> dict[str, Any]:
    """The file envelope only: strip one LF, decode UTF-8, parse, require an object.

    This deliberately stops **short** of ``self_digest`` verification.  §14 fixes
    E1-E26 in numbered order and aborts on the first failure, so E20 must not run
    before E1: a manifest missing a top-level key fails E1, not E20.  Work Unit
    1's ``parse_artifact`` verifies the digest as part of parsing, which is
    correct for a Stage-A draft but would invert this contract, so only its
    envelope is reproduced here.

    **Nothing is canonicalized and nothing is hashed.**  This is JSON syntax
    handling, not a second serializer: the frozen canonicalization and digest
    algorithm stay Work Unit 1's and are reached at E20 through
    :func:`verify_self_digest`.  §16's reader semantics are otherwise unchanged —
    at most one trailing LF is stripped, the parse is semantic, and no
    byte-for-byte canonical-input gate is introduced.
    """

    if data.endswith(b"\n"):
        data = data[:-1]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ConfirmatoryEligibilityError(
            f"eligibility manifest bytes are not valid UTF-8: {error}"
        ) from error
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise ConfirmatoryEligibilityError(
            f"eligibility manifest is not valid JSON: {error}"
        ) from error
    if not isinstance(parsed, dict):
        raise ConfirmatoryEligibilityError(
            "eligibility manifest must be a JSON object, got "
            f"{type(parsed).__name__}"
        )
    artifact: dict[str, Any] = parsed
    return artifact


def load_eligibility_manifest(
    path: Path, *, registration_draft: RegistrationDraft
) -> EligibilityManifestV1:
    """Read, verify, and rebuild a persisted eligibility manifest, failing closed.

    The bytes are taken through the file envelope only, then the frozen E1-E26
    contract is applied in numbered order and aborts on the first failure —
    ``self_digest`` verification is E20, at its own numbered position, not a
    precondition of parsing.

    Reader semantics are §5.B.2's, unchanged: at most one trailing LF is
    stripped, the parse is semantic, and the digest is recomputed over the
    recanonicalized object with only ``self_digest`` removed.  No byte-for-byte
    input canonicality gate is added, so semantically equivalent noncanonical JSON
    carrying a correct ``self_digest`` remains acceptable (§16).

    Nothing is normalized, repaired, sorted, deduplicated, default-filled, or
    partially accepted.  No evidence locator is dereferenced.
    """

    artifact = _parse_eligibility_bytes(Path(path).read_bytes())
    records = _validate_tier_one(artifact)
    _validate_tier_two(artifact, records, registration_draft)
    return _manifest_from_validated(artifact, records)
