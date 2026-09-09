# Claim-Evidence-Boundary map

| ID | Type | Claim | Evidence | Supported boundary | Status |
|---|---|---|---|---|---|
| `C-MEDIATION` | mechanism | Instrumented protected tool and service execution passes through an IQA-SOA authorization boundary. | deterministic integration test; machine-readable paired trace | Complete mediation at the instrumented tool/service execution boundary when applications use the documented ServiceDecorator and ServiceGateway path. | `VERIFIED` |
|  |  | **Nonclaim** |  | No protection is claimed against arbitrary host compromise or raw operating-system, filesystem, network, or subprocess access outside the instrumented boundary. |  |
|  |  | **Nonclaim** |  | The paired deterministic trace is not a real-model treatment-effect estimate. |  |
| `C-FAIL-CLOSED` | mechanism | Declared pre-execution failures and policy violations do not silently become authorization. | deterministic fail-closed regression tests; bypass coverage inventory | The schema-validated policy, ordered guard chain, evidence preflight, rewrite reauthorization, and exact-name sandbox dispatch paths covered by the named tests. | `VERIFIED` |
|  |  | **Nonclaim** |  | Post-execution validation can contain returned data but cannot undo a side effect that already occurred. |  |
|  |  | **Nonclaim** |  | The frozen instrument's legacy would_execute field is not used as proof of side-effect occurrence for argument-validation refusals; the regression asserts the sandbox state directly. |  |
|  |  | **Nonclaim** |  | Application code that imports and calls ToolRegistry directly is inside the trusted host and outside the claimed mediation boundary. |  |
| `C-POLICY-IR` | mechanism | Runtime guards consume normalized QA Policy IR; QA-XML is its schema-validated serialization front end. | parser tests; typed policy implementation | The implemented typed Policy objects and the QA-XML v0.1 parser/schema used by this artifact. | `VERIFIED` |
|  |  | **Nonclaim** |  | No Cedar, Rego, XACML, SMT, or natural-language policy compiler integration is implemented or evaluated. |  |
|  |  | **Nonclaim** |  | Novelty is not claimed for XML syntax. |  |
| `C-EVIDENCE` | mechanism | Governed decisions produce append-only, disposition-bearing evidence with protected-value redaction. | deterministic evidence persistence tests; trace artifact | The local append-only JSONL evidence slice created by the in-process artifact runtime. | `VERIFIED` |
|  |  | **Nonclaim** |  | The evidence store is not claimed to be a cryptographic ledger, tamper-proof store, or complete QA-IUM graph database. |  |
| `C-QUALIFICATION` | governance | The frozen conjunctive qualification rule holds the study when any required frozen task is unqualified. | frozen qualification analysis; read-only recomputation; regression tests | The prospectively frozen 17-task successor qualification under its all-required-tasks conjunction. | `VERIFIED` |
|  |  | **Nonclaim** |  | The observed HOLD may not be replaced post hoc by an effect among support-qualified tasks. |  |
|  |  | **Nonclaim** |  | A support-qualified-task estimand would require a new, separately identified prospective study. |  |
| `C-LIFECYCLE` | governance | The prospective lifecycle preserved terminal accounting and blocked downstream confirmatory execution. | frozen run manifest; terminal row ledger; authorization regression tests | The retained successor qualification namespace and its prospectively frozen authorization and no-retry lifecycle. | `VERIFIED` |
|  |  | **Nonclaim** |  | No new qualification or confirmatory execution is authorized by this verification manifest. |  |
|  |  | **Nonclaim** |  | Invalidated and HOLD observations are preserved rather than retried, removed, or relabeled. |  |
| `C-EFFECTIVENESS-BOUNDARY` | effectiveness | The current artifact establishes no QA FULL versus QA OFF safety treatment effect. | absence-of-eligible-stage boundary; frozen authorization state | A verified nonclaim about this frozen study: effectiveness evidence is absent because the eligibility gate did not pass and confirmatory execution did not occur. | `VERIFIED_NONCLAIM` |
|  |  | **Nonclaim** |  | The repository does not claim that IQA-SOA improves real-model safety. |  |
|  |  | **Nonclaim** |  | QA-OFF qualification observations are not QA-FULL treatment evidence. |  |
