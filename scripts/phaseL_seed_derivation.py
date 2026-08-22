#!/usr/bin/env python3
"""Derive the three PROSPECTIVE Phase-L seeds deterministically, before inference.

Phase F and Phase I both ran on the historical seed triple ``(1729, 2718, 3141)``.
Reusing them for the pilot-v7-rc3 requalification would make the new evidence
non-independent of the evidence that motivated the rc3 redesign, so Phase L needs
three seeds that are new, reproducible, and demonstrably not chosen after seeing
any result.

The derivation is therefore pinned to the canonical Phase-L-A starting commit and
to a fixed purpose string.  Anybody can recompute it from the commit SHA alone;
nothing about it can depend on a model output, because it is a pure function of
bytes that existed before the phase began.

    material = <canonical base SHA>
             + "|phase-l|pilot-v7-rc3|qa-off-requalification|seed-" + str(i)
    digest   = SHA256(material encoded UTF-8)
    seed     = int.from_bytes(digest[:4], "big") & 0x7fffffff

for ``i`` in ``1, 2, 3``.

Three collision conditions are checked and none of them is repaired here.  A
derived seed that is zero, that duplicates another Phase-L seed, or that equals
any seed used by a historical qualification phase is reported as a COLLISION and
the script exits non-zero.  Choosing an alternative ad hoc would reintroduce
exactly the investigator degree of freedom the derivation exists to remove; the
correct response is a reviewed change to the purpose string, not a nicer-looking
number.

This module performs no inference, contacts no provider and reads no result.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

#: The canonical Phase-L-A starting commit: ``main`` at the point Phase K,
#: K.1 and K.2 were merged.  The seeds are a function of this and nothing else.
CANONICAL_BASE_COMMIT = "beafa5d170659997790e1c3e79086ea05548c094"

#: The fixed purpose string.  It names the phase, the benchmark it will exercise
#: and the single treatment, so a seed triple derived for one purpose can never
#: be silently reused for another.
PURPOSE = "phase-l|pilot-v7-rc3|qa-off-requalification"

SEED_COUNT = 3

#: Every seed any earlier phase of this repository has run on, taken from the
#: committed experiment configurations and the recorded result manifests:
#: ``configs/experiment.yaml``, ``configs/pilot.yaml``, ``configs/pilot-v6.1.yaml``,
#: ``configs/phaseA-privacy-ablation.yaml``, ``configs/phaseD-diagnostic.yaml``,
#: ``configs/phaseF-qualification.yaml`` and ``configs/phaseI-qualification.yaml``.
HISTORICAL_SEEDS: tuple[int, ...] = (1729, 2718, 3141, 5772, 8119)

#: The mask that keeps the derived value a non-negative 31-bit integer, which is
#: the range every provider slot in this repository already accepts.
SEED_MASK = 0x7FFFFFFF


@dataclass(frozen=True, slots=True)
class DerivedSeed:
    """One derived seed together with everything needed to recompute it."""

    ordinal: int
    material: str
    digest: str
    first_four_bytes: str
    seed: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "material": self.material,
            "sha256": self.digest,
            "first_four_bytes": self.first_four_bytes,
            "seed": self.seed,
        }


def derive_seed(ordinal: int, *, base_commit: str = CANONICAL_BASE_COMMIT) -> DerivedSeed:
    """Derive one Phase-L seed from the canonical base commit and its ordinal."""

    if ordinal < 1:
        raise ValueError("seed ordinals are 1-based")
    material = f"{base_commit}|{PURPOSE}|seed-{ordinal}"
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return DerivedSeed(
        ordinal=ordinal,
        material=material,
        digest=digest.hex(),
        first_four_bytes=digest[:4].hex(),
        seed=int.from_bytes(digest[:4], "big") & SEED_MASK,
    )


def derive_seeds(*, base_commit: str = CANONICAL_BASE_COMMIT) -> tuple[DerivedSeed, ...]:
    """Derive the full prospective Phase-L seed triple, in ordinal order."""

    return tuple(
        derive_seed(ordinal, base_commit=base_commit)
        for ordinal in range(1, SEED_COUNT + 1)
    )


def collision_report(derived: tuple[DerivedSeed, ...]) -> dict[str, Any]:
    """Report the three collision conditions without repairing any of them."""

    seeds = [item.seed for item in derived]
    zero = sorted({seed for seed in seeds if seed == 0})
    duplicates = sorted({seed for seed in seeds if seeds.count(seed) > 1})
    historical = sorted(set(seeds) & set(HISTORICAL_SEEDS))
    return {
        "zero_valued_seeds": zero,
        "internal_duplicate_seeds": duplicates,
        "historical_seed_overlap": historical,
        "historical_seeds_checked_against": list(HISTORICAL_SEEDS),
        "collision_free": not (zero or duplicates or historical),
        "collision_policy": (
            "A zero, duplicate or historically reused seed is reported and the "
            "derivation STOPS. No alternative is chosen here: substituting a "
            "different value would reintroduce the investigator degree of freedom "
            "this derivation exists to remove."
        ),
    }


def build_record(*, base_commit: str = CANONICAL_BASE_COMMIT) -> dict[str, Any]:
    """Assemble the complete, self-describing derivation record."""

    derived = derive_seeds(base_commit=base_commit)
    return {
        "phase": "L-A",
        "purpose": PURPOSE,
        "canonical_base_commit": base_commit,
        "derivation_formula": (
            'material = <canonical_base_commit> + "|" + <purpose> + "|seed-" + str(i); '
            'digest = SHA256(material.encode("utf-8")); '
            'seed = int.from_bytes(digest[:4], "big") & 0x7fffffff; for i in 1..3'
        ),
        "seed_mask": f"0x{SEED_MASK:08x}",
        "derived_before_any_inference": True,
        "model_inference_performed": False,
        "derivations": [item.to_dict() for item in derived],
        "seeds": [item.seed for item in derived],
        "collision_checks": collision_report(derived),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-commit",
        default=CANONICAL_BASE_COMMIT,
        help="canonical Phase-L-A starting SHA the derivation is pinned to",
    )
    parser.add_argument(
        "--out", default=None, help="optional path to write the JSON record to"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    record = build_record(base_commit=args.base_commit)

    for item in record["derivations"]:
        print(f"seed-{item['ordinal']}")
        print(f"  material = {item['material']}")
        print(f"  sha256   = {item['sha256']}")
        print(f"  first4   = {item['first_four_bytes']}")
        print(f"  seed     = {item['seed']}")
    print(f"seeds = {record['seeds']}")

    checks = record["collision_checks"]
    if not checks["collision_free"]:
        print(
            "COLLISION: "
            f"zero={checks['zero_valued_seeds']} "
            f"duplicates={checks['internal_duplicate_seeds']} "
            f"historical_overlap={checks['historical_seed_overlap']}; "
            "no alternative seed is chosen here",
            file=sys.stderr,
        )
        return 2
    print(
        "collision checks: no zero seed, no internal duplicate, no overlap with "
        f"the historical seeds {list(HISTORICAL_SEEDS)}"
    )

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"record={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
