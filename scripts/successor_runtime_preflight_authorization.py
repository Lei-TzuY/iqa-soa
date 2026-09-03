#!/usr/bin/env python3
"""The NARROW runtime-preflight contact authorization for the successor candidate.

**THIS MODULE OPENS NO SOCKET.** It grants a permission and decides what falls
inside it; it is not an HTTP client, it performs no probe, it captures no
snapshot and it writes no evidence. Importing it, calling every function in it
and running its CLI contacts nothing, runs no model and writes nothing under any
results namespace.

WHAT IT AUTHORIZES
==================

``docs/post_phaseP_successor_runtime_preflight_contact_authorization.md`` is the
human record. It authorizes a LATER, SEPARATE runtime-preflight session to
perform exactly two loopback metadata operations --

    GET http://127.0.0.1:11434/api/version
    GET http://127.0.0.1:11434/api/tags

-- and, only after both succeed, to call the repository-owned
``iqa_soa.experiment.confirmatory.capture_runtime_snapshot_v1`` for exactly the
two frozen strata and persist the resulting ``RuntimeSnapshotV1`` documents as
PRE-EXECUTION provenance evidence.

That is the whole grant. :data:`RUNTIME_PREFLIGHT_METADATA_CONTACT_AUTHORIZED`
and :data:`RUNTIME_SNAPSHOT_CAPTURE_AUTHORIZED` are its machine-readable form.

WHY THIS IS A SEPARATE MODULE AND NOT A FLIPPED PROTOCOL CONSTANT
=================================================================

``scripts/successor_qualification_protocol.py`` carries
``PROVIDER_CONTACT_AUTHORIZED``, ``ENDPOINT_PROBE_AUTHORIZED``,
``MODEL_INFERENCE_AUTHORIZED`` and ``QUALIFICATION_EXECUTION_AUTHORIZED``. Those
govern QUALIFICATION EXECUTION: ``run_successor_qualification`` reads them and
``check_authorization_state`` enforces them. Flipping either contact constant
would have been the smaller edit and the wrong one -- it would advertise a
contact permission vastly wider than two GETs, and it would erode the standing
scientific statement that real qualification still requires its own later human
decision.

So the permission lives here, under its own narrow names, and
:func:`check_qualification_authorization_unchanged` ASSERTS that all four
qualification constants are still ``False``. Widening qualification
authorization therefore breaks this validator rather than being silently
inherited by it.

WHAT A SUCCESSFUL PREFLIGHT WOULD AND WOULD NOT ESTABLISH
=========================================================

It would establish that the live environment presents the prospectively pinned
runtime version and the two prospectively pinned model identities, and it would
produce pre-execution provenance for that observation. It would NOT make either
stratum ``PROVIDER_QUALIFIED`` or ``CONFIRMATORY_ELIGIBLE``, would NOT make the
candidate ``QUALIFIED``, would NOT enter Stage B -- ``successor_eligibility_preflight``
still refuses every offered snapshot and is not modified here -- and would NOT
authorize a single benchmark cell.

Every disagreement is a HOLD, never a repair instruction. Nothing here pulls,
updates, retags or replaces a model, installs or repins a runtime, rewrites a
frozen input, or re-freezes the candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePath
import sys
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _root in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import successor_derive_seeds as successor_seeds  # noqa: E402
import successor_qualification_protocol as protocol  # noqa: E402
import validate_successor_scope as successor_scope  # noqa: E402


class RuntimePreflightAuthorizationError(RuntimeError):
    """The narrow preflight authorization refused something."""


class RuntimePreflightContactRefused(RuntimePreflightAuthorizationError):
    """An HTTP operation outside the two-member allowlist was offered.

    Deliberately its own class. "Outside the allowlist" is a refusal a caller
    must never recover from by retrying differently -- the allowlist is closed,
    and an operation is authorized only by being in it, never by resembling
    something in it or by also being metadata-only.
    """


class RuntimePreflightCaptureRefused(RuntimePreflightAuthorizationError):
    """A RuntimeSnapshotV1 capture outside the authorized scope was offered."""


class RuntimePreflightHold(RuntimePreflightAuthorizationError):
    """A fail-closed condition holds. A HOLD is a stop, never a repair."""


# --------------------------------------------------------------------------
# Canonical provenance of this authorization
# --------------------------------------------------------------------------

#: The canonical ``main`` this authorization was written against, fetched
#: dynamically and recorded once.
CANONICAL_MAIN_COMMIT = "469b0c5916ae74f098da8ab2a45955297a04120b"

AUTHORIZATION_VERSION = "successor-runtime-preflight-contact-authorization-1"

AUTHORIZATION_RECORD_RELATIVE = (
    "docs/post_phaseP_successor_runtime_preflight_contact_authorization.md"
)
MACHINE_RECORD_RELATIVE = (
    "docs/post_phaseP_successor_runtime_preflight_contact_authorization.json"
)

#: SHA-256 over the exact on-disk bytes of the human record this module
#: implements. Pinned so a silently edited authorization fails the validator
#: instead of quietly changing what the code claims a human agreed to.
AUTHORIZATION_RECORD_DIGEST = (
    "a444585878f6d7b5a742628bc31160e95d2c7db65606f34f59acbe92aebdacc3"
)

#: The governing upstream. It selected the strata and withheld provider
#: contact; this record lifts that withholding for two operations and nothing
#: more, so the upstream is named rather than superseded.
UPSTREAM_AUTHORIZATION_RECORD_RELATIVE = protocol.AUTHORIZATION_RECORD_RELATIVE

#: The candidate, REBOUND from the protocol rather than re-spelled. A second
#: literal copy of an identity is a second thing that can drift from it.
CANDIDATE_IDENTIFIER = protocol.CANDIDATE_IDENTIFIER
CANDIDATE_NAMESPACE = protocol.CANDIDATE_NAMESPACE
CANDIDATE_STATUS_AT_ENTRY = protocol.CANDIDATE_STATUS_AT_ENTRY
CANDIDATE_QUALIFICATION_STATUS = protocol.CANDIDATE_QUALIFICATION_STATUS

# --------------------------------------------------------------------------
# Authorization state -- the machine-readable form of the human record
# --------------------------------------------------------------------------

#: The two things this record grants, under names that describe exactly them.
RUNTIME_PREFLIGHT_METADATA_CONTACT_AUTHORIZED = True
RUNTIME_SNAPSHOT_CAPTURE_AUTHORIZED = True
RUNTIME_SNAPSHOT_PERSISTENCE_AUTHORIZED = True

#: Everything this record withholds, stated as data so each refusal is
#: machine-checkable rather than a promise in prose.
MODEL_INFERENCE_AUTHORIZED = False
QUALIFICATION_EXECUTION_AUTHORIZED = False
CONFIRMATORY_EXECUTION_AUTHORIZED = False
PRODUCTION_RANDOMIZATION_AUTHORIZED = False
STAGE_B_ELIGIBILITY_DISPOSITION_AUTHORIZED = False
STAGE_C_FINAL_REGISTRATION_AUTHORIZED = False
REMOTE_PROVIDER_ACCESS_AUTHORIZED = False
CREDENTIAL_TRANSMISSION_AUTHORIZED = False
BENCHMARK_PROMPT_AUTHORIZED = False
MODEL_PULL_AUTHORIZED = False
MODEL_UPDATE_AUTHORIZED = False
MODEL_RETAG_AUTHORIZED = False
MODEL_REPLACEMENT_AUTHORIZED = False
RUNTIME_REPIN_AUTHORIZED = False
QUALIFICATION_RESULT_ROW_AUTHORIZED = False
CONFIRMATORY_RESULT_ROW_AUTHORIZED = False
RANDOMIZATION_ARTIFACT_AUTHORIZED = False
BENCHMARK_OUTCOME_AUTHORIZED = False
REPAIR_DURING_PREFLIGHT_AUTHORIZED = False
CANDIDATE_REFREEZE_AUTHORIZED = False

#: The grant, as a mapping, for the summary and the tests.
GRANTED_SCOPES: Mapping[str, bool] = {
    "RUNTIME_PREFLIGHT_METADATA_CONTACT_AUTHORIZED": (
        RUNTIME_PREFLIGHT_METADATA_CONTACT_AUTHORIZED
    ),
    "RUNTIME_SNAPSHOT_CAPTURE_AUTHORIZED": RUNTIME_SNAPSHOT_CAPTURE_AUTHORIZED,
    "RUNTIME_SNAPSHOT_PERSISTENCE_AUTHORIZED": (
        RUNTIME_SNAPSHOT_PERSISTENCE_AUTHORIZED
    ),
}

#: The withholdings, as a mapping. :func:`check_authorization_state` fails if
#: any member is ever ``True``.
WITHHELD_SCOPES: Mapping[str, bool] = {
    "MODEL_INFERENCE_AUTHORIZED": MODEL_INFERENCE_AUTHORIZED,
    "QUALIFICATION_EXECUTION_AUTHORIZED": QUALIFICATION_EXECUTION_AUTHORIZED,
    "CONFIRMATORY_EXECUTION_AUTHORIZED": CONFIRMATORY_EXECUTION_AUTHORIZED,
    "PRODUCTION_RANDOMIZATION_AUTHORIZED": PRODUCTION_RANDOMIZATION_AUTHORIZED,
    "STAGE_B_ELIGIBILITY_DISPOSITION_AUTHORIZED": (
        STAGE_B_ELIGIBILITY_DISPOSITION_AUTHORIZED
    ),
    "STAGE_C_FINAL_REGISTRATION_AUTHORIZED": STAGE_C_FINAL_REGISTRATION_AUTHORIZED,
    "REMOTE_PROVIDER_ACCESS_AUTHORIZED": REMOTE_PROVIDER_ACCESS_AUTHORIZED,
    "CREDENTIAL_TRANSMISSION_AUTHORIZED": CREDENTIAL_TRANSMISSION_AUTHORIZED,
    "BENCHMARK_PROMPT_AUTHORIZED": BENCHMARK_PROMPT_AUTHORIZED,
    "MODEL_PULL_AUTHORIZED": MODEL_PULL_AUTHORIZED,
    "MODEL_UPDATE_AUTHORIZED": MODEL_UPDATE_AUTHORIZED,
    "MODEL_RETAG_AUTHORIZED": MODEL_RETAG_AUTHORIZED,
    "MODEL_REPLACEMENT_AUTHORIZED": MODEL_REPLACEMENT_AUTHORIZED,
    "RUNTIME_REPIN_AUTHORIZED": RUNTIME_REPIN_AUTHORIZED,
    "QUALIFICATION_RESULT_ROW_AUTHORIZED": QUALIFICATION_RESULT_ROW_AUTHORIZED,
    "CONFIRMATORY_RESULT_ROW_AUTHORIZED": CONFIRMATORY_RESULT_ROW_AUTHORIZED,
    "RANDOMIZATION_ARTIFACT_AUTHORIZED": RANDOMIZATION_ARTIFACT_AUTHORIZED,
    "BENCHMARK_OUTCOME_AUTHORIZED": BENCHMARK_OUTCOME_AUTHORIZED,
    "REPAIR_DURING_PREFLIGHT_AUTHORIZED": REPAIR_DURING_PREFLIGHT_AUTHORIZED,
    "CANDIDATE_REFREEZE_AUTHORIZED": CANDIDATE_REFREEZE_AUTHORIZED,
}

#: The qualification constants this module must never have loosened. Read from
#: the protocol at import; :func:`check_qualification_authorization_unchanged`
#: fails if any of them has become ``True``.
QUALIFICATION_CONSTANTS_THAT_MUST_STAY_FALSE: tuple[str, ...] = (
    "PROVIDER_CONTACT_AUTHORIZED",
    "ENDPOINT_PROBE_AUTHORIZED",
    "MODEL_INFERENCE_AUTHORIZED",
    "QUALIFICATION_EXECUTION_AUTHORIZED",
    "CONFIRMATORY_EXECUTION_AUTHORIZED",
    "RANDOMIZATION_REALIZATION_AUTHORIZED",
    "STAGE_C_FINAL_REGISTRATION_AUTHORIZED",
)

# --------------------------------------------------------------------------
# The allowed contact surface -- a CLOSED two-member allowlist
# --------------------------------------------------------------------------

ALLOWED_SCHEME = "http"
ALLOWED_HOST = "127.0.0.1"
ALLOWED_PORT = 11434
ALLOWED_METHOD = "GET"
ALLOWED_ORIGIN = f"{ALLOWED_SCHEME}://{ALLOWED_HOST}:{ALLOWED_PORT}"

ALLOWED_PATHS: tuple[str, ...] = ("/api/version", "/api/tags")

#: The complete grant, as (method, path) pairs. Exactly two members, by
#: construction. A third member is a change to a frozen tuple that a test fails
#: on, rather than something somebody quietly appends.
ALLOWED_HTTP_OPERATIONS: tuple[tuple[str, str], ...] = tuple(
    (ALLOWED_METHOD, path) for path in ALLOWED_PATHS
)

ALLOWED_URLS: tuple[str, ...] = tuple(
    f"{ALLOWED_ORIGIN}{path}" for path in ALLOWED_PATHS
)

#: Named refusals. The allowlist above already refuses everything not in it;
#: these exist so the most dangerous confusions produce their OWN message
#: instead of a generic one, and so the prohibition is directly testable.
#: ``/api/show``, ``/api/ps``, ``/v1/models`` and ``/v1/embeddings`` are
#: metadata or read-only and are refused anyway: the human decision named two
#: operations, not a category.
REFUSED_PATHS: tuple[str, ...] = (
    "/api/generate",
    "/api/chat",
    "/v1/chat/completions",
    "/v1/completions",
    "/v1/embeddings",
    "/v1/models",
    "/api/show",
    "/api/pull",
    "/api/push",
    "/api/create",
    "/api/copy",
    "/api/delete",
    "/api/blobs",
    "/api/embed",
    "/api/embeddings",
    "/api/ps",
)

#: Host spellings that are NOT the authorized loopback address. ``localhost``
#: and ``::1`` are refused even though they usually resolve to the same
#: interface: the grant names a literal address, and accepting a name would put
#: a resolver between the authorization and what is actually contacted.
REFUSED_HOSTS: tuple[str, ...] = (
    "localhost",
    "::1",
    "0.0.0.0",
    "127.0.0.2",
    "host.docker.internal",
    "ollama",
    "api.openai.com",
    "api.anthropic.com",
)

REFUSED_METHODS: tuple[str, ...] = (
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "HEAD",
    "OPTIONS",
    "TRACE",
    "CONNECT",
)

#: The authorized operations carry NO caller-supplied request header and NO
#: request body. That is the strongest honest reading of "no credentials": a
#: header allowlist that is empty cannot be talked into carrying a token.
ALLOWED_REQUEST_HEADERS: tuple[str, ...] = ()
ALLOWED_REQUEST_BODY = None

#: Named so the credential prohibition is citable rather than implied.
REFUSED_REQUEST_HEADERS: tuple[str, ...] = (
    "authorization",
    "proxy-authorization",
    "api-key",
    "x-api-key",
    "openai-api-key",
    "cookie",
)

#: Checked by NAME only, exactly as the qualification protocol does. Its value
#: is never read, never sent, never printed and never written to an artifact.
CREDENTIAL_ENV = protocol.CREDENTIAL_ENV

# --------------------------------------------------------------------------
# The frozen runtime and model identities this preflight would verify
# --------------------------------------------------------------------------

#: REBOUND from the protocol. The human record restates these so the contact
#: authorization is self-contained; :func:`check_human_record_agreement` proves
#: the restatement still agrees with the repository instead of drifting from it.
EXPECTED_RUNTIME_VERSION = protocol.EXPECTED_RUNTIME_VERSION
ACCEPTED_RUNTIME_VERSIONS = protocol.ACCEPTED_RUNTIME_VERSIONS
RUNTIME_VERSION_COMPARISON = protocol.RUNTIME_VERSION_COMPARISON
RUNTIME_VERSION_RESOLUTION = protocol.RUNTIME_VERSION_RESOLUTION
EXPECTED_MODEL_DIGEST = protocol.EXPECTED_MODEL_DIGEST

#: What the HUMAN RECORD states, spelled once here so a disagreement between the
#: record and the repository is a validator failure rather than an unnoticed
#: divergence. These are restatements, not a second selection.
HUMAN_RECORD_RUNTIME_VERSION = "0.32.13"
HUMAN_RECORD_MODEL_IDENTITY: Mapping[str, str] = {
    "qwen3.5:27b": (
        "7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"
    ),
    "mistral-small3.2:24b": (
        "5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b"
    ),
}

# --------------------------------------------------------------------------
# Bindings -- recomputed from disk, never trusted from the record
# --------------------------------------------------------------------------

FROZEN_INPUTS_RELATIVE = protocol.FROZEN_INPUTS_RELATIVE
EXPERIMENT_CONFIG_RELATIVE = protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE
MODELS_CONFIG_RELATIVE = protocol.CANONICAL_MODELS_RELATIVE
QUALIFICATION_PROTOCOL_RELATIVE = "scripts/successor_qualification_protocol.py"
SEED_DERIVATION_RECORD_RELATIVE = protocol.SEED_DERIVATION_RECORD_RELATIVE

#: Every artifact this authorization is bound to, with the digest it must still
#: present. Two entries are REBOUND from the protocol's own pins; the rest are
#: pinned here because the protocol does not pin them.
#:
#: The prospective seed VALUES are deliberately absent from this module and from
#: the machine record. ``successor_derive_seeds.SUCCESSOR_ARTIFACTS`` is an
#: exhaustive list of the three files permitted to name them, and its collision
#: scan reports a successor seed appearing anywhere else as a LEAK. The seed
#: derivation is therefore bound by digest, which identifies the triple without
#: disclosing it.
BOUND_ARTIFACT_DIGESTS: Mapping[str, str] = {
    protocol.FREEZE_RECORD_RELATIVE: protocol.FREEZE_RECORD_DIGEST,
    protocol.QUALIFICATION_CONTRACT_RELATIVE: protocol.QUALIFICATION_CONTRACT_DIGEST,
    FROZEN_INPUTS_RELATIVE: (
        "f8c8ee086ca52ba3b4b93ceb3d72c5e9d2691b7d2152a6fba45185bc5f778ce2"
    ),
    EXPERIMENT_CONFIG_RELATIVE: (
        "f5240e2571c3d6141e9d53b0a244daf8f9ce7be8c0f25b0dfd063484d7d8d090"
    ),
    MODELS_CONFIG_RELATIVE: (
        "7ff2ec9e7a452331e80414194a4f5a74ab87e1c677c48d1abebd173b063566c2"
    ),
    QUALIFICATION_PROTOCOL_RELATIVE: (
        "ddf82fc080d4c462f0230a8f646a6f08fc020ffac5b7818a3b58a97b98eb3cea"
    ),
    SEED_DERIVATION_RECORD_RELATIVE: (
        "08afb9ec753358ed1f75d1db645cfe179b1a952dcdc51a29aa23c82f8d70a05e"
    ),
    UPSTREAM_AUTHORIZATION_RECORD_RELATIVE: (
        "cff940697c110b6b7e507ab051127c9d62676fccec2f868d9434bf45aa4d042b"
    ),
}

#: The seed derivation's own digest -- a property of the derivation, not of the
#: file that records it, and therefore pinned separately.
SEED_DERIVATION_DIGEST = (
    "97674242a12d05ccac8fe1ee1c1ef3885f2a999da538f1ccc3d2a429b62d4b3b"
)

#: The two scientific digests, REBOUND from the scope validator, which
#: recomputes both from the benchmark bytes.
BENCHMARK_CASE_BYTES_DIGEST = successor_scope.BENCHMARK_CASE_BYTES_DIGEST
CANONICAL_EXPOSURE_DIGEST = successor_scope.CANONICAL_EXPOSURE_DIGEST

# --------------------------------------------------------------------------
# The RuntimeSnapshotV1 capture this record authorizes
# --------------------------------------------------------------------------

AUTHORIZED_CAPTURE_CALLABLE = (
    "iqa_soa.experiment.confirmatory.capture_runtime_snapshot_v1"
)

#: Exactly the two frozen strata, REBOUND from the protocol. Not a third, and
#: not one alone.
AUTHORIZED_CAPTURE_STRATA = protocol.PROPOSED_STRATA

#: Where pre-execution provenance may be written. Deliberately NOT the
#: qualification namespace: a pre-execution capture is not a result, and writing
#: it where a result row lives would make it readable later as evidence that a
#: qualification began.
RUNTIME_PREFLIGHT_EVIDENCE_NAMESPACE = f"results/{CANDIDATE_IDENTIFIER}-runtime-preflight"

QUALIFICATION_RESULTS_NAMESPACE = protocol.RESULTS_NAMESPACE

#: Artifact kinds this authorization permits, and the ones it does not. The
#: second tuple is the point: a capture that produced any of these would have
#: exceeded the grant regardless of where it was written.
PERMITTED_ARTIFACT_KINDS: tuple[str, ...] = (
    "RuntimeSnapshotV1",
    "runtime_preflight_metadata_observation",
    "runtime_preflight_report",
)
FORBIDDEN_ARTIFACT_KINDS: tuple[str, ...] = (
    "qualification_result_row",
    "confirmatory_result_row",
    "randomization_artifact",
    "assignment_manifest",
    "eligibility_manifest",
    "benchmark_outcome",
    "raw_run_record",
)

PERSISTENCE_POLICY: Mapping[str, bool] = {
    "overwrite_permitted": False,
    "resume_permitted": False,
    "merge_permitted": False,
    "fail_closed": True,
    "write_once": True,
}

# --------------------------------------------------------------------------
# Historical boundary
# --------------------------------------------------------------------------

#: Refused by NAME, and by LEXICAL path comparison only. A guard that stats the
#: thing it exists to keep untouched is not a guard, so nothing here opens,
#: lists, stats or hashes any of these.
FORBIDDEN_RESULTS_NAMESPACES = protocol.FORBIDDEN_RESULTS_NAMESPACES

#: The untracked local clarification directories. Refused by top-level segment
#: PREFIX rather than by enumerating their names, so a fifth one is refused the
#: moment it exists and nothing has to be inspected to learn about it.
FORBIDDEN_TOP_LEVEL_PREFIXES: tuple[str, ...] = ("FSE-",)

PHASE_P_STATUS = "UNQUALIFIED"
PHASE_P_VERDICT = "HOLD"
PHASE_P_TERMINAL_STATUS = "SCHEDULE_COMPLETE_VERDICT_HOLD"
HISTORICAL_ROW_ACCESS_AUTHORIZED = False

# --------------------------------------------------------------------------
# Fail-closed conditions
# --------------------------------------------------------------------------

FAIL_CLOSED_ACTION = "HOLD_WITH_ZERO_INFERENCE"

LIVE_RUNTIME_VERSION_MISMATCH = "LIVE_RUNTIME_VERSION_MISMATCH"
QWEN_MODEL_DIGEST_MISMATCH = "QWEN_MODEL_DIGEST_MISMATCH"
MISTRAL_MODEL_DIGEST_MISMATCH = "MISTRAL_MODEL_DIGEST_MISMATCH"
ENDPOINT_NOT_LOOPBACK = "ENDPOINT_NOT_LOOPBACK"
UNEXPECTED_HTTP_OPERATION_REQUIRED = "UNEXPECTED_HTTP_OPERATION_REQUIRED"
FROZEN_INPUT_DIGEST_MISMATCH = "FROZEN_INPUT_DIGEST_MISMATCH"
CANDIDATE_FREEZE_INVALID = "CANDIDATE_FREEZE_INVALID"
QUALIFICATION_RESULT_NAMESPACE_EXISTS = "QUALIFICATION_RESULT_NAMESPACE_EXISTS"
RUNTIME_SNAPSHOT_CAPTURE_FAILED = "RUNTIME_SNAPSHOT_CAPTURE_FAILED"

#: The complete set. Every member is a STOP with zero inference, and none is a
#: repair instruction: :data:`REPAIR_DURING_PREFLIGHT_AUTHORIZED` is ``False``.
FAIL_CLOSED_CONDITIONS: tuple[str, ...] = (
    LIVE_RUNTIME_VERSION_MISMATCH,
    QWEN_MODEL_DIGEST_MISMATCH,
    MISTRAL_MODEL_DIGEST_MISMATCH,
    ENDPOINT_NOT_LOOPBACK,
    UNEXPECTED_HTTP_OPERATION_REQUIRED,
    FROZEN_INPUT_DIGEST_MISMATCH,
    CANDIDATE_FREEZE_INVALID,
    QUALIFICATION_RESULT_NAMESPACE_EXISTS,
    RUNTIME_SNAPSHOT_CAPTURE_FAILED,
)

#: Which model's mismatch maps to which condition name.
MODEL_MISMATCH_CONDITION: Mapping[str, str] = {
    "qwen3.5:27b": QWEN_MODEL_DIGEST_MISMATCH,
    "mistral-small3.2:24b": MISTRAL_MODEL_DIGEST_MISMATCH,
}

EXIT_OK = 0
EXIT_HOLD = 2


# --------------------------------------------------------------------------
# Path helpers -- lexical, never touching the filesystem
# --------------------------------------------------------------------------


def _lexical_absolute(supplied: Path | str) -> PurePath:
    """Absolutize and normalize a path WITHOUT touching the filesystem.

    Deliberately lexical, for the same reason the qualification protocol's guard
    is: refusing a historical evidence path must not require stat-ing it, and
    the refusal must not depend on what happens to be on the machine.
    """

    candidate = Path(supplied)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return PurePath(os.path.normpath(str(candidate)))


def _is_within(offered: PurePath, root: PurePath) -> bool:
    return offered == root or root in offered.parents


def _relative_segments(offered: PurePath) -> tuple[str, ...]:
    root = _lexical_absolute(".")
    if not _is_within(offered, root):
        return ()
    return PurePath(os.path.relpath(str(offered), str(root))).parts


def sha256_file(relative: str) -> str:
    """SHA-256 over the exact on-disk bytes of a repository-relative file."""

    return hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# The contact decision -- what is inside the two-member allowlist
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthorizedOperation:
    """One HTTP operation proved to be inside the closed allowlist."""

    method: str
    url: str
    host: str
    port: int
    path: str


def _refuse(reason: str) -> None:
    raise RuntimePreflightContactRefused(
        f"RUNTIME_PREFLIGHT_CONTACT_REFUSED: {reason}. The authorization "
        f"{AUTHORIZATION_RECORD_RELATIVE} permits exactly "
        f"{[f'{method} {path}' for method, path in ALLOWED_HTTP_OPERATIONS]} "
        f"against {ALLOWED_ORIGIN}, with no credential, no header and no body. "
        "The allowlist is closed: nothing is authorized by resembling a member "
        "of it, by also being metadata-only, or by being read-only."
    )


def authorize_http_operation(method: str, url: str) -> AuthorizedOperation:
    """Prove one offered HTTP operation is inside the grant, or refuse it.

    Every comparison is exact. There is no normalization, no case folding of the
    path, no percent-decoding, no trailing-slash tolerance and no default port:
    a URL that would need any of those to match is a different URL, and the
    whole purpose of this function is to be unpassable by anything but the two
    operations a human named.
    """

    if not RUNTIME_PREFLIGHT_METADATA_CONTACT_AUTHORIZED:
        _refuse("metadata contact is not authorized")
    if type(method) is not str:
        _refuse(f"method {method!r} is not a string and is never coerced")
    if type(url) is not str:
        _refuse(f"url {url!r} is not a string and is never coerced")
    if method != ALLOWED_METHOD:
        _refuse(f"method {method!r} is not {ALLOWED_METHOD!r}")

    try:
        parts = urlsplit(url)
    except ValueError as error:
        raise RuntimePreflightContactRefused(
            f"RUNTIME_PREFLIGHT_CONTACT_REFUSED: {url!r} is not a parseable URL"
        ) from error

    if parts.scheme != ALLOWED_SCHEME:
        _refuse(f"scheme {parts.scheme!r} is not {ALLOWED_SCHEME!r}")
    if parts.username is not None or parts.password is not None:
        _refuse("the URL carries userinfo; no credential may be presented")
    try:
        port = parts.port
    except ValueError:
        port = None
    if parts.hostname != ALLOWED_HOST:
        _refuse(
            f"host {parts.hostname!r} is not the authorized loopback address "
            f"{ALLOWED_HOST!r}"
        )
    if port != ALLOWED_PORT:
        _refuse(f"port {port!r} is not {ALLOWED_PORT}")
    if parts.query:
        _refuse("the URL carries a query string")
    if parts.fragment:
        _refuse("the URL carries a fragment")
    if parts.path in REFUSED_PATHS:
        _refuse(
            f"path {parts.path!r} is an inference, mutation or unlisted "
            "metadata endpoint and is refused by name"
        )
    if parts.path not in ALLOWED_PATHS:
        _refuse(f"path {parts.path!r} is not one of {list(ALLOWED_PATHS)}")
    if (method, parts.path) not in ALLOWED_HTTP_OPERATIONS:
        _refuse(f"{method} {parts.path} is not an authorized operation")

    return AuthorizedOperation(
        method=method,
        url=url,
        host=ALLOWED_HOST,
        port=ALLOWED_PORT,
        path=parts.path,
    )


def authorize_request(
    method: str,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    body: object = None,
) -> AuthorizedOperation:
    """The whole request, not just its target, must be inside the grant.

    A correct URL reached with an ``Authorization`` header or a request body is
    not the operation a human authorized, so the header allowlist is empty and
    the body must be absent.
    """

    if body is not ALLOWED_REQUEST_BODY:
        _refuse("the request carries a body; both authorized operations are bodiless")
    if headers:
        offered = sorted(str(name).casefold() for name in headers)
        credential = [name for name in offered if name in REFUSED_REQUEST_HEADERS]
        if credential:
            _refuse(
                f"the request carries credential header(s) {credential}; this "
                "authorization transmits no credential of any kind"
            )
        _refuse(
            f"the request carries header(s) {offered}; the authorized header set "
            "is empty"
        )
    return authorize_http_operation(method, url)


def is_authorized_operation(method: str, url: str) -> bool:
    """Whether an operation is inside the grant, as a predicate."""

    try:
        authorize_http_operation(method, url)
    except RuntimePreflightContactRefused:
        return False
    return True


# --------------------------------------------------------------------------
# The observation decision -- what a metadata result MEANS
# --------------------------------------------------------------------------


def evaluate_metadata_observation(
    *,
    runtime_version: object,
    model_digests: Mapping[str, str] | None,
) -> tuple[str, ...]:
    """Which fail-closed conditions a live metadata observation triggers.

    The caller supplies the observation; this function performs no probe. It
    decides only what a probe's result MEANS, so the decision rule is frozen
    offline before any probe is authorized to exist.

    A MISSING observation is a mismatch. "The preflight did not look" must never
    read as "the preflight looked and found agreement", which is the same stance
    :func:`successor_qualification_protocol.verify_runtime_identity` already
    takes and is not softened here.
    """

    conditions: list[str] = []
    if type(runtime_version) is not str:
        conditions.append(LIVE_RUNTIME_VERSION_MISMATCH)
    elif runtime_version not in ACCEPTED_RUNTIME_VERSIONS:
        conditions.append(LIVE_RUNTIME_VERSION_MISMATCH)

    observed = dict(model_digests or {})
    for model, expected in sorted(EXPECTED_MODEL_DIGEST.items()):
        actual = observed.get(model)
        if type(actual) is not str or actual != expected:
            conditions.append(MODEL_MISMATCH_CONDITION[model])
    return tuple(conditions)


def offline_hold_conditions() -> tuple[str, ...]:
    """The fail-closed conditions decidable right now, with no contact."""

    conditions: list[str] = []
    if binding_failures():
        conditions.append(FROZEN_INPUT_DIGEST_MISMATCH)
    if protocol.check_candidate_freeze():
        conditions.append(CANDIDATE_FREEZE_INVALID)
    if (PROJECT_ROOT / QUALIFICATION_RESULTS_NAMESPACE).exists():
        conditions.append(QUALIFICATION_RESULT_NAMESPACE_EXISTS)
    return tuple(conditions)


def require_no_hold(conditions: Sequence[str] = ()) -> None:
    """Refuse to proceed while any fail-closed condition holds."""

    held = tuple(conditions) + offline_hold_conditions()
    if held:
        raise RuntimePreflightHold(
            f"RUNTIME_PREFLIGHT_HOLD: {sorted(set(held))}. The required action is "
            f"{FAIL_CLOSED_ACTION}: stop with zero inference and report. No "
            "mismatch may be repaired during the preflight -- no model is "
            "pulled, updated, retagged or replaced, no runtime is installed or "
            "repinned, no frozen input is rewritten and the candidate is not "
            "re-frozen."
        )


# --------------------------------------------------------------------------
# The capture decision
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthorizedCapture:
    """One RuntimeSnapshotV1 capture proved to be inside the grant."""

    provider_slot: str
    model: str
    capture_callable: str
    experiment_config: str
    models_config: str
    evidence_namespace: str


def authorize_runtime_snapshot_capture(
    *,
    provider_slot: str,
    model: str,
    completed_metadata_paths: Sequence[str],
) -> AuthorizedCapture:
    """Prove one offered capture is inside the grant, or refuse it.

    The capture is authorized only AFTER both metadata operations have actually
    succeeded, because that is what makes the snapshot an observation of a real
    runtime rather than a well-formed assertion about an unobserved one.
    """

    if not RUNTIME_SNAPSHOT_CAPTURE_AUTHORIZED:
        raise RuntimePreflightCaptureRefused(
            "RUNTIME_SNAPSHOT_CAPTURE: NOT_AUTHORIZED"
        )
    if (provider_slot, model) not in AUTHORIZED_CAPTURE_STRATA:
        raise RuntimePreflightCaptureRefused(
            f"RUNTIME_SNAPSHOT_CAPTURE_REFUSED: ({provider_slot!r}, {model!r}) is "
            f"not one of the two frozen strata "
            f"{[list(item) for item in AUTHORIZED_CAPTURE_STRATA]}. The grant "
            "covers exactly those two; it covers no third stratum, no "
            "replacement model and no newer tag."
        )
    completed = {str(path) for path in completed_metadata_paths}
    if completed != set(ALLOWED_PATHS):
        raise RuntimePreflightCaptureRefused(
            f"RUNTIME_SNAPSHOT_CAPTURE_REFUSED: the capture is authorized only "
            f"after both {list(ALLOWED_PATHS)} succeed; this session completed "
            f"{sorted(completed)}. An unobserved runtime fact is never treated "
            "as a matching one."
        )
    require_no_hold()
    return AuthorizedCapture(
        provider_slot=provider_slot,
        model=model,
        capture_callable=AUTHORIZED_CAPTURE_CALLABLE,
        experiment_config=EXPERIMENT_CONFIG_RELATIVE,
        models_config=MODELS_CONFIG_RELATIVE,
        evidence_namespace=RUNTIME_PREFLIGHT_EVIDENCE_NAMESPACE,
    )


def require_preflight_evidence_path(supplied: Path | str) -> Path:
    """Prove a write target is inside the preflight evidence namespace.

    A historical namespace and the qualification namespace are refused with
    their OWN messages, because "this is frozen historical evidence" and "this
    is where results live and a preflight writes none" are different mistakes
    and a reader deserves to be told which one they made.
    """

    offered = _lexical_absolute(supplied)
    for forbidden in FORBIDDEN_RESULTS_NAMESPACES:
        if _is_within(offered, _lexical_absolute(forbidden)):
            raise RuntimePreflightCaptureRefused(
                f"HISTORICAL_BOUNDARY: {forbidden} is frozen historical evidence "
                "under a different instrument generation. The runtime preflight "
                "never reads, lists, writes, appends to, repairs or pools with "
                "it, and Phase P remains permanently "
                f"{PHASE_P_STATUS} / {PHASE_P_VERDICT}."
            )
    segments = _relative_segments(offered)
    if segments:
        for prefix in FORBIDDEN_TOP_LEVEL_PREFIXES:
            if segments[0].startswith(prefix):
                raise RuntimePreflightCaptureRefused(
                    f"HISTORICAL_BOUNDARY: {segments[0]!r} is an out-of-scope "
                    "clarification directory. The runtime preflight never "
                    "inspects one."
                )
    if _is_within(offered, _lexical_absolute(QUALIFICATION_RESULTS_NAMESPACE)):
        raise RuntimePreflightCaptureRefused(
            f"SCOPE_REFUSED: {QUALIFICATION_RESULTS_NAMESPACE} is the "
            "qualification result namespace. This authorization permits "
            "PRE-EXECUTION provenance only and creates no qualification result "
            "row, so it never writes there -- and it never creates that "
            "namespace, which would be readable later as evidence a "
            "qualification began."
        )
    namespace = _lexical_absolute(RUNTIME_PREFLIGHT_EVIDENCE_NAMESPACE)
    if not _is_within(offered, namespace):
        raise RuntimePreflightCaptureRefused(
            f"SCOPE_REFUSED: pre-execution evidence is written only under "
            f"{RUNTIME_PREFLIGHT_EVIDENCE_NAMESPACE}; {offered} is not."
        )
    return Path(str(offered))


# --------------------------------------------------------------------------
# Offline checks
# --------------------------------------------------------------------------


def check_authorization_state() -> list[str]:
    """The grant is exactly two scopes, and nothing else claims one."""

    failures: list[str] = []
    for name, value in GRANTED_SCOPES.items():
        if value is not True:
            failures.append(
                f"AUTHORIZATION: {name} is {value!r}; the human record grants it"
            )
    for name, value in WITHHELD_SCOPES.items():
        if value:
            failures.append(
                f"AUTHORIZATION: {name} is True; "
                f"{AUTHORIZATION_RECORD_RELATIVE} withholds it"
            )
    if CANDIDATE_QUALIFICATION_STATUS in protocol.FORBIDDEN_CANDIDATE_STATUSES:
        failures.append(
            "AUTHORIZATION: the candidate's qualification status claims a state "
            "that only executed evidence could establish"
        )
    if CANDIDATE_STATUS_AT_ENTRY != "FROZEN_NOT_YET_QUALIFIED":
        failures.append(
            f"AUTHORIZATION: candidate status at entry is "
            f"{CANDIDATE_STATUS_AT_ENTRY!r}, not FROZEN_NOT_YET_QUALIFIED"
        )
    return failures


def check_qualification_authorization_unchanged() -> list[str]:
    """Qualification authorization was not loosened to obtain this permission."""

    failures: list[str] = []
    for name in QUALIFICATION_CONSTANTS_THAT_MUST_STAY_FALSE:
        value = getattr(protocol, name)
        if value is not False:
            failures.append(
                f"QUALIFICATION_UNCHANGED: successor_qualification_protocol.{name} "
                f"is {value!r}; the narrow runtime-preflight permission must "
                "never be obtained by widening qualification authorization"
            )
    try:
        protocol.require_execution_authorization()
    except protocol.QualificationExecutionNotAuthorized:
        pass
    else:
        failures.append(
            "QUALIFICATION_UNCHANGED: require_execution_authorization no longer "
            "refuses; the qualification runner has become executable"
        )
    return failures


def check_contact_surface() -> list[str]:
    """The allowlist is closed, has exactly two members, and refuses the rest."""

    failures: list[str] = []
    if len(ALLOWED_HTTP_OPERATIONS) != 2:
        failures.append(
            f"CONTACT_SURFACE: {len(ALLOWED_HTTP_OPERATIONS)} operations are "
            "allowed; the human record names exactly two"
        )
    if set(ALLOWED_PATHS) != {"/api/version", "/api/tags"}:
        failures.append(
            f"CONTACT_SURFACE: the allowed paths are {list(ALLOWED_PATHS)}, the "
            "human record names /api/version and /api/tags"
        )
    if ALLOWED_HOST != "127.0.0.1" or ALLOWED_PORT != 11434:
        failures.append(
            f"CONTACT_SURFACE: the allowed origin is {ALLOWED_ORIGIN}, the human "
            "record names http://127.0.0.1:11434"
        )
    if ALLOWED_METHOD != "GET":
        failures.append(
            f"CONTACT_SURFACE: the allowed method is {ALLOWED_METHOD!r}, not 'GET'"
        )
    if ALLOWED_REQUEST_HEADERS:
        failures.append(
            "CONTACT_SURFACE: the authorized header set must be empty; no "
            "credential is transmitted"
        )

    for url in ALLOWED_URLS:
        if not is_authorized_operation(ALLOWED_METHOD, url):
            failures.append(f"CONTACT_SURFACE: {ALLOWED_METHOD} {url} is refused")
    for path in REFUSED_PATHS:
        if is_authorized_operation(ALLOWED_METHOD, f"{ALLOWED_ORIGIN}{path}"):
            failures.append(f"CONTACT_SURFACE: {path} is accepted and must not be")
    for host in REFUSED_HOSTS:
        for path in ALLOWED_PATHS:
            url = f"{ALLOWED_SCHEME}://{host}:{ALLOWED_PORT}{path}"
            if is_authorized_operation(ALLOWED_METHOD, url):
                failures.append(f"CONTACT_SURFACE: host {host} is accepted")
    for method in REFUSED_METHODS:
        if is_authorized_operation(method, ALLOWED_URLS[0]):
            failures.append(f"CONTACT_SURFACE: method {method} is accepted")
    if is_authorized_operation(ALLOWED_METHOD, f"https://{ALLOWED_HOST}:{ALLOWED_PORT}/api/tags"):
        failures.append("CONTACT_SURFACE: a non-http scheme is accepted")
    if is_authorized_operation(ALLOWED_METHOD, f"{ALLOWED_SCHEME}://{ALLOWED_HOST}/api/tags"):
        failures.append("CONTACT_SURFACE: an absent port is accepted")
    return failures


def binding_failures() -> list[str]:
    """Every bound artifact still hashes to the digest this record accepted."""

    failures: list[str] = []
    for relative, expected in sorted(BOUND_ARTIFACT_DIGESTS.items()):
        path = PROJECT_ROOT / relative
        if not path.is_file():
            failures.append(f"BINDING: {relative} does not exist")
            continue
        actual = sha256_file(relative)
        if actual != expected:
            failures.append(
                f"BINDING: {relative} digests to {actual}, this authorization is "
                f"bound to {expected}"
            )
    return failures


def check_bindings() -> list[str]:
    """The bound artifacts, the seed derivation and the human record agree."""

    failures = binding_failures()
    actual_seed_derivation = successor_seeds.derivation_digest(
        protocol.SEEDS, base_commit=protocol.SEED_DERIVATION_BASE_COMMIT
    )
    if actual_seed_derivation != SEED_DERIVATION_DIGEST:
        failures.append(
            f"BINDING: the prospective seed derivation digests to "
            f"{actual_seed_derivation}, this authorization is bound to "
            f"{SEED_DERIVATION_DIGEST}"
        )
    record = PROJECT_ROOT / AUTHORIZATION_RECORD_RELATIVE
    if not record.is_file():
        failures.append(f"BINDING: {AUTHORIZATION_RECORD_RELATIVE} does not exist")
    else:
        actual_record = sha256_file(AUTHORIZATION_RECORD_RELATIVE)
        if actual_record != AUTHORIZATION_RECORD_DIGEST:
            failures.append(
                f"BINDING: {AUTHORIZATION_RECORD_RELATIVE} digests to "
                f"{actual_record}, this module implements "
                f"{AUTHORIZATION_RECORD_DIGEST}"
            )
    return failures


def check_human_record_agreement() -> list[str]:
    """The record's restated runtime and model identities match the repository."""

    failures: list[str] = []
    if HUMAN_RECORD_RUNTIME_VERSION != EXPECTED_RUNTIME_VERSION:
        failures.append(
            f"HUMAN_RECORD: the record states runtime "
            f"{HUMAN_RECORD_RUNTIME_VERSION!r}, the repository pins "
            f"{EXPECTED_RUNTIME_VERSION!r}"
        )
    if dict(HUMAN_RECORD_MODEL_IDENTITY) != dict(EXPECTED_MODEL_DIGEST):
        failures.append(
            "HUMAN_RECORD: the record's restated model identities disagree with "
            "the prospectively pinned ones"
        )
    if len(ACCEPTED_RUNTIME_VERSIONS) != 1:
        failures.append(
            f"HUMAN_RECORD: {len(ACCEPTED_RUNTIME_VERSIONS)} runtime versions are "
            "accepted; the frozen requirement is exactly one"
        )
    if RUNTIME_VERSION_COMPARISON != "EXACT_STRING_EQUALITY":
        failures.append(
            f"HUMAN_RECORD: the runtime comparison is "
            f"{RUNTIME_VERSION_COMPARISON!r}, not exact string equality"
        )
    if len(AUTHORIZED_CAPTURE_STRATA) != 2:
        failures.append(
            f"HUMAN_RECORD: {len(AUTHORIZED_CAPTURE_STRATA)} strata are in "
            "capture scope; the human record names exactly two"
        )
    return failures


def check_historical_boundary() -> list[str]:
    """Every out-of-scope namespace is refused, by name and without touching it."""

    failures: list[str] = []
    if HISTORICAL_ROW_ACCESS_AUTHORIZED:
        failures.append("HISTORICAL_BOUNDARY: historical row access claims to be authorized")
    if "results/phaseP-rc4-qualification" not in FORBIDDEN_RESULTS_NAMESPACES:
        failures.append(
            "HISTORICAL_BOUNDARY: the Phase-P namespace is not refused by name"
        )
    probes = [
        f"{namespace}/anything.json" for namespace in FORBIDDEN_RESULTS_NAMESPACES
    ]
    probes.append("FSE-schema-clarification/anything.md")
    probes.append(f"{QUALIFICATION_RESULTS_NAMESPACE}/raw/successor-runs.jsonl")
    for probe in probes:
        try:
            require_preflight_evidence_path(probe)
        except RuntimePreflightCaptureRefused:
            continue
        failures.append(f"HISTORICAL_BOUNDARY: {probe} is accepted as a write target")
    if PHASE_P_VERDICT != "HOLD" or PHASE_P_STATUS != "UNQUALIFIED":
        failures.append(
            "HISTORICAL_BOUNDARY: Phase P is no longer recorded as UNQUALIFIED/HOLD"
        )
    return failures


def check_no_qualification_result_namespace() -> list[str]:
    """The qualification namespace must not exist; a preflight never creates it."""

    if (PROJECT_ROOT / QUALIFICATION_RESULTS_NAMESPACE).exists():
        return [
            f"NAMESPACE: {QUALIFICATION_RESULTS_NAMESPACE} already exists; the "
            "preflight holds rather than proceeding"
        ]
    if (PROJECT_ROOT / RUNTIME_PREFLIGHT_EVIDENCE_NAMESPACE).exists():
        return [
            f"NAMESPACE: {RUNTIME_PREFLIGHT_EVIDENCE_NAMESPACE} already exists; "
            "pre-execution evidence is written once, never appended to"
        ]
    return []


def check_scientific_inputs_unchanged() -> list[str]:
    """Benchmark bytes, canonical exposure and the candidate freeze are unmoved."""

    failures: list[str] = []
    failures.extend(protocol.check_candidate_freeze())
    manifest = successor_scope.load_manifest()
    cases = successor_scope.load_cases()
    contract = successor_scope.load_contract()
    failures.extend(successor_scope.check_benchmark_case_bytes_unchanged(manifest))
    failures.extend(successor_scope.check_canonical_exposure_unchanged(cases, contract))
    if BENCHMARK_CASE_BYTES_DIGEST != protocol.BENCHMARK_CASE_BYTES_DIGEST:
        failures.append("SCIENTIFIC_INPUTS: the benchmark case-byte digest disagrees")
    if CANONICAL_EXPOSURE_DIGEST != protocol.CANONICAL_EXPOSURE_DIGEST:
        failures.append("SCIENTIFIC_INPUTS: the canonical exposure digest disagrees")
    return failures


def check_machine_record() -> list[str]:
    """The committed machine record still equals what this module computes."""

    path = PROJECT_ROOT / MACHINE_RECORD_RELATIVE
    if not path.is_file():
        return [f"MACHINE_RECORD: {MACHINE_RECORD_RELATIVE} does not exist"]
    try:
        committed = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as error:
        return [f"MACHINE_RECORD: {MACHINE_RECORD_RELATIVE} is unreadable: {error}"]
    if committed != machine_record():
        return [
            f"MACHINE_RECORD: {MACHINE_RECORD_RELATIVE} disagrees with the "
            "authorization surface it claims to record"
        ]
    return []


def offline_validation() -> list[str]:
    """Every offline check, in order. Contacts nothing, captures nothing."""

    failures: list[str] = []
    failures.extend(check_authorization_state())
    failures.extend(check_qualification_authorization_unchanged())
    failures.extend(check_contact_surface())
    failures.extend(check_bindings())
    failures.extend(check_human_record_agreement())
    failures.extend(check_scientific_inputs_unchanged())
    failures.extend(check_historical_boundary())
    failures.extend(check_no_qualification_result_namespace())
    failures.extend(check_machine_record())
    return failures


# --------------------------------------------------------------------------
# Machine-readable statement of the authorization
# --------------------------------------------------------------------------


def machine_record() -> dict[str, Any]:
    """The machine-readable form of the human record.

    Deliberately carries no key named ``seed`` or ``seeds``:
    ``successor_derive_seeds`` scans every tracked JSON document under ``docs``
    for exactly those keys, and a fourth file naming the successor triple would
    be reported by its collision scan as a leak. The derivation is bound by
    digest instead.
    """

    return {
        "record_kind": "successor_runtime_preflight_contact_authorization",
        "authorization_version": AUTHORIZATION_VERSION,
        "authorization_record": AUTHORIZATION_RECORD_RELATIVE,
        "authorization_record_sha256": sha256_file(AUTHORIZATION_RECORD_RELATIVE),
        "upstream_authorization_record": UPSTREAM_AUTHORIZATION_RECORD_RELATIVE,
        "validator": "scripts/successor_runtime_preflight_authorization.py",
        "canonical_main_commit": CANONICAL_MAIN_COMMIT,
        "candidate_identifier": CANDIDATE_IDENTIFIER,
        "candidate_namespace": CANDIDATE_NAMESPACE,
        "candidate_status_at_entry": CANDIDATE_STATUS_AT_ENTRY,
        "candidate_qualification_status": CANDIDATE_QUALIFICATION_STATUS,
        "granted": dict(GRANTED_SCOPES),
        "withheld": dict(WITHHELD_SCOPES),
        "qualification_constants_that_must_stay_false": {
            name: getattr(protocol, name)
            for name in QUALIFICATION_CONSTANTS_THAT_MUST_STAY_FALSE
        },
        "allowed_scheme": ALLOWED_SCHEME,
        "allowed_host": ALLOWED_HOST,
        "allowed_port": ALLOWED_PORT,
        "allowed_origin": ALLOWED_ORIGIN,
        "allowed_method": ALLOWED_METHOD,
        "allowed_paths": list(ALLOWED_PATHS),
        "allowed_http_operations": [
            f"{method} {path}" for method, path in ALLOWED_HTTP_OPERATIONS
        ],
        "allowed_urls": list(ALLOWED_URLS),
        "allowed_request_headers": list(ALLOWED_REQUEST_HEADERS),
        "request_body_permitted": False,
        "credential_env_checked_by_name_only": CREDENTIAL_ENV,
        "refused_paths": list(REFUSED_PATHS),
        "refused_hosts": list(REFUSED_HOSTS),
        "refused_methods": list(REFUSED_METHODS),
        "refused_request_headers": list(REFUSED_REQUEST_HEADERS),
        "capture_callable": AUTHORIZED_CAPTURE_CALLABLE,
        "capture_strata": [list(item) for item in AUTHORIZED_CAPTURE_STRATA],
        "capture_experiment_config": EXPERIMENT_CONFIG_RELATIVE,
        "capture_models_config": MODELS_CONFIG_RELATIVE,
        "runtime_preflight_evidence_namespace": RUNTIME_PREFLIGHT_EVIDENCE_NAMESPACE,
        "qualification_results_namespace": QUALIFICATION_RESULTS_NAMESPACE,
        "permitted_artifact_kinds": list(PERMITTED_ARTIFACT_KINDS),
        "forbidden_artifact_kinds": list(FORBIDDEN_ARTIFACT_KINDS),
        "persistence_policy": dict(PERSISTENCE_POLICY),
        "expected_runtime_version": EXPECTED_RUNTIME_VERSION,
        "accepted_runtime_versions": list(ACCEPTED_RUNTIME_VERSIONS),
        "runtime_version_comparison": RUNTIME_VERSION_COMPARISON,
        "runtime_version_resolution": RUNTIME_VERSION_RESOLUTION,
        "expected_model_identity": dict(EXPECTED_MODEL_DIGEST),
        "bound_artifact_digests": dict(BOUND_ARTIFACT_DIGESTS),
        "seed_derivation_record": SEED_DERIVATION_RECORD_RELATIVE,
        "seed_derivation_digest": SEED_DERIVATION_DIGEST,
        "seed_derivation_algorithm": protocol.SEED_DERIVATION_ALGORITHM,
        "benchmark_version": protocol.BENCHMARK_VERSION,
        "benchmark_case_bytes_digest": BENCHMARK_CASE_BYTES_DIGEST,
        "canonical_exposure_digest": CANONICAL_EXPOSURE_DIGEST,
        "fail_closed_action": FAIL_CLOSED_ACTION,
        "fail_closed_conditions": list(FAIL_CLOSED_CONDITIONS),
        "repair_during_preflight_authorized": REPAIR_DURING_PREFLIGHT_AUTHORIZED,
        "forbidden_results_namespaces": list(FORBIDDEN_RESULTS_NAMESPACES),
        "forbidden_top_level_prefixes": list(FORBIDDEN_TOP_LEVEL_PREFIXES),
        "historical_row_access_authorized": HISTORICAL_ROW_ACCESS_AUTHORIZED,
        "phase_p_status": PHASE_P_STATUS,
        "phase_p_verdict": PHASE_P_VERDICT,
        "phase_p_terminal_status": PHASE_P_TERMINAL_STATUS,
        "provider_contacted": False,
        "model_inference_performed": False,
        "qualification_executed": False,
        "confirmatory_executed": False,
        "randomization_realized": False,
        "candidate_refrozen": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Report the narrow authorization and its offline verdict. Contacts nothing."""

    import argparse  # noqa: PLC0415 - CLI only

    parser = argparse.ArgumentParser(
        description="Successor runtime-preflight contact authorization"
    )
    parser.add_argument(
        "--json", action="store_true", help="emit the machine record as JSON"
    )
    parser.add_argument(
        "--write-record",
        action="store_true",
        help="write the machine record; refuses to overwrite an existing one",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.write_record:
        target = PROJECT_ROOT / MACHINE_RECORD_RELATIVE
        if target.exists():
            print(
                f"REFUSED: {MACHINE_RECORD_RELATIVE} already exists; the "
                "authorization record is written once and never overwritten"
            )
            return EXIT_HOLD
        payload = json.dumps(
            machine_record(), ensure_ascii=False, indent=2, sort_keys=True
        )
        target.write_text(payload + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {MACHINE_RECORD_RELATIVE}")
        return EXIT_OK

    failures = offline_validation()
    if args.json:
        print(
            json.dumps(
                {**machine_record(), "failures": failures}, indent=2, sort_keys=True
            )
        )
    else:
        print(json.dumps(machine_record(), indent=2, sort_keys=True))
        for failure in failures:
            print(failure)
    print(
        f"Successor runtime-preflight contact authorization: "
        f"{'PASS' if not failures else 'FAIL'} ({len(failures)} failure(s)); "
        "NO PROVIDER CONTACT; NO MODEL INFERENCE; NO CAPTURE PERFORMED"
    )
    return EXIT_OK if not failures else EXIT_HOLD


if __name__ == "__main__":
    raise SystemExit(main())
