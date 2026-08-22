#!/usr/bin/env python3
"""Regenerate the Phase-L frozen-input record and the plan's SHA-256 sidecar.

Deterministic and offline.  Running it twice on an unchanged tree produces
byte-identical output, which is what lets a test assert that the committed
record was not hand-edited.  It contacts no provider and runs no model.

This is TOOLING, not a scientific execution input: the record it produces is
what the driver asserts, and the record is independently verifiable by
re-running this script.  It is deliberately separate from
``scripts/phaseL_protocol.py`` for the same reason
``scripts/phaseM_write_instrument_revision.py`` is separate from
``scripts/instrument_revision.py`` -- the thing that WRITES a freeze and the
thing that ENFORCES it should not be the same file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import phaseL_protocol as protocol  # noqa: E402


def render_record() -> str:
    return json.dumps(protocol.compute_frozen_inputs(), indent=2, sort_keys=True) + "\n"


def render_sidecar() -> str:
    return f"{protocol.sha256_file(protocol.PLAN_RELATIVE)}  {protocol.PLAN_RELATIVE}\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed artifacts match, and write nothing",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    record_path = PROJECT_ROOT / protocol.FROZEN_INPUTS_RELATIVE
    sidecar_path = (PROJECT_ROOT / protocol.PLAN_RELATIVE).with_suffix(".sha256")

    record = render_record()
    sidecar = render_sidecar()

    if args.check:
        failures: list[str] = []
        for path, expected in ((record_path, record), (sidecar_path, sidecar)):
            actual = path.read_text(encoding="utf-8") if path.is_file() else ""
            if actual != expected:
                failures.append(
                    f"{path.relative_to(PROJECT_ROOT).as_posix()} is not what this "
                    "generator produces from the current tree"
                )
        for failure in failures:
            print(failure)
        print(
            f"Phase-L frozen-input record: {'PASS' if not failures else 'FAIL'} "
            f"({len(failures)} failure(s)); NO MODEL INFERENCE"
        )
        return 0 if not failures else 1

    record_path.write_text(record, encoding="utf-8", newline="\n")
    sidecar_path.write_text(sidecar, encoding="utf-8", newline="\n")
    print(f"wrote {protocol.FROZEN_INPUTS_RELATIVE}")
    print(f"wrote {sidecar_path.relative_to(PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
