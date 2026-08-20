#!/usr/bin/env python3
"""Preflight or run credential-gated real-model smoke/pilot cells."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from iqa_soa.experiment.pilot import (  # noqa: E402
    PilotConfigError,
    load_pilot_config,
    preflight_pilot,
    run_real_pilot,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", default=str(PROJECT_ROOT / "configs" / "pilot.yaml")
    )
    parser.add_argument(
        "--stage", choices=("preflight", "smoke", "pilot"), default="preflight"
    )
    parser.add_argument(
        "--providers",
        nargs="+",
        help="Configured provider IDs; defaults to the complete pilot list.",
    )
    parser.add_argument(
        "--verified-smoke-dirs",
        nargs="+",
        type=Path,
        help="For pilot stage, one validated four-cell smoke directory per provider.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_pilot_config(args.config)
        preflight_stage = "pilot" if args.stage == "preflight" else args.stage
        report = preflight_pilot(
            config, provider_ids=args.providers, stage=preflight_stage
        )
        print(f"benchmark_version: {report.benchmark_version}")
        print(f"models: {report.models}")
        print(f"tasks: {report.tasks}")
        print(f"treatments: {report.treatments}")
        print(f"repetitions: {report.repetitions}")
        print(f"expected_total_model_runs: {report.expected_total_runs}")
        print(f"max_total_runs: {report.max_total_runs}")
        for name, details in report.provider_environment.items():
            status = "ready" if not details.get("missing") else "missing environment"
            missing = ",".join(str(item) for item in details.get("missing", []))
            print(f"provider {name}: {status}{f' ({missing})' if missing else ''}")
        if args.stage == "preflight":
            return 0 if report.credentials_ready else 3
        outputs = run_real_pilot(
            config,
            provider_ids=args.providers,
            stage=args.stage,
            verified_smoke_dirs=args.verified_smoke_dirs,
        )
    except (PilotConfigError, ValueError) as exc:
        print(f"real pilot failed: {exc}", file=sys.stderr)
        return 2
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
