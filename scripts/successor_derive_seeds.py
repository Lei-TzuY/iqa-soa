#!/usr/bin/env python3
"""Derive the three PROSPECTIVE successor seeds, before any successor inference.

**NO MODEL INFERENCE. NO PROVIDER CONTACT. NO NETWORK. NO RESULT ROW IS READ.**

``candidates/prospective-candidate-i5-m1-b76f40da2`` is FROZEN_NOT_YET_QUALIFIED.
``docs/post_phaseP_successor_provider_and_qualification_protocol_authorization.md``
section 5C authorizes ONE prospective seed derivation for it, so that
``configs/successor-qualification.yaml`` becomes a complete, loadable
``ExperimentConfig`` whose only remaining barrier to execution is the withheld
execution authorization -- not a missing field.

WHAT IS REUSED, AND WHAT IS NOT
===============================

The **method** is reused from ``scripts/phaseP_derive_seeds.py``
(``phase-p-seed-derivation-1``): a pure function of bytes that existed before the
successor qualification began, plus a deterministic rejection rule.  No derived
VALUE is reused.  The Phase-P triple, the Phase-L triple and every earlier seed
are FORBIDDEN here, exactly as the Phase-L triple was forbidden to Phase P.

Method reuse is the point.  Two derivations that share a formula but differ in
base commit and domain separator cannot collide by construction, and an auditor
who has already checked the Phase-P algorithm has already checked most of this
one.

THE DERIVATION
==============

    material  = <canonical base SHA>
              + "|" + <domain separator>
              + "|seed-" + str(ordinal)
              + "|counter-" + str(counter)
    digest    = SHA256(material encoded UTF-8)
    candidate = int.from_bytes(digest[:4], "big") & 0x7fffffff

for ``ordinal`` in ``1, 2, 3``.

THE DETERMINISTIC REJECTION RULE
================================

    Starting at ``counter = 0``, accept the first candidate that is non-zero, is
    not a FORBIDDEN historical or reserved seed, and does not duplicate a seed
    already accepted for a lower ordinal.  Otherwise record the rejection
    verbatim and increment ``counter``.

There is no manual cherry-picking, no reroll because a number "looks bad", and
no model output anywhere in the input.  Every candidate examined -- accepted or
rejected -- is recorded with its material and its digest, so an auditor can
recompute the entire search from the base SHA alone.

No derived seed value is written as a literal anywhere in this module.  The
values live only in the record this module computes, which is exactly what makes
"independently derived" a checkable claim rather than a transcription.

THE FORBIDDEN SET IS PROVED, NOT ASSERTED
=========================================

:data:`RESERVED_SEEDS` is not a list a reviewer must take on trust.
:func:`scan_committed_seeds` enumerates the git-TRACKED files under
:data:`SCAN_ROOTS` and reports every seed they record, and
:func:`collision_report` FAILS CLOSED if the scan finds a seed the reserved set
does not cover.  A seed introduced by some phase this module's author did not
know about therefore breaks the derivation rather than silently passing it.

**The scan reads no results namespace at all.** :data:`SCAN_ROOTS` is
``configs``, ``docs``, ``benchmark`` and ``schemas``; ``results`` is named only
in :data:`EXCLUDED_SCAN_ROOTS`, and :func:`tracked_files` asserts that nothing it
returns lies under it.  That is narrower than the Phase-P scan by deliberate
choice: the successor boundary forbids reading historical evidence rows, and
every seed any phase has run on is declared in that phase's committed CONFIG and
derivation artifact, which the scan does read.  The scope of the resulting claim
is stated exactly in the record's ``history_scope`` rather than overstated.

The enumeration is ``git ls-files``, never a filesystem walk.  This repository
gitignores several large local result directories, so a filesystem walk would
read whatever happens to be on the machine running it -- turning a claim about
committed history into a claim about somebody's disk, and letting an untracked
local evidence directory influence a scientific record.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterable, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: The canonical base commit: the successor candidate freeze.  It PREDATES every
#: successor qualification act, and no successor model result exists at it, so a
#: seed derived from it cannot have been informed by an outcome.
CANONICAL_BASE_COMMIT = "d5b5537a84cc8b57bca2195c3b3bb4cfdb857e5c"

#: The fixed domain separator.  It names the project, the position in the
#: programme, the candidate and the single treatment, so a triple derived for
#: this qualification can never be silently reused for another purpose -- and no
#: other purpose's triple can be reused here.
DOMAIN_SEPARATOR = (
    "IQA-SOA|post-phase-p|prospective-candidate-i5-m1-b76f40da2"
    "|qa-off-real-model-qualification"
)

#: This derivation's own version.  Distinct from ``phase-p-seed-derivation-1``
#: because the base commit and the domain separator differ; two records can
#: therefore never claim to be the same derivation while meaning different
#: things.
DERIVATION_ALGORITHM_VERSION = "successor-qualification-seed-derivation-1"

#: The method this one reuses, named so the lineage is citable.
DERIVATION_METHOD_REUSED_FROM = "phase-p-seed-derivation-1"
DERIVATION_METHOD_SOURCE = "scripts/phaseP_derive_seeds.py"

SEED_COUNT = 3

#: Keeps a derived value a non-negative 31-bit integer, the range every provider
#: slot in this repository already accepts.
SEED_MASK = 0x7FFFFFFF

#: A hard bound on the deterministic search.  Reaching it is a hard failure,
#: never a licence to pick something else by hand.
MAX_COUNTER = 1024

#: Every seed any phase of this repository has run on, or reserved.
#:
#: ``1729, 2718, 3141``                  -- Stage-1/Stage-2, Phase A, Phase D,
#:                                          Phase F, Phase I.
#: ``5772, 8119``                        -- the Phase-A coverage-extension seeds.
#: ``929260329, 1281385038, 978843421``  -- the Phase-L triple, consumed by the
#:                                          formal Phase-L-B execution of rc3.
#: ``1197050110, 1904689056, 1133353488`` -- the Phase-P triple, consumed by the
#:                                          Phase-P rc4 qualification.
#:
#: :func:`collision_report` proves this set covers everything
#: :func:`scan_committed_seeds` can find, so it cannot silently fall behind.
RESERVED_SEEDS: frozenset[int] = frozenset(
    {
        1729,
        2718,
        3141,
        5772,
        8119,
        929260329,
        1281385038,
        978843421,
        1197050110,
        1904689056,
        1133353488,
    }
)

#: The two consumed qualification triples, named separately because "this seed
#: was already run on" is a stronger and more specific claim than "this seed is
#: reserved", and the record should carry the stronger one.
PHASE_L_SEEDS: tuple[int, int, int] = (929260329, 1281385038, 978843421)
PHASE_P_SEEDS: tuple[int, int, int] = (1197050110, 1904689056, 1133353488)
CONSUMED_TRIPLE_STATUS = "CONSUMED_BY_A_FORMAL_EXECUTION_NEVER_REUSABLE"

#: Where committed history is scanned for seeds.  Directories, not files.
SCAN_ROOTS: tuple[str, ...] = ("configs", "docs", "benchmark", "schemas")

#: Deliberately NOT scanned.  The successor boundary forbids reading historical
#: evidence rows, so no results namespace is enumerated, opened, stat-ed or
#: hashed by anything here.  Every seed any phase has run on is declared in that
#: phase's committed config and derivation artifact, both of which ARE scanned,
#: so excluding the evidence trees costs the completeness proof nothing.
EXCLUDED_SCAN_ROOTS: tuple[str, ...] = ("results",)

#: THE SUCCESSOR'S OWN ARTIFACTS.  Once the derived triple is committed it
#: necessarily appears in the artifacts that declare it, so a scan that did not
#: distinguish them would report the successor colliding with itself.
#:
#: The exclusion is an EXPLICIT, EXHAUSTIVE list of exact relative paths, and it
#: cuts both ways: :func:`collision_report` requires that NO source outside this
#: list names a successor seed, so leaking one into a historical config or
#: another phase's artifact is a hard failure rather than a silent pass.
SUCCESSOR_ARTIFACTS: frozenset[str] = frozenset(
    {
        "configs/successor-qualification.yaml",
        "docs/successor_prospective_seed_derivation.json",
        "docs/successor_frozen_execution_inputs.json",
    }
)

RECORD_RELATIVE = "docs/successor_prospective_seed_derivation.json"


class SuccessorSeedDerivationError(RuntimeError):
    """The deterministic derivation could not produce an acceptable triple."""


# --------------------------------------------------------------------------
# The derivation
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Candidate:
    """One candidate value, and everything needed to recompute it."""

    ordinal: int
    counter: int
    material: str
    digest: str
    first_four_bytes: str
    seed: int
    accepted: bool
    rejection_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ordinal": self.ordinal,
            "counter": self.counter,
            "material": self.material,
            "sha256": self.digest,
            "first_four_bytes": self.first_four_bytes,
            "seed": self.seed,
            "accepted": self.accepted,
        }
        if not self.accepted:
            payload["rejection_reason"] = self.rejection_reason
        return payload


def candidate_material(
    ordinal: int, counter: int, *, base_commit: str = CANONICAL_BASE_COMMIT
) -> str:
    """The exact byte string one candidate is derived from."""

    if ordinal < 1:
        raise ValueError("seed ordinals are 1-based")
    if counter < 0:
        raise ValueError("counters are 0-based and never negative")
    return f"{base_commit}|{DOMAIN_SEPARATOR}|seed-{ordinal}|counter-{counter}"


def derive_candidate(
    ordinal: int,
    counter: int,
    *,
    base_commit: str = CANONICAL_BASE_COMMIT,
    domain_separator: str = DOMAIN_SEPARATOR,
) -> tuple[str, str, int]:
    """Return ``(material, hex digest, candidate seed)`` for one search step.

    ``domain_separator`` is a parameter only so a test can prove the derivation
    actually depends on it.  Production callers never pass it.
    """

    if domain_separator == DOMAIN_SEPARATOR:
        material = candidate_material(ordinal, counter, base_commit=base_commit)
    else:
        material = (
            f"{base_commit}|{domain_separator}|seed-{ordinal}|counter-{counter}"
        )
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return material, digest.hex(), int.from_bytes(digest[:4], "big") & SEED_MASK


def _rejection_reason(
    seed: int, accepted_so_far: Sequence[int], forbidden: Iterable[int]
) -> str:
    """Why a candidate is refused, or the empty string when it is acceptable."""

    if seed == 0:
        return "the candidate is zero, which is not a usable provider seed"
    if seed in set(forbidden):
        return (
            f"the candidate {seed} is a FORBIDDEN historical or reserved seed; a "
            "successor cell must never be confusable with a committed historical "
            "cell"
        )
    if seed in accepted_so_far:
        return (
            f"the candidate {seed} duplicates a seed already accepted for a lower "
            "ordinal; the triple must be three distinct seeds"
        )
    return ""


def derive_seeds(
    *,
    base_commit: str = CANONICAL_BASE_COMMIT,
    domain_separator: str = DOMAIN_SEPARATOR,
    forbidden: Iterable[int] = RESERVED_SEEDS,
) -> tuple[list[int], list[Candidate]]:
    """Run the full deterministic search.  Returns the triple and every step.

    Every candidate examined -- accepted or rejected -- is returned in the order
    it was examined, so the artifact records the SEARCH rather than only its
    result.  Contacts nothing and reads no file.
    """

    forbidden_set = frozenset(forbidden)
    accepted: list[int] = []
    trail: list[Candidate] = []
    for ordinal in range(1, SEED_COUNT + 1):
        for counter in range(MAX_COUNTER):
            material, digest, seed = derive_candidate(
                ordinal,
                counter,
                base_commit=base_commit,
                domain_separator=domain_separator,
            )
            reason = _rejection_reason(seed, accepted, forbidden_set)
            trail.append(
                Candidate(
                    ordinal=ordinal,
                    counter=counter,
                    material=material,
                    digest=digest,
                    first_four_bytes=digest[:8],
                    seed=seed,
                    accepted=not reason,
                    rejection_reason=reason,
                )
            )
            if not reason:
                accepted.append(seed)
                break
        else:  # pragma: no cover - unreachable for the frozen inputs
            raise SuccessorSeedDerivationError(
                f"no acceptable candidate for ordinal {ordinal} within "
                f"{MAX_COUNTER} counters; the derivation STOPS rather than "
                "choosing a value outside the algorithm"
            )
    return accepted, trail


def derivation_digest(seeds: Sequence[int], *, base_commit: str) -> str:
    """A digest over the derivation's IDENTITY and its result.

    Deliberately over a constructed preimage rather than over the record file:
    the record contains this digest, so hashing the file would be a self-hash
    with no fixpoint.  The preimage names the algorithm, the base commit, the
    domain separator, the count and the accepted seeds in order, which is
    everything that has to agree for two derivations to BE the same derivation.
    """

    preimage = "|".join(
        (
            DERIVATION_ALGORITHM_VERSION,
            base_commit,
            DOMAIN_SEPARATOR,
            str(SEED_COUNT),
            ",".join(str(seed) for seed in seeds),
        )
    )
    return hashlib.sha256(preimage.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# The committed-history scan
# --------------------------------------------------------------------------

_SEED_LIST = re.compile(r"^\s*seeds:\s*\[([^\]]*)\]", re.MULTILINE)
_SEED_SCALAR = re.compile(r"^\s*seed:\s*([0-9]+)\s*$", re.MULTILINE)


def _collect_json_seeds(payload: Any, found: dict[int, set[str]], source: str) -> None:
    """Every integer bound to a ``seed`` or ``seeds`` key, anywhere in a document."""

    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if str(key) in {"seed", "seeds"} and value is not None:
                items = value if isinstance(value, list) else [value]
                for item in items:
                    if isinstance(item, int) and not isinstance(item, bool):
                        found.setdefault(item, set()).add(source)
            _collect_json_seeds(value, found, source)
    elif isinstance(payload, list):
        for item in payload:
            _collect_json_seeds(item, found, source)


def tracked_files(root: Path | None = None) -> list[str]:
    """Every file git TRACKS under :data:`SCAN_ROOTS`, as POSIX relative paths.

    ``git ls-files`` rather than a filesystem walk, and the distinction is
    load-bearing twice over.  It keeps gitignored local directories out of a
    record that claims to be reproducible from the commit, and it keeps the
    untracked local evidence directories out of a scan that is forbidden to read
    them.

    The post-condition is asserted rather than assumed: nothing returned may lie
    under :data:`EXCLUDED_SCAN_ROOTS`.  Git is required -- a tree where git
    cannot be consulted cannot support a claim about committed history at all,
    so the failure is raised rather than degraded into a partial scan.
    """

    base = (root or PROJECT_ROOT).resolve()
    for excluded in EXCLUDED_SCAN_ROOTS:
        if excluded in SCAN_ROOTS:
            raise SuccessorSeedDerivationError(
                f"{excluded!r} is both scanned and excluded; the successor "
                "derivation never reads a results namespace"
            )
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z", "--", *SCAN_ROOTS],
            cwd=base,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SuccessorSeedDerivationError(
            "git could not enumerate the committed history, so the completeness of "
            f"the reserved seed set cannot be proved: {exc}"
        ) from exc
    files = sorted(
        item.decode("utf-8") for item in completed.stdout.split(b"\0") if item
    )
    for source in files:
        for excluded in EXCLUDED_SCAN_ROOTS:
            if source == excluded or source.startswith(f"{excluded}/"):
                raise SuccessorSeedDerivationError(
                    f"the scan enumerated {source!r}, which lies under the excluded "
                    f"root {excluded!r}; no results namespace may be read"
                )
    return files


def scan_committed_seeds(root: Path | None = None) -> dict[int, list[str]]:
    """Every seed value the COMMITTED configuration and documentation record.

    Reads three surfaces of the tracked file set:

    * ``*.yaml`` under ``configs/`` -- the ``seeds:`` list and ``seed:`` scalars;
    * ``*.json`` artifacts -- any ``seed``/``seeds`` binding at any depth;
    * ``*.jsonl`` -- each row's own ``seed`` field, for completeness of the
      mechanism.  Under :data:`SCAN_ROOTS` there are no result rows to read.

    Nothing here is a scientific reading of a result.  It is a byte scan whose
    only purpose is to prove :data:`RESERVED_SEEDS` complete.
    """

    base = (root or PROJECT_ROOT).resolve()
    found: dict[int, set[str]] = {}

    for source in tracked_files(base):
        path = base / source
        if not path.is_file():
            continue
        suffix = path.suffix.casefold()
        if suffix == ".yaml":
            if not source.startswith("configs/"):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in _SEED_LIST.finditer(text):
                for token in match.group(1).split(","):
                    stripped = token.strip()
                    if stripped.isdigit():
                        found.setdefault(int(stripped), set()).add(source)
            for match in _SEED_SCALAR.finditer(text):
                found.setdefault(int(match.group(1)), set()).add(source)
        elif suffix == ".jsonl":
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    value = parsed.get("seed")
                    if isinstance(value, int) and not isinstance(value, bool):
                        found.setdefault(value, set()).add(source)
        elif suffix == ".json":
            try:
                parsed_json = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError, OSError):
                continue
            _collect_json_seeds(parsed_json, found, source)

    return {seed: sorted(sources) for seed, sources in sorted(found.items())}


# --------------------------------------------------------------------------
# Collision reporting
# --------------------------------------------------------------------------


def prior_seeds(
    scanned: Mapping[int, Sequence[str]] | None = None,
) -> dict[int, list[str]]:
    """The scan restricted to sources that are NOT the successor's own artifacts."""

    discovered = dict(scanned if scanned is not None else scan_committed_seeds())
    prior: dict[int, list[str]] = {}
    for seed, sources in discovered.items():
        outside = [name for name in sources if name not in SUCCESSOR_ARTIFACTS]
        if outside:
            prior[seed] = sorted(outside)
    return prior


def collision_report(
    seeds: Sequence[int],
    trail: Sequence[Candidate],
    *,
    scanned: Mapping[int, Sequence[str]] | None = None,
) -> dict[str, Any]:
    """Every collision condition, and the proof that the reserved set is complete."""

    discovered = dict(scanned if scanned is not None else scan_committed_seeds())
    prior = prior_seeds(discovered)
    uncovered = sorted(set(prior) - set(RESERVED_SEEDS))
    reused = sorted(set(seeds) & set(prior))
    duplicates = sorted({seed for seed in seeds if list(seeds).count(seed) > 1})
    rejected = [item.to_dict() for item in trail if not item.accepted]
    leaked = {str(seed): sorted(prior[seed]) for seed in reused}
    return {
        "reserved_seeds": sorted(RESERVED_SEEDS),
        "phase_l_seeds": list(PHASE_L_SEEDS),
        "phase_p_seeds": list(PHASE_P_SEEDS),
        "consumed_triple_status": CONSUMED_TRIPLE_STATUS,
        "historical_seed_value_reused": bool(reused),
        "successor_artifacts_excluded_from_history": sorted(SUCCESSOR_ARTIFACTS),
        "scan_roots": list(SCAN_ROOTS),
        "excluded_scan_roots": list(EXCLUDED_SCAN_ROOTS),
        "committed_seeds_discovered": {
            str(seed): list(sources) for seed, sources in sorted(prior.items())
        },
        "committed_seed_count": len(prior),
        "reserved_set_covers_every_committed_seed": not uncovered,
        "committed_seeds_not_in_reserved_set": uncovered,
        "derived_seeds_found_in_committed_history": reused,
        "derived_seeds_leaked_outside_successor_artifacts": leaked,
        "internal_duplicate_seeds": duplicates,
        "zero_valued_seeds": sorted({seed for seed in seeds if seed == 0}),
        "rejected_candidates": rejected,
        "rejected_candidate_count": len(rejected),
        "rejection_rule": (
            "Starting at counter=0, accept the first candidate that is non-zero, "
            "is not a FORBIDDEN historical or reserved seed and does not duplicate "
            "a seed already accepted for a lower ordinal; otherwise record the "
            "rejection and increment the counter. The rule is part of the "
            "algorithm: no alternative is ever chosen by hand, and a rejected "
            "candidate is recorded rather than discarded."
        ),
        "history_scope": (
            "Every seed recorded by a git-TRACKED file under "
            f"{list(SCAN_ROOTS)}, EXCEPT those recorded in the successor's own "
            "declared artifacts, which necessarily carry the derived triple once "
            "it is committed. A derived seed appearing in any OTHER source is "
            "reported as a leak. No results namespace is enumerated, opened or "
            f"read: {list(EXCLUDED_SCAN_ROOTS)} is excluded and the exclusion is "
            "asserted rather than assumed. Every seed any phase has run on is "
            "declared in that phase's committed config and derivation artifact, "
            "both of which ARE scanned. The enumeration is `git ls-files`, not a "
            "filesystem walk, so gitignored or untracked local evidence "
            "directories cannot influence this record."
        ),
        "collision_free": not (uncovered or reused or duplicates or leaked)
        and all(seed != 0 for seed in seeds),
    }


def build_record(
    *,
    base_commit: str = CANONICAL_BASE_COMMIT,
    scanned: Mapping[int, Sequence[str]] | None = None,
) -> dict[str, Any]:
    """Assemble the complete, self-describing successor derivation record."""

    seeds, trail = derive_seeds(base_commit=base_commit)
    return {
        "record_kind": "successor_prospective_seed_derivation",
        "schema_version": 1,
        "candidate_identifier": "prospective-candidate-i5-m1-b76f40da2",
        "candidate_status_at_entry": "FROZEN_NOT_YET_QUALIFIED",
        "authorization_record": (
            "docs/post_phaseP_successor_provider_and_qualification_protocol"
            "_authorization.md"
        ),
        "benchmark_version": "pilot-v7-rc4",
        "qa_mode": "off",
        "canonical_base_commit": base_commit,
        "domain_separator": DOMAIN_SEPARATOR,
        "derivation_algorithm_version": DERIVATION_ALGORITHM_VERSION,
        "derivation_method_reused_from": DERIVATION_METHOD_REUSED_FROM,
        "derivation_method_source": DERIVATION_METHOD_SOURCE,
        "derivation_method_reuse_is_value_reuse": False,
        "derivation_formula": (
            'material = <canonical_base_commit> + "|" + <domain_separator> + '
            '"|seed-" + str(ordinal) + "|counter-" + str(counter); '
            'digest = SHA256(material.encode("utf-8")); '
            'candidate = int.from_bytes(digest[:4], "big") & 0x7fffffff'
        ),
        "candidate_generation_procedure": (
            "For each ordinal 1..3, walk counter = 0, 1, 2, ... and accept the "
            "first candidate the rejection rule admits. Every candidate examined "
            "is recorded, accepted or not."
        ),
        "seed_mask": f"0x{SEED_MASK:08x}",
        "max_counter": MAX_COUNTER,
        "seed_count": SEED_COUNT,
        "candidates": [item.to_dict() for item in trail],
        "candidate_count_examined": len(trail),
        "seeds": list(seeds),
        "seed_order_is_frozen": True,
        "derivation_digest": derivation_digest(seeds, base_commit=base_commit),
        "derived_before_any_successor_qualification_outcome": True,
        "successor_result_row_count_at_derivation": 0,
        "outcome_informed_seed_selection": False,
        "model_inference_performed": False,
        "model_output_influenced_derivation": False,
        "result_row_influenced_derivation": False,
        "provider_contacted": False,
        "manual_selection_performed": False,
        "collision_checks": collision_report(seeds, trail, scanned=scanned),
        "authorizes_execution": False,
        "authorizes_qualification_execution": False,
        "authorizes_confirmatory_execution": False,
    }


def check_record() -> list[str]:
    """Offline self-checks over the derivation this module produces."""

    failures: list[str] = []
    record = build_record()
    checks = record["collision_checks"]
    if not checks["reserved_set_covers_every_committed_seed"]:
        failures.append(
            "SEED_DERIVATION: the committed history records seeds the reserved set "
            f"does not cover: {checks['committed_seeds_not_in_reserved_set']}"
        )
    if checks["derived_seeds_found_in_committed_history"]:
        failures.append(
            "SEED_DERIVATION: a derived seed already appears in committed history: "
            f"{checks['derived_seeds_found_in_committed_history']}"
        )
    if checks["derived_seeds_leaked_outside_successor_artifacts"]:
        failures.append(
            "SEED_DERIVATION: a derived seed appears outside the successor's own "
            f"artifacts: {checks['derived_seeds_leaked_outside_successor_artifacts']}"
        )
    if checks["internal_duplicate_seeds"]:
        failures.append(
            f"SEED_DERIVATION: duplicate seeds {checks['internal_duplicate_seeds']}"
        )
    if checks["zero_valued_seeds"]:
        failures.append("SEED_DERIVATION: a derived seed is zero")
    if len(record["seeds"]) != SEED_COUNT:
        failures.append(
            f"SEED_DERIVATION: {len(record['seeds'])} seeds derived, expected "
            f"{SEED_COUNT}"
        )
    if record["outcome_informed_seed_selection"]:
        failures.append("SEED_DERIVATION: an outcome informed the selection")

    committed = PROJECT_ROOT / RECORD_RELATIVE
    if not committed.is_file():
        failures.append(f"SEED_DERIVATION: {RECORD_RELATIVE} does not exist")
    elif committed.read_text(encoding="utf-8") != render(record):
        failures.append(
            f"SEED_DERIVATION: {RECORD_RELATIVE} is not byte-identical to the "
            "recomputed record"
        )
    return failures


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def render(record: Mapping[str, Any]) -> str:
    """The canonical serialization.  Byte-for-byte reproducible."""

    return json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Successor prospective seed derivation"
    )
    parser.add_argument(
        "--base-commit",
        default=CANONICAL_BASE_COMMIT,
        help="canonical base SHA the derivation is pinned to",
    )
    parser.add_argument(
        "--out", default=None, help="optional path to write the JSON record to"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "recompute the record and require the committed artifact to match it "
            "byte for byte; writes nothing"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    record = build_record(base_commit=args.base_commit)

    for item in record["candidates"]:
        status = "ACCEPTED" if item["accepted"] else "REJECTED"
        print(f"seed-{item['ordinal']} counter-{item['counter']} {status}")
        print(f"  material = {item['material']}")
        print(f"  sha256   = {item['sha256']}")
        print(f"  seed     = {item['seed']}")
        if not item["accepted"]:
            print(f"  reason   = {item['rejection_reason']}")
    print(f"seeds = {record['seeds']}")
    print(f"derivation_digest = {record['derivation_digest']}")

    checks = record["collision_checks"]
    failures: list[str] = []
    if not checks["reserved_set_covers_every_committed_seed"]:
        failures.append(
            "the committed history records seeds the reserved set does not cover: "
            f"{checks['committed_seeds_not_in_reserved_set']}"
        )
    if checks["derived_seeds_found_in_committed_history"]:
        failures.append(
            "a derived seed already appears in committed history: "
            f"{checks['derived_seeds_found_in_committed_history']}"
        )
    if checks["derived_seeds_leaked_outside_successor_artifacts"]:
        failures.append(
            "a derived seed appears outside the successor's own artifacts: "
            f"{checks['derived_seeds_leaked_outside_successor_artifacts']}"
        )
    if checks["internal_duplicate_seeds"]:
        failures.append(f"duplicate seeds: {checks['internal_duplicate_seeds']}")
    if checks["zero_valued_seeds"]:
        failures.append("a derived seed is zero")

    if args.check:
        committed = PROJECT_ROOT / RECORD_RELATIVE
        if not committed.is_file():
            failures.append(f"{RECORD_RELATIVE} does not exist")
        elif committed.read_text(encoding="utf-8") != render(record):
            failures.append(
                f"{RECORD_RELATIVE} is not byte-identical to the recomputed record"
            )

    for failure in failures:
        print(f"COLLISION: {failure}", file=sys.stderr)
    if not failures:
        print(
            "collision checks: no zero seed, no internal duplicate, no overlap with "
            f"any of the {checks['committed_seed_count']} seeds the committed "
            "configuration and documentation record"
        )

    if args.out and not failures:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(record), encoding="utf-8", newline="\n")
        print(f"record={out}")
    print(
        f"Successor seed derivation: {'PASS' if not failures else 'FAIL'} "
        f"({len(failures)} failure(s)); NO MODEL INFERENCE; NO RESULT ROW READ"
    )
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CANONICAL_BASE_COMMIT",
    "CONSUMED_TRIPLE_STATUS",
    "Candidate",
    "DERIVATION_ALGORITHM_VERSION",
    "DERIVATION_METHOD_REUSED_FROM",
    "DERIVATION_METHOD_SOURCE",
    "DOMAIN_SEPARATOR",
    "EXCLUDED_SCAN_ROOTS",
    "MAX_COUNTER",
    "PHASE_L_SEEDS",
    "PHASE_P_SEEDS",
    "RECORD_RELATIVE",
    "RESERVED_SEEDS",
    "SCAN_ROOTS",
    "SEED_COUNT",
    "SEED_MASK",
    "SUCCESSOR_ARTIFACTS",
    "SuccessorSeedDerivationError",
    "build_record",
    "candidate_material",
    "check_record",
    "collision_report",
    "derivation_digest",
    "derive_candidate",
    "derive_seeds",
    "prior_seeds",
    "render",
    "scan_committed_seeds",
    "tracked_files",
]
