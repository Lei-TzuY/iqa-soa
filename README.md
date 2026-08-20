# IQA-SOA Before/After Experimental Prototype

This repository is a runnable research artifact for controlled comparison of an
autonomous agent with runtime quality assurance disabled (`QA OFF`) and with the
full IQA-SOA governance chain enabled (`QA FULL`). It also includes the
permission-and-budget partial baseline and six FULL-minus-one ablations.

The terminology and research design follow `2026-final.pdf`:

- **QA-XML** is the executable, schema-validated constraint representation.
- **IQA-SOA** is the runtime enforcement layer: Service Gateway, Service
  Decorator, and ordered QA Module chain.
- **QA-IUM** is the proposal's lifecycle evidence DAG. This prototype implements
  only an append-only, QA-IUM-compatible evidence slice; it is not a graph
  database or tamper-proof ledger.

The default provider is an offline deterministic fixture provider. Its results
validate experimental plumbing and mechanism behavior; they are not evidence of
real-model generalization or statistical power.

## Requirements and setup

- Python 3.11 or newer
- No credentials for the default experiment

Create an isolated environment and install the pinned runtime and development
dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

On Linux or macOS, replace `.\.venv\Scripts\python` with
`./.venv/bin/python`.

## Reproduce the artifact

Run the four-case vertical slice:

```powershell
python scripts/run_smoke.py --config configs/experiment.yaml --repetitions 1
```

Run the complete paired OFF/PARTIAL/FULL experiment and the six ablations:

```powershell
python scripts/run_before_after.py --config configs/experiment.yaml
python scripts/run_ablation.py --config configs/experiment.yaml
```

Each command prints a newly created directory under `results/raw/`. Pass the
before/after directory to the analyzer and both directories to the figure
generator:

```powershell
python scripts/analyze_results.py results/raw/<before-after-experiment-id>
python scripts/generate_figures.py results/raw/<before-after-experiment-id> --ablation-dir results/raw/<ablation-experiment-id>
python scripts/replay.py results/raw/<before-after-experiment-id>
```

Run verification:

```powershell
python -m pytest -q
python -m mypy src/iqa_soa
```

The current Phase 2 tree was validated in this workspace with 131 passing tests,
a strict mypy pass over all 43 package modules, and a built-wheel installation
smoke. The canonical deterministic Phase 1 main run created 72 records (8 cases x 3
repetitions x 3 treatments); the ablation run created 168 records (8 x 3 x 7
treatments). Both completed with exact manifests and zero runner errors. These
counts describe artifact validation runs, not a publication sample.

Canonical validation artifacts:

- [main raw run](results/raw/exp-20260813T161812.131986Z-4e15b9c3c6164b59bc79f75727e368db)
- [ablation raw run](results/raw/exp-20260813T161812.142075Z-790dc69d41464fae8f1c5faf43bd3231)
- [paired Markdown table](results/tables/exp-20260813T161812.131986Z-4e15b9c3c6164b59bc79f75727e368db/before_after-20260813T161909Z-e87b2bbf.md)
- [Figures A–D](results/figures/exp-20260813T161812.131986Z-4e15b9c3c6164b59bc79f75727e368db/20260813T161910Z-39e4dc33)

The fixture result moves unauthorized-action execution from 15/15 under OFF to
0/15 under FULL, with interception recall moving from 0/15 to 15/15 and no
blocked required benign actions (0/24 in both arms). These are deterministic
mechanism checks; inferential fields are intentionally suppressed.

## Outputs

No command silently overwrites an earlier artifact.

- `results/raw/<experiment-id>/runs.jsonl` and `runs.csv`: one machine-readable
  record per case, repetition, and treatment.
- `results/raw/<experiment-id>/evidence/*.jsonl`: append-only action decisions,
  policy references, guard results, execution disposition, and tool traces.
- `results/raw/<experiment-id>/manifest.json`: input paths and SHA-256 digests,
  provider/software descriptors, cases, treatments, repetitions, seeds,
  expected/observed record counts, and explicit running/completed state.
- `results/processed/` and `results/tables/`: paired effect tables.
- `results/figures/`: Figures A-D in PNG and PDF plus source provenance.

The analyzer pairs only unablated OFF and FULL rows by task, repetition, seed,
provider, and model. For the deterministic fixture provider it reports raw
paired effects but suppresses confidence intervals and hypothesis tests because
repeated fixture executions are not independent model samples. Unknown cost is
kept as `null`. Online-provider inference aggregates repetitions within task,
uses task-cluster bootstrap/sign-flip procedures, and is explicitly limited to
the fixed benchmark-suite estimand. Derived tables and figures include SHA-256
digests of their raw inputs.

## Treatments and safety boundary

- `off`: proposals execute in the sandbox, while minimal observation remains so
  outcomes can be measured.
- `partial`: permission and budget guards only. This is an explicit FSE
  prototype choice because the proposal does not define the partial baseline.
- `full`: injection, privacy, permission, budget, output-validation, and evidence
  modules.
- `full_minus_*`: removal of exactly one module, loaded from the strict maps in
  `configs/ablations.yaml` and hashed into every experiment manifest.

Every tool is simulated or confined to experiment state. There is no production
filesystem, database, messaging, network, shell, or robot execution. Injection
detection is a deterministic benchmark heuristic, and simulated latency faults
do not sleep in real time.

## Optional OpenAI-compatible provider

`configs/models.yaml` contains a disabled OpenAI-compatible chat-completions
provider. To use it, work on a copied configuration, set it as
`default_provider`, explicitly set `enabled: true`, configure its endpoint/model,
and provide the named API-key environment variable (default:
`OPENAI_API_KEY`). Credentials are read from the environment and never written
to result records. Freeze provider/model versions and determine repetitions with
an a priori study plan before treating online runs as empirical evidence.

## Phase 2 real-model pilot

The repository now includes a credential-gated real-model pilot path without
changing or relabeling the deterministic artifacts. It provides frozen
`pilot-v1`, `pilot-v2`, and active metric/protocol successor `pilot-v3`, two environment-only
provider slots, native-tool/strict-JSON action protocols, explicit refusal and
failure classifications, a 300-run safety ceiling, a mandatory four-cell smoke
gate, complete real-provider provenance, per-model analysis, and separate
Figures P1--P4.

Local-Ollama smoke artifacts are kept separate from deterministic results. The
active v3 protocol reports safety/security and resource-budget violations
separately; its overall constraint metric is their explicitly labeled union.
Inspect the planned 240-run design without making an API request:

```powershell
python scripts/run_real_pilot.py --stage preflight
```

See [`docs/real_model_pilot.md`](docs/real_model_pilot.md) for environment
variables, gated smoke/pilot commands, analysis, figures, and the current
evidence limitations.

## Design documentation

- [`docs/architecture.md`](docs/architecture.md): runtime structure and scope
- [`docs/benchmark.md`](docs/benchmark.md): typed case schema and construction
- [`docs/metrics.md`](docs/metrics.md): operational definitions and statistics
- [`docs/experiment_protocol.md`](docs/experiment_protocol.md): controls,
  repetitions, randomization, and validity threats
- [`docs/paper_mapping.md`](docs/paper_mapping.md): proposal and FSE RQ mapping
- [`docs/real_model_pilot.md`](docs/real_model_pilot.md): frozen real-provider pilot protocol and status
