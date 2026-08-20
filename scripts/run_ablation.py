"""Run FULL and every configured full-minus-one QA Module treatment."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from iqa_soa.experiment.ablation import load_ablation_treatments
from iqa_soa.experiment.runner import ExperimentRunner, load_experiment_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(PROJECT_ROOT / "configs" / "experiment.yaml"))
    parser.add_argument("--output-root")
    parser.add_argument("--repetitions", type=int)
    args = parser.parse_args()
    config = load_experiment_config(args.config).with_overrides(
        output_root=args.output_root, repetitions=args.repetitions
    )
    output = ExperimentRunner(config).run(
        treatments=load_ablation_treatments(config.ablations_path),
        repetitions=config.repetitions,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
