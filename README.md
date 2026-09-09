# IQA-SOA: auditable runtime governance for LLM agents

This repository is the executable artifact for a study of IQA-SOA as an
independently enforced tool/service execution boundary and of a prospective
evaluation lifecycle that can refuse unsupported effectiveness inference.

The evidence is deliberately separated:

| Evidence class | Current support | Boundary |
|---|---|---|
| Mechanism | Established by deterministic runtime, fail-closed, evidence, and end-to-end trace tests | Instrumented `ServiceDecorator` / `ServiceGateway` path |
| Governance | Established for the frozen qualification lifecycle | Retained successor manifests, terminal rows, and authorization records |
| Effectiveness | **Not established** | No eligible QA FULL versus QA OFF confirmatory study was entered |

The current frozen successor state is generated directly from retained JSON in
[`artifact/generated/study_status.md`](artifact/generated/study_status.md). Its
terminal verdict is **HOLD**. HOLD is preserved as evidence that the lifecycle
refused a downstream claim; it is not a reason to retry cells, remove tasks,
change thresholds, or relabel QA-OFF observations as treatment evidence.

## Reviewer verification path

Create an isolated environment with Python 3.11 or newer and install the pinned
development dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

On Linux or macOS, use `./.venv/bin/python` instead. The portable aggregate
command is:

```text
python scripts/submission_artifact.py verify-artifact
```

The Make aliases used by CI and Unix-like reviewer environments are:

```text
make verify-mechanism
make verify-qualification
make verify-paper
make verify-anonymity
make verify-artifact
```

The first four commands print, respectively, `MECHANISM VERIFIED`,
`QUALIFICATION VERIFIED`, `PAPER EVIDENCE VERIFIED`, and the exact anonymity
scope checked. The aggregate target runs them all. These commands do not contact
a provider, rerun qualification, or create a confirmatory result.

`make generate-paper-evidence` regenerates the derived metadata, tables, and
trace. Verification fails if their bytes drift from the frozen sources.
`make build-anonymous-artifact` writes the anonymous directory and uploadable
ZIP; `verify-anonymity` builds it twice in isolated temporary directories and
requires byte-identical archives without modifying the checked-in evidence.

## Claim, trace, and trust-boundary artifacts

- [`artifact/claim_evidence_manifest.json`](artifact/claim_evidence_manifest.json)
  maps each important claim to evidence, tests, supported scope, and explicit
  nonclaims.
- [`artifact/traces/privacy_exfiltration.json`](artifact/traces/privacy_exfiltration.json)
  records one fixed-proposal end-to-end demonstration. QA OFF dispatches the
  synthetic protected message once; QA FULL blocks it before dispatch. This is
  mechanism evidence, not a model comparison.
- [`artifact/trust_boundary.json`](artifact/trust_boundary.json) names the trusted
  computing base, untrusted inputs, reviewed bypass cases, and threats outside
  the claimed boundary.

The precise claim is **complete mediation at the instrumented tool/service
execution boundary**. Host/runtime compromise, raw filesystem or network access,
arbitrary subprocess execution, direct calls around the documented gateway, and
malicious replacement of trusted enforcement code are not claimed to be
prevented by this in-process prototype.

## Runtime architecture

Agent output, prompt content, retrieved documents, and model-proposed tool
arguments are untrusted. Applications route proposals through the
`ServiceDecorator` and `ServiceGateway`; an ordered guard chain evaluates the
normalized QA Policy IR and only then reaches the exact-name sandbox registry.
Append-only evidence records the proposal, applicable policy, guard decisions,
dispatch disposition, and result.

QA-XML is one schema-validated serialization front end for the normalized typed
policy objects in `src/iqa_soa/iqa/policy.py`. The contribution is enforcement,
auditability, and lifecycle governance--not XML syntax. No Cedar, Rego, XACML,
or other adapter is claimed or stubbed.

Every tool in the artifact is simulated or confined to in-memory/temporary
experiment state. There is no production filesystem, database, messaging,
network, shell, or robot execution path.

## Repository map

- `src/iqa_soa/`: runtime, guards, sandbox adapters, evidence, and experiment machinery
- `schemas/` and `configs/`: QA-XML schema and frozen/public-safe configuration
- `benchmark/` and `candidates/`: benchmark and candidate identities
- `results/prospective-candidate-i5-m1-b76f40da2-qualification/`: retained successor qualification evidence
- `artifact/`: canonical submission metadata, claim map, trust boundary, trace, and generated tables
- `tests/`: deterministic mechanism, fail-closed, lifecycle, and integrity checks
- `paper/fse2027/`: anonymous LaTeX manuscript, supplement, and verification tooling

## Development-only experiments

The repository retains older deterministic and pilot tooling for provenance and
software development. Running those scripts creates new development artifacts;
it does not alter, qualify, or supersede the frozen study. Online-provider paths
remain separately credential- and authorization-gated. Do not treat fixture,
smoke, qualification, or QA-OFF-only output as QA-FULL effectiveness evidence.

Architecture, benchmark, metrics, protocol, and historical pilot details are in
[`docs/architecture.md`](docs/architecture.md),
[`docs/benchmark.md`](docs/benchmark.md),
[`docs/metrics.md`](docs/metrics.md), and
[`docs/experiment_protocol.md`](docs/experiment_protocol.md).
