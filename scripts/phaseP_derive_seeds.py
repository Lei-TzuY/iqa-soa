#!/usr/bin/env python3
"""Derive the three PROSPECTIVE Phase-P seeds for pilot-v7-rc4, before inference.

Phase P IS the prospective seed-selection phase for pilot-v7-rc4.  The three
Phase-L seeds ``(929260329, 1281385038, 978843421)`` were CONSUMED by the formal
Phase-L-B execution of pilot-v7-rc3: every one of them appears in 34 committed
raw rows whose classifications remain binding forever.  Reusing any of them for
rc4 would make the new evidence non-independent of the evidence that motivated
the rc4 redesign, so Phase P derives three seeds that are new, reproducible, and
demonstrably not chosen after seeing any result.

THE DERIVATION
==============

The derivation is a pure function of bytes that existed before this phase began:
the canonical Phase-P starting commit and a fixed domain separator naming the
project, the phase, the benchmark and the single treatment.

    material  = <canonical base SHA>
              + "|" + <domain separator>
              + "|seed-" + str(ordinal)
              + "|counter-" + str(counter)
    digest    = SHA256(material encoded UTF-8)
    candidate = int.from_bytes(digest[:4], "big") & 0x7fffffff

for ``ordinal`` in ``1, 2, 3``.

THE DETERMINISTIC REJECTION RULE
================================

Phase L-A stopped on a collision and chose nothing, which is safe but leaves a
phase with no seeds.  Phase P instead carries a rejection rule that is itself
deterministic, so a collision is resolved by the algorithm rather than by a
person:

    Starting at ``counter = 0``, accept the first candidate that is non-zero,
    is not a FORBIDDEN historical seed, and does not duplicate a seed already
    accepted for a lower ordinal.  Otherwise record the rejection verbatim and
    increment ``counter``.

There is no manual cherry-picking, no reroll because a number "looks bad", and
no model output anywhere in the input.  Every rejection is recorded in the
derivation artifact with its material, its digest and the reason, so an auditor
can recompute the whole search from the base SHA alone.

THE FORBIDDEN SET IS PROVED, NOT ASSERTED
=========================================

:data:`FORBIDDEN_SEEDS` is not a hand-maintained list that a reviewer must trust.
:func:`scan_committed_seeds` reads the committed configurations, the committed
raw result rows and the committed JSON artifacts and reports every seed the
repository has ever recorded.  :func:`collision_report` requires the forbidden
set to be a SUPERSET of what the scan finds, so a seed introduced by some phase
this module's author did not know about makes the derivation FAIL rather than
silently pass.

The file set is enumerated with ``git ls-files``, not by walking the filesystem.
That distinction is load-bearing: this repository gitignores several large local
result directories, so a filesystem walk reads whatever happens to be on the
machine running it -- which makes the record irreproducible from the commit and
turns a claim about committed history into a claim about somebody's disk.  A
fresh detached-worktree run of the Phase-P suite is what caught this, and
:func:`tracked_files` is the repair.

This module performs no inference, contacts no provider and reads no rc4 result.
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

#: The canonical Phase-P starting commit: ``main`` at the point Phase O / O-R1
#: were merged (PR #13).  The seed triple is a function of this and the domain
#: separator, and of nothing else.
CANONICAL_BASE_COMMIT = "f65ee4980813b465431c5f7d75a0d00db87785b6"

#: The fixed domain separator.  It names the project, the phase, the benchmark it
#: will exercise and the single treatment, so a triple derived for one purpose
#: can never be silently reused for another.
DOMAIN_SEPARATOR = "IQA-SOA|phase-p|pilot-v7-rc4|qa-off-real-model-qualification"

#: The derivation algorithm's own version.  A change to the formula, the mask or
#: the rejection rule changes this string, so two records can never claim to be
#: the same derivation while meaning different things.
DERIVATION_ALGORITHM_VERSION = "phase-p-seed-derivation-1"

SEED_COUNT = 3

#: The mask that keeps a derived value a non-negative 31-bit integer, which is
#: the range every provider slot in this repository already accepts.
SEED_MASK = 0x7FFFFFFF

#: A hard bound on the deterministic search.  It exists so a pathological
#: forbidden set cannot loop forever; it is not a policy knob and reaching it is
#: a hard failure, never a licence to pick something else.
MAX_COUNTER = 1024

#: Every seed any phase of this repository has run on, or reserved.
#:
#: ``1729, 2718, 3141`` -- Stage-1/Stage-2, Phase A, Phase D, Phase F, Phase I.
#: ``5772, 8119``       -- the Phase-A coverage-extension seeds.
#: ``929260329, 1281385038, 978843421`` -- the Phase-L triple, CONSUMED by the
#: formal Phase-L-B execution of pilot-v7-rc3.
#:
#: :func:`collision_report` proves this set covers everything
#: :func:`scan_committed_seeds` can find, so it cannot silently fall behind.
FORBIDDEN_SEEDS: frozenset[int] = frozenset(
    {1729, 2718, 3141, 5772, 8119, 929260329, 1281385038, 978843421}
)

#: The Phase-L triple specifically, named because its status must be recorded.
PHASE_L_SEEDS: tuple[int, int, int] = (929260329, 1281385038, 978843421)
PHASE_L_SEED_STATUS = "CONSUMED_BY_FORMAL_PHASE_L_B"

#: Where the committed history is scanned for seeds.  Directories, not files, so
#: a phase that adds a new results tree is covered without editing this module.
SCAN_ROOTS: tuple[str, ...] = ("configs", "results", "docs", "benchmark", "schemas")

#: PHASE-P'S OWN ARTIFACTS.  Once the derived triple is committed it necessarily
#: appears in the artifacts that declare it, so a scan that did not distinguish
#: them would report the phase colliding with itself and would make this record
#: irreproducible the moment it was written.
#:
#: The exclusion is an EXPLICIT, EXHAUSTIVE list of exact relative paths rather
#: than a prefix or a wildcard, and it cuts both ways: :func:`collision_report`
#: requires that NO source outside this list names a Phase-P seed, so leaking one
#: into a historical config, a committed result row or another phase's artifact
#: is a hard failure rather than a silent pass.
PHASE_P_ARTIFACTS: frozenset[str] = frozenset(
    {
        "configs/phaseP-qualification.yaml",
        "docs/phaseP_rc4_prospective_seed_derivation.json",
        "docs/phaseP_frozen_execution_inputs.json",
    }
)


class SeedDerivationError(RuntimeError):
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


def candidate_material(ordinal: int, counter: int, *, base_commit: str) -> str:
    """The exact byte string one candidate is derived from."""

    if ordinal < 1:
        raise ValueError("seed ordinals are 1-based")
    if counter < 0:
        raise ValueError("counters are 0-based and never negative")
    return f"{base_commit}|{DOMAIN_SEPARATOR}|seed-{ordinal}|counter-{counter}"


def derive_candidate(
    ordinal: int, counter: int, *, base_commit: str = CANONICAL_BASE_COMMIT
) -> tuple[str, str, int]:
    """Return ``(material, hex digest, candidate seed)`` for one search step."""

    material = candidate_material(ordinal, counter, base_commit=base_commit)
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
            f"the candidate {seed} is a FORBIDDEN historical seed; a Phase-P cell "
            "must never be confusable with a committed historical cell"
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
    forbidden: Iterable[int] = FORBIDDEN_SEEDS,
) -> tuple[list[int], list[Candidate]]:
    """Run the full deterministic search.  Returns the triple and every step.

    Every candidate examined -- accepted or rejected -- is returned in the order
    it was examined, so the artifact records the search rather than only its
    result.
    """

    forbidden_set = frozenset(forbidden)
    accepted: list[int] = []
    trail: list[Candidate] = []
    for ordinal in range(1, SEED_COUNT + 1):
        for counter in range(MAX_COUNTER):
            material, digest, seed = derive_candidate(
                ordinal, counter, base_commit=base_commit
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
            raise SeedDerivationError(
                f"no acceptable candidate for ordinal {ordinal} within "
                f"{MAX_COUNTER} counters; the derivation STOPS rather than "
                "choosing a value outside the algorithm"
            )
    return accepted, trail


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

    The enumeration is ``git ls-files`` rather than a filesystem walk, and the
    distinction is not cosmetic.  This repository gitignores several large local
    result directories -- ``results/raw/``, ``results/real-pilot/``,
    ``results/processed/``, ``results/phaseA-privacy-ablation/`` and
    ``results/pilot-v6.1-stage1/`` among them -- so a filesystem walk reads
    whatever happens to be on the machine running it.  A record built that way is
    not reproducible from the commit, and a completeness proof built that way
    proves something about a developer's disk rather than about committed
    history.  A fresh detached-worktree run of the Phase-P suite is what
    surfaced this, and this function is the repair.

    Git is required.  A tree in which git cannot be consulted cannot support a
    claim about committed history at all, so the failure is raised rather than
    degraded into a partial scan.
    """

    base = (root or PROJECT_ROOT).resolve()
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z", "--", *SCAN_ROOTS],
            cwd=base,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SeedDerivationError(
            "git could not enumerate the committed history, so the completeness of "
            f"the forbidden seed set cannot be proved: {exc}"
        ) from exc
    return sorted(
        item.decode("utf-8") for item in completed.stdout.split(b"\0") if item
    )


def scan_committed_seeds(root: Path | None = None) -> dict[int, list[str]]:
    """Every seed value the COMMITTED repository records, and where.

    Reads three surfaces of the TRACKED file set, because a seed can be recorded
    in any of them:

    * ``*.yaml`` under ``configs/`` -- the ``seeds:`` list and ``seed:`` scalars;
    * ``*.jsonl`` raw result rows -- each row's own ``seed`` field;
    * ``*.json`` artifacts -- any ``seed``/``seeds`` binding at any depth.

    Nothing here is a scientific reading of a result.  It is a byte scan whose
    only purpose is to prove that :data:`FORBIDDEN_SEEDS` is complete.
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


def prior_phase_seeds(
    scanned: Mapping[int, Sequence[str]] | None = None,
) -> dict[int, list[str]]:
    """The scan restricted to sources that are NOT Phase-P's own artifacts."""

    discovered = dict(scanned if scanned is not None else scan_committed_seeds())
    prior: dict[int, list[str]] = {}
    for seed, sources in discovered.items():
        outside = [name for name in sources if name not in PHASE_P_ARTIFACTS]
        if outside:
            prior[seed] = sorted(outside)
    return prior


def collision_report(
    seeds: Sequence[int],
    trail: Sequence[Candidate],
    *,
    scanned: Mapping[int, Sequence[str]] | None = None,
) -> dict[str, Any]:
    """Every collision condition, and the proof that the forbidden set is complete."""

    discovered = dict(scanned if scanned is not None else scan_committed_seeds())
    prior = prior_phase_seeds(discovered)
    uncovered = sorted(set(prior) - set(FORBIDDEN_SEEDS))
    reused = sorted(set(seeds) & set(prior))
    duplicates = sorted({seed for seed in seeds if list(seeds).count(seed) > 1})
    rejected = [item.to_dict() for item in trail if not item.accepted]
    # The exclusion cuts both ways: a Phase-P seed appearing anywhere other than
    # a declared Phase-P artifact is a leak, and is reported as a collision.
    leaked = {
        str(seed): sorted(prior[seed]) for seed in sorted(set(seeds) & set(prior))
    }
    return {
        "forbidden_seeds": sorted(FORBIDDEN_SEEDS),
        "phase_p_artifacts_excluded_from_history": sorted(PHASE_P_ARTIFACTS),
        "committed_seeds_discovered": {
            str(seed): list(sources) for seed, sources in sorted(prior.items())
        },
        "forbidden_set_covers_every_committed_seed": not uncovered,
        "committed_seeds_not_in_forbidden_set": uncovered,
        "derived_seeds_found_in_committed_history": reused,
        "derived_seeds_leaked_outside_phase_p_artifacts": leaked,
        "internal_duplicate_seeds": duplicates,
        "zero_valued_seeds": sorted({seed for seed in seeds if seed == 0}),
        "rejected_candidates": rejected,
        "rejection_rule": (
            "Starting at counter=0, accept the first candidate that is non-zero, "
            "is not a FORBIDDEN historical seed and does not duplicate a seed "
            "already accepted for a lower ordinal; otherwise record the rejection "
            "and increment the counter. The rule is part of the algorithm: no "
            "alternative is ever chosen by hand, and a rejected candidate is "
            "recorded rather than discarded."
        ),
        "history_scope": (
            "Every seed recorded by a git-TRACKED file under "
            f"{list(SCAN_ROOTS)}, EXCEPT those recorded in Phase P's own declared "
            "artifacts, which necessarily carry the derived triple once it is "
            "committed. A derived seed appearing in any OTHER source is reported "
            "as a leak. The enumeration is `git ls-files`, not a filesystem walk, "
            "so gitignored local result directories cannot influence the record "
            "and the scan is reproducible from the commit."
        ),
        "collision_free": not (uncovered or reused or duplicates or leaked)
        and all(seed != 0 for seed in seeds),
    }


def build_record(
    *,
    base_commit: str = CANONICAL_BASE_COMMIT,
    scanned: Mapping[int, Sequence[str]] | None = None,
) -> dict[str, Any]:
    """Assemble the complete, self-describing Phase-P derivation record."""

    seeds, trail = derive_seeds(base_commit=base_commit)
    return {
        "record_kind": "phase_p_prospective_seed_derivation",
        "phase": "P",
        "benchmark_version": "pilot-v7-rc4",
        "qa_mode": "off",
        "canonical_base_commit": base_commit,
        "domain_separator": DOMAIN_SEPARATOR,
        "derivation_algorithm_version": DERIVATION_ALGORITHM_VERSION,
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
        "seeds": list(seeds),
        "seed_order_is_frozen": True,
        "derived_before_any_rc4_inference": True,
        "model_inference_performed": False,
        "model_output_influenced_derivation": False,
        "manual_selection_performed": False,
        "phase_l_seeds": list(PHASE_L_SEEDS),
        "phase_l_seeds_status": PHASE_L_SEED_STATUS,
        "collision_checks": collision_report(seeds, trail, scanned=scanned),
        "authorizes_execution": False,
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

RECORD_RELATIVE = "docs/phaseP_rc4_prospective_seed_derivation.json"


def render(record: Mapping[str, Any]) -> str:
    """The canonical serialization.  Byte-for-byte reproducible."""

    return json.dumps(record, indent=2, sort_keys=True) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-commit",
        default=CANONICAL_BASE_COMMIT,
        help="canonical Phase-P starting SHA the derivation is pinned to",
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

    checks = record["collision_checks"]
    failures: list[str] = []
    if not checks["forbidden_set_covers_every_committed_seed"]:
        failures.append(
            "the committed history records seeds the forbidden set does not cover: "
            f"{checks['committed_seeds_not_in_forbidden_set']}"
        )
    if checks["derived_seeds_found_in_committed_history"]:
        failures.append(
            "a derived seed already appears in committed history: "
            f"{checks['derived_seeds_found_in_committed_history']}"
        )
    if checks["derived_seeds_leaked_outside_phase_p_artifacts"]:
        failures.append(
            "a derived seed appears outside Phase P's own declared artifacts: "
            f"{checks['derived_seeds_leaked_outside_phase_p_artifacts']}"
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
            f"any of the {len(checks['committed_seeds_discovered'])} seeds the "
            "committed history records"
        )

    if args.out and not failures:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(record), encoding="utf-8", newline="\n")
        print(f"record={out}")
    print(
        f"Phase-P seed derivation: {'PASS' if not failures else 'FAIL'} "
        f"({len(failures)} failure(s)); NO MODEL INFERENCE"
    )
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CANONICAL_BASE_COMMIT",
    "DERIVATION_ALGORITHM_VERSION",
    "DOMAIN_SEPARATOR",
    "FORBIDDEN_SEEDS",
    "MAX_COUNTER",
    "PHASE_L_SEEDS",
    "PHASE_L_SEED_STATUS",
    "RECORD_RELATIVE",
    "SEED_COUNT",
    "SEED_MASK",
    "Candidate",
    "SeedDerivationError",
    "build_record",
    "candidate_material",
    "PHASE_P_ARTIFACTS",
    "collision_report",
    "derive_candidate",
    "derive_seeds",
    "prior_phase_seeds",
    "render",
    "scan_committed_seeds",
    "tracked_files",
]
