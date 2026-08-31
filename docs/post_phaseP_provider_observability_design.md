# Post-Phase-P provider observability design

**Record kind:** prospective observability design record
**Status:** DESIGN RECORD, not an implementation specification and not an authorization
**Revision:** 1
**Date:** 2026-08-29
**Canonical main:** `a270c65ee1db9dd0c79c62f0be6d9acd774ec598`
**Working branch HEAD at time of design:** `883c425daf2e6462877f0626f5fce0664ac85ca9`
**Discharges:** prospective-redesign prerequisite 3, change **C3** only
(`docs/post_phaseP_prospective_redesign_decision.md` §4.2 Ground 2, §6.2 C3, §9.1, §9.3, §9.5, §11.5 item 3)

---

## 1. Purpose and boundary

### 1.1 What this record is

**[OBSERVED]** `docs/post_phaseP_prospective_redesign_decision.md` §6.2 registers change **C3**:

> *Provider failure-path telemetry, minimum set only (§9.3)* — class `MEASUREMENT_IMPROVEMENT`,
> *"Requires a mutation proof that the accept/refuse decision function is unchanged. If any decision
> changes, it is not this class and must be reclassified."*

**[OBSERVED]** §11.5 lists four prerequisites before candidate implementation may be considered.
Prerequisite 3 is *"the corrected provider observability design — the §9.3 minimum set with the §9.5
mutation proof."* This record discharges that prerequisite and **nothing else**.

This is the **design** of the smallest prospective repair. It is not the repair.

### 1.2 What was done to produce it

**[OBSERVED]** Producing this record involved:

- **no model inference**, no provider contact, no Ollama contact, no OpenAI contact, no network call,
  no socket open;
- **no execution** of any validator, probe, harness, analyzer, writer or `pytest` invocation;
- **no read, list, traversal, hash or modification** of anything beneath `results/phaseP-rc4-qualification/`;
- **no use of any Phase-P outcome row, proposal, trajectory or count** to select, size, name or tune any
  telemetry field;
- **no seed derivation**;
- **no modification** of any file under `src/`, `tests/`, `benchmark/`, `configs/`, `schemas/` or `scripts/`;
- **no version constant moved**;
- **no successor candidate, candidate version number or phase name created**;
- **no staging, commit, push, tag or merge**.

Exactly one file is written: this document. Every other repository path was read-only input.

### 1.3 Inputs actually read

**[OBSERVED]** `docs/post_phaseP_prospective_redesign_decision.md` (in full);
`src/iqa_soa/agent/providers.py`; `src/iqa_soa/agent/agent.py`; `src/iqa_soa/experiment/runner.py`;
`src/iqa_soa/experiment/failure_events.py`; `src/iqa_soa/instrument.py`;
`src/iqa_soa/metrics/definitions.py`; `src/iqa_soa/failure_taxonomy.py`;
`src/iqa_soa/experiment/confirmatory.py` (provider-error handling only);
`src/iqa_soa/metrics/pilot.py` (attempt projection only); `scripts/instrument_revision.py`;
`scripts/phaseP_protocol.py` (version pins only); `scripts/analyze_phaseL_requalification.py` and
`scripts/analyze_phaseD_qualification.py` (attempt readers only);
`tests/unit/test_benchmark_providers.py`; `tests/integration/test_post_phaseP_instrument_revision.py`;
`benchmark/pilot-v7-rc4/qualification-contract.json` (the `rc4_instrument_boundary` string only).

**[OBSERVED]** Every failure-path claim in §2 below is derived from **code control flow only**. No claim
in this record is derived from an observed Phase-P outcome, count or trajectory.

### 1.4 The two accepted prerequisite-2 records

**[OBSERVED]** `docs/post_phaseP_legitimate_sink_applicability_audit.md` and
`docs/post_phaseP_BUD018_information_architecture_review.md` exist as uncommitted accepted records and
were **not modified, reformatted or re-derived** by this task. They are preserved byte-for-byte.

### 1.5 Standing status, restated and unchanged

**[OBSERVED]** `pilot-v7-rc4` remains **UNQUALIFIED**. The official Phase-P verdict remains **permanently
HOLD** with terminal status `SCHEDULE_COMPLETE_VERDICT_HOLD`. The classification of the preserved
invalidated cell `mistral | BEN-003 | 1133353488` remains `MODEL_PROTOCOL_INVALID`, the BEN-003 task
status remains `MATRIX_INVALID`, and the forensic attribution remains `MODEL_PROTOCOL_FAILURE`.
**Nothing in this record revises, reinterprets, softens, repairs or re-attributes any of them.**

### 1.6 What this design must not do

**[OBSERVED]** C3 is an observability repair. It must not, and this design does not:

improve model performance; alter any prompt, system message or user message; alter the tool definition,
the tool contract or the model-visible argument schema; alter token budgets, `max_tool_calls`,
`max_model_calls` or `max_agent_steps`; alter retry counts or retry policy; alter provider selection;
turn malformed model output into valid output; rescue a previously invalid cell; or reinterpret any
Phase-P evidence.

---

## 2. Current failure-path information loss

### 2.1 The control-flow landmarks

**[OBSERVED]** The single provider call path is
`OpenAICompatibleProvider.generate_action` (`src/iqa_soa/agent/providers.py:456-729`), with two helpers,
`_parse_message_action` (`:734-866`) and `_parse_action_object` (`:868-905`). The landmarks that decide
what is knowable at each raise site:

| Line | Landmark |
|---|---|
| `:553` | `client_request_id = str(uuid4())` — the only identifier that exists before the request |
| `:564` | `started = time.perf_counter()` |
| `:566-568` | `urlopen` succeeds; `raw_bytes = response.read()`; `request_id` read from the `x-request-id` header |
| `:594` | `latency_ms` computed |
| `:595-607` | envelope decode and shape walk: `json.loads` then `Mapping`, `choices`, `choice`, `message` |
| `:615-632` | `usage` shape check and `prompt_tokens` / `completion_tokens` extraction into locals |
| `:634-640` | `refusal` type check |
| `:642-645` | `finish_reason`, `response_id`, `effective_model`, `system_fingerprint` extracted into locals |
| `:662-664` | `_parse_message_action(message)` |
| `:679-686` | `_parse_action_object(candidate)` per emitted call |
| `:707-729` | `ProviderResponse` constructed — the success path |

**[OBSERVED]** There are exactly **23 `raise ProviderError` sites** reachable from this path:
7 in `generate_action` (`:469, :573, :581, :588, :609, :617, :636`), 11 in `_parse_message_action`
(`:749, :759, :770, :778, :787, :794, :823, :835, :842, :850, :856`), 4 in `_parse_action_object`
(`:873, :879, :885, :892`), and 1 in `_nonnegative_int` (`:912`, re-raised through `:630-632`).

**[OBSERVED]** `ProviderError.provenance()` (`:139-160`) hard-codes `response_id`, `effective_model`,
`finish_reason`, `system_fingerprint`, `input_tokens` and `output_tokens` to `None` for **all 23** of
them, unconditionally, by construction. It also emits **no** `protocol` key and **no** `effective_seed`
key at all, where `ProviderResponse.provenance()` (`:230-265`) emits both.

**[OBSERVED]** The five things that **do** survive a failure today: `failure_class`,
`client_request_id`, `request_id`, `tool_call_count` (only where it is back-filled at `:684`), and
`tool_contract_refreshed`. `failure_origin` exists on the exception (`:126-137`) and is deliberately
**not** persisted — `tests/unit/test_benchmark_providers.py:149` asserts its absence from
`provenance()`.

### 2.2 Failure-class map

**[OBSERVED]** "Available" below means *the value is reachable from a variable in scope at the raise
site*, decided from control flow alone.

| Class | Raise site(s) | HTTP response received | Envelope parsed | Assistant message available | Native tool-call payload available | Usage/token object available | Persisted today | Lost before `provenance()` |
|---|---|---|---|---|---|---|---|---|
| **A0** — credential env var unset (pre-transport) | `:469` | no | no | no | no | no | `failure_class="provider_error"` only | `protocol` (known from `__init__`) |
| **A** — transport/network failure before response | `:581` (timeout), `:588` (`URLError`) | no | no | no | no | no | `failure_class`, `client_request_id`, `retryable` | `protocol`, `effective_seed` |
| **B** — non-2xx HTTP/provider response | `:573` | yes (error response; body deliberately never read) | no | no | no | no | `failure_class`, `client_request_id`, `request_id` (from `exc.headers`), `retryable` | `protocol`, `effective_seed`; `exc.code` is used to select `failure_class`/`retryable` at `:569-572` and then discarded |
| **C1** — payload is not decodable JSON, or is not an object | `:609` via `UnicodeDecodeError`, `JSONDecodeError`, or the `TypeError` at `:597` | yes | no | no | no | no | `failure_class="invalid_json"`, both ids | `protocol`, `effective_seed` |
| **C2** — payload decodes to a mapping but the choice/message walk fails | `:609` via `KeyError`/`TypeError` at `:599-607` | yes | **top level yes** | no (that is the failure) | no | reachable via `envelope["usage"]` | same as C1 | **`response_id`, `effective_model`, `system_fingerprint` are reachable from `envelope` and are dropped**; `finish_reason` reachable whenever `choice` is a mapping |
| **D** — valid envelope, malformed assistant structure | `:617` (usage not an object), `:630`/`:912` (usage field not a non-negative int), `:636` (refusal not text or null) | yes | yes | yes | not yet inspected | yes at `:617`/`:630`; **already bound locals** at `:636` | `failure_class="invalid_json"`, both ids | **all four envelope fields reachable at every site**; at `:636` `input_tokens` and `output_tokens` are already bound locals and are dropped |
| **E** — valid assistant message, invalid or missing native tool call | `:749`, `:823`, `:835` | yes | yes | yes | inspected; falsy or unusable | yes (locals) | `failure_class="invalid_tool_call"`, both ids back-filled at `:665-670`, `tool_contract_refreshed` | **all six values are live locals in `generate_action` and all six are dropped**; the native tool-call state is collapsed by the falsy guard at `:747` and is unrepresented |
| **F** — invalid tool-call arguments / protocol violation | `:759, :770, :778, :787, :794, :842, :850, :856`; `:873, :879, :885, :892` | yes | yes | yes | yes | yes (locals) | as E, plus `tool_call_count` back-filled at `:684` for the `_parse_action_object` sites | **all six values are live locals and all six are dropped** |
| **G** — successful valid action path | — | yes | yes | yes | yes | yes | `ProviderResponse.provenance()` emits all six plus `protocol`, `effective_seed`, emitted proposals and tool-call ids | **nothing** |

### 2.3 The four structural findings

**[OBSERVED] F-1 — the ambiguity is total on the failure path.** Because `provenance()` writes the six
values as literal `None` at `:150-157` regardless of branch, a persisted `None` on a failure row cannot
be distinguished from a value the provider genuinely omitted, and neither can be distinguished from a
value that was never reachable. Three different facts collapse to one byte. This is exactly the finding
recorded at redesign-decision §9.2.

**[OBSERVED] F-2 — the loss is largest exactly where attribution matters most.** Classes **E** and **F**
are the model-protocol failure classes (`ProviderFailureOrigin.MODEL_OUTPUT` at `:752-798`, `:826-859`,
`:876-895`). At every one of those sites all six values are already bound local variables in
`generate_action` — `input_tokens`/`output_tokens` at `:623-628` and the four envelope fields at
`:642-645` — and the existing `except ProviderError` handlers at `:665-670` and `:681-686` back-fill
three unrelated attributes while stepping over all six.

**[OBSERVED] F-3 — the row-level projection inherits the loss and adds one more.**
`src/iqa_soa/experiment/runner.py:661` takes `final_attempt = agent_run.provider_attempts[-1]`, and
`:709, :712-717` project `effective_provider_seed`, `provider_response_id`, `effective_model`,
`finish_reason` and `system_fingerprint` from it. On a failure row the first is `None` because the key is
**absent** from the failure provenance dict, and the other four are `None` because they are
**hard-coded**. Two different causes, one indistinguishable persisted value.

**[OBSERVED] F-4 — provider failures are invisible to `failure_events`.**
`src/iqa_soa/experiment/failure_events.py` derives its ordered list from `GatewayOutcome`s only. A
`ProviderError` breaks the agent loop at `src/iqa_soa/agent/agent.py:144-155` before any outcome exists,
so `failure_events` is empty and `failure_event_count` is `0` for every class A-F. The Phase-O
per-action telemetry therefore does **not** cover the provider boundary, and cannot be extended to cover
it without changing what a failure event means. `provider_attempts` is the only surface that carries
provider-boundary failure information.

**[INFERENCE]** Consequence: the whole of C3 is confined to `provider_attempts[]` entries. That is both
the correct location and the smallest one.

---

## 3. Exact §9.3 minimum telemetry

### 3.1 The frozen set, quoted

**[OBSERVED]** Redesign decision §9.3 states the recommended minimum set *"and nothing beyond it"* as
four items:

1. *"A stable parser/failure branch code.* An enumerated constant identifying which branch raised — for
   example a distinct code for the `providers.py:815-819` branch — so attribution does not require
   matching an English error string against source."
2. *"Envelope and token fields, each with an explicit presence flag.* `response_id`,
   `system_fingerprint`, `finish_reason`, `effective_model`, `input_tokens`, `output_tokens`, each
   paired with a flag distinguishing "the provider did not supply this" from "we did not capture it".
   The presence flags are the point: they are what removes the ambiguity in §9.2."
3. *"Protocol and effective seed where available.* Which protocol path was in force (`native_tools` or
   the JSON path) and the effective seed actually sent, so a failure is attributable to a configuration
   without inference."
4. *"Typed native-tool-call state.* An enumerated value distinguishing the states the guard collapses —
   key absent, `null`, empty list, present-but-unusable, present-and-parsed — replacing a bare
   `tool_call_count` integer that cannot express them."

### 3.2 The eleven persisted fields, in §9.3 order

**[INFERENCE]** The four items resolve to exactly eleven persisted keys on a `provider_attempts[]` entry.
This list is **frozen by this record**. Nothing is added to it because it would be convenient.

| # | §9.3 item | Persisted key | Type |
|---:|---|---|---|
| 1 | (1) | `failure_branch` | closed enum string |
| 2 | (2) | `response_id` | string or null *(existing key; value contract changes)* |
| 3 | (2) | `system_fingerprint` | string or null *(existing key; value contract changes)* |
| 4 | (2) | `finish_reason` | string or null *(existing key; value contract changes)* |
| 5 | (2) | `effective_model` | string or null *(existing key; value contract changes)* |
| 6 | (2) | `input_tokens` | non-negative integer or null *(existing key; value contract changes)* |
| 7 | (2) | `output_tokens` | non-negative integer or null *(existing key; value contract changes)* |
| 8 | (2) | `envelope_field_presence` | closed 6-key object, each value a closed enum string |
| 9 | (3) | `protocol` | string *(new on the failure record; already on the success record)* |
| 10 | (3) | `effective_seed` | integer or null *(new on the failure record; already on the success record)* |
| 11 | (4) | `native_tool_call_state` | closed enum string |

**[INFERENCE]** Six of the eleven keys **already exist** in `ProviderError.provenance()` and are today
written as literal `None`. C3 does not add those keys; it makes their values true. Two more
(`protocol`, `effective_seed`) already exist on `ProviderResponse.provenance()` and are simply absent
from the failure record. **Only three keys are genuinely new anywhere:** `failure_branch`,
`envelope_field_presence`, `native_tool_call_state`.

### 3.3 Per-field classification against every failure class

**[INFERENCE]** `MANDATORY` abbreviates `MANDATORY_IF_AVAILABLE`: the field must be captured whenever the
class makes it reachable. `UNAVAILABLE` abbreviates
`STRUCTURALLY_UNAVAILABLE_ON_THIS_FAILURE_CLASS`: the class cannot reach it, and the correct record is
the value `null` with presence `UNOBSERVED`.

| Field | A0 | A | B | C1 | C2 | D | E | F | G |
|---|---|---|---|---|---|---|---|---|---|
| `failure_branch` | MANDATORY | MANDATORY | MANDATORY | MANDATORY | MANDATORY | MANDATORY | MANDATORY | MANDATORY | n/a (success record) |
| `response_id` | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | **MANDATORY** | MANDATORY | MANDATORY | MANDATORY | already captured |
| `system_fingerprint` | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | **MANDATORY** | MANDATORY | MANDATORY | MANDATORY | already captured |
| `finish_reason` | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | MANDATORY *when `choice` is a mapping* | MANDATORY | MANDATORY | MANDATORY | already captured |
| `effective_model` | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | **MANDATORY** | MANDATORY | MANDATORY | MANDATORY | already captured |
| `input_tokens` | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | MANDATORY at `:636`; UNAVAILABLE at `:617` and `:630` | MANDATORY | MANDATORY | already captured |
| `output_tokens` | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | MANDATORY at `:636`; UNAVAILABLE at `:617` and `:630` | MANDATORY | MANDATORY | already captured |
| `envelope_field_presence` | MANDATORY | MANDATORY | MANDATORY | MANDATORY | MANDATORY | MANDATORY | MANDATORY | MANDATORY | n/a (success record) |
| `protocol` | MANDATORY | MANDATORY | MANDATORY | MANDATORY | MANDATORY | MANDATORY | MANDATORY | MANDATORY | already captured |
| `effective_seed` | UNAVAILABLE (raised at `:469`, before `:472`) | MANDATORY | MANDATORY | MANDATORY | MANDATORY | MANDATORY | MANDATORY | MANDATORY | already captured |
| `native_tool_call_state` | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | **MANDATORY** | MANDATORY | already implied by `tool_call_count` |

**[INFERENCE]** Two entries in that table deserve naming, because they are where the current adapter is
demonstrably losing reachable information rather than merely lacking it:

- **C2** — `response_id`, `effective_model` and `system_fingerprint` are reachable from `envelope`
  whenever the payload decoded to a mapping, which is precisely the `KeyError`/`TypeError` half of the
  `:608` except clause. Today the whole clause is treated as *nothing was observed*.
- **E and F** — every one of the six is a bound local. This is the class the `:835` branch belongs to.

**[INFERENCE]** `effective_seed` carries `null` legitimately whenever `supports_seed` is false or the
configured seed is `None` — the same semantics the success record already has at `:214`. On class A0 it
is `null` for a different reason. The two are separated by `failure_branch` alone; no extra flag is
introduced, and §9.3 item 1 exists to carry exactly that disambiguation.

### 3.4 Explicitly outside the minimum set

**[INFERENCE]** Classified `NOT_IN_MINIMUM_SET`. None is adopted.

| Candidate | Classification | Reason |
|---|---|---|
| Assistant message content, full or partial | `NOT_IN_MINIMUM_SET` | §9.4 excludes *"full or partial assistant message text; prompt echoes; chain-of-thought"* |
| Tool-call arguments or resource values from refused content | `NOT_IN_MINIMUM_SET` | §9.4 excludes them by name |
| Any hash of assistant content or of the response | `NOT_IN_MINIMUM_SET` | §9.4: hashes *"add cross-cell identity matching that the branch code and typed state already largely provide, and a hash of short content drawn from a known schema is weakly reversible"* |
| Content byte length, top-level key set, unrecognized-key count | `NOT_IN_MINIMUM_SET` | §9.4 withdrew these in revision 2: *"a descriptor that supports no sound inference is not minimum telemetry"* |
| HTTP status code (class B) | `NOT_IN_MINIMUM_SET` | Not in §9.3. It is a real resolution loss — 400, 500 and 502 all map to `provider_error` at `:569-572` — and is **recorded here as a known limitation**, not repaired. Adding it would expand a frozen set for convenience |
| `failure_origin` | `NOT_IN_MINIMUM_SET` | Not in §9.3, and `tests/unit/test_benchmark_providers.py:149` pins its absence from `provenance()`. C3 does not add it and does not disturb that assertion |
| Raw response headers, endpoint URL, credentials, request body | `NOT_IN_MINIMUM_SET` and **forbidden** | §7 below |

**[INFERENCE]** **Answer to the standing question: assistant-content and tool-call diagnostic material is
NOT part of the §9.3 minimum set, and is not adopted as optional diagnostic data either.** §9.4 places
it in the excluded list rather than in an optional tier, and §9.1 records that the lost assistant intent
was not reconstructable from any metadata — so a bounded excerpt would buy an unsound inference at a real
privacy cost. The typed `native_tool_call_state` is the sanctioned substitute: it distinguishes the
states the guard at `:747` collapses **without persisting a single byte the model wrote**.

---

## 4. Proposed `ProviderError` / provenance shape

**[NOT AUTHORIZED]** Nothing in this section is implemented. It is a frozen design, not a change.

### 4.1 Three closed vocabularies

**[INFERENCE]** All three are instrument-authored constants. None contains provider text, model text or
any value copied from a response.

**(a) `ProviderCaptureState(str, Enum)`** — three members, and exactly three:

| Member | Meaning |
|---|---|
| `SUPPLIED` | The provider supplied a usable value at a point control flow reached. The paired value key carries it. |
| `NOT_SUPPLIED` | Control flow reached the point at which this field is read, and the provider omitted it, sent `null`, or sent a value that `_optional_string` / `_nonnegative_int` rejects. The paired value key is `null`. |
| `UNOBSERVED` | Control flow failed **before** the provider could supply this field. The adapter never had it. The paired value key is `null`. |

**[INFERENCE]** There is deliberately **no fourth member meaning "available but dropped"**. A
self-reported *I dropped it* flag would be written by the same code that dropped it, and is therefore not
evidence of anything. The distinction is instead made **unreachable and test-refuted**: T-13 in §6 pins a
static floor table binding every `failure_branch` to the capture stage it occurs at, and asserts that no
persisted record may carry `UNOBSERVED` for a field the branch's stage makes reachable. A dropped field
becomes a test failure, not a persisted ambiguity.

**(b) `ProviderFailureBranch(str, Enum)`** — one member per `raise ProviderError` site, plus one legacy
default. 24 members:

| Member | Site | Capture stage |
|---|---|---|
| `CREDENTIAL_ENV_UNSET` | `:469` | 0 `PRE_REQUEST` |
| `HTTP_STATUS` | `:573` | 1 `TRANSPORT` |
| `TRANSPORT_TIMEOUT` | `:581` | 1 |
| `TRANSPORT_ERROR` | `:588` | 1 |
| `ENVELOPE_UNPARSABLE` | `:609` | 2 `ENVELOPE_DECODE` |
| `USAGE_NOT_OBJECT` | `:617` | 3 `ENVELOPE_PARSED` |
| `USAGE_FIELD_INVALID` | `:912`, surfaced through `:630-632` | 3 |
| `REFUSAL_TYPE_INVALID` | `:636` | 3+ (tokens bound) |
| `NATIVE_TOOL_CALLS_NOT_LIST` | `:749` | 4 `MESSAGE_PARSED` |
| `NATIVE_CALL_NOT_FUNCTION` | `:759` | 4 |
| `NATIVE_FUNCTION_UNEXPECTED` | `:770` | 4 |
| `NATIVE_ARGUMENTS_NOT_TEXT` | `:778` | 4 |
| `NATIVE_ARGUMENTS_INVALID_JSON` | `:787` | 4 |
| `NATIVE_ARGUMENTS_NOT_OBJECT` | `:794` | 4 |
| `NATIVE_CONTENT_TYPE_INVALID` | `:823` | 4 |
| `NATIVE_CONTENT_ACTION_WRONG_CHANNEL` | `:835` — **the branch §9.3 item 1 names** | 4 |
| `JSON_CONTENT_MISSING` | `:842` | 4 |
| `JSON_CONTENT_INVALID_JSON` | `:850` | 4 |
| `JSON_CONTENT_NOT_OBJECT` | `:856` | 4 |
| `ACTION_KEYS_MISSING` | `:873` | 4 |
| `ACTION_KEYS_UNKNOWN` | `:879` | 4 |
| `ACTION_ARGUMENTS_NOT_OBJECT` | `:885` | 4 |
| `ACTION_FIELD_NOT_STRING` | `:892` | 4 |
| `UNSPECIFIED` | legacy and third-party `AgentProvider` implementations | 0 |

**[INFERENCE]** `UNSPECIFIED` exists **only** so that `ProviderError("message")` — constructed with a
bare positional argument by `tests/unit/test_benchmark_providers.py:250` and available to any external
`AgentProvider` — keeps working unchanged. Its silent use inside `providers.py` is prevented by a
source-level closure test (T-12), not by a runtime requirement.

**(c) `NativeToolCallState(str, Enum)`** — the states the falsy guard at `:747` collapses, exactly as
§9.3 item 4 enumerates them, plus the two states outside the native path:

`UNOBSERVED` · `NOT_APPLICABLE` (the `json_object` protocol) · `KEY_ABSENT` · `NULL` · `EMPTY_LIST` ·
`PRESENT_UNUSABLE` · `PRESENT_PARSED`

**[INFERENCE]** This is the field that makes the redesign decision's careful §9.1 wording — *"a falsy /
no-usable-native-tool-call state"* — expressible for the first time. It replaces an inference from
`tool_call_count == 0` with an observation. It carries no function name, no arguments and no content.

### 4.2 The carried capture object

**[INFERENCE]** One frozen, slotted dataclass, constructed only from values in scope at the raise site:

```
@dataclass(frozen=True, slots=True)
class ProviderEnvelopeCapture:
    response_id:        str | None
    system_fingerprint: str | None
    finish_reason:      str | None
    effective_model:    str | None
    input_tokens:       int | None
    output_tokens:      int | None
    presence:           Mapping[str, ProviderCaptureState]   # exactly the six keys above
    protocol:           str | None
    effective_seed:     int | None
```

with two constructors: `ProviderEnvelopeCapture.unobserved(protocol=..., effective_seed=...)`, which sets
all six values to `None` and all six presence entries to `UNOBSERVED`; and
`ProviderEnvelopeCapture.observed(...)`, which sets each presence entry to `SUPPLIED` when the paired
value is not `None` and `NOT_SUPPLIED` otherwise, **for the fields the caller declares it reached**, and
leaves the rest `UNOBSERVED`. Presence is never derived from the value alone at read time — that
derivation is precisely the ambiguity being repaired.

### 4.3 `ProviderError` constructor

**[INFERENCE]** Three new **keyword-only** parameters, each with a default. The existing eight parameters
and the positional `message` are untouched.

| Parameter | Default | Internal representation |
|---|---|---|
| `failure_branch: ProviderFailureBranch` | `ProviderFailureBranch.UNSPECIFIED` | stored verbatim |
| `envelope: ProviderEnvelopeCapture \| None` | `None` | stored verbatim; `None` means *no capture has been attached* |
| `native_tool_call_state: NativeToolCallState` | `NativeToolCallState.UNOBSERVED` | stored verbatim |

**[INFERENCE]** `envelope=None` is the internal marker, and it is rendered as an all-`UNOBSERVED`
capture. The two are kept distinct in memory so the attachment rule in §4.5 can be idempotent, using the
exact `if exc.X is None:` idiom the file already uses at `:666-669`.

### 4.4 `provenance()` output

**[INFERENCE]** Signature unchanged: `provenance(self, *, model: str, latency_ms: float)`. The returned
mapping keeps **every existing key, with the same name and the same type domain**, and adds three. In the
terms of §3.2:

- **unchanged keys and values:** `outcome`, `tool_call_count`, `multi_tool_call`,
  `additional_action_count`, `tool_contract_refreshed`, `failure_class`, `client_request_id`,
  `request_id`, `configured_model`, `latency_ms`, `retryable`;
- **existing keys whose value contract changes** from a hard-coded `None` to the captured value:
  `response_id`, `effective_model`, `finish_reason`, `system_fingerprint`, `input_tokens`,
  `output_tokens`;
- **keys added to the failure record that the success record already emits:** `protocol`,
  `effective_seed`;
- **genuinely new keys:** `failure_branch`, `envelope_field_presence`, `native_tool_call_state`.

`envelope_field_presence` is a closed object with exactly the six keys of §3.2 rows 2-7, each valued by a
`ProviderCaptureState` member. No seventh key is admitted, and none of the six may be absent.

**[INFERENCE]** `failure_origin` remains absent, preserving `tests/unit/test_benchmark_providers.py:149`.

### 4.5 Which call site populates what

**[INFERENCE]** The governing rule: **capture is attached at the innermost point where the value is in
scope**, and attachment never overwrites a capture a raise site already set.

| Site(s) | How the capture is attached |
|---|---|
| `:469` | `unobserved(protocol=self.protocol, effective_seed=None)`; branch `CREDENTIAL_ENV_UNSET` |
| `:573`, `:581`, `:588` | `unobserved(protocol=self.protocol, effective_seed=effective_seed)`; the class-B site keeps its existing `request_id` extraction unchanged |
| `:609` | `envelope` is initialised to `None` **before** the `try` at `:595`, so the handler can test it. When the decoded value is a `Mapping`, attach `observed(...)` reading `id`, `model` and `system_fingerprint` through the same `_optional_string` the success path uses, and `finish_reason` only when `choices[0]` is a mapping; otherwise attach `unobserved(...)`. This is the C1/C2 split |
| `:617`, `:630-632`, `:636` | `observed(...)` with all four envelope fields; the token pair is `UNOBSERVED` at `:617` and `:630`, and `SUPPLIED`/`NOT_SUPPLIED` at `:636`, where both are already bound |
| `:912` | sets `failure_branch=USAGE_FIELD_INVALID` only; the capture is attached by the existing handler at `:630-632` |
| `:749, :759, :770, :778, :787, :794, :823, :835, :842, :850, :856` | Each sets its own `failure_branch` **and** its own `native_tool_call_state`, both derivable from `message` in local scope. The envelope capture is not reachable here and is attached by the caller |
| `:665-670` | Extended in the existing idiom: `if exc.envelope is None: exc.envelope = observed(...)`, using the six locals bound at `:623-628` and `:642-645`. `failure_branch` and `native_tool_call_state` are **not** touched — the raise site owns them |
| `:873, :879, :885, :892` | Each sets its own `failure_branch`. `native_tool_call_state` is not derivable inside `_parse_action_object` |
| `:681-686` | Extended in the same idiom: attaches the envelope capture, and sets `native_tool_call_state` to `PRESENT_PARSED` under `native_tools` or `NOT_APPLICABLE` under `json_object`, alongside the `tool_call_count` back-fill that already happens at `:684` |
| `:340` (`DeterministicStubProvider`) and any third-party `AgentProvider` | untouched. A `ProviderError` raised there keeps `UNSPECIFIED` / `None` / `UNOBSERVED`, which is the true record |

### 4.6 How absent values stay explicitly null

**[INFERENCE]** Every one of the six value keys is `None` in exactly two situations, and
`envelope_field_presence` names which: `NOT_SUPPLIED` (reached, provider omitted it) or `UNOBSERVED`
(never reached). No value is ever defaulted to a placeholder string, a zero, or an empty string.
`input_tokens` and `output_tokens` in particular are **never** defaulted to `0` on a failure path — the
existing `usage.get("prompt_tokens", 0)` default at `:624` applies only to the success path and is not
extended. A failure that never read usage records `null` with `UNOBSERVED`, so the standing guarantee at
`tests/unit/test_benchmark_providers.py:244-273` that a failed attempt invents no tokens is preserved
verbatim.

### 4.7 How the success path stays unchanged

**[INFERENCE]** `ProviderResponse` is not modified. `ProviderResponse.provenance()` is not modified.
`_native_action_tool`, the request payload, the message construction, `tool_choice`,
`parallel_tool_calls`, `response_format`, `_native_history_messages`, `_resolve_canonical_resource`,
`_canonicalize_action_id` and `TOOL_CONTRACT_NOTICE` are not modified. No line between `:456` and `:645`
changes what is *sent*; the only edits before `:645` are the initialisation of `envelope = None` at
`:594` and the addition of keyword arguments to seven `raise` expressions. Every accept/refuse predicate
— `if refusal:`, `if not parsed_calls:`, `if self.protocol == "native_tools" and tool_calls:`,
`if parsed == {"done": True}`, `if isinstance(parsed, Mapping)`, and the
`_ACTION_REQUIRED`/`_ACTION_OPTIONAL` key algebra — is byte-identical.

### 4.8 How legacy callers stay compatible

**[OBSERVED]** Every existing consumer survives without modification:

| Consumer | Why it is unaffected |
|---|---|
| `ProviderError("msg")` (`tests/unit/test_benchmark_providers.py:250`) | all new parameters are keyword-only with defaults |
| `agent.py:154` `exc.provenance(model=..., latency_ms=...)` | signature unchanged; the returned mapping is a superset |
| `agent.py:161` `response.provenance()` | success path untouched |
| `confirmatory.py:435` `_provider_failure_origin` | reads `.failure_origin`, `.failure_class` and `.__cause__` — none of which C3 touches |
| `runner.py:709, :712-717` | read `final_attempt.get(...)`; the four envelope keys already exist and now carry values, and `effective_seed` becomes present. **No runner edit is required for this to work** |
| `analyze_phaseD/F/I/L`, `phaseN_diagnose_phaseL_hold`, `metrics/pilot.py` | all read `provider_attempts` with `.get()` and ignore unknown keys; none validates the attempt entry against a closed key set |
| `tests/unit/test_benchmark_providers.py:149` | `failure_origin` is still absent from `provenance()` |

**[INFERENCE]** Unlike `iqa_soa.experiment.failure_events`, whose persisted event schema is **closed in
both directions** and refuses an unknown key, the `provider_attempts` entry has never had a closed
persisted schema. That is why C3 is additive at the reader level. It is also a gap worth naming: this
design does **not** propose closing the `provider_attempts` schema, because doing so would be a separate,
larger change with its own fail-closed consequences for every historical row.

### 4.9 The distinction the existing persisted schema cannot represent

**[OBSERVED]** **Stated explicitly, as required.** The current persisted schema **cannot** represent
*"field unavailable because failure occurred before the provider supplied it"* versus *"field was
available but the adapter dropped it."* `ProviderError.provenance()` emits a single flat `None` for all
six fields at all 23 raise sites, and neither `PILOT_RAW_FIELDS_V5` nor the `provider_attempts` entry has
any presence dimension. There is no field, flag or convention anywhere in the persisted record from which
the distinction could be recovered.

**[INFERENCE]** **A schema change is therefore required.** `envelope_field_presence` is the minimum
carrier of the distinction, and §5 states the version consequences that follow from adding it.

---

## 5. Schema and instrument version consequences

**[NOT AUTHORIZED]** No constant is moved by this record. Each conclusion below states what a future
implementation would have to do, and why, under the repository's own version semantics.

### 5.1 `RAW_SCHEMA_VERSION` — **BUMP REQUIRED**, 5 → 6

**[OBSERVED]** §9.5 states the adoption condition directly: *"the raw schema version is bumped and the
**model-visible** contract version is not, since the model's inputs do not change."* The requirement is
frozen by the decision record and is not a judgement made here.

**[INFERENCE]** It is also independently required by the repository's own semantics, for a reason worth
recording because it differs from every earlier bump. Schemas 3, 4 and 5 each **added columns**
(`PROTOCOL_TELEMETRY_FIELDS`, `FAULT_PROVENANCE_TELEMETRY_FIELDS`, `FAILURE_EVENT_TELEMETRY_FIELDS`), and
`src/iqa_soa/metrics/definitions.py:112-115` justifies each as *"strictly additive over schema N: no
schema-N field changed name, type or meaning."* **C3 cannot make that claim.** Five existing columns —
`provider_response_id`, `effective_model`, `finish_reason`, `system_fingerprint` and
`effective_provider_seed` — are projected from the final attempt at `runner.py:709, :712-717` and are
`None` on **every** failure row today by construction. After C3 they carry real values. Their *name* and
*type* are unchanged; their *content contract on failure rows* changes, for an instrument reason.
Pooling a schema-5 failure row with a schema-6 failure row would attribute an instrument change to the
provider. That is exactly what the version constant exists to prevent.

**[INFERENCE]** The field **tuple** is not required to grow. All eleven fields live inside
`provider_attempts[]`, which is already a persisted column (`definitions.py:128`). A future
`PILOT_RAW_FIELDS_V6` would therefore be defined as equal to `PILOT_RAW_FIELDS_V5`, with a comment
stating that the version moves because the content contract of five existing columns on failure rows
changed, not because a column was added. `RAW_FIELDS_BY_SCHEMA_VERSION` gains the permanent entry `6`;
`READABLE_RAW_SCHEMA_VERSIONS` and `READABLE_PILOT_RAW_SCHEMA_VERSIONS` append `6`; nothing is removed;
no historical row is rewritten; schemas 1-5 stay readable exactly as `instrument.py:99-103` requires.

**[INFERENCE]** No new row-level column is proposed. A `provider_failure_telemetry_present` flag would
duplicate what the manifest's `raw_schema_version` already states, and §9.3 does not contain it.

### 5.2 `INSTRUMENT_VERSION` — **BUMP REQUIRED**, "4" → "5"

**[OBSERVED]** The repository's rule for this constant is stated at `src/iqa_soa/instrument.py:20-31`,
about Phase M, which is the exact precedent for C3: *"That is an additive observation change: it alters
no prompt, no policy, no guard, no tool dispatch and no metric, so a Phase-M row and a Phase-B..L row
measure the same quantities in the same way. The version is nevertheless bumped, because the harness that
produced them is not the same harness and this module exists precisely so that such a difference is
machine-checkable rather than argued from memory."*

**[INFERENCE]** C3 is the same shape as Phase M: observation-only, prompt-neutral, dispatch-neutral,
metric-neutral, and produced by a harness that is not the same harness. Under the repository's own stated
rule it bumps. A future constant would be named permanently — for example
`PROVIDER_FAILURE_TELEMETRY_INSTRUMENT_VERSION = "5"` — with `INSTRUMENT_VERSION` re-aliased to it, and
`TOOL_CONTRACT_INSTRUMENT_VERSION = "4"` preserved verbatim as the permanent name of the instrument every
frozen Phase-P artifact was written under.

### 5.3 `NATIVE_TOOL_ADAPTER_VERSION` — **NO BUMP**

**[OBSERVED]** The constant's stated purpose (`instrument.py:79-92`) is to identify *"the native-tools
request/response adapter specifically, so a later adapter change is distinguishable from an unrelated
instrument change."* It has moved exactly once, at Phase O, and the recorded reason is specific: *"The
adapter's request payload changed: `_native_action_tool` now advertises a per-tool argument contract."*
Phase M *"deliberately held this constant because Phase M did not touch the adapter."*

**[INFERENCE]** C3 changes neither half of the adapter's behaviour. The request payload is
byte-identical: `_native_action_tool`, `tool_choice`, `parallel_tool_calls`, the function description and
the argument schema are untouched. The response-side accept/refuse function is byte-identical: every
predicate in `_parse_message_action` and `_parse_action_object` is unchanged, every `failure_class` is
unchanged, and every response accepted today is still accepted while every response refused today is
still refused with the same class — which is precisely what the §9.5 mutation proof exists to
demonstrate. C3 changes only what the adapter **records while raising**.

**[INFERENCE]** Bumping it would therefore assert something false: that a Phase-P row and a post-C3 row
were produced by different native-tools adapters. That would degrade the constant's ability to carry the
one meaning it currently carries, and would collapse the independence between the two boundaries that
Phase M deliberately established. **Phase M is the controlling precedent, and the answer is no bump.**

### 5.4 Model-visible contract versions — **NO BUMP**

**[INFERENCE]** `TOOL_ARGUMENT_CONTRACT_VERSION` and `contract_digest(SANDBOX_TOOL_NAMES)` do not move.
§9.5 states the condition directly, and it holds by construction: the model's inputs do not change, so
`controlled_input_digest`, `system_prompt_sha256` and `user_prompt_sha256` are unaffected.

### 5.5 The declared instrument boundary — **PRESERVED AND EXTENDED**

**[OBSERVED]** The frozen `rc4_instrument_boundary` limit in
`benchmark/pilot-v7-rc4/qualification-contract.json` binds rows written under *"instrument 4 / raw schema
5 / native-tools-adapter-3"* and forbids merging them with instrument-3 rows.

**[INFERENCE]** C3 creates a **second** boundary of the same kind, and §9.5 requires it to be declared
explicitly *"so no future analyst pools rows across it by default."* The declaration must state, in the
same form the existing one uses, that rows written under **instrument 5 / raw schema 6 /
native-tools-adapter-3** and rows written under **instrument 4 / raw schema 5 / native-tools-adapter-3**
are separated by an observation-only change on the provider failure path, that the default is separation,
and that any analyst who wishes to pool across it must say so explicitly and justify it. The shared
adapter version in both triples is informative, not accidental: it is the machine-checkable record that
the adapter itself did not move.

### 5.6 The Phase-P protocol pins are **untouched, and that is the mechanism**

**[OBSERVED]** `scripts/phaseP_protocol.py:346-349` pins `EXPECTED_INSTRUMENT_VERSION = "4"`,
`EXPECTED_RAW_SCHEMA_VERSION = 5` and `EXPECTED_NATIVE_TOOL_ADAPTER_VERSION = "native-tools-adapter-3"`
as literals.

**[INFERENCE]** After a C3 bump, the Phase-P protocol module would **refuse to run** under the new
instrument, because its pins would no longer match the code's constants. **That is the correct and
desired behaviour, and it must not be repaired.** It is the enforcement mechanism for the requirement
that any future successor candidate be bound **only** to the new post-C3 instrument and never
retroactively reinterpret Phase-P rows: a successor requires its own protocol module with its own pins,
and Phase P's frozen pins stay exactly where they are. Editing `scripts/phaseP_protocol.py` is therefore
classified `FORBIDDEN` in §9.

### 5.7 Governance consequence

**[OBSERVED]** `scripts/instrument_revision.py:471-478` requires the approved instrument-revision chain
HEAD to declare a `raw_schema_version` equal to the code's `RAW_SCHEMA_VERSION`, and `_check_chain_link`
(`:226-277`) requires each link to name its parent commit, enumerate its changed files, and give each a
scientific reason of at least 20 characters.

**[INFERENCE]** A C3 implementation therefore requires a **new link on the approved instrument-revision
chain**, additive to the current head (`docs/post_phaseP_confirmatory_instrument_revision.json`), with
its own `observation_only: true`, its own enumerated `changed_files`, and the standing assertions that no
Phase-P evidence was touched, no historical row was rescored, no Phase-P result was reinterpreted, and no
predecessor record was edited. This is listed as `REQUIRED` in §9.

---

## 6. §9.5 acceptance and mutation-proof plan

**[NOT AUTHORIZED]** No test is written and none is executed. **No real provider call is authorized by
this plan.** Every case below is driven by a synthetic in-memory response object substituted for
`request.urlopen`, exactly as `tests/unit/test_benchmark_providers.py:115-131` already does.

### 6.1 The four §9.5 conditions as acceptance criteria

**[OBSERVED]** §9.5 states that C3 *"holds that classification only if"* four conditions are met.
Reproduced faithfully in meaning and turned into criteria:

| ID | §9.5 condition | Acceptance criterion |
|---|---|---|
| **AC-1** | *a **mutation proof** demonstrates the accept/refuse decision function is unchanged — every input accepted is still accepted, every input refused still refused, with the same `failure_class`. If any decision changes, it is not a measurement improvement and must be reclassified* | T-01, T-14, T-15, T-16, T-17 |
| **AC-2** | *the raw schema version is bumped and the **model-visible** contract version is not, since the model's inputs do not change* | T-18, T-19 |
| **AC-3** | *a synthetic fault-injection dry-run (§8.5) proves the fields populate on the native-tools path with no provider contact* | T-20 |
| **AC-4** | *the instrument boundary is declared explicitly, per the frozen `rc4_instrument_boundary` discipline, so no future analyst pools rows across it by default* | T-21, T-22 |

### 6.2 The mutation-proof strategy

**[INFERENCE]** The strategy must demonstrate that each field is **read from the provider envelope**, not
fabricated, defaulted or reconstructed. Three independent mechanisms, because no one of them is
sufficient alone:

**M-1 — distinct-sentinel differential.** For each of the six envelope/token fields, build **two**
synthetic envelopes that are byte-identical except for that one field's value (`"id": "ENVELOPE-A-..."`
versus `"ENVELOPE-B-..."`; `"prompt_tokens": 11` versus `13`; and so on), drive **the same failure
branch** with each, and assert that the persisted value tracks the input. A constant, a default, a
fabrication, or a value copied from configuration cannot vary with an input it never read, so M-1 fails
any implementation that is not genuinely reading the envelope. The sentinel values are authored for the
test and are drawn from no model output of any kind.

**M-2 — three-way presence discrimination.** For each field, drive three scenarios and assert that all
three persisted shapes differ: key present with a value gives `SUPPLIED` plus the value; key **removed
from the envelope entirely** gives `NOT_SUPPLIED` plus `null`; failure **before** the envelope exists
gives `UNOBSERVED` plus `null`. This is the direct test of the §9.2 ambiguity: an implementation that
emits `None` without a presence flag cannot pass, and neither can one that reports `NOT_SUPPLIED` for a
transport failure.

**M-3 — static branch and stage closure.** Two source-level tests with no provider involvement at all: an
AST scan of `providers.py` asserting that every `raise ProviderError` names an explicit
`ProviderFailureBranch` member and that the set of members used is **exactly** the enum minus
`UNSPECIFIED` (T-12, whose precedent is the `_self_check` assertion at
`src/iqa_soa/failure_taxonomy.py:93`); and a floor-table test asserting that no branch at capture stage 3
or 4 may ever persist `UNOBSERVED` for a field its stage makes reachable (T-13). Together these make
*the adapter dropped it* a build failure rather than a persisted ambiguity, which is the guarantee §4.1
promises.

### 6.3 The acceptance suite

**[INFERENCE]** Twenty-two named cases. The eleven the task enumerates are marked with a star.

| ID | Case | Assertion |
|---|---|---|
| **T-01** ★ | **Response id survives a later native-tool validation failure.** A native-tools envelope carrying `id`, `model`, `system_fingerprint`, `finish_reason` and `usage`, with assistant `content` that parses to a JSON mapping other than `{"done": true}` — the `:835` branch | `failure_class == "invalid_tool_call"` and `failure_origin is MODEL_OUTPUT` (**unchanged**); `provenance()["response_id"]` equals the envelope's `id`; presence `SUPPLIED`; `failure_branch == NATIVE_CONTENT_ACTION_WRONG_CHANNEL`. Repeated under M-1 with two distinct ids |
| **T-02** ★ | Effective model survives the same branch | `effective_model` equals the envelope's `model`; presence `SUPPLIED`; M-1 differential |
| **T-03** ★ | Finish reason survives the same branch | `finish_reason` equals `choices[0].finish_reason`; presence `SUPPLIED`; M-1 differential |
| **T-04** ★ | System fingerprint survives the same branch | `system_fingerprint` equals the envelope's `system_fingerprint`; presence `SUPPLIED`; M-1 differential |
| **T-05** ★ | Input and output tokens survive **when supplied** | `input_tokens` and `output_tokens` equal `usage.prompt_tokens` and `usage.completion_tokens`; presence `SUPPLIED`; M-1 differential with two distinct integer pairs |
| **T-06** ★ | **Absent optional provider fields remain null.** Same branch, envelope with `id`, `model`, `system_fingerprint`, `finish_reason` and `usage` **removed** | all six values `null`; all six presence entries `NOT_SUPPLIED`; the run still refuses with the same `failure_class` |
| **T-07** ★ | **Transport failure has no response-envelope metadata.** `urlopen` raises `URLError`, and separately `TimeoutError` | all six values `null`; all six presence entries `UNOBSERVED`; `native_tool_call_state == UNOBSERVED`; `protocol` populated; `effective_seed` populated; `failure_branch` is `TRANSPORT_ERROR` or `TRANSPORT_TIMEOUT`; `failure_class` and `retryable` unchanged from today |
| **T-08** ★ | **Malformed JSON cannot fabricate envelope values.** (a) the body is `b"{not-a-provider-envelope"`; (b) the body is a valid JSON object whose `choices` key is missing | (a) all six `UNOBSERVED`; (b) `response_id`, `effective_model` and `system_fingerprint` `SUPPLIED` from the top-level mapping, with tokens and `finish_reason` `UNOBSERVED`. Both raise `invalid_json` with the same message and origin as today. **No sentinel from (a) may ever appear in a persisted field.** This is the C1/C2 split |
| **T-09** ★ | **Success behaviour is semantically equivalent.** A fixed synthetic native-tools success envelope; capture `ProviderResponse.provenance()` and `descriptor()` | the dict equals a committed pre-C3 snapshot, and `json.dumps(..., sort_keys=True, separators=(",", ":"))` is **byte-identical**. Extends the existing serialization check at `tests/unit/test_benchmark_providers.py:369` |
| **T-10** ★ | **Tool-contract rejection is unchanged.** The full existing parametrization at `tests/unit/test_benchmark_providers.py:60-153`, re-run | every `failure_class` and every `failure_origin` identical; `"failure_origin" not in provenance(...)` still holds |
| **T-11** ★ | **Retry behaviour is unchanged.** (a) the `retryable` mapping over `{408, 429, 500, 502, 503, 504}` and the `rate_limit`/`timeout`/`provider_error` selection at `:569-579`; (b) a call-counting fake provider driven through `ExperimentalAgent.run` | (a) identical to today; (b) `generate_action` is called exactly once and the loop still breaks at `agent.py:155`, so `provider_attempt_count == 1` and no retry is introduced |
| **T-12** | **Branch closure (M-3).** AST scan of `providers.py` | every `raise ProviderError` names an explicit branch; the used set equals the enum minus `UNSPECIFIED`; a deliberately unlabelled raise added in a fixture is detected |
| **T-13** | **Capture floor (M-3).** Static table mapping branch to stage | no stage-3 branch may persist `UNOBSERVED` for the four envelope fields; no stage-4 branch, and not `REFUSAL_TYPE_INVALID`, may persist `UNOBSERVED` for any of the six. Driven synthetically for every one of the 23 branches |
| **T-14** | **AC-1 accept-set invariance.** A corpus of synthetic envelopes accepted today — single native tool call, multi tool call, `content: null`, `{"done": true}`, non-JSON assistant text, a `json_object` action object, and a refusal | every one still yields the same `outcome`, the same `action`, the same `additional_actions`, the same `emitted_proposals()` and the same `tool_call_ids` |
| **T-15** | **AC-1 refuse-set invariance.** One synthetic envelope per refusing branch, covering all 23 | every one still raises, with the same `failure_class`, the same `failure_origin` and the same message text |
| **T-16** | **AC-1 no rescue.** The T-01 envelope specifically | no `Action` is produced, `provider_attempts` records a failure, and no gateway outcome exists. A malformed action is still not accepted |
| **T-17** | **AC-1 model-visible input invariance.** Capture the request `payload` and `messages` for a fixed input, pre- and post-C3 | byte-identical, including `tools`, `tool_choice`, `parallel_tool_calls`, `response_format`, the system prompt and `TOOL_CONTRACT_NOTICE`; `controlled_input_digest` unchanged |
| **T-18** | **AC-2 version movement** | `RAW_SCHEMA_VERSION == 6`; `INSTRUMENT_VERSION == "5"`; `NATIVE_TOOL_ADAPTER_VERSION == "native-tools-adapter-3"` (**unmoved**); `TOOL_ARGUMENT_CONTRACT_VERSION` unmoved; every historical named constant still holds its original value; the `READABLE_*` tuples still contain 1-5 |
| **T-19** | **AC-2 historical readability** | `RAW_FIELDS_BY_SCHEMA_VERSION[5]` is unchanged; a synthetic schema-5 row still validates under its own contract; no historical row is rewritten |
| **T-20** | **AC-3 dry-run (§8.5).** The complete `run_one` path driven with a fake `urlopen` returning the T-01 envelope, asserting that no socket is opened | the persisted raw row's `provider_attempts[-1]` carries all eleven fields with the expected values, and the row-level `provider_response_id`, `effective_model`, `finish_reason`, `system_fingerprint` and `effective_provider_seed` are non-null on a **failure** row for the first time |
| **T-21** | **AC-4 boundary declaration** | the new boundary string exists, names instrument 5 / raw schema 6 / native-tools-adapter-3, states that the default is separation, and does not weaken or replace `rc4_instrument_boundary` |
| **T-22** | **AC-4 chain link.** `scripts/instrument_revision.py` checks | the new link declares `raw_schema_version == 6`, names its parent commit, enumerates its changed files with reasons, asserts `observation_only`, and leaves both predecessor links byte-identical |

### 6.4 What the suite deliberately does not do

**[INFERENCE]** It contacts no provider. It runs no model. It reads no Phase-P row, and no fixture in it
is derived from one — rule **A1** applies in full, and every sentinel is authored for the test. It
asserts no exposure rate, no per-task expectation, and nothing about what a model will do.

---

## 7. Security and privacy constraints

### 7.1 Confirmation against the required list

**[INFERENCE]** The proposed telemetry persists **none** of the following, and the design contains no
mechanism by which any of them could reach a persisted field:

| Item | Status | Basis |
|---|---|---|
| API keys | **not persisted** | the credential is read at `:466` into a local, used only in the `Authorization` header at `:558`, and never enters an exception, a capture object or a provenance mapping. `tests/unit/test_benchmark_providers.py:531` already pins that the key does not appear in the error string, and C3 adds no path that could change that |
| Authorization headers | **not persisted** | no header other than the `x-request-id` **value** is ever read back; `_response_header` and `_header_mapping_value` are called for that one name only, at `:568` and `:577` |
| Environment secrets | **not persisted** | the only environment reads are `api_key_env`, `base_url_env` and `model_env`; none is persisted, and the *names* already appear in `descriptor()` at `:437-443`, unchanged |
| Arbitrary raw HTTP headers | **not persisted** | no header mapping is captured, iterated or serialized |
| Full prompts | **not persisted** | the capture object has no prompt field; prompts continue to reach the row only as SHA-256 digests at `runner.py:699-700` |
| Unbounded raw provider payloads | **not persisted** | `raw_bytes` is never stored, never hashed, never length-measured and never partially copied. The class-B path continues to **not read the error body at all** (`:569-579`), which `tests/unit/test_benchmark_providers.py:532` pins |
| Endpoint URL | **not persisted** on the failure record | unchanged; `descriptor()` continues to emit only `_public_endpoint(...)` |

### 7.2 The stronger structural statement

**[INFERENCE]** Every one of the eleven fields is exactly one of three things:

1. **an instrument-authored closed enum** — `failure_branch`, the `envelope_field_presence` values,
   `native_tool_call_state`, `protocol`. These contain no provider text and no model text at all;
2. **a provider-generated identifier or short enum already persisted on the success path** —
   `response_id`, `system_fingerprint`, `finish_reason`, `effective_model`. Each is emitted today by
   `ProviderResponse.provenance()` at `:250-254` and projected to the row at `runner.py:712-715`;
3. **an integer** — `input_tokens`, `output_tokens`, `effective_seed`. Each is already persisted on the
   success path and in the existing usage and descriptor telemetry.

**[INFERENCE]** **C3 therefore persists no class of information that is not already persisted on the
success path.** It makes the failure record carry what the success record has always carried, plus three
enums the instrument writes about itself. That is the whole of its privacy footprint, and it is why the
docstring contract at `:140` — *"failure metadata without response bodies, URLs, or credentials"* — is
preserved rather than merely respected.

### 7.3 Assistant content and tool-call content

**[INFERENCE]** **None is proposed**, so no bounded-schema justification is required. §9.4 excludes
assistant text, prompt echoes, chain-of-thought, tool arguments, resource values from refused content,
response hashes, content byte length and key descriptors, and this design adopts that exclusion in full.
`native_tool_call_state` is an enumerated observation **about the shape of** `message["tool_calls"]` and
copies nothing out of it — not the function name, not the arguments string, not the call id.

**[OBSERVED]** One pre-existing content-adjacent surface is **unchanged by C3 and named here for
completeness**: `agent.py:150` composes `error = f"{type(exc).__name__}: {exc}"`, and the exception
message for the `_parse_action_object` branches contains model-supplied **key names** (`:874`, `:880`).
That is existing Phase-O behaviour, already bounded to key names drawn from the model's own proposal, and
C3 neither widens it nor adds to it.

### 7.4 Default preference honoured

**[INFERENCE]** The design is minimum structured metadata, not raw response dumping. The response body is
read exactly once at `:567`, parsed, and discarded, exactly as today.

---

## 8. Scientific interpretation boundary

### 8.1 What C3 does

**[INFERENCE]** C3 improves the **attribution and observability of future provider and model-protocol
failures**, and nothing else. Specifically, and only prospectively:

- it makes a persisted `None` unambiguous, by pairing every envelope and token field with a presence
  state that distinguishes *the provider omitted it* from *it was never reachable*;
- it makes the raising branch identifiable from an enumerated constant rather than by matching an English
  error string against source;
- it makes the native tool-call state that the guard at `:747` collapses into a typed observation;
- it makes protocol and effective seed attributable on a failure row without inference;
- it removes the `runner.py:709` gap in which `effective_provider_seed` was null on failure rows because
  the key was absent rather than because the seed was.

### 8.2 What C3 does not do

**[INFERENCE]** Explicitly, and each independently checkable:

| Claim | Why it holds |
|---|---|
| **Does not change canonical exposure** | No contract, vocabulary, predicate or analyzer file is touched. The canonical tool, resource, argument-predicate, ordering and equivalence settings of all 17 tasks are untouched (rule A9; §10.7 item 1) |
| **Does not change benchmark reachability** | No case bytes, no resource enum, no budget, no prompt. The model's inputs are byte-identical (T-17) |
| **Does not change task semantics** | No benchmark file is in the change set at all |
| **Does not change QA treatment** | `treatments.py` is untouched; `Treatment.detailed_evidence` still returns `False` for `QAMode.OFF`; the evidence guard stays disabled |
| **Does not change model outputs** | The request payload is byte-identical, so the model is asked exactly the same question |
| **Does not change whether a malformed action is accepted** | Every accept/refuse predicate is byte-identical, and AC-1 (T-14, T-15, T-16) is the proof obligation |
| **Does not rehabilitate BEN-003** | The preserved invalidated cell remains `MODEL_PROTOCOL_INVALID`, BEN-003 remains `MATRIX_INVALID`, and the attribution remains `MODEL_PROTOCOL_FAILURE`. C3 is prospective; it cannot and does not act on a frozen row |
| **Does not change the Phase-P HOLD** | The verdict remains permanently `SCHEDULE_COMPLETE_VERDICT_HOLD`; `pilot-v7-rc4` remains UNQUALIFIED |

### 8.3 The nothing-recovered statement

**[OBSERVED]** Redesign decision §9.1 records: *"Nothing recommended below would have changed the Phase-P
classification, exposure count or verdict."*

**[INFERENCE]** This design adds nothing that alters that. The BEN-003 envelope and token values were
never persisted and are **unknowable**; no telemetry design can recover them, and this one does not
attempt to. C3 buys attribution for failures that have **not yet happened**.

### 8.4 Classification held

**[INFERENCE]** C3 remains a `MEASUREMENT_IMPROVEMENT` under §6.1's mechanical discriminator — *"a
measurement change is invisible to the model"* — and holds that classification only conditionally on
AC-1. §6.2 states the consequence plainly: *"If any decision changes, it is not this class and must be
reclassified."* This design preserves that condition rather than assuming it away.

---

## 9. Exact future implementation file plan

**[NOT AUTHORIZED]** This is a plan for a future pull request. **None of it is implemented, and this
document does not authorize any of it.**

### 9.1 REQUIRED

| Path | Change | Why |
|---|---|---|
| `src/iqa_soa/agent/providers.py` | add `ProviderCaptureState`, `ProviderFailureBranch`, `NativeToolCallState` and `ProviderEnvelopeCapture`; three keyword-only `ProviderError` fields; extend `provenance()` per §4.4; initialise `envelope = None` before `:595`; label all 23 raise sites; extend the two existing back-fill handlers at `:665-670` and `:681-686` | the whole of C3 |
| `src/iqa_soa/agent/__init__.py` | export the new public names | precedent: `ProviderFailureOrigin` is an approved export path (`tests/integration/test_post_phaseP_instrument_revision.py:76`) |
| `src/iqa_soa/instrument.py` | add permanent `PROVIDER_FAILURE_TELEMETRY_INSTRUMENT_VERSION = "5"` and `PROVIDER_FAILURE_TELEMETRY_RAW_SCHEMA_VERSION = 6`; re-alias `INSTRUMENT_VERSION` and `RAW_SCHEMA_VERSION`; append `6` to both `READABLE_*` tuples; extend `__all__`; document the boundary in the module docstring | §5.1, §5.2 |
| `src/iqa_soa/metrics/definitions.py` | add `PILOT_RAW_FIELDS_V6` (equal to V5, with the comment stating that the version moves for a content-contract change, not an added column) and the permanent `RAW_FIELDS_BY_SCHEMA_VERSION[6]`; extend `__all__` | §5.1 |
| `src/iqa_soa/experiment/runner.py` | **one line only** — `:311`, `PILOT_RAW_FIELDS_V5` becomes `PILOT_RAW_FIELDS_V6` | the writer must select the tuple named for the schema it declares. Everything else in this file is `FORBIDDEN`: `:709` and `:712-717` already read the keys and need no edit (§4.8) |
| `tests/unit/test_benchmark_providers.py` | add T-01 through T-17 | AC-1, and mechanisms M-1, M-2, M-3 |
| `tests/integration/` — one new module | add T-18 through T-22 | AC-2, AC-3, AC-4 |
| `docs/` — one new instrument-revision chain link (JSON) | an additive link on the approved chain, `observation_only: true` | `scripts/instrument_revision.py:471-478`; §5.7 |
| a boundary declaration for the successor instrument | states instrument 5 / raw schema 6 / native-tools-adapter-3, and that the default is separation | §9.5 condition 4; §5.5. **Its location is a successor-candidate decision and is not chosen here** |

### 9.2 OPTIONAL

| Path | Change | Note |
|---|---|---|
| `scripts/post_phaseP_write_instrument_revision.py`, or a successor writer | extend the approved src-change set to the new paths | required **only** if the new chain link is produced by that writer rather than by a new one; the choice is a governance decision, not a design one |
| `docs/` — a short implementation report | record the AC-1 through AC-4 results | mirrors existing phase practice |

### 9.3 FORBIDDEN

**[INFERENCE]** Editing any of these as part of C3 would take the change out of
`MEASUREMENT_IMPROVEMENT`:

- `scripts/phaseP_protocol.py` — its literal pins at `:346-349` **must** stop matching. That is the
  mechanism binding a successor to the new instrument only (§5.6);
- `scripts/analyze_phaseP_rc4_qualification.py`, `scripts/analyze_phaseL_requalification.py`,
  `scripts/analyze_phaseI_requalification.py`, `scripts/analyze_phaseF_qualification.py`,
  `scripts/analyze_phaseD_qualification.py`, `scripts/phaseN_diagnose_phaseL_hold.py` — every one already
  reads `provider_attempts` tolerantly and needs no change; editing one would be reinterpreting frozen
  evidence;
- `scripts/rc4_scoring_vocabulary.py` and `scripts/validate_pilot_v7_rc4.py` — C1, C2 and C4a territory,
  not C3;
- `benchmark/**` — any file, any byte;
- `configs/**`, including `configs/phaseP-qualification.yaml`;
- `schemas/qa-policy.xsd`;
- `src/iqa_soa/experiment/failure_events.py` and `src/iqa_soa/experiment/fault_provenance.py` — the
  provider boundary is not a gateway outcome (§2.3 F-4), and widening a failure **event** to cover it
  would change what a failure event means;
- `src/iqa_soa/experiment/treatments.py`;
- `src/iqa_soa/tools/argument_schema.py`, `SANDBOX_TOOL_NAMES`, `_native_action_tool`,
  `_argument_contract_statement`, `TOOL_CONTRACT_NOTICE`, `TOOL_CONTRACT_POLICIES` — all model-visible;
- `ProviderResponse` and `ProviderResponse.provenance()`;
- any accept/refuse predicate, any `failure_class` assignment, any `retryable` computation, any
  `failure_origin` assignment;
- `docs/post_phaseP_prospective_redesign_decision.md`,
  `docs/post_phaseP_legitimate_sink_applicability_audit.md`,
  `docs/post_phaseP_BUD018_information_architecture_review.md`, and every predecessor
  instrument-revision record;
- anything beneath `results/`.

### 9.4 Explicitly not in the plan

**[NOT AUTHORIZED]** Creating a successor candidate; assigning a candidate version number; naming a
phase; deriving seeds; creating registration or randomization artifacts; executing anything; contacting
any provider.

---

## 10. Closure decision

### 10.1 Closure criteria, each answered

| Requirement | Status |
|---|---|
| **Exact minimum telemetry identified** | Yes — eleven fields, §3.2, taken from §9.3's four items and expanded by nothing. Every field is classified against every failure class in §3.3, and every excluded candidate is named in §3.4 |
| **Every failure boundary mapped** | Yes — classes A0, A, B, C1, C2, D, E, F and G in §2.2, from control flow only, with all 23 raise sites enumerated and staged in §4.1(b) |
| **Schema and version consequences decided** | Yes — §5: raw schema 5 to 6 (required); instrument "4" to "5" (required); native tool adapter unmoved (Phase-M precedent); model-visible contract unmoved; boundary declared; Phase-P pins deliberately left to break |
| **§9.5 mutation proof fully specified** | Yes — §6: four acceptance criteria from §9.5, three mutation mechanisms M-1/M-2/M-3, and twenty-two named cases including all eleven required synthetic cases, with no provider contact |
| **No open implementation architecture choice remains** | Yes — constructor fields, defaults, internal representation, `provenance()` output, per-site population, null discipline, success-path invariance and legacy compatibility are all fixed in §4 |

### 10.2 The one thing that is not decided, and is not an architecture choice

**[NOT AUTHORIZED]** **Where the new instrument-boundary declaration lives.** The frozen
`rc4_instrument_boundary` string lives in `benchmark/pilot-v7-rc4/qualification-contract.json`, and rc4's
contract must not be edited. Its successor's location is a property of a successor candidate, which §11.5
forbids creating. This is a **successor-candidate decision**, not an open question about C3's
architecture: §5.5 fixes the declaration's required content in full, and only its file placement waits on
prerequisite 4.

### 10.3 Decision

## **`PROVIDER_OBSERVABILITY_DESIGN_CLOSED`**

**[INFERENCE]** Prerequisite 3 of `docs/post_phaseP_prospective_redesign_decision.md` §11.5 is
discharged. C3's design is frozen at the §9.3 minimum set, with the §9.5 mutation proof specified.

### 10.4 Required explicit statements

**[OBSERVED]**

- **No provider was contacted.** No Ollama contact, no OpenAI contact, no network call, no socket opened,
  no model inference performed, and no runtime provenance probe executed.
- **No Phase-P evidence or result row was used.** Nothing beneath `results/phaseP-rc4-qualification/` was
  read, listed, traversed, hashed or modified. Every failure-path claim is derived from code control flow
  alone, and no telemetry field was selected, sized, named or tuned from any Phase-P outcome, count or
  trajectory.
- **Phase P remains UNQUALIFIED / HOLD.** `pilot-v7-rc4` is UNQUALIFIED and the official verdict remains
  permanently `SCHEDULE_COMPLETE_VERDICT_HOLD`.
- **BEN-003 is not repaired or reinterpreted.** The preserved invalidated cell remains
  `MODEL_PROTOCOL_INVALID`; BEN-003 remains `MATRIX_INVALID`; the attribution remains
  `MODEL_PROTOCOL_FAILURE`; the task disposition remains `KEEP_UNCHANGED`.
- **No successor candidate is created.** No candidate version number, no phase name, no seed, and no
  registration or randomization artifact.
- **This document does not authorize implementation.** It is a design record.
- **Implementation requires a separate explicit human authorization**, together with the remaining §11.5
  prerequisites — item 1, the purpose and architecture of the future qualification criterion, and item 4,
  explicit human authorization — neither of which this record touches.

### 10.5 Confirmation

- **ZERO MODEL INFERENCE.** No provider, Ollama or network contact. No `pytest` invocation. No validator,
  probe, harness, analyzer or writer executed in any mode.
- **NO PHASE-P EVIDENCE TOUCHED.** The evidence tree was not read, listed, traversed, hashed or modified.
- **NO SOURCE, TEST, SCHEMA, CONFIG OR BENCHMARK FILE MODIFIED.** No version constant moved.
- **BOTH PREREQUISITE-2 RECORDS PRESERVED BYTE-FOR-BYTE.**
- **ONLY THIS DOCUMENT WAS WRITTEN.** Nothing was staged, committed, pushed, tagged or merged.

---

**C3_PROVIDER_OBSERVABILITY_DESIGN: PASS**

**CLOSURE: `PROVIDER_OBSERVABILITY_DESIGN_CLOSED`**

**MINIMUM_TELEMETRY:** `failure_branch`, `response_id`, `system_fingerprint`, `finish_reason`,
`effective_model`, `input_tokens`, `output_tokens`, `envelope_field_presence`, `protocol`,
`effective_seed`, `native_tool_call_state`

**PROVIDER_ERROR_SHAPE_FROZEN: YES**

**RAW_SCHEMA_VERSION_BUMP_REQUIRED: YES** — 5 to 6

**INSTRUMENT_VERSION_BUMP_REQUIRED: YES** — "4" to "5"

**NATIVE_TOOL_ADAPTER_VERSION_BUMP_REQUIRED: NO**

**TRANSPORT_FAILURE_DISTINGUISHED: YES**

**MUTATION_PROOF_PLAN: PASS**

**SECURITY_PRIVACY_BOUNDARY: PASS**

**PHASEP_INTERPRETATION_CHANGED: NO**

**BEN003_REHABILITATED: NO**

**SUCCESSOR_CANDIDATE_AUTHORIZED: NO**
