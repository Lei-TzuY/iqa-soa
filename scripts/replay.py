"""Replay one experiment's JSONL evidence under a deterministic ordering."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from iqa_soa.experiment.replay import replay_experiment
from iqa_soa.experiment.runner import load_experiment_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment_dir")
    parser.add_argument("--config", default=str(PROJECT_ROOT / "configs" / "experiment.yaml"))
    parser.add_argument("--output-root", help="Optional directory for the replay report")
    parser.add_argument("--repetitions", type=int, help="Accepted for CLI symmetry; replay uses recorded runs")
    parser.add_argument("--ordering", choices=["recorded", "timestamp", "run_id"], default="recorded")
    args = parser.parse_args()
    try:
        config = load_experiment_config(args.config)
        target = None
        if args.output_root:
            target = Path(args.output_root) / f"replay-{args.ordering}.json"
        report = replay_experiment(
            args.experiment_dir,
            benchmark_path=config.benchmark_path,
            ordering=args.ordering,
            output_path=target,
        )
    except (FileExistsError, ValueError, OSError) as exc:
        print(f"replay failed: {exc}", file=sys.stderr)
        return 2
    print(f"verified={report['verified']} runs={report['run_count']} digest={report['ordered_event_digest']}")
    return 0 if report["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
