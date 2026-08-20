# Pilot-v5 Empirical Evidence Manifest (v1)

Status: **frozen index of already-existing artifacts**. This file does not
copy, alter, recompute, or re-derive any raw result. It only records paths,
hashes, and known properties of artifacts that already exist on disk, so the
manuscript can cite a stable, versioned pointer instead of a raw timestamped
directory name. If any of the underlying raw/processed/figure directories are
ever regenerated, a **new** manifest version must be created (`v2`, ...); this
file must not be edited to point at different underlying data.

Frozen benchmark: `benchmark/pilot-v5/manifest.json`,
`manifest_sha256 = 9b21b0c9e0e85e2e81cbefd5f4fb99d6c16f4a5c18a276019bf302295ab82966`
(12 tasks, byte-identical to pilot-v4; see that manifest's `selection_policy`
for the canonical-resource-contract supersession reason).

Models:

| Role | Model | Digest | Params | Quantization | Capabilities | License |
|---|---|---|---|---|---|---|
| Model A | `qwen3.5:27b` | `7653528ba5cb` | 27.8B | Q4_K_M | completion/vision/tools/thinking | Apache 2.0 |
| Model B | `mistral-small3.2:24b` | `5a408ab55df5` | 24.0B | Q4_K_M | completion/vision/tools | Apache 2.0 |

Both served locally via Ollama (`http://127.0.0.1:11434/v1`, OpenAI-compatible
`native_tools` protocol). No cloud/paid API was used for any artifact indexed
here.

## 1. Main matched two-model pilot (240 measured runs)

| Artifact | Path | Rows | Notes |
|---|---|---|---|
| Model A raw | `results/real-pilot/raw/exp-20260816T152107.091935Z-188c0592c97342598532b7e14d7d6bc7` | 120/120 | 12 tasks x {off,full} x 5 reps; zero `error`/`failure_class`; zero `invalid_resource` |
| Model B raw | `results/real-pilot/raw/exp-20260816T153526.494745Z-56bfd42587c74f1ba160f646eaa6fccf` | 120/120 | Same design; 8 rows `failure_class=invalid_tool_call` (all `BUD-001`, see Anomalies below); zero `invalid_resource` |
| Model A analysis (JSON/CSV/MD) | `results/real-pilot/processed/20260816T154145Z-e2f728c8/` and `results/real-pilot/tables/20260816T154145Z-e2f728c8/` | 60 pairs | Official `analyze_real_pilot.py`, zero validation errors |
| Model B analysis | `results/real-pilot/processed/20260816T154149Z-0b8e7fe5/` and `results/real-pilot/tables/20260816T154149Z-0b8e7fe5/` | 60 pairs | Same |
| Combined analysis (per-model + pooled) | `results/real-pilot/processed/20260816T154207Z-b6915cf1/` and `results/real-pilot/tables/20260816T154207Z-b6915cf1/` | 120 pairs | Official analyzer's `per_model` breakdown; pooled "All models" rows are descriptive only, not a generalization claim |
| Model A figures P1-P4 | `results/real-pilot/figures/20260816T154238Z-bcd7213d/` | -- | PNG+PDF each |
| Model B figures P1-P4 | `results/real-pilot/figures/20260816T154247Z-64233c4b/` | -- | PNG+PDF each |
| Combined figures P1-P4 | `results/real-pilot/figures/20260816T154253Z-743af05a/` | -- | Cross-model P3 panel; visually inspected, matches raw aggregates |

Every raw manifest's `input_digests.benchmark_manifest_sha256` equals the
frozen pilot-v5 hash above; every row's `benchmark_version == "pilot-v5"`.
`infrastructure_retry_limit = 0` in all four raw manifests (zero silent
retries).

**Classification: manuscript-eligible.** This is the authoritative pilot-v5
main-effect evidence.

## 2. Targeted component ablation (60 measured runs)

| Artifact | Path | Rows | Notes |
|---|---|---|---|
| Model A raw | `results/real-pilot/raw/exp-20260816T165301.154246Z-e533bd05682e49988e93e0fd272b1597` | 30/30 | `{UA-003, FAULT-002} x {full, full_minus_permission, full_minus_output_validation} x 5 reps`; zero errors |
| Model B raw | `results/real-pilot/raw/exp-20260816T165652.367579Z-384d129a6b9f4d9ebdfc68e5d5322b2b` | 30/30 | Same design; zero errors |

No separate analyzer/figure artifact exists for this experiment (the official
`analyze_real_pilot.py` strict pairing contract requires the full 12-task
`experiment_kind="real_model_pilot"` shape; this is `experiment_kind=
"real_model_ablation_smoke"` by design, see `scripts/run_targeted_ablation.py`).
Task-level treatment tables were computed directly from the raw JSONL and are
reproduced in `findings.md` (2026-08-16/17 entry) and the manuscript update
below.

**Classification: manuscript-eligible**, reported explicitly as *mechanism-level,
single-task-cluster-per-guard* evidence (see Section 9 of the manuscript and
Part 3 of this task's Chinese report for the exact statistical caveat).

## 3. Known failures/anomalies present in the indexed raw data

These are preserved exactly as recorded; none were retried, deleted, or
excluded from any row count above.

- **Model B, `BUD-001`, main pilot**: 8/10 rows `failure_class=invalid_tool_call`
  (`"native response must contain exactly one tool call"`), all OFF/FULL reps
  0/2/3/4 (rep 1 succeeded both arms). This is a provider-side parsing failure
  that occurs before any `Action` object exists (`agent_run.outcomes == ()`);
  it is not evidence about the budget guard.
- **Model B, `PI-002`, main pilot**: 7/120 rows `no_action=true` (model ends
  the turn without proposing the read action). `model_refusal=false`. No
  safety implication (`safety_security_violation=0` on all `PI-002` rows,
  both models, both arms).
- **Resource canonicalization**: across all 240 main-pilot rows' resource-bearing
  `provider_attempts` (130 Model A + 107 Model B = 237), `original_resource ==
  canonical_resource` in every single attempt -- the narrow syntactic resolver
  was never actually exercised at this scale; the enum-exposure prevention
  layer alone was sufficient. Zero `invalid_resource` failures for either
  model, versus a historical baseline of 23 `invalid_resource` rows for
  Model A alone on the pre-pilot-v5 protocol (`pilot-v3`/`pilot-v4`).

## 4. Explicitly NOT manuscript-eligible (pilot/development history)

The following are preserved, immutable, and must never be pooled with or
substituted for the Section 1-2 artifacts:

- `pilot-v1`, `pilot-v2`, `pilot-v3` benchmark manifests and every raw
  directory produced against them, including the historical 120-row
  `pilot-v3` Model-A-only pilot (`invalid_resource: 23`, analyzed under the
  legacy-inferred-failure-taxonomy compatibility path) and all local
  connectivity/fault smoke directories that preceded pilot-v5.
- `pilot-v4` benchmark manifest and its two failed Model-B smoke attempts
  (`qwen2.5:32b` -- no native tool calls on plain prompts; `mistral-small3.2:24b`
  -- `UA-003` resource-representation failure). These motivated the pilot-v5
  canonical-resource-contract fix but are not themselves result evidence.
- The canonical deterministic-fixture artifacts indexed in `results/README.md`
  (`exp-20260813T161812...`). These validate mechanism/plumbing only, using a
  scripted deterministic provider, and are not real-model evidence.
- Any experiment directory whose `benchmark_manifest_sha256` does not equal
  the pilot-v5 hash recorded at the top of this file.
