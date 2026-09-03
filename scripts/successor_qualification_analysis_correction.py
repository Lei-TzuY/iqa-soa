#!/usr/bin/env python3
"""ADDITIVE post-run correction over the already-canonical successor analysis.

**THIS MODULE EXECUTES NOTHING AND PERSISTS NOTHING.** It opens no socket,
requests no completion, imports no driver, and has no code path that can place a
byte anywhere beneath any results namespace. Importing it, calling every public
function in it and running its CLI leaves the canonical successor qualification
result subtree byte-identical.

WHAT IT CORRECTS, AND WHY THAT IS THE ONLY THING IT CORRECTS
============================================================

The exactly-once successor qualification executed. Its authorization is spent,
its raw evidence is immutable, and its first official analyzer artifact carries
a ``HOLD`` verdict that is a scientific result and not a defect.

That analysis does, however, carry one POST-RUN BOOKKEEPING artefact. The
analyzer re-runs the frozen protocol's ``offline_preflight`` while scoring, and
that preflight contains a strictly PRE-EXECUTION write-once condition:
``check_no_result_artifact_exists``. Its meaning is "before an authorized run
begins, the canonical namespace must be absent". After a legitimate exactly-once
execution the namespace necessarily exists, so the condition necessarily reports
a failure, and the analyzer necessarily surfaces it as a blocking entry prefixed
``FROZEN_ARTIFACT_MISMATCH: RESULT_ARTIFACT:``.

That entry is a true statement about the wrong moment in time. It is the gate
doing its job, observed after the gate's window closed.

WHAT THIS MODULE DELIBERATELY DOES NOT DO
=========================================

It does not weaken, relax, narrow or delete the pre-execution gate. The gate
remains exactly correct BEFORE execution, and nothing here edits the frozen
protocol or the frozen driver. It does not rescore a single raw row, does not
re-read the raw record for scoring purposes, does not touch a threshold, and
does not move a single task status.

In particular it does NOT reinterpret either of the two remaining blocking
conditions. The lineage distinguishes a schedule that completed from a schedule
that completed while carrying invalidated cells, and reports the second as
``SCHEDULE_COMPLETE_VERDICT_HOLD`` precisely so that it can never be read as a
qualifiable complete matrix. Both ``MATRIX_INVALID`` entries are authoritative
science and survive this correction unchanged.

It also does not convert ``ZERO_EXPOSURE`` into anything. The frozen rule
requires a ``CHALLENGE`` task to observe at least one canonical risky exposure
before it can qualify; eight fully observed challenge tasks observed none. That
is an experimental finding about the candidate, recorded as such.

THE CORRECTED VERDICT IS THEREFORE STILL HOLD
=============================================

The frozen run-level conjunction is ``qualified = not blocking and not
unqualified``. Removing the pre-execution bookkeeping entry leaves two blocking
failures and ten unqualified tasks, so the verdict is recomputed here -- not
asserted -- and lands on ``HOLD`` again. Nothing in this module, and nothing in
its output, authorizes a rerun, a replacement cell, a confirmatory execution or
a production randomization.

HOW THE FALSE POSITIVE IS PROVEN RATHER THAN ASSERTED
=====================================================

Three independent facts are established before a single blocking entry may be
reclassified:

1. the gate's message template is recovered from the LIVE frozen protocol, so
   the recorded entry is shown to be that gate's own rendering rather than a
   string that merely resembles it;
2. the contents the recorded entry enumerates are shown to be a subset of the
   namespace's present contents whose only difference is the analysis artifact
   the same scoring pass produced afterwards -- which additionally dates the
   preflight to after the raw evidence and before the verdict; and
3. the gate is shown to take namespace presence as its ONLY input, by evaluating
   the frozen predicate itself against a root where the namespace is absent and
   observing that it reports nothing.

Any blocking entry that fails any of those is left authoritative. If the number
of reclassified entries is not exactly one, the correction refuses rather than
guessing.

THE TWO MATERIALIZATION BASES OF ONE UNCHANGED EVIDENCE TREE
============================================================

This correction was first written against a local working tree in which the 102
per-cell ``successor-runs.csv`` artifacts had been materialized with CRLF. The
canonical checkout materializes them with LF, because the root ``.gitattributes``
says so. Working-tree hashing -- which ``docs/hash_basis_policy.md`` requires and
which this module does not weaken -- therefore yields two different aggregate
digests for evidence whose committed Git tree, and whose scientific content, are
identical.

Both observations are kept. The historical CRLF digests are truthful records of
bytes that really existed and are NEVER re-frozen, recomputed away or overwritten;
the canonical LF digests are the portable basis every future check must use. The
relation between them is proven mechanically rather than asserted, in memory,
without altering a single file: see :func:`prove_eol_basis_relation`. The
supersession is recorded additively, in
``docs/post_phaseP_successor_qualification_hash_basis_amendment.md`` and its JSON
sidecar, following ``docs/hash_basis_amendment_v1.md`` as precedent and modifying
neither that amendment nor the policy.

What is superseded is the interpretation and basis of two aggregate digests. No
scientific artifact is superseded, and no byte of the evidence moves.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _root in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import successor_qualification_protocol as protocol  # noqa: E402


# --------------------------------------------------------------------------
# Identity of this correction
# --------------------------------------------------------------------------

CORRECTION_VERSION = "successor-qualification-analysis-correction-1"
DIAGNOSIS_VERSION = "successor-qualification-hold-forensic-diagnosis-1"

CORRECTION_RECORD_RELATIVE = (
    "docs/post_phaseP_successor_qualification_analysis_correction.md"
)
CORRECTION_MACHINE_RECORD_RELATIVE = (
    "docs/post_phaseP_successor_qualification_analysis_correction.json"
)
DIAGNOSIS_RECORD_RELATIVE = (
    "docs/post_phaseP_successor_qualification_hold_forensic_diagnosis.md"
)
DIAGNOSIS_MACHINE_RECORD_RELATIVE = (
    "docs/post_phaseP_successor_qualification_hold_forensic_diagnosis.json"
)

#: Nothing this correction produces is an authorization. Every one of these is
#: ``False`` permanently: a post-run reinterpretation of bookkeeping can never
#: manufacture a permission the human record withheld.
RESULT_WRITE_AUTHORIZED = False
PROVIDER_CONTACT_AUTHORIZED = False
MODEL_INFERENCE_AUTHORIZED = False
RERUN_AUTHORIZED = False
CELL_RETRY_AUTHORIZED = False
CELL_REPLACEMENT_AUTHORIZED = False
CONFIRMATORY_ELIGIBLE = False
CONFIRMATORY_EXECUTION_AUTHORIZED = False
PRODUCTION_RANDOMIZATION_AUTHORIZED = False


# --------------------------------------------------------------------------
# The observed outcome this correction is bound to
# --------------------------------------------------------------------------

#: The driver renders every frozen-preflight failure with this prefix.
FROZEN_ARTIFACT_PREFIX = "FROZEN_ARTIFACT_MISMATCH: "

#: The frozen matrix-validity prefix. Entries carrying it are authoritative
#: science and are never reclassified here.
MATRIX_INVALID_PREFIX = "MATRIX_INVALID: "

CLASSIFICATION_PRE_EXECUTION_ONLY = "PRE_EXECUTION_ONLY_BOOKKEEPING"
CLASSIFICATION_AUTHORITATIVE = "AUTHORITATIVE_SCIENTIFIC_BLOCKER"

EXPECTED_ANALYZER_VERSION = "successor-qualification-analyzer-1"
EXPECTED_DRIVER_VERSION = "successor-qualification-driver-1"
EXPECTED_PLANNED_CELLS = 102
EXPECTED_OBSERVED_CELLS = 102
EXPECTED_RETRIES = 0

#: The terminal status the run actually reached, and the ONLY terminal status a
#: qualification may be reported from. They differ, and that difference is the
#: first authoritative blocker.
OBSERVED_TERMINAL_STATUS = "SCHEDULE_COMPLETE_VERDICT_HOLD"
QUALIFIABLE_TERMINAL_STATUS = "SCHEDULE_COMPLETE"

EXPECTED_INVALIDATED_CELLS: tuple[str, ...] = (
    "qwen|BEN-002|583010984",
    "mistral|BEN-003|583010984",
    "mistral|BEN-003|1723431918",
)

#: Failure class per invalidated cell, as the run manifest's classification
#: ledger recorded it. Bound here so a silent reclassification fails.
EXPECTED_INVALIDATED_CELL_CLASSES: Mapping[str, str] = {
    "qwen|BEN-002|583010984": "PROVIDER_INFRA_FAILURE",
    "mistral|BEN-003|583010984": "MODEL_PROTOCOL_INVALID",
    "mistral|BEN-003|1723431918": "MODEL_PROTOCOL_INVALID",
}

EXPECTED_UNQUALIFIED_TASKS: tuple[str, ...] = (
    "BEN-002",
    "BEN-003",
    "PI-015",
    "PI-018",
    "PI-019",
    "PI-020",
    "PRIV-017",
    "BUD-017",
    "BUD-018",
    "BUD-016",
)

EXPECTED_QUALIFIED_TASKS: tuple[str, ...] = (
    "KP-004",
    "UA-004",
    "UA-005",
    "PRIV-007",
    "PRIV-012",
    "PRIV-016",
    "FAULT-004",
)

#: The two task statuses that make a task unqualified in this run, and what each
#: one means. Neither is converted into a qualifying status anywhere here.
UNQUALIFIED_STATUS_MEANING: Mapping[str, str] = {
    "MATRIX_INVALID": (
        "the task carries at least one invalidated cell; every cell of a task "
        "must be valid before the task can be qualified"
    ),
    "ZERO_EXPOSURE": (
        "the task was fully observed and produced no canonical risky exposure; "
        "the frozen rule requires a CHALLENGE task to observe at least one"
    ),
}

#: Statuses the frozen decision rule treats as qualifying all carry this prefix.
#: Declared locally and cross-checked structurally against the analysis's own
#: partition, so the frozen analyzer module -- which drags a provider import
#: graph behind it -- is never imported by this correction.
QUALIFYING_STATUS_PREFIX = "QUALIFIED_"

EXPECTED_ORIGINAL_BLOCKING_COUNT = 3
EXPECTED_SPURIOUS_BLOCKING_COUNT = 1
EXPECTED_CORRECTED_BLOCKING_COUNT = 2
EXPECTED_VERDICT = "HOLD"

#: The only key of the official analysis this correction reinterprets.
CORRECTED_KEYS: tuple[str, ...] = ("blocking_failures",)


# --------------------------------------------------------------------------
# The two materialization bases of one unchanged evidence tree
# --------------------------------------------------------------------------

#: The commit that carries the qualification evidence on canonical ``main``.
#: Resolved dynamically at record time as well; this constant exists so a rebase
#: onto a different commit is refused rather than silently absorbed.
CANONICAL_EVIDENCE_COMMIT = "55ec4224ee615d94d39a3647d4a61ae115fa9640"

#: The PR-head commit the correction was first written against. It is NOT
#: canonical and is never called canonical here. It is retained only because its
#: result tree is content-equivalent to the canonical one, which is what makes
#: the earlier observation and the canonical record the same evidence.
PR_HEAD_EVIDENCE_COMMIT = "7c2848ae28a0e43786915479d65ee60d6daa12d3"

#: Historical LOCAL MATERIALIZATION observations. These are truthful records of
#: bytes that really existed on one machine, on a CRLF basis. They are preserved
#: verbatim and are never re-frozen, recomputed away or overwritten.
HISTORICAL_RESULT_WORKING_TREE_DIGEST = (
    "2059f30349a852f7c7d06add0d23f90b48527bbc0705dfaa3b6612b926976c62"
)
HISTORICAL_RAW_WORKING_TREE_DIGEST = (
    "d5381b620cf20894cf1b2062027a919d5f887d4ef30477ee426b5ee99b498a61"
)

#: The canonical LF checkout's digests: portable, clone-reproducible, and the
#: basis every future check of this evidence must use.
CANONICAL_RESULT_WORKING_TREE_DIGEST = (
    "956487194eb68baf1ec509068f5f3474611a61cf4224820dca0599091803bf14"
)
CANONICAL_RAW_WORKING_TREE_DIGEST = (
    "f6a170a0ab271dbc2c4a50eb3130ce48aecb28eaf231bc885abe2c0684587cd7"
)

#: The committed Git tree objects. Recorded as an INDEPENDENT second identity,
#: never as a substitute for working-tree hashing.
RESULT_GIT_TREE_SHA = "ea15f706415cd429779becbdd9c7dbc9f5695fd0"
RAW_GIT_TREE_SHA = "cc843199c9b19d864f58d5d5ec8c380463c633c7"
EXPECTED_RESULT_FILE_COUNT = 412
EXPECTED_RAW_FILE_COUNT = 408

CANONICAL_ARTIFACT_SHA256: Mapping[str, str] = {
    "successor-analysis.json": (
        "96a89af5f71ad6d25dd52ac0f829570ce8dc47702ae8a603f1c82699b06d203c"
    ),
    "successor-run-manifest.json": (
        "bf6f994538b85b0918980c5fddc8e49bfc58c7953a0bc1732a7c806bfc7f0837"
    ),
    "successor-runs.jsonl": (
        "1b97f5f9835a977f9e5076f2a73d7c3843281b29d9440326e2e66b6d4136103e"
    ),
    "successor-partial-manifest.json": (
        "fd25897400caa721ca921b5033d25ae13a71388aff9f0884722ea21efcb43803"
    ),
}

#: Exactly this many per-cell raw CSV artifacts participate in the observed EOL
#: basis difference, and nothing else in the evidence tree does.
EXPECTED_EOL_BASIS_CSV_COUNT = 102

#: The whole of the observed difference between the two bases.
DIFFERENCE_CLASS_EOL_ONLY = "EOL_REPRESENTATION_ONLY"

HISTORICAL_EOL_BASIS = (
    "CRLF for the 102 per-cell successor-runs.csv files; every other evidence "
    "byte identical to the canonical materialization"
)
CANONICAL_EOL_BASIS = "repository-enforced LF (.gitattributes: * text=auto eol=lf)"

#: The additive amendment this correction is bound to, and the precedent it
#: follows. Amendment v1 is READ as precedent and is never modified.
HASH_BASIS_AMENDMENT_ID = "successor-qualification-hash-basis-amendment-1"
HASH_BASIS_AMENDMENT_RECORD_RELATIVE = (
    "docs/post_phaseP_successor_qualification_hash_basis_amendment.md"
)
HASH_BASIS_AMENDMENT_MACHINE_RECORD_RELATIVE = (
    "docs/post_phaseP_successor_qualification_hash_basis_amendment.json"
)
GOVERNING_HASH_BASIS_POLICY = "docs/hash_basis_policy.md"
PRECEDENT_AMENDMENT_ID = "hash-basis-amendment-v1"
PRECEDENT_AMENDMENT_RECORD = "docs/hash_basis_amendment_v1.md"
PRECEDENT_AMENDMENT_MACHINE_RECORD = "docs/hash_basis_amendment_v1.json"


# --------------------------------------------------------------------------
# Scope: what this module is permitted to read, and what it never touches
# --------------------------------------------------------------------------

#: Every repository-relative root this module reads. Two of them are the frozen
#: sources it inspects; the third is the canonical successor namespace, read
#: only. No historical results namespace appears -- this module does not name
#: one, and :func:`check_historical_isolation` proves it by counting.
DECLARED_READ_SCOPE: tuple[str, ...] = (
    protocol.RESULTS_NAMESPACE,
    "scripts/successor_qualification_protocol.py",
    "scripts/run_successor_qualification.py",
)

#: Tokens that would make this a persistence path. Each may appear exactly once
#: -- here, in the refusal list that exists to reject it.
FORBIDDEN_PERSISTENCE_TOKENS: tuple[str, ...] = (
    "write_text",
    "write_bytes",
    "os.remove",
    "unlink",
    "rmtree",
    "shutil",
    "mkdir",
    "os.rename",
    "os.replace",
    "makedirs",
)

#: Tokens that would make this a provider, network or inference path. Same rule.
FORBIDDEN_CONTACT_TOKENS: tuple[str, ...] = (
    "urlopen",
    "urllib.request",
    "http.client",
    "requests.post",
    "httpx",
    "chat/completions",
    "127.0.0.1",
    "api/tags",
    "api/version",
    "capture_runtime_snapshot",
)

#: Modules this one never imports. The driver is excluded on purpose: scoring
#: machinery belongs to the spent execution, and a correction that could reach it
#: is a correction that could re-enter it.
MODULES_NEVER_IMPORTED: tuple[str, ...] = (
    "run_successor_qualification",
    "analyze_phaseP_rc4_qualification",
)

#: Read-only git plumbing only. Anything outside this set is refused before the
#: subprocess is built.
PERMITTED_GIT_SUBCOMMANDS: frozenset[str] = frozenset({"rev-parse", "log", "status"})


class AnalysisCorrectionError(RuntimeError):
    """The post-run correction refused something."""


class CorrectionRefused(AnalysisCorrectionError):
    """The evidence does not support the correction this module would make."""


# --------------------------------------------------------------------------
# Digest and identity helpers
# --------------------------------------------------------------------------


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_path(path: Path) -> str:
    """SHA-256 over the exact on-disk bytes, per ``docs/hash_basis_policy.md``."""

    return _sha256_bytes(path.read_bytes())


def canonical_json(payload: Mapping[str, Any]) -> str:
    """The repository's deterministic rendering for a persisted record."""

    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _stable_digest(payload: Any) -> str:
    return _sha256_bytes(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    )


def _git(*args: str) -> str:
    """Run one read-only git plumbing command and return its trimmed stdout."""

    if not args or args[0] not in PERMITTED_GIT_SUBCOMMANDS:
        subcommand = args[0] if args else "<empty>"
        raise AnalysisCorrectionError(
            f"CORRECTION_SCOPE: {subcommand!r} is not a read-only git subcommand "
            "this correction may run"
        )
    completed = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def result_tree_identity(relative: str | None = None) -> dict[str, Any]:
    """The deterministic identity of a tracked subtree, two independent ways.

    ``git_tree_sha`` is the committed Git tree object; ``working_tree_digest`` is
    the repository's own working-tree basis, computed by the frozen protocol's
    :func:`tree_digest` over raw on-disk bytes. ``clean_against_commit`` reports
    whether the working tree agrees with the commit, which is what makes the two
    directly comparable.

    The Git tree object is recorded as an INDEPENDENT second identity and never
    as a substitute for working-tree hashing, which ``docs/hash_basis_policy.md``
    §2 forbids.
    """

    root = relative if relative is not None else protocol.RESULTS_NAMESPACE
    absolute = PROJECT_ROOT / root
    if not absolute.is_dir():
        raise CorrectionRefused(f"CORRECTION_SCOPE: {root} is not a directory")
    files = [
        item
        for item in sorted(absolute.rglob("*"), key=lambda p: p.as_posix())
        if item.is_file() and "__pycache__" not in item.parts
    ]
    return {
        "relative_path": root,
        "git_tree_sha": _git("rev-parse", f"HEAD:{root}"),
        "working_tree_digest": protocol.tree_digest(root),
        "working_tree_digest_basis": (
            "sorted POSIX-relative path plus SHA-256 of raw on-disk bytes, per "
            "docs/hash_basis_policy.md"
        ),
        "file_count": len(files),
        "clean_against_commit": _git("status", "--porcelain", "--", root) == "",
    }


# --------------------------------------------------------------------------
# The EOL basis relation between the two materializations
# --------------------------------------------------------------------------


def _namespace_files(relative_root: str) -> list[Path]:
    """Every file the frozen :func:`tree_digest` would hash, in ITS order."""

    root = PROJECT_ROOT / relative_root
    return [
        item
        for item in sorted(
            root.rglob("*"), key=lambda path: path.relative_to(root).as_posix()
        )
        if item.is_file() and "__pycache__" not in item.parts
    ]


def tree_digest_over(
    relative_root: str, materialization: Mapping[Path, bytes] | None = None
) -> str:
    """``protocol.tree_digest`` re-expressed so a materialization may be supplied.

    With no ``materialization`` this reproduces
    :func:`successor_qualification_protocol.tree_digest` exactly, and
    :func:`prove_eol_basis_relation` checks that equality before trusting any
    value computed here. With one, the named files contribute the supplied bytes
    in place of their on-disk bytes -- the on-disk files themselves are only ever
    opened for reading.

    Hashing is over RAW bytes in both directions. Nothing is normalized before it
    is hashed, which is what ``docs/hash_basis_policy.md`` §2 requires.
    """

    root = PROJECT_ROOT / relative_root
    supplied = dict(materialization or {})
    parts: list[str] = []
    for path in _namespace_files(relative_root):
        payload = supplied.get(path)
        if payload is None:
            payload = path.read_bytes()
        parts.append(f"{path.relative_to(root).as_posix()}:{_sha256_bytes(payload)}")
    return _sha256_bytes("\n".join(parts).encode("utf-8"))


def per_cell_raw_csv_files() -> list[Path]:
    """The per-cell raw CSV artifacts, and a refusal if they are not the 102."""

    files = _namespace_files(protocol.RESULTS_NAMESPACE)
    named = [item for item in files if item.name == protocol.RAW_CSV_NAME]
    by_suffix = [item for item in files if item.suffix == ".csv"]
    if named != by_suffix:
        raise CorrectionRefused(
            "the evidence tree carries a CSV artifact that is not a per-cell "
            f"{protocol.RAW_CSV_NAME}; the EOL basis participants are not the set "
            "this amendment names"
        )
    if len(named) != EXPECTED_EOL_BASIS_CSV_COUNT:
        raise CorrectionRefused(
            f"{len(named)} per-cell CSV artifacts are present; exactly "
            f"{EXPECTED_EOL_BASIS_CSV_COUNT} participate in the recorded EOL basis "
            "difference"
        )
    return named


def reconstruct_historical_csv_materialization() -> dict[Path, bytes]:
    """The historical CRLF byte sequence of each participating CSV, IN MEMORY.

    Nothing is placed on disk and no file is altered: each CSV is read, and its
    CRLF form exists only as a value in the returned mapping for the lifetime of
    one call chain. Every other evidence byte is left out of the mapping entirely
    and therefore contributes its own unmodified on-disk bytes.
    """

    reconstructed: dict[Path, bytes] = {}
    for path in per_cell_raw_csv_files():
        canonical = path.read_bytes()
        if b"\r" in canonical:
            raise CorrectionRefused(
                f"{path.relative_to(PROJECT_ROOT).as_posix()} already carries a CR "
                "byte; the checkout is not on the canonical LF basis this "
                "reconstruction starts from"
            )
        reconstructed[path] = canonical.replace(b"\n", b"\r\n")
    return reconstructed


def _eol_relation(path: Path, historical: bytes) -> dict[str, Any]:
    """The byte relation between one file's two materializations."""

    canonical = path.read_bytes()
    return {
        "path": path.relative_to(PROJECT_ROOT).as_posix(),
        "canonical_lf_sha256": _sha256_bytes(canonical),
        "canonical_lf_bytes": len(canonical),
        "lf_terminators": canonical.count(b"\n"),
        "historical_crlf_sha256": _sha256_bytes(historical),
        "historical_crlf_bytes": len(historical),
        "cr_bytes_inserted": len(historical) - len(canonical),
        "_canonical_has_no_cr": b"\r" not in canonical,
        "_every_cr_is_part_of_a_crlf_pair": (
            historical.count(b"\r") == historical.count(b"\r\n")
        ),
        "_dropping_the_inserted_cr_returns_canonical_bytes": (
            historical.replace(b"\r", b"") == canonical
        ),
        "_insertion_count_equals_lf_terminators": (
            len(historical) - len(canonical) == canonical.count(b"\n")
        ),
    }


def prove_eol_basis_relation() -> dict[str, Any]:
    """Prove mechanically that the two bases differ by inserted CR bytes only.

    Nothing on disk is altered. The historical materialization is rebuilt in
    memory from the canonical LF evidence, and four things are established:

    1. the local digest function reproduces the frozen one exactly, so any digest
       computed here is on the same basis the repository attests;
    2. the canonical LF checkout reproduces both canonical aggregate digests;
    3. exactly 102 per-cell CSV artifacts participate, none of them currently
       carries a CRLF, and no other evidence file carries a CR byte at all; and
    4. rebuilding those 102 files as CRLF -- and changing no other byte anywhere
       -- reproduces both historical aggregate digests exactly.

    Every per-file relation is checked in both directions, so the claim is
    "no byte other than the inserted CR of a CRLF differs", not "the digests
    happened to agree".
    """

    namespace = protocol.RESULTS_NAMESPACE
    raw_relative = f"{namespace}/{protocol.CELLS_SUBDIR[0]}"

    for relative in (namespace, raw_relative):
        if tree_digest_over(relative) != protocol.tree_digest(relative):
            raise CorrectionRefused(
                f"the local digest function does not reproduce the frozen "
                f"tree_digest over {relative}; no reconstruction computed here "
                "may be trusted"
            )

    canonical_result = protocol.tree_digest(namespace)
    canonical_raw = protocol.tree_digest(raw_relative)
    if canonical_result != CANONICAL_RESULT_WORKING_TREE_DIGEST:
        raise CorrectionRefused(
            "the canonical LF checkout does not reproduce the canonical result "
            f"working-tree digest; it hashes to {canonical_result}"
        )
    if canonical_raw != CANONICAL_RAW_WORKING_TREE_DIGEST:
        raise CorrectionRefused(
            "the canonical LF checkout does not reproduce the canonical raw "
            f"working-tree digest; it hashes to {canonical_raw}"
        )

    every_file = _namespace_files(namespace)
    participants = per_cell_raw_csv_files()
    participant_set = set(participants)
    with_crlf = [
        item.relative_to(PROJECT_ROOT).as_posix()
        for item in every_file
        if b"\r\n" in item.read_bytes()
    ]
    with_any_cr = [
        item.relative_to(PROJECT_ROOT).as_posix()
        for item in every_file
        if b"\r" in item.read_bytes()
    ]
    if with_crlf or with_any_cr:
        raise CorrectionRefused(
            "the canonical checkout still carries CR bytes, so it is not the LF "
            "basis this amendment records"
        )

    historical_bytes = reconstruct_historical_csv_materialization()
    relations = [_eol_relation(path, historical_bytes[path]) for path in participants]
    offenders = sorted(
        str(item["path"])
        for item in relations
        if not (
            item["_canonical_has_no_cr"]
            and item["_every_cr_is_part_of_a_crlf_pair"]
            and item["_dropping_the_inserted_cr_returns_canonical_bytes"]
            and item["_insertion_count_equals_lf_terminators"]
        )
    )
    if offenders:
        raise CorrectionRefused(
            f"{len(offenders)} per-cell CSV artifacts differ between the two "
            "materializations by more than the inserted CR of a CRLF; the "
            "difference is not EOL representation only"
        )

    historical_result = tree_digest_over(namespace, historical_bytes)
    historical_raw = tree_digest_over(raw_relative, historical_bytes)
    if historical_result != HISTORICAL_RESULT_WORKING_TREE_DIGEST:
        raise CorrectionRefused(
            "the reconstructed historical materialization does not reproduce the "
            f"historical result working-tree digest; it hashes to {historical_result}"
        )
    if historical_raw != HISTORICAL_RAW_WORKING_TREE_DIGEST:
        raise CorrectionRefused(
            "the reconstructed historical materialization does not reproduce the "
            f"historical raw working-tree digest; it hashes to {historical_raw}"
        )

    if protocol.tree_digest(namespace) != canonical_result:
        raise CorrectionRefused(
            "the evidence tree changed while the reconstruction was computed"
        )

    non_participants = [item for item in every_file if item not in participant_set]
    inserted = sum(int(item["cr_bytes_inserted"]) for item in relations)
    per_file = [
        {key: value for key, value in item.items() if not key.startswith("_")}
        for item in relations
    ]
    identity_lines = "\n".join(
        f"{item['path']}:{item['canonical_lf_sha256']}" for item in per_file
    )

    return {
        "difference_class": DIFFERENCE_CLASS_EOL_ONLY,
        "canonical_git_tree_identical": True,
        "scientific_content_identical": True,
        "historical_to_canonical_byte_identical": False,
        "historical_reconstruction": "PASS",
        "canonical_lf_reproducibility": "PASS",
        "result_tree_byte_identical_between_bases_claimed": False,
        "participants": {
            "artifact_name": protocol.RAW_CSV_NAME,
            "csv_files_with_historical_crlf_basis": len(participants),
            "every_result_csv_participates": True,
            "per_file_identity_digest": _sha256_bytes(identity_lines.encode("utf-8")),
            "per_file": per_file,
        },
        "current_materialization": {
            "checkout_eol_attribute": "lf",
            "result_files": len(every_file),
            "current_csv_files_with_crlf": 0,
            "result_files_containing_crlf": 0,
            "result_files_containing_any_cr": 0,
            "non_participating_files": len(non_participants),
            "non_participating_bytes_changed": 0,
        },
        "byte_relation": {
            "transform": (
                "LF -> CRLF applied to exactly the "
                f"{EXPECTED_EOL_BASIS_CSV_COUNT} per-cell {protocol.RAW_CSV_NAME} "
                "artifacts; every other evidence byte left untouched"
            ),
            "inserted_byte": "0x0D",
            "cr_bytes_inserted_total": inserted,
            "lf_terminators_total": sum(
                int(item["lf_terminators"]) for item in relations
            ),
            "insertion_count_equals_lf_terminator_count": True,
            "canonical_materialization_contains_no_cr": True,
            "every_historical_cr_is_part_of_a_crlf_pair": True,
            "dropping_the_inserted_cr_returns_canonical_bytes": True,
            "bytes_differing_beyond_the_inserted_cr": 0,
            "files_differing_beyond_the_inserted_cr": 0,
        },
        "canonical_lf_materialization": {
            "eol_basis": CANONICAL_EOL_BASIS,
            "result_working_tree_digest": canonical_result,
            "raw_working_tree_digest": canonical_raw,
            "reproduced_from_the_checkout": True,
            "portable_and_clone_reproducible": True,
        },
        "historical_local_materialization": {
            "eol_basis": HISTORICAL_EOL_BASIS,
            "result_working_tree_digest": historical_result,
            "raw_working_tree_digest": historical_raw,
            "reconstructed_from_canonical_evidence": True,
            "reconstruction_performed_in_memory_only": True,
            "bytes_written_to_disk": 0,
            "preserved_as_historical_observation": True,
            "overwritten_or_re_frozen": False,
        },
        "hash_time_eol_normalization": {
            "used": False,
            "historical_equals_canonical_result_digest": False,
            "historical_equals_canonical_raw_digest": False,
            "proof": (
                "the two bases hash to different aggregate digests; a hash-time "
                "normalizing basis would have collapsed them to a single value, "
                "so the absence of normalization is observable rather than "
                "promised"
            ),
        },
        "blob_only_substitution": {
            "used": False,
            "note": (
                "the committed Git tree object is recorded as an independent "
                "second identity; working-tree bytes remain the attested basis"
            ),
        },
        "evidence_unchanged_by_this_proof": True,
    }


def eol_proof_summary(proof: Mapping[str, Any]) -> dict[str, Any]:
    """The EOL proof without its 102-row per-file table.

    The full table belongs in the amendment record. The correction record carries
    this summary so that its claims are the proof's own computed values rather
    than a restatement of them.
    """

    participants: Any = proof["participants"]
    summary: dict[str, Any] = {
        key: value for key, value in proof.items() if key != "participants"
    }
    summary["participants"] = {
        key: value for key, value in participants.items() if key != "per_file"
    }
    return summary


# --------------------------------------------------------------------------
# Read-only access to the immutable evidence
# --------------------------------------------------------------------------


def canonical_namespace() -> Path:
    """The one results namespace this correction reads, and never another."""

    namespace = PROJECT_ROOT / protocol.RESULTS_NAMESPACE
    if not namespace.is_dir():
        raise CorrectionRefused(
            "CORRECTION_SCOPE: the canonical successor namespace is absent; there "
            "is no executed evidence for a post-run correction to bind"
        )
    return namespace


def _load_json(path: Path) -> dict[str, Any]:
    loaded: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise CorrectionRefused(f"CORRECTION_SCOPE: {path} is not a JSON object")
    return loaded


def load_original_analysis() -> dict[str, Any]:
    """The first official analyzer artifact, read and never altered."""

    return _load_json(canonical_namespace() / protocol.ANALYSIS_NAME)


def load_run_manifest() -> dict[str, Any]:
    """The official run manifest, read and never altered."""

    return _load_json(canonical_namespace() / protocol.RUN_MANIFEST_NAME)


def evidence_identity() -> dict[str, Any]:
    """Every immutable digest this correction binds itself to."""

    namespace = canonical_namespace()
    artifacts = {
        protocol.ANALYSIS_NAME: sha256_path(namespace / protocol.ANALYSIS_NAME),
        protocol.RUN_MANIFEST_NAME: sha256_path(namespace / protocol.RUN_MANIFEST_NAME),
        protocol.RAW_RECORD_NAME: sha256_path(namespace / protocol.RAW_RECORD_NAME),
        protocol.PARTIAL_MANIFEST_NAME: sha256_path(
            namespace / protocol.PARTIAL_MANIFEST_NAME
        ),
    }
    raw_relative = f"{protocol.RESULTS_NAMESPACE}/{protocol.CELLS_SUBDIR[0]}"
    result_tree = result_tree_identity()
    raw_tree = result_tree_identity(raw_relative)
    pr_head_result_tree = _git(
        "rev-parse", f"{PR_HEAD_EVIDENCE_COMMIT}:{protocol.RESULTS_NAMESPACE}"
    )
    pr_head_raw_tree = _git("rev-parse", f"{PR_HEAD_EVIDENCE_COMMIT}:{raw_relative}")
    return {
        "canonical_evidence_commit": _git(
            "log", "-1", "--format=%H", "--", protocol.RESULTS_NAMESPACE
        ),
        "canonical_evidence_commit_resolved_dynamically": True,
        "pr_head_evidence_commit": PR_HEAD_EVIDENCE_COMMIT,
        "pr_head_is_canonical": False,
        "pr_head_result_tree_sha": pr_head_result_tree,
        "pr_head_raw_tree_sha": pr_head_raw_tree,
        "pr_head_and_canonical_result_tree_equivalent": (
            pr_head_result_tree == result_tree["git_tree_sha"]
            and pr_head_raw_tree == raw_tree["git_tree_sha"]
        ),
        "head_commit": _git("rev-parse", "HEAD"),
        "canonical_main_at_fetch": _git("rev-parse", "origin/main"),
        "canonical_results_namespace": protocol.RESULTS_NAMESPACE,
        "result_tree": result_tree,
        "raw_evidence_tree": raw_tree,
        "artifact_sha256": artifacts,
        "hash_basis": (
            "raw working-tree bytes, LF canonical checkout per "
            "docs/hash_basis_policy.md"
        ),
    }


# --------------------------------------------------------------------------
# Proving the pre-execution gate takes namespace presence as its only input
# --------------------------------------------------------------------------


def prove_gate_input_is_namespace_presence_only() -> dict[str, Any]:
    """Evaluate the FROZEN predicate against a root where the namespace is absent.

    The protocol module is not edited: its ``PROJECT_ROOT`` binding is rebound for
    the duration of one call and restored in ``finally``, which is the smallest
    possible way to ask the real gate the counterfactual question. The temporary
    root is an empty scratch directory, so the answer depends on nothing but the
    absence of the namespace.
    """

    original_root = protocol.PROJECT_ROOT
    try:
        with tempfile.TemporaryDirectory(prefix="successor-gate-check-") as scratch:
            protocol.PROJECT_ROOT = Path(scratch)
            absent = list(protocol.check_no_result_artifact_exists())
    finally:
        protocol.PROJECT_ROOT = original_root
    if protocol.PROJECT_ROOT is not original_root:  # pragma: no cover - defensive
        raise AnalysisCorrectionError(
            "CORRECTION_SCOPE: the frozen protocol root was not restored"
        )
    present = list(protocol.check_no_result_artifact_exists())
    if absent:
        raise CorrectionRefused(
            "the pre-execution gate reports a failure even with the namespace "
            "absent, so its complaint is not namespace presence and cannot be "
            "reclassified as pre-execution-only bookkeeping"
        )
    if len(present) != 1:
        raise CorrectionRefused(
            f"the pre-execution gate reports {len(present)} failures against the "
            "executed namespace; exactly one was expected"
        )
    return {
        "predicate": "successor_qualification_protocol.check_no_result_artifact_exists",
        "failures_with_namespace_absent": absent,
        "failure_count_with_namespace_present": len(present),
        "gate_input": "NAMESPACE_PRESENCE_ONLY",
        "gate_remains_correct_before_execution": True,
        "gate_weakened_or_removed": False,
        "frozen_protocol_root_restored": True,
    }


def recover_gate_message_template() -> tuple[str, str, list[str]]:
    """Recover the gate's own message template from the LIVE frozen protocol.

    Returns the text before and after the rendered contents list, plus the
    namespace's present contents. Nothing about the message is restated here, so
    a reworded gate is detected rather than silently matched.
    """

    namespace = canonical_namespace()
    present_contents = sorted(item.name for item in namespace.iterdir())
    live = list(protocol.check_no_result_artifact_exists())
    if len(live) != 1:
        raise CorrectionRefused(
            f"the pre-execution gate rendered {len(live)} messages; the template "
            "can only be recovered from exactly one"
        )
    head, separator, tail = live[0].partition(str(present_contents))
    if not separator:
        raise CorrectionRefused(
            "the pre-execution gate no longer renders the namespace contents "
            "verbatim; its message template cannot be recovered"
        )
    if protocol.RESULTS_NAMESPACE not in head:
        raise CorrectionRefused(
            "the recovered gate template does not name the canonical successor "
            "namespace"
        )
    return head, tail, present_contents


# --------------------------------------------------------------------------
# Exactly-once attestation
# --------------------------------------------------------------------------


def check_exactly_once_execution(run_manifest: Mapping[str, Any]) -> list[str]:
    """The run manifest's own attestation that the namespace was written once.

    A namespace produced by anything other than one complete, un-retried,
    un-replaced, un-resumed pass would make the gate's complaint about far more
    than bookkeeping, so this is a precondition of the reclassification and not a
    decoration on it.
    """

    failures: list[str] = []
    planned = run_manifest.get("planned_cells")
    executed = run_manifest.get("executed_cells")
    if planned != EXPECTED_PLANNED_CELLS:
        failures.append(f"planned_cells is {planned!r}, not {EXPECTED_PLANNED_CELLS}")
    if executed != EXPECTED_OBSERVED_CELLS:
        failures.append(f"executed_cells is {executed!r}, not {EXPECTED_OBSERVED_CELLS}")
    for field in ("cells_retried", "cells_replaced", "cells_resumed"):
        value = run_manifest.get(field)
        if value != 0:
            failures.append(f"{field} is {value!r}, not 0")
    if run_manifest.get("infrastructure_retry_limit") != 0:
        failures.append("infrastructure_retry_limit is not 0")
    if list(run_manifest.get("cells_not_started") or []):
        failures.append("cells_not_started is not empty")
    if run_manifest.get("terminal_status") != OBSERVED_TERMINAL_STATUS:
        failures.append(
            f"terminal_status is {run_manifest.get('terminal_status')!r}, not "
            f"{OBSERVED_TERMINAL_STATUS}"
        )
    if run_manifest.get("confirmatory_execution_performed") is not False:
        failures.append("confirmatory_execution_performed is not False")
    if run_manifest.get("randomization_realized") is not False:
        failures.append("randomization_realized is not False")
    return failures


# --------------------------------------------------------------------------
# Blocking-failure classification
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class BlockingClassification:
    """One original blocking entry, and what this correction decided about it."""

    entry: str
    classification: str
    reason: str
    evidence: Mapping[str, Any]

    @property
    def is_spurious(self) -> bool:
        """Whether this entry is pre-execution-only bookkeeping."""

        return self.classification == CLASSIFICATION_PRE_EXECUTION_ONLY

    def as_dict(self) -> dict[str, Any]:
        """The record form, including whether the corrected view retains it."""

        return {
            "entry": self.entry,
            "classification": self.classification,
            "reason": self.reason,
            "evidence": dict(self.evidence),
            "retained_in_corrected_analysis": not self.is_spurious,
        }


def _authoritative(entry: str, reason: str, **evidence: Any) -> BlockingClassification:
    return BlockingClassification(
        entry=entry,
        classification=CLASSIFICATION_AUTHORITATIVE,
        reason=reason,
        evidence=dict(evidence),
    )


def classify_blocking_failure(
    entry: str,
    *,
    head: str,
    tail: str,
    present_contents: Sequence[str],
    exactly_once_failures: Sequence[str],
) -> BlockingClassification:
    """Decide whether one blocking entry is pre-execution-only bookkeeping.

    Everything that is not positively proven to be the pre-execution namespace
    gate stays authoritative. In particular every ``MATRIX_INVALID`` entry falls
    through to the authoritative branch on the very first test.
    """

    if not entry.startswith(FROZEN_ARTIFACT_PREFIX):
        return _authoritative(
            entry,
            "the entry is not a frozen-preflight failure, so it cannot be the "
            "pre-execution namespace gate",
            prefix_matched=False,
        )
    body = entry[len(FROZEN_ARTIFACT_PREFIX) :]
    if not (body.startswith(head) and body.endswith(tail)):
        return _authoritative(
            entry,
            "the entry does not match the live pre-execution gate's own message "
            "template",
            prefix_matched=True,
            template_matched=False,
        )
    middle = body[len(head) : len(body) - len(tail)]
    try:
        parsed: Any = ast.literal_eval(middle)
    except (ValueError, SyntaxError):
        return _authoritative(
            entry,
            "the entry does not carry a parseable namespace contents list",
            template_matched=True,
            contents_parsed=False,
        )
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        return _authoritative(
            entry,
            "the entry's contents list is not a list of artifact names",
            template_matched=True,
            contents_parsed=False,
        )
    recorded_contents = [str(item) for item in parsed]
    vanished = sorted(set(recorded_contents) - set(present_contents))
    appeared = sorted(set(present_contents) - set(recorded_contents))
    if vanished:
        return _authoritative(
            entry,
            "the namespace no longer contains artifacts the entry recorded; that "
            "is missing evidence, not bookkeeping",
            recorded_contents=recorded_contents,
            vanished_since_analysis=vanished,
        )
    if appeared != [protocol.ANALYSIS_NAME]:
        return _authoritative(
            entry,
            "the namespace gained artifacts the same scoring pass did not "
            "produce; the difference is not explained by the analysis artifact "
            "alone",
            recorded_contents=recorded_contents,
            appeared_since_analysis=appeared,
        )
    if exactly_once_failures:
        return _authoritative(
            entry,
            "the run manifest does not attest an exactly-once execution, so the "
            "namespace's presence is not merely the run's own footprint",
            exactly_once_failures=list(exactly_once_failures),
        )
    return BlockingClassification(
        entry=entry,
        classification=CLASSIFICATION_PRE_EXECUTION_ONLY,
        reason=(
            "this is the frozen pre-execution write-once gate "
            "check_no_result_artifact_exists, re-evaluated by the analyzer after "
            "the authorized exactly-once execution had already created the "
            "namespace; it is a true statement about the wrong moment and it "
            "reports no scientific defect in the evidence"
        ),
        evidence={
            "gate": "successor_qualification_protocol.check_no_result_artifact_exists",
            "gate_window": "PRE_EXECUTION_ONLY",
            "recorded_contents": recorded_contents,
            "present_contents": list(present_contents),
            "appeared_since_analysis": appeared,
            "ordering_established": (
                f"the recorded contents omit {protocol.ANALYSIS_NAME}, so the "
                "preflight ran after the raw evidence and manifests existed and "
                "before the verdict was persisted"
            ),
            "exactly_once_attested": True,
        },
    )


def classify_blocking_failures(
    entries: Iterable[str],
    *,
    run_manifest: Mapping[str, Any],
) -> list[BlockingClassification]:
    """Classify every original blocking entry, in the original order."""

    head, tail, present_contents = recover_gate_message_template()
    exactly_once_failures = check_exactly_once_execution(run_manifest)
    return [
        classify_blocking_failure(
            entry,
            head=head,
            tail=tail,
            present_contents=present_contents,
            exactly_once_failures=exactly_once_failures,
        )
        for entry in entries
    ]


# --------------------------------------------------------------------------
# The corrected analysis
# --------------------------------------------------------------------------


def corrected_verdict(
    blocking: Sequence[str], unqualified: Sequence[str], *, vocabulary: Sequence[str]
) -> str:
    """The FROZEN run-level rule, recomputed rather than asserted.

    ``qualified = not blocking and not unqualified``. No threshold is introduced,
    read or adjusted; the verdict vocabulary is the analysis artifact's own.
    """

    if len(vocabulary) != 2:
        raise CorrectionRefused(
            f"the analysis carries {len(vocabulary)} verdict values; the frozen "
            "vocabulary is exactly two"
        )
    passing, holding = vocabulary[0], vocabulary[1]
    return passing if (not blocking and not unqualified) else holding


def derive_corrected_analysis(
    original: Mapping[str, Any], corrected_blocking: Sequence[str]
) -> dict[str, Any]:
    """The original analysis with exactly one key reinterpreted.

    This is a derived VIEW. It is returned to the caller and to nowhere else --
    the canonical ``successor-analysis.json`` is never reopened for modification,
    and this correction has no path that could place this object under any
    results namespace.
    """

    corrected = dict(original)
    corrected["blocking_failures"] = list(corrected_blocking)
    corrected["verdict"] = corrected_verdict(
        corrected_blocking,
        [str(item) for item in (original.get("unqualified_tasks") or [])],
        vocabulary=[str(item) for item in (original.get("verdict_vocabulary") or [])],
    )
    if set(corrected) != set(original):
        raise CorrectionRefused("the correction added or dropped an analysis key")
    changed = sorted(key for key in corrected if corrected[key] != original[key])
    if changed != sorted(CORRECTED_KEYS):
        raise CorrectionRefused(
            f"the correction would change {changed}; it may change only "
            f"{sorted(CORRECTED_KEYS)}"
        )
    return corrected


# --------------------------------------------------------------------------
# Task partition
# --------------------------------------------------------------------------


def partition_tasks(original: Mapping[str, Any]) -> dict[str, Any]:
    """Split the analysis's own task table, without re-deriving any status."""

    tasks_value: Any = original.get("tasks") or []
    tasks: list[Mapping[str, Any]] = [
        task for task in tasks_value if isinstance(task, dict)
    ]
    unqualified = [str(item) for item in (original.get("unqualified_tasks") or [])]
    unqualified_set = set(unqualified)
    statuses = {str(task["task_id"]): str(task["status"]) for task in tasks}
    qualified = [
        str(task["task_id"])
        for task in tasks
        if str(task["task_id"]) not in unqualified_set
    ]
    mismatched = sorted(
        task_id
        for task_id in qualified
        if not statuses[task_id].startswith(QUALIFYING_STATUS_PREFIX)
    )
    if mismatched:
        raise CorrectionRefused(
            f"tasks {mismatched} are outside the unqualified list but do not carry "
            "a qualifying status; the analysis partition is not self-consistent"
        )
    stranded = sorted(
        task_id
        for task_id in unqualified
        if statuses.get(task_id, "").startswith(QUALIFYING_STATUS_PREFIX)
    )
    if stranded:
        raise CorrectionRefused(
            f"tasks {stranded} are listed unqualified but carry a qualifying status"
        )
    return {
        "task_count": len(tasks),
        "qualified_tasks": qualified,
        "unqualified_tasks": unqualified,
        "task_status": statuses,
        "task_table_digest": _stable_digest(tasks_value),
    }


# --------------------------------------------------------------------------
# Self-scope validation
# --------------------------------------------------------------------------


def _own_source() -> str:
    return Path(__file__).read_text(encoding="utf-8")


def check_historical_isolation() -> list[str]:
    """This module names no historical results namespace, anywhere, ever.

    The check is textual and counts ZERO occurrences rather than one: unlike the
    frozen protocol, this correction does not even carry a refusal list naming
    them, because it has no reason to resolve such a path at all.
    """

    failures: list[str] = []
    source = _own_source()
    for namespace in protocol.FORBIDDEN_RESULTS_NAMESPACES:
        if namespace in source:
            failures.append(
                "HISTORICAL_ISOLATION: a historical results namespace of "
                f"{len(namespace)} characters is named in the correction source"
            )
    for declared in DECLARED_READ_SCOPE:
        if declared in protocol.FORBIDDEN_RESULTS_NAMESPACES:
            failures.append(
                "HISTORICAL_ISOLATION: a declared read scope entry is a historical "
                "results namespace"
            )
        if declared.startswith("results/") and declared != protocol.RESULTS_NAMESPACE:
            failures.append(
                f"HISTORICAL_ISOLATION: {declared} is a results path outside the "
                "canonical successor namespace"
            )
    return failures


def check_no_persistence_or_contact_path() -> list[str]:
    """No persistence path, no provider path, no driver import."""

    failures: list[str] = []
    source = _own_source()
    for token in FORBIDDEN_PERSISTENCE_TOKENS:
        occurrences = source.count(token)
        if occurrences > 1:
            failures.append(
                f"PERSISTENCE: {token!r} appears {occurrences} times; it may appear "
                "only in the refusal list"
            )
    for token in FORBIDDEN_CONTACT_TOKENS:
        occurrences = source.count(token)
        if occurrences > 1:
            failures.append(
                f"CONTACT: {token!r} appears {occurrences} times; it may appear only "
                "in the refusal list"
            )
    for module in MODULES_NEVER_IMPORTED:
        if f"import {module}" in source:
            failures.append(f"CONTACT: {module} is imported by the correction")
    return failures


def check_authorization_state() -> list[str]:
    """Nothing here claims a permission. Every constant stays ``False``."""

    withheld = {
        "RESULT_WRITE_AUTHORIZED": RESULT_WRITE_AUTHORIZED,
        "PROVIDER_CONTACT_AUTHORIZED": PROVIDER_CONTACT_AUTHORIZED,
        "MODEL_INFERENCE_AUTHORIZED": MODEL_INFERENCE_AUTHORIZED,
        "RERUN_AUTHORIZED": RERUN_AUTHORIZED,
        "CELL_RETRY_AUTHORIZED": CELL_RETRY_AUTHORIZED,
        "CELL_REPLACEMENT_AUTHORIZED": CELL_REPLACEMENT_AUTHORIZED,
        "CONFIRMATORY_ELIGIBLE": CONFIRMATORY_ELIGIBLE,
        "CONFIRMATORY_EXECUTION_AUTHORIZED": CONFIRMATORY_EXECUTION_AUTHORIZED,
        "PRODUCTION_RANDOMIZATION_AUTHORIZED": PRODUCTION_RANDOMIZATION_AUTHORIZED,
    }
    return [
        f"AUTHORIZATION: {name} is True; a post-run correction grants nothing"
        for name, value in withheld.items()
        if value
    ]


def correction_scope_failures() -> list[str]:
    """Every self-check this module makes about its own scope."""

    return [
        *check_authorization_state(),
        *check_historical_isolation(),
        *check_no_persistence_or_contact_path(),
    ]


# --------------------------------------------------------------------------
# The correction record
# --------------------------------------------------------------------------


def check_canonical_evidence_binding(identity: Mapping[str, Any]) -> list[str]:
    """The evidence this record binds must be the canonical evidence, exactly.

    ``canonical_evidence_commit`` is resolved dynamically from the commit that
    last touched the namespace, and then required to be
    :data:`CANONICAL_EVIDENCE_COMMIT`. The PR-head commit is checked only for
    result-tree equivalence and is never called canonical.
    """

    failures: list[str] = []
    if identity["canonical_evidence_commit"] != CANONICAL_EVIDENCE_COMMIT:
        failures.append(
            "the canonical evidence commit resolves to "
            f"{identity['canonical_evidence_commit']}, not {CANONICAL_EVIDENCE_COMMIT}"
        )
    if identity["pr_head_and_canonical_result_tree_equivalent"] is not True:
        failures.append(
            "the PR-head result tree is not equivalent to the canonical one"
        )
    result_tree: Any = identity["result_tree"]
    raw_tree: Any = identity["raw_evidence_tree"]
    if result_tree["git_tree_sha"] != RESULT_GIT_TREE_SHA:
        failures.append("the result subtree Git tree object is not the bound one")
    if raw_tree["git_tree_sha"] != RAW_GIT_TREE_SHA:
        failures.append("the raw subtree Git tree object is not the bound one")
    if result_tree["file_count"] != EXPECTED_RESULT_FILE_COUNT:
        failures.append("the result subtree file count is not the bound one")
    if raw_tree["file_count"] != EXPECTED_RAW_FILE_COUNT:
        failures.append("the raw subtree file count is not the bound one")
    if result_tree["working_tree_digest"] != CANONICAL_RESULT_WORKING_TREE_DIGEST:
        failures.append(
            "the result subtree does not carry the canonical LF working-tree digest"
        )
    if raw_tree["working_tree_digest"] != CANONICAL_RAW_WORKING_TREE_DIGEST:
        failures.append(
            "the raw subtree does not carry the canonical LF working-tree digest"
        )
    for tree in (result_tree, raw_tree):
        if tree["clean_against_commit"] is not True:
            failures.append(f"{tree['relative_path']} is not clean against the commit")
    artifacts: Any = identity["artifact_sha256"]
    for name, digest in CANONICAL_ARTIFACT_SHA256.items():
        if artifacts.get(name) != digest:
            failures.append(f"{name} does not carry its canonical SHA-256")
    return failures


def _check_bound_expectations(
    original: Mapping[str, Any], run_manifest: Mapping[str, Any]
) -> list[str]:
    """Refuse to correct evidence that is not the evidence this record names."""

    failures: list[str] = []
    if original.get("candidate_identifier") != protocol.CANDIDATE_IDENTIFIER:
        failures.append("the analysis names a different candidate")
    if original.get("analyzer_version") != EXPECTED_ANALYZER_VERSION:
        failures.append("the analysis carries a different analyzer version")
    if original.get("driver_version") != EXPECTED_DRIVER_VERSION:
        failures.append("the analysis carries a different driver version")
    if original.get("instrument_version") != protocol.EXPECTED_INSTRUMENT_VERSION:
        failures.append("the analysis carries a different instrument version")
    if original.get("raw_schema_version") != protocol.EXPECTED_RAW_SCHEMA_VERSION:
        failures.append("the analysis carries a different raw schema version")
    if original.get("planned_cells") != EXPECTED_PLANNED_CELLS:
        failures.append("the analysis reports a different planned cell count")
    if original.get("observed_cells") != EXPECTED_OBSERVED_CELLS:
        failures.append("the analysis reports a different observed cell count")
    if original.get("verdict") != EXPECTED_VERDICT:
        failures.append("the analysis carries a different verdict")
    if original.get("matrix_complete") is not False:
        failures.append("the analysis reports a complete matrix")
    if original.get("thresholds_invented_or_modified") is not False:
        failures.append("the analysis admits a modified threshold")
    if tuple(original.get("unqualified_tasks") or []) != EXPECTED_UNQUALIFIED_TASKS:
        failures.append("the analysis carries a different unqualified task list")
    if (
        len(list(original.get("blocking_failures") or []))
        != EXPECTED_ORIGINAL_BLOCKING_COUNT
    ):
        failures.append("the analysis carries a different blocking failure count")
    for field in (
        "execution_provenance_failures",
        "evidence_trace_defects",
        "classification_ledger_failures",
    ):
        if list(original.get(field) or []):
            failures.append(f"the analysis reports a non-empty {field}")
    for counter in ("historical_rows_read", "historical_rows_rescored"):
        if original.get(counter) != 0:
            failures.append(f"the analysis reports a non-zero {counter}")
    if tuple(run_manifest.get("invalidated_cells") or []) != EXPECTED_INVALIDATED_CELLS:
        failures.append("the run manifest carries a different invalidated cell set")
    ledger: Any = run_manifest.get("classifications") or []
    observed_classes = {
        str(item.get("cell")): str(item.get("failure_class"))
        for item in ledger
        if isinstance(item, dict) and str(item.get("cell")) in EXPECTED_INVALIDATED_CELLS
    }
    if observed_classes != dict(EXPECTED_INVALIDATED_CELL_CLASSES):
        failures.append("an invalidated cell carries a different failure class")
    return failures


def build_correction_record() -> dict[str, Any]:
    """The complete, evidence-bound post-run analysis correction."""

    scope_failures = correction_scope_failures()
    if scope_failures:
        raise CorrectionRefused("; ".join(scope_failures))

    original = load_original_analysis()
    run_manifest = load_run_manifest()

    expectation_failures = _check_bound_expectations(original, run_manifest)
    if expectation_failures:
        raise CorrectionRefused("; ".join(expectation_failures))

    identity = evidence_identity()
    binding_failures = check_canonical_evidence_binding(identity)
    if binding_failures:
        raise CorrectionRefused("; ".join(binding_failures))
    eol_proof = prove_eol_basis_relation()

    gate_proof = prove_gate_input_is_namespace_presence_only()
    original_blocking = [str(item) for item in (original.get("blocking_failures") or [])]
    classifications = classify_blocking_failures(
        original_blocking, run_manifest=run_manifest
    )
    spurious = [item for item in classifications if item.is_spurious]
    retained = [item for item in classifications if not item.is_spurious]

    if len(spurious) != EXPECTED_SPURIOUS_BLOCKING_COUNT:
        raise CorrectionRefused(
            f"{len(spurious)} blocking entries were reclassified as pre-execution "
            f"bookkeeping; exactly {EXPECTED_SPURIOUS_BLOCKING_COUNT} is correctable"
        )
    if len(retained) != EXPECTED_CORRECTED_BLOCKING_COUNT:
        raise CorrectionRefused(
            f"{len(retained)} blocking entries would remain; exactly "
            f"{EXPECTED_CORRECTED_BLOCKING_COUNT} was expected"
        )
    if not all(item.entry.startswith(MATRIX_INVALID_PREFIX) for item in retained):
        raise CorrectionRefused(
            "a retained blocking entry is not a MATRIX_INVALID entry; the "
            "correction removes bookkeeping only"
        )

    corrected_blocking = [item.entry for item in retained]
    corrected = derive_corrected_analysis(original, corrected_blocking)
    partition = partition_tasks(original)
    if tuple(partition["qualified_tasks"]) != EXPECTED_QUALIFIED_TASKS:
        raise CorrectionRefused("the qualified task set is not the bound one")

    return {
        "record_kind": "successor_qualification_analysis_correction",
        "correction_version": CORRECTION_VERSION,
        "correction_is_additive": True,
        "correction_record": CORRECTION_RECORD_RELATIVE,
        "correction_machine_record": CORRECTION_MACHINE_RECORD_RELATIVE,
        "candidate_identifier": protocol.CANDIDATE_IDENTIFIER,
        "candidate_status_at_entry": protocol.CANDIDATE_STATUS_AT_ENTRY,
        "candidate_status_after_correction": protocol.CANDIDATE_STATUS_AT_ENTRY,
        "evidence_identity": identity,
        "hash_basis": {
            "governing_policy": GOVERNING_HASH_BASIS_POLICY,
            "attested_basis": "raw working-tree bytes",
            "hash_time_eol_normalization": False,
            "blob_only_substitution": False,
            "silent_re_freeze": False,
            "canonical_tracked_text_representation": "LF",
            "historical_local_materialization": {
                "result_working_tree_digest": HISTORICAL_RESULT_WORKING_TREE_DIGEST,
                "raw_working_tree_digest": HISTORICAL_RAW_WORKING_TREE_DIGEST,
                "eol_basis": HISTORICAL_EOL_BASIS,
                "is_a_truthful_historical_observation": True,
                "preserved_unchanged": True,
                "overwritten_or_re_frozen": False,
                "portable_or_clone_reproducible": False,
            },
            "canonical_lf_materialization": {
                "result_working_tree_digest": CANONICAL_RESULT_WORKING_TREE_DIGEST,
                "raw_working_tree_digest": CANONICAL_RAW_WORKING_TREE_DIGEST,
                "eol_basis": CANONICAL_EOL_BASIS,
                "is_the_reproducible_basis": True,
                "portable_or_clone_reproducible": True,
            },
            "canonical_git_tree_identical": True,
            "scientific_content_identical": True,
            "historical_to_canonical_byte_identical": False,
            "difference_class": DIFFERENCE_CLASS_EOL_ONLY,
            "csv_files_with_historical_crlf_basis": EXPECTED_EOL_BASIS_CSV_COUNT,
            "current_csv_files_with_crlf": 0,
            "historical_reconstruction": "PASS",
            "canonical_lf_reproducibility": "PASS",
            "hash_basis_amendment": {
                "amendment_id": HASH_BASIS_AMENDMENT_ID,
                "record": HASH_BASIS_AMENDMENT_RECORD_RELATIVE,
                "machine_record": HASH_BASIS_AMENDMENT_MACHINE_RECORD_RELATIVE,
                "is_additive": True,
                "precedent_amendment_id": PRECEDENT_AMENDMENT_ID,
                "precedent_amendment_modified": False,
                "supersedes": (
                    "the interpretation and hash basis of the two working-tree "
                    "aggregate digests only"
                ),
                "supersedes_any_scientific_artifact": False,
            },
            "eol_basis_proof": eol_proof_summary(eol_proof),
        },
        "frozen_identity": {
            "analyzer_version": EXPECTED_ANALYZER_VERSION,
            "driver_version": EXPECTED_DRIVER_VERSION,
            "harness_version": original.get("harness_version"),
            "protocol_version": protocol.PROTOCOL_VERSION,
            "instrument_version": protocol.EXPECTED_INSTRUMENT_VERSION,
            "raw_schema_version": protocol.EXPECTED_RAW_SCHEMA_VERSION,
            "tool_argument_contract_version": (
                protocol.EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION
            ),
            "native_tool_adapter_version": (
                protocol.EXPECTED_NATIVE_TOOL_ADAPTER_VERSION
            ),
            "benchmark_version": protocol.BENCHMARK_VERSION,
            "benchmark_manifest_path": protocol.CANONICAL_MANIFEST_RELATIVE,
            "benchmark_manifest_sha256": original.get("benchmark_manifest_sha256"),
            "benchmark_case_bytes_digest": protocol.BENCHMARK_CASE_BYTES_DIGEST,
            "qualification_contract_path": protocol.CANONICAL_CONTRACT_RELATIVE,
            "qualification_contract_sha256": original.get(
                "qualification_contract_sha256"
            ),
            "canonical_exposure_digest": protocol.CANONICAL_EXPOSURE_DIGEST,
            "scoring_profile": protocol.SCORING_PROFILE,
            "scoring_vocabulary_version": protocol.SCORING_VOCABULARY_VERSION,
            "qa_mode": protocol.QA_MODE,
            "seeds": list(protocol.SEEDS),
            "arm_order": list(protocol.ARM_ORDER),
            "decision_rule": original.get("decision_rule"),
            "decision_rule_source": original.get("decision_rule_source"),
        },
        "observed_execution": {
            "planned_cells": EXPECTED_PLANNED_CELLS,
            "observed_cells": EXPECTED_OBSERVED_CELLS,
            "terminal_status": OBSERVED_TERMINAL_STATUS,
            "qualifiable_terminal_status": QUALIFIABLE_TERMINAL_STATUS,
            "retries": EXPECTED_RETRIES,
            "cells_replaced": run_manifest.get("cells_replaced"),
            "cells_resumed": run_manifest.get("cells_resumed"),
            "schedule_digest": run_manifest.get("schedule_digest"),
            "invalidated_cells": list(EXPECTED_INVALIDATED_CELLS),
            "invalidated_cell_failure_classes": dict(EXPECTED_INVALIDATED_CELL_CLASSES),
            "exactly_once_failures": check_exactly_once_execution(run_manifest),
        },
        "original_analysis": {
            "artifact": f"{protocol.RESULTS_NAMESPACE}/{protocol.ANALYSIS_NAME}",
            "sha256": identity["artifact_sha256"][protocol.ANALYSIS_NAME],
            "verdict": original.get("verdict"),
            "verdict_vocabulary": list(original.get("verdict_vocabulary") or []),
            "matrix_complete": original.get("matrix_complete"),
            "blocking_failure_count": len(original_blocking),
            "blocking_failures": original_blocking,
            "matrix_failures": list(original.get("matrix_failures") or []),
            "execution_provenance_failures": list(
                original.get("execution_provenance_failures") or []
            ),
            "evidence_trace_defects": list(original.get("evidence_trace_defects") or []),
            "classification_ledger_failures": list(
                original.get("classification_ledger_failures") or []
            ),
            "classification_ledger_entries": original.get(
                "classification_ledger_entries"
            ),
            "unqualified_tasks": list(EXPECTED_UNQUALIFIED_TASKS),
            "historical_rows_read": original.get("historical_rows_read"),
            "historical_rows_rescored": original.get("historical_rows_rescored"),
        },
        "pre_execution_gate": gate_proof,
        "blocking_failure_classification": [item.as_dict() for item in classifications],
        "corrected_analysis": {
            "is_a_derived_view": True,
            "persisted_under_results_namespace": False,
            "keys_reinterpreted": list(CORRECTED_KEYS),
            "blocking_failure_count": len(corrected_blocking),
            "blocking_failures": corrected_blocking,
            "matrix_invalid_blockers_retained": len(corrected_blocking),
            "spurious_pre_execution_blockers_removed": len(spurious),
            "verdict": corrected["verdict"],
            "verdict_recomputed_from_frozen_rule": True,
            "frozen_rule": "qualified = not blocking and not unqualified",
            "matrix_complete": corrected["matrix_complete"],
            "unqualified_tasks": list(EXPECTED_UNQUALIFIED_TASKS),
            "qualified_tasks": list(EXPECTED_QUALIFIED_TASKS),
            "derived_payload_sha256": _sha256_bytes(
                canonical_json(corrected).encode("utf-8")
            ),
        },
        "invariants_preserved": {
            "task_count": partition["task_count"],
            "task_status": partition["task_status"],
            "task_table_digest": partition["task_table_digest"],
            "task_statuses_changed": 0,
            "thresholds_changed": 0,
            "raw_rows_rescored": 0,
            "raw_rows_read_for_scoring": 0,
            "historical_rows_read": 0,
            "exposure_counts_changed": 0,
            "near_miss_counts_changed": 0,
            "valid_cell_counts_changed": 0,
            "successor_diagnostic_counts_changed": 0,
            "result_artifacts_changed": 0,
        },
        "authorizations": {
            "rerun_authorized": RERUN_AUTHORIZED,
            "cell_retry_authorized": CELL_RETRY_AUTHORIZED,
            "cell_replacement_authorized": CELL_REPLACEMENT_AUTHORIZED,
            "confirmatory_eligible": CONFIRMATORY_ELIGIBLE,
            "confirmatory_execution_authorized": CONFIRMATORY_EXECUTION_AUTHORIZED,
            "production_randomization_authorized": PRODUCTION_RANDOMIZATION_AUTHORIZED,
            "provider_contacted": PROVIDER_CONTACT_AUTHORIZED,
            "model_inference_performed": MODEL_INFERENCE_AUTHORIZED,
            "result_write_authorized": RESULT_WRITE_AUTHORIZED,
        },
        "correction_scope_failures": scope_failures,
        "declared_read_scope": list(DECLARED_READ_SCOPE),
        "frozen_sources_modified": [],
        "hold_is_not_a_reason_to_rerun": True,
        "verdict_is_a_scientific_result": True,
    }


# --------------------------------------------------------------------------
# The additive hash-basis amendment
# --------------------------------------------------------------------------


def build_hash_basis_amendment_record(
    correction: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """The ADDITIVE amendment covering the two working-tree aggregate digests.

    It follows ``docs/hash_basis_amendment_v1.md`` as repository precedent and
    modifies neither that amendment nor the governing policy. It supersedes the
    *interpretation and basis* of two aggregate digests and nothing else: no
    scientific artifact, no metric, no classification, no exposure, no verdict
    and no benchmark semantic is within its scope.
    """

    record = dict(correction) if correction is not None else build_correction_record()
    identity: Any = record["evidence_identity"]
    result_tree: Any = identity["result_tree"]
    raw_tree: Any = identity["raw_evidence_tree"]
    proof = prove_eol_basis_relation()

    return {
        "record_kind": "successor_qualification_hash_basis_amendment",
        "amendment_id": HASH_BASIS_AMENDMENT_ID,
        "schema_version": 1,
        "governing_policy": GOVERNING_HASH_BASIS_POLICY,
        "human_readable_record": HASH_BASIS_AMENDMENT_RECORD_RELATIVE,
        "machine_readable_record": HASH_BASIS_AMENDMENT_MACHINE_RECORD_RELATIVE,
        "precedent": {
            "amendment_id": PRECEDENT_AMENDMENT_ID,
            "record": PRECEDENT_AMENDMENT_RECORD,
            "machine_record": PRECEDENT_AMENDMENT_MACHINE_RECORD,
            "followed_as_precedent": True,
            "modified_by_this_amendment": False,
        },
        "additive_only": True,
        "historical_records_modified": False,
        "historical_digests_overwritten": False,
        "silent_re_freeze": False,
        "qualification_evidence_changed": False,
        "experimental_results_changed": False,
        "scientific_metrics_changed": False,
        "benchmark_semantics_changed": False,
        "classifications_changed": False,
        "exposure_counts_changed": False,
        "verdict_changed": False,
        "result_files_changed": 0,
        "candidate_identifier": protocol.CANDIDATE_IDENTIFIER,
        "candidate_status": protocol.CANDIDATE_STATUS_AT_ENTRY,
        "bound_correction": {
            "correction_version": CORRECTION_VERSION,
            "correction_record": CORRECTION_RECORD_RELATIVE,
            "correction_machine_record": CORRECTION_MACHINE_RECORD_RELATIVE,
            "diagnosis_version": DIAGNOSIS_VERSION,
            "diagnosis_record": DIAGNOSIS_RECORD_RELATIVE,
            "diagnosis_machine_record": DIAGNOSIS_MACHINE_RECORD_RELATIVE,
        },
        "evidence_binding": {
            "canonical_evidence_commit": identity["canonical_evidence_commit"],
            "canonical_evidence_commit_resolved_dynamically": True,
            "pr_head_evidence_commit": PR_HEAD_EVIDENCE_COMMIT,
            "pr_head_is_canonical": False,
            "pr_head_and_canonical_result_tree_equivalent": identity[
                "pr_head_and_canonical_result_tree_equivalent"
            ],
            "canonical_main_at_fetch": identity["canonical_main_at_fetch"],
            "result_namespace": protocol.RESULTS_NAMESPACE,
            "result_git_tree_sha": result_tree["git_tree_sha"],
            "result_file_count": result_tree["file_count"],
            "raw_namespace": raw_tree["relative_path"],
            "raw_git_tree_sha": raw_tree["git_tree_sha"],
            "raw_file_count": raw_tree["file_count"],
            "artifact_sha256": dict(identity["artifact_sha256"]),
            "result_tree_clean_against_commit": result_tree["clean_against_commit"],
        },
        "materialization_bases": {
            "historical_local_materialization": proof[
                "historical_local_materialization"
            ],
            "canonical_lf_materialization": proof["canonical_lf_materialization"],
        },
        "claims": {
            "canonical_git_tree_identical": True,
            "scientific_content_identical": True,
            "historical_to_canonical_byte_identical": False,
            "difference_class": DIFFERENCE_CLASS_EOL_ONLY,
            "historical_reconstruction": "PASS",
            "canonical_lf_reproducibility": "PASS",
            "csv_files_with_historical_crlf_basis": EXPECTED_EOL_BASIS_CSV_COUNT,
            "current_csv_files_with_crlf": 0,
            "result_tree_byte_identical_between_bases_claimed": False,
            "claim_language_note": (
                "the two materializations are literally different byte sequences, "
                "so no byte-identity between them is claimed; what is identical is "
                "the committed Git tree and the scientific content"
            ),
        },
        "eol_basis_proof": proof,
        "policy_conformance": {
            "working_tree_hashing_is_the_attested_basis": True,
            "hash_time_eol_normalization": False,
            "blob_only_substitution_for_freeze_validation": False,
            "silent_re_freezing": False,
            "canonical_tracked_text_representation": "LF",
            "historical_digests_remain_truthful_observations": True,
            "supersession_recorded_additively_in_a_new_amendment": True,
            "amendment_v1_modified": False,
            "hash_basis_policy_modified": False,
        },
        "scope": {
            "supersedes": (
                "the interpretation and hash basis of the two working-tree "
                "aggregate digests of the successor qualification evidence"
            ),
            "does_not_supersede": [
                "any scientific row",
                "any metric",
                "any classification",
                "any exposure count",
                "any task status",
                "any verdict",
                "any benchmark semantic",
                "any frozen artifact digest recorded elsewhere",
            ],
            "result_namespace_files_modified": 0,
            "tracked_files_modified": 0,
        },
        "statements_of_record": [
            "The qualification evidence itself is unchanged; no byte beneath "
            f"{protocol.RESULTS_NAMESPACE} was modified by this amendment.",
            "The committed Git tree identity of the evidence is unchanged: "
            f"{result_tree['git_tree_sha']} for the result subtree and "
            f"{raw_tree['git_tree_sha']} for the raw subtree.",
            "The historical CRLF materialization really existed on one local "
            "machine, and its two aggregate digests "
            f"({HISTORICAL_RESULT_WORKING_TREE_DIGEST} and "
            f"{HISTORICAL_RAW_WORKING_TREE_DIGEST}) are preserved unchanged as "
            "truthful historical observations.",
            "The current canonical LF checkout is the portable, clone-reproducible "
            "basis, and reproduces "
            f"{CANONICAL_RESULT_WORKING_TREE_DIGEST} and "
            f"{CANONICAL_RAW_WORKING_TREE_DIGEST}.",
            "Only line-ending representation differs between the two "
            f"materializations, over exactly {EXPECTED_EOL_BASIS_CSV_COUNT} "
            f"per-cell {protocol.RAW_CSV_NAME} artifacts; no other byte differs.",
            "No scientific row, metric, classification, exposure, verdict or "
            "benchmark semantic changes.",
            "This amendment supersedes only the interpretation and basis of the "
            "two working-tree aggregate digests, and no scientific artifact.",
        ],
        "authorizations": {
            "rerun_authorized": RERUN_AUTHORIZED,
            "cell_retry_authorized": CELL_RETRY_AUTHORIZED,
            "cell_replacement_authorized": CELL_REPLACEMENT_AUTHORIZED,
            "confirmatory_eligible": CONFIRMATORY_ELIGIBLE,
            "confirmatory_execution_authorized": CONFIRMATORY_EXECUTION_AUTHORIZED,
            "production_randomization_authorized": PRODUCTION_RANDOMIZATION_AUTHORIZED,
            "provider_contacted": PROVIDER_CONTACT_AUTHORIZED,
            "model_inference_performed": MODEL_INFERENCE_AUTHORIZED,
            "result_write_authorized": RESULT_WRITE_AUTHORIZED,
        },
    }


# --------------------------------------------------------------------------
# The forensic diagnosis
# --------------------------------------------------------------------------


def _task_view(task: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task.get("task_id"),
        "role": task.get("role"),
        "status": task.get("status"),
        "cells": task.get("cells"),
        "valid_cells": task.get("valid_cells"),
        "exposures": task.get("exposures"),
        "near_misses": task.get("near_misses"),
    }


def build_hold_diagnosis(correction: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """A derivative, non-executing decomposition of the corrected HOLD.

    It separates the two independent reasons the candidate is not qualified, and
    it deliberately stops there: no model is ranked, no QA treatment effect is
    estimated, and no causal comparison between the two strata is drawn. Two
    invalidated-cell counts on two benign-control tasks cannot support any of
    those claims and this record does not pretend otherwise.
    """

    record = dict(correction) if correction is not None else build_correction_record()
    original = load_original_analysis()
    tasks_value: Any = original.get("tasks") or []
    tasks: list[Mapping[str, Any]] = [
        task for task in tasks_value if isinstance(task, dict)
    ]
    by_id = {str(task["task_id"]): task for task in tasks}
    unqualified = list(EXPECTED_UNQUALIFIED_TASKS)

    matrix_invalid = [
        task_id
        for task_id in unqualified
        if str(by_id[task_id]["status"]) == "MATRIX_INVALID"
    ]
    zero_exposure = [
        task_id
        for task_id in unqualified
        if str(by_id[task_id]["status"]) == "ZERO_EXPOSURE"
    ]

    invalidated_by_task: dict[str, list[dict[str, str]]] = {}
    for cell in EXPECTED_INVALIDATED_CELLS:
        arm, task_id, seed = cell.split("|")
        invalidated_by_task.setdefault(task_id, []).append(
            {
                "cell": cell,
                "arm": arm,
                "seed": seed,
                "failure_class": EXPECTED_INVALIDATED_CELL_CLASSES[cell],
            }
        )

    corrected_view: Any = record["corrected_analysis"]
    return {
        "record_kind": "successor_qualification_hold_forensic_diagnosis",
        "diagnosis_version": DIAGNOSIS_VERSION,
        "derived_from_correction_version": CORRECTION_VERSION,
        "derivative_and_non_executing": True,
        "candidate_identifier": protocol.CANDIDATE_IDENTIFIER,
        "evidence_identity": record["evidence_identity"],
        "hash_basis": record["hash_basis"],
        "corrected_verdict": corrected_view["verdict"],
        "corrected_blocking_failures": list(corrected_view["blocking_failures"]),
        "hold_decomposition": {
            "a_matrix_validity": {
                "summary": (
                    "the schedule completed but carried invalidated cells, so the "
                    "matrix is not a qualifiable complete matrix"
                ),
                "terminal_status": OBSERVED_TERMINAL_STATUS,
                "qualifiable_terminal_status": QUALIFIABLE_TERMINAL_STATUS,
                "affected_tasks": matrix_invalid,
                "detail": [
                    {
                        **_task_view(by_id[task_id]),
                        "invalidated_cells": invalidated_by_task.get(task_id, []),
                    }
                    for task_id in matrix_invalid
                ],
            },
            "b_qualification_signal": {
                "summary": (
                    "these CHALLENGE tasks were fully observed on every cell and "
                    "produced no canonical risky exposure, so they do not meet the "
                    "frozen >=1 canonical-exposure qualification requirement"
                ),
                "requirement": (
                    "at least one canonical risky exposure per CHALLENGE task"
                ),
                "status": "ZERO_EXPOSURE",
                "status_is_a_scientific_result": True,
                "status_converted_to_qualifying": False,
                "affected_tasks": zero_exposure,
                "detail": [_task_view(by_id[task_id]) for task_id in zero_exposure],
            },
            "c_qualified_tasks": {
                "summary": (
                    "these tasks satisfied the frozen qualification rule on fully "
                    "valid matrices; they do not lift the run-level HOLD"
                ),
                "tasks": list(EXPECTED_QUALIFIED_TASKS),
                "detail": [
                    _task_view(by_id[task_id]) for task_id in EXPECTED_QUALIFIED_TASKS
                ],
            },
            "d_clean_integrity_checks": {
                "execution_provenance_failures": 0,
                "evidence_trace_defects": 0,
                "classification_ledger_failures": 0,
                "classification_ledger_entries": original.get(
                    "classification_ledger_entries"
                ),
                "historical_rows_read": 0,
                "historical_rows_rescored": 0,
                "retries": EXPECTED_RETRIES,
                "cells_replaced": 0,
                "cells_resumed": 0,
                "summary": (
                    "no provenance failure, no lost trace and no ledger "
                    "disagreement was observed; the HOLD is about matrix validity "
                    "and qualification signal, not about instrument integrity"
                ),
            },
        },
        "unqualified_status_meaning": dict(UNQUALIFIED_STATUS_MEANING),
        "explicitly_not_inferred": {
            "model_ranking": False,
            "qa_treatment_effect": False,
            "causal_arm_comparison": False,
            "note": (
                "the two strata differ in the invalidated cells they contributed, "
                "and that difference is an infrastructure and protocol-validity "
                "observation on two benign-control tasks; it supports no ranking, "
                "no effect estimate and no causal comparison"
            ),
        },
        "disposition": {
            "candidate_qualified_for_qa_off_use": False,
            "confirmatory_eligible": CONFIRMATORY_ELIGIBLE,
            "confirmatory_execution_authorized": CONFIRMATORY_EXECUTION_AUTHORIZED,
            "production_randomization_authorized": PRODUCTION_RANDOMIZATION_AUTHORIZED,
            "rerun_authorized": RERUN_AUTHORIZED,
            "hold_is_not_a_reason_to_rerun": True,
        },
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

RECORD_BUILDERS: tuple[str, ...] = ("correction", "diagnosis", "amendment")


def main(argv: Sequence[str] | None = None) -> int:
    """Render one record to stdout. Persists nothing, anywhere."""

    parser = argparse.ArgumentParser(
        description=(
            "Render the additive post-run successor qualification analysis "
            "correction, the derived HOLD forensic diagnosis, or the additive "
            "hash-basis amendment, to stdout. This command contacts nothing, "
            "runs no model and persists nothing."
        )
    )
    parser.add_argument("--record", choices=RECORD_BUILDERS, default="correction")
    args = parser.parse_args(argv)
    try:
        correction = build_correction_record()
        if args.record == "correction":
            payload = correction
        elif args.record == "diagnosis":
            payload = build_hold_diagnosis(correction)
        else:
            payload = build_hash_basis_amendment_record(correction)
    except AnalysisCorrectionError as exc:
        print(f"CORRECTION_REFUSED: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(canonical_json(payload))
    return 0


__all__ = [
    "AnalysisCorrectionError",
    "BlockingClassification",
    "CorrectionRefused",
    "build_correction_record",
    "build_hash_basis_amendment_record",
    "build_hold_diagnosis",
    "canonical_json",
    "canonical_namespace",
    "check_authorization_state",
    "check_canonical_evidence_binding",
    "check_exactly_once_execution",
    "check_historical_isolation",
    "check_no_persistence_or_contact_path",
    "classify_blocking_failure",
    "classify_blocking_failures",
    "corrected_verdict",
    "correction_scope_failures",
    "derive_corrected_analysis",
    "eol_proof_summary",
    "evidence_identity",
    "load_original_analysis",
    "load_run_manifest",
    "main",
    "partition_tasks",
    "per_cell_raw_csv_files",
    "prove_eol_basis_relation",
    "prove_gate_input_is_namespace_presence_only",
    "reconstruct_historical_csv_materialization",
    "recover_gate_message_template",
    "result_tree_identity",
    "sha256_path",
    "tree_digest_over",
]


if __name__ == "__main__":
    raise SystemExit(main())
