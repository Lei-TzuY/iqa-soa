# Result artifact index

## Canonical deterministic validation

- Main OFF/PARTIAL/FULL run:
  `raw/exp-20260813T161812.131986Z-4e15b9c3c6164b59bc79f75727e368db`
  (72/72 rows, zero errors, balanced treatment positions).
- FULL plus six data-driven ablations:
  `raw/exp-20260813T161812.142075Z-790dc69d41464fae8f1c5faf43bd3231`
  (168/168 rows, zero errors).
- Paired analysis:
  `processed/exp-20260813T161812.131986Z-4e15b9c3c6164b59bc79f75727e368db/before_after-20260813T161909Z-e87b2bbf.json`
  and the matching files under `tables/`.
- Publication-oriented renderings:
  `figures/exp-20260813T161812.131986Z-4e15b9c3c6164b59bc79f75727e368db/20260813T161910Z-39e4dc33/`.
- Replay: 72 records verified; ordered evidence digest
  `b09d31e659063fbc258e5ed1a916fdbafe20ff4aada6c70cc2375ceda4bc6041`.

The main manifest binds the runtime package source, QA-XML/schema, benchmark,
model/experiment/ablation configurations, provider descriptor, Python version,
and exact design size. Analysis and figure provenance bind the raw records and
manifest plus the generator script.

All earlier directories are preserved as immutable development/pilot history;
some intentionally contain failed or superseded runs. They must not be pooled
with or substituted for the canonical artifacts above. The canonical data use
the offline deterministic fixture and validate the artifact/mechanisms only;
they are not evidence of real-model generalization or statistical power.

## Real-model pilot status

Superseded by the frozen `pilot-v5` two-model evidence. See
[`results/pilot-v5-evidence-manifest.md`](pilot-v5-evidence-manifest.md) for
the authoritative, versioned index of the 240-run matched main pilot
(`qwen3.5:27b` / `mistral-small3.2:24b`) and the 60-run targeted
permission/output-validation ablation, including which artifacts are
manuscript-eligible versus preserved pilot/development history. All outputs
live under `results/real-pilot/`, generated/analyzed only with the commands
in `docs/real_model_pilot.md` and `scripts/run_targeted_ablation.py`;
deterministic directories in the section above must never be copied or
relabeled into that namespace.
