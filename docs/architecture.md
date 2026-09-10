# IQA-SOA FSE Prototype Architecture

## Source-of-truth terminology

The 2026 proposal is authoritative for the research vocabulary and design:

- **QA Policy IR** says what must hold. The immutable typed objects in `iqa.policy` are the normalized executable semantics consumed by deterministic guards.
- **QA-XML (Quality Assurance eXtensible Markup Language)** is the current schema-validated serialization/front end that compiles into QA Policy IR. XML syntax is not the novelty claim.
- **IQA-SOA (Intelligent Quality Assurance Service Oriented Architecture)** enforces those constraints at runtime. Its Service Gateway, non-invasive Service Decorator, and pluggable QA Module responsibility chain separate probabilistic reasoning from execution authority.
- **QA-IUM (Quality Assurance Integrated Unified Model)** records what was specified, deployed, observed, decided, and done—and why. The full proposal defines it as a lifecycle DAG for consistency audit, tracing, attribution, rollback, and optimization feedback.

QA-UML, the proposal's visual collaborative notation for QA-XML, is separate from QA-IUM and is outside this prototype.

## Narrowed FSE architecture

The master implementation prompt narrows the four-year proposal to a controlled experiment:

```text
BenchmarkCase + seed
        |
        v
AgentProvider -> proposed Action[]
        |
        v
ServiceDecorator
        |
        v
ServiceGateway (the only governed execution entry)
        |
        +--> QA OFF: observe, then execute in sandbox
        |
        +--> QA PARTIAL/FULL/ABLATION
                 |
                 v
          normalized QA Policy IR
                 |
          ordered QA Module chain
          injection -> permission -> privacy -> budget -> output validation -> evidence
                 |
                 v
       ALLOW | BLOCK | MODIFY | ESCALATE
                 |
                 v
          sandbox ToolRegistry
                 |
                 v
       evidence fragment + run metrics
```

The invariant is `LLM reasoning != execution authority`: providers propose actions; only the gateway can authorize a governed action. Tools remain independently registerable, and the decorator inserts governance without changing their business logic.

## Component responsibilities

### Agent layer

`AgentProvider` isolates the harness from a model vendor. The deterministic provider replays case-defined action proposals for CI and exact paired controls. The OpenAI-compatible provider reads endpoint/key/model configuration from environment variables, prefers a native `sandbox_action` function call, retains a strict JSON-object fallback, and validates every result locally. It records non-content request/response provenance and explicit refusal/parse/transport classifications. Exact tool/resource matches receive a canonical benchmark action ID only after the model has chosen the action; the original ID remains auditable, and evaluator labels are never sent to the model.

### QA Policy IR and QA-XML front end

The normalized FSE Policy IR supports permissions, protected resources/data, budgets, injection indicators, deterministic output requirements, and high-risk confirmation. QA-XML is schema-validated before conversion to those typed policy objects. Runtime guards depend on the normalized objects rather than XML nodes, so another front end could be implemented later without changing guard semantics. Directly contradictory rules are rejected. This artifact does not implement or claim a Cedar, Rego, XACML, SMT, or natural-language compiler adapter, complete formal semantics, or convergence proofs.

### IQA-SOA layer

- `ServiceGateway` builds/accepts the runtime context, invokes the configured chain, aggregates decisions, invokes the sandbox only when authorized, and returns a structured outcome.
- `ServiceDecorator` is the non-invasive interceptor.
- `QAGuard` modules have deterministic order, explicit enablement, per-experiment configuration, latency measurement, matched-policy references, and structured reasons.
- Decision precedence is conservative: `BLOCK > ESCALATE > MODIFY > ALLOW`. The current guards do not silently invent a modification.

G1/partial is an FSE protocol choice because the proposal does not define the partial baseline. It enables the conventional permission and budget controls; the exact list is serialized with every experiment.

### Sandbox layer

The registry exposes the required file, database, message, API, simulated shell, and simulated robot actions. State lives only in an in-memory or temporary experiment environment. Email, HTTP effects, shell commands, and robot movements are simulations. A result distinguishes actual sandbox execution from a governance block and records that a dangerous proposal *would have executed* in the simulation.

### Evidence layer

Each action creates an append-only observation; a run that produces no action creates a terminal lifecycle observation. With detailed evidence enabled it includes a stable evidence ID, run/task/policy identity, proposal, QA Module results, final decision, executed action, tool trace, reason, latency, and causal link labels compatible with later QA-IUM import:

```text
requirement/case -> QA-XML policy -> proposed action/checkpoint
                 -> guard decision -> tool/disposition event
```

This is a **QA-IUM-compatible evidence slice**, not the full proposal DAG or an industrial graph database. It does not claim cryptographic tamper resistance. Event/version identifiers keep the stored fragment acyclic even though the broader research system has an evolution feedback loop.

## Safety boundaries and honest scope

The claimed boundary is **complete mediation at the instrumented tool/service execution boundary**. Its trusted computing base comprises the Service Decorator, Service Gateway, QA-XML parser and QA Policy IR, ordered guard chain, exact-name ToolRegistry/execution adapters, evidence persistence, and the in-process host that wires them together. Model output, prompts, retrieved documents, and model-proposed tool/resource arguments are untrusted inputs.

- Prompt-injection detection is deterministic and benchmark-scoped; it is not a general injection solution.
- QA-XML injection regular expressions are trusted experiment configuration. Syntax is validated, but the Python regular-expression engine provides no execution timeout; untrusted policy authors are outside this prototype's boundary.
- The in-process Python harness and extension code are trusted. `ToolRegistry` remains independently importable for unit testing/composition, so this prototype does not claim OS-level capability isolation against malicious host code that deliberately bypasses the documented Decorator/Gateway path.
- Compromised host/runtime code, raw network or filesystem access outside the gateway, arbitrary subprocess execution outside the instrumented path, malicious replacement of trusted enforcement code or policy bytes, and principal authentication supplied by the host are outside the threat model.
- Model-call ceilings are enforced before the next provider request in budget-enabled treatments. Token, cost, and elapsed-time values that become known only after a provider response cannot undo already consumed provider resources; the Budget Guard can contain the ensuing tool action and later requests.
- Output validation uses declared policy requirements and tool provenance, not an LLM judging itself; benchmark ground truth remains evaluator-only.
- No production filesystem, database, messaging, network, shell, or robot action is reachable.
- Online reinforcement learning, the Quality-Based Cost Model, full UC-SCEM, formal proofs, graph neural consistency checking, and autonomous self-modification remain outside the FSE runtime slice.
- The paper's `<500 ms` QA-IUM query target and 95% constraint-satisfaction optimization target are research objectives, not preclaimed results of this artifact.

The machine-readable inventory in `artifact/trust_boundary.json` binds these components and nonclaims to reviewed bypass tests. `artifact/claim_evidence_manifest.json` separately maps mechanism, governance, and effectiveness claims to evidence so that these boundaries cannot be elided in paper-facing summaries.
