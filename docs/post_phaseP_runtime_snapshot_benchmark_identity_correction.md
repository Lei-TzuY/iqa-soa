# RuntimeSnapshotV1 benchmark-identity capture correction

**Record kind:** binding narrow repair addendum to
`docs/post_phaseP_confirmatory_execution_io_clarification.md` (the frozen Work
Unit 5 execution-I/O contract).
**Status:** INSTRUMENTATION CORRECTNESS REPAIR — capture path REPAIRED and
covered; downstream successor re-freeze **BLOCKED** on an upstream
instrument-revision governance precondition (§8).
**Date:** 2026-09-03
**Base canonical commit:** `a24d8924e7bd3e42c07530aab074236db7478447`
**Candidate:** `prospective-candidate-i5-m1-b76f40da2`
**Discovered by:** the first real runtime-preflight attempt against
`configs/successor-qualification.yaml`.

**Provider contacted:** NO. **Model inference:** NO. **Qualification execution:**
NOT AUTHORIZED. **Confirmatory execution:** NOT AUTHORIZED. This record
authorizes no execution of any kind.

---

## 0. Boundary and precedence

This addendum corrects **exactly one derivation**: how `benchmark_sha256` inside
the `ExperimentExecutionConfigIdentityV1` preimage is computed from
`config.benchmark_path`.

It does **not** reopen or modify:

- the `RuntimeSnapshotV1` schema, its twenty fields, or their names and order;
- the `experiment_config_digest` object's key set;
- the seventeen-field `runtime_identity_digest` basis, or the `self_digest` rule;
- `provider_config_digest`, `provider_parameters_digest`, `prompt_digest`,
  `models_config_digest`, `environment_fingerprint`, `retry_policy`,
  `tool_contract_policy`, `timeout_seconds`, or endpoint capture;
- `package_source_sha256` semantics;
- `ExperimentRunner` benchmark-loading semantics;
- any benchmark or model-visible byte, any scoring rule, any exposure
  definition, the qualification decision rule, or the confirmatory statistical
  design.

**Precedence rule:** where the base execution-I/O clarification conflicts with
this addendum, this addendum controls for `benchmark_sha256` only. All other
text in the base clarification remains binding and unchanged.

---

## 1. The defect

Two repository contracts could not both hold.

**ExperimentConfig / ExperimentRunner semantics.**
`ExperimentConfig.benchmark_path` is a benchmark **source root**. It is resolved
as a plain path by `load_experiment_config`
([runner.py:195](../src/iqa_soa/experiment/runner.py#L195)), which — unlike
`ablations_path` — applies no `is_file()` requirement. `ExperimentRunner` passes
it to `load_benchmark_cases(self.config.benchmark_path, ...)`
([runner.py:272](../src/iqa_soa/experiment/runner.py#L272)), a root loader, and
records its identity with the **directory-capable tree digest**
`_path_digest(self.config.benchmark_path)` under the field name
`benchmark_sha256` ([runner.py:368](../src/iqa_soa/experiment/runner.py#L368)).

**The production configuration.** `configs/successor-qualification.yaml` sets
`benchmark_path: benchmark`, which resolves to the `benchmark/` **directory**
(98 tracked files across 21 category and frozen-selection subdirectories). The
config's own commentary states the intent plainly: *"benchmark_path is the
benchmark root only so the runner can digest it."*

**The frozen capture rule.** The base clarification §4.5.4 specified
`benchmark_sha256 = file_sha256(config.benchmark_path)`, and
`capture_runtime_snapshot_v1` implemented it with the file-only helper
`_file_sha256`, which calls `path.read_bytes()`.

A directory cannot be read as a file. The production capture therefore did not
merely produce a questionable value — it **could not be computed at all**:

```
file_sha256(config.benchmark_path)
  -> OSError: [Errno 13] Permission denied: '<repo>/benchmark'   (Windows)
  -> IsADirectoryError                                            (POSIX)
  -> ConfirmatoryExecutionError: cannot read runtime identity input: <repo>/benchmark
```

The existing confirmatory tests all built **file-valued** synthetic benchmark
paths (`root / "synthetic-cases.yaml"`, `root / "cases.yaml"`), so the
production directory-valued shape was never covered and the contradiction
survived the freeze.

---

## 2. OLD → NEW

**OLD** (base clarification §4.5.4, and the implementation of it):

```text
benchmark_sha256 = file_sha256(config.benchmark_path)
```

**DEFECT:**

`ExperimentConfig.benchmark_path` is a benchmark source root, and production
configurations set it to a directory. `file_sha256` is defined only for a
regular file, so the rule was unsatisfiable against every real configuration.

**NEW:**

```text
benchmark_sha256 = benchmark_source_sha256(config.benchmark_path)
```

where `benchmark_source_sha256` is the repository's **existing** canonical
path-tree digest, restricted to the frozen benchmark source set:

```text
benchmark_source_sha256(path)
    = path_tree_sha256(path, include_suffixes = {".json", ".md", ".yaml"})
```

`path_tree_sha256` is `iqa_soa.experiment.runner._path_digest`, unchanged — the
same algorithm, over the same path, that `ExperimentRunner` already records as
`benchmark_sha256`. **No second benchmark identity is introduced.**

---

## 3. Benchmark source digest algorithm — exact

```text
path_tree_sha256(root, include_suffixes):

  1. FILE SET
     if root is a regular file:
         files := [root]                       # suffix restriction does NOT apply
     else:
         files := every regular file f in root.rglob("*")
                  such that f.suffix in include_suffixes,
                  sorted by path
     if files is empty:
         RAISE  (ExperimentConfigError -> ConfirmatoryExecutionError)

  2. NAME BASIS  (per file f)
     if root is a regular file:  name := f.name
     else:                       name := f.relative_to(root).as_posix()

  3. ACCUMULATION  (files in the order fixed by step 1)
     h := SHA256()
     for f in files:
         n := utf8(name(f))
         c := exact bytes of f
         h.update( uint64_big_endian(len(n)) ); h.update(n)
         h.update( uint64_big_endian(len(c)) ); h.update(c)

  4. RESULT
     lowercase hex of h
```

### 3.1 Requirements satisfied

| Requirement | How |
|---|---|
| deterministic | fixed sorted order; no clock, environment, locale or randomness |
| repository-relative | names are POSIX paths relative to the benchmark root, never absolute |
| enumeration-order insensitive | the file list is **sorted** before accumulation |
| hashes exact scientific bytes | raw `read_bytes()`; no line-ending normalization, no YAML reparse or reserialization |
| excludes unrelated/untracked files | the frozen source-set restriction (§3.2) |
| detects any bound case-byte change | content is length-prefixed and included verbatim |
| detects rename/add/remove | the relative path is length-prefixed into the same digest |
| identical for identical tracked content | content + relative path are the only inputs |
| works for a directory `benchmark_path` | the directory branch is the production branch |
| fails closed | missing, empty, source-free or unreadable root raises; it never degrades to a digest over nothing |
| traverses no forbidden evidence | the walk is rooted at `config.benchmark_path`; `results/` is never reached |

### 3.2 The frozen source set

`BENCHMARK_SOURCE_SUFFIXES = {".json", ".md", ".yaml"}`

These are exactly the three kinds of tracked scientific source the benchmark
tree holds: `.yaml` case files (68), `.json` manifests / freeze records /
qualification contracts (24), `.md` audits (6) — 98 of 98 tracked files.

The restriction is the **same idiom** the repository already applies to the
package digest, where `package_source_sha256` restricts to `{".py"}` so that
`__pycache__` build output cannot enter a scientific identity. It keeps build
artifacts, editor droppings and backup files out of benchmark identity.

**On a clean checkout the restriction is a no-op.** Both digests over
`benchmark/` at the base commit are:

```
538eaac4f6472c23a061b84a5f85f44ebde33476d2f1e54892ecdd77a9dcddb6
```

so the corrected confirmatory `benchmark_sha256` and the runner's existing
`benchmark_sha256` **agree exactly**, and the repository still has one benchmark
identity rather than two. This equality is pinned by test
`test_corrected_rule_matches_the_runner_benchmark_identity_on_a_clean_tree`.

### 3.3 The regular-file case

A `benchmark_path` naming a regular file remains well defined: the file set is
exactly that file and the name basis is its bare filename, so a synthetic
single-file fixture stays deterministic and byte-sensitive. The suffix
restriction is deliberately **not** applied on this branch — an explicitly named
file is the benchmark source whatever it is called. This preserves the existing
file-valued confirmatory fixtures without a compatibility shim.

Note that this branch is not bit-identical to the OLD `file_sha256`: it frames
name and content with length prefixes. No stored digest depended on the OLD
value (§5), so nothing is invalidated.

---

## 4. What did not change

- **Field name** remains `benchmark_sha256`.
- **`RuntimeSnapshotV1` schema does not change** — still exactly twenty fields.
- **`experiment_config_digest` object key set does not change** — still exactly
  the sixteen keys of base §4.5.4, with no `output_root`.
- **Only the derivation of `benchmark_sha256` is corrected.**
- Benchmark and model-visible bytes: **unchanged**.
- Scoring: **unchanged**. Exposure semantics: **unchanged**.
- Qualification decision rule: **unchanged**.
- Confirmatory statistical design: **unchanged**.
- `ExperimentRunner` benchmark loading: **unchanged**.
- No caller override, hook, keyword, registry entry, environment switch or
  exported alternative is added. `capture_runtime_snapshot_v1` still accepts
  exactly `config` and `provider`, both keyword-only.

---

## 5. Why this is a capture-only correction, not an instrument boundary

`INSTRUMENT_VERSION` exists so that a **measurement** boundary is
machine-checkable: rows produced by materially different harnesses must not be
pooled. Every previous bump (`2` protocol telemetry, `3` fault provenance, `4`
tool contract, `5` provider-failure telemetry) changed what the harness
**observes or writes into a raw row**.

This repair does none of that. It writes no new row field, changes no row
content contract, and alters no prompt, policy, guard, tool dispatch, request
payload, accept/refuse predicate, `failure_class`, retry rule or metric. The
model is asked exactly the same question under exactly the same rules.

Decisively, **no measurement is retroactively affected**:

- **No prior successor `RuntimeSnapshotV1` exists.** The first real preflight
  refused, which is how the defect was found.
- **No successor model outcome exists.** No successor row, evidence file or
  result artifact has been written.
- The OLD rule was **unsatisfiable** against a directory-valued
  `benchmark_path`, so it produced no persisted value that this correction could
  contradict. It fixes an impossible implementation of an already-intended
  identity field.
- Historical phases recorded benchmark identity through the **runner's**
  `_path_digest` path, which this correction does not touch and now agrees with.

The repair therefore occurred **prospectively, before any inference**, and no
externally recorded instrument contract changed.

**Determination:**

| Pin | Value | Status |
|---|---|---|
| `INSTRUMENT_VERSION` | `5` | unchanged — no bump required or taken |
| `RAW_SCHEMA_VERSION` | `6` | unchanged |
| `NATIVE_TOOL_ADAPTER_VERSION` | `native-tools-adapter-3` | unchanged |
| tool argument contract | `tool-arguments-1` | unchanged |
| `RuntimeSnapshotV1` schema | 20 fields | unchanged |

No repository governance rule requires a bump for a capture-only correction that
retroactively invalidates no measurement, so none is invented here.

**This is not the same as saying nothing is required.** Governance *does* require
that the approved instrument-revision chain be extended to cover the changed
`src/iqa_soa` tree — a new link, at unchanged version constants. That link is a
human-authorized, commit-anchored act and was **not** written here; see §8.

---

## 6. Implementation

| File | Change |
|---|---|
| `src/iqa_soa/experiment/runner.py` | adds `BENCHMARK_SOURCE_SUFFIXES` and the public canonical helper `benchmark_source_sha256`, delegating to the existing `_path_digest` exactly as `package_source_sha256` already does. `_path_digest` itself is unchanged. |
| `src/iqa_soa/experiment/confirmatory.py` | imports that one helper; adds the fail-closed wrapper `_benchmark_source_sha256`; changes the single `benchmark_sha256` line in the `ExperimentExecutionConfigIdentityV1` preimage. |

No other production behaviour is touched.

---

## 7. Scientific invariants — recomputed at the repaired state

| Invariant | Value | Status |
|---|---|---|
| benchmark case-byte digest | `76f40da2402780736616d886f5865a89c66981c4a0aa858340b6b431df03acea` | **unchanged** |
| canonical exposure digest | `23bd76a57989ac3dc30ea718f0d0b3ac2ae3983a850c3a696868e45b632c4092` | **unchanged** |
| tracked benchmark diff | zero changed bytes | **unchanged** |
| C1 / C2 / C4a | as frozen | unchanged |
| C3 provider telemetry | as frozen | unchanged |
| C4b | absent | unchanged |
| C5 | as frozen | unchanged |
| C6 | absent | unchanged |

---

## 8. Downstream re-freeze — ATTEMPTED, BLOCKED UPSTREAM

`src/iqa_soa` bytes changed, so every successor-owned binding that covers
package/source identity is now stale and is **not** treated as still valid:

| Binding | State |
|---|---|
| `docs/successor_frozen_execution_inputs.json` → `trees["src/iqa_soa"]` | **STALE.** Records `205a21ed…`; the live tree is `ab63e8b1…`. Every other bound file digest and `trees["benchmark/pilot-v7-rc4"]` still verify. |
| `candidates/prospective-candidate-i5-m1-b76f40da2/provenance.json` → `instrument_tree_digest["src/iqa_soa"]` | **STALE.** Records `1d0f1371…`; the live tree is `5d1126cf…` under the git-tracked tree-digest algorithm. |
| candidate tier-1 `digest-manifest.json` / tier-2 `freeze-record.json` | **NOT REWRITTEN** — they digest the tier-0 artifacts, which were not regenerated. |

The re-freeze was attempted with the repository's own generator,
`scripts/successor_candidate_freeze.py`. **It refused to write.** It writes only
after every offline gate passes, and two gates fail:

```
gate FAIL: HISTORICAL_RC4_VALIDATOR_UNCHANGED
gate FAIL: OFFLINE_CAPABILITY_CRITERIA
```

Both trace to **one** root cause. `scripts/instrument_revision.py` maintains an
approved instrument-revision **chain**, whose current head is
`docs/post_phaseP_provider_observability_instrument_revision.json` with
`current_instrument.src_iqa_soa_tree = 1d0f1371…` and per-file pins including
`src/iqa_soa/experiment/runner.py = 6c8007e6…`. Changing any byte under
`src/iqa_soa` makes the chain stop describing the live instrument:

```
A: the working src/iqa_soa tree digests to 5d1126cf…, which is not the approved
   revision '1d0f1371…'. Either an unapproved edit was made, or the revision
   record was not regenerated.
A: src/iqa_soa/experiment/confirmatory.py changed since 883c425d… but is not in
   the approved instrument revision
A: src/iqa_soa/experiment/runner.py hashes to 459c4755…, not the approved
   '6c8007e6…'
```

`OFFLINE_CAPABILITY_CRITERIA` is a cascade of the same fact: criterion 1,
`static_validity_over_all_17_tasks`, calls `rc4_validator.run_all()` and
inherits its ten class-`A` failures. No benchmark, exposure, scope, sink, ledger,
determinism or authorization gate fails.

**This is the mechanism working, not a defect.** The sanctioned response — stated
in `scripts/post_phaseP_write_provider_observability_revision.py` — is to append
a **fifth reviewed link** to the revision chain that names its parent commit,
binds the current head as predecessor, enumerates each changed instrument file
with its SHA-256 and a scientific reason, and pins the new tree.

**That link was NOT written here, for two reasons:**

1. **It is a human-authorized governance act.** Every existing link was admitted
   by a separate explicit human authorization record and carries hand-authored
   scientific judgment — per-file `reason`, `observation_only`,
   `why_observation_only`, and a boundary declaration governing whether analysts
   may pool across it. This repair session authorizes an instrumentation fix, a
   contract addendum and a downstream re-freeze; it does not authorize minting a
   new instrument-revision link.
2. **It is commit-anchored, and this session may not commit.** Each link pins a
   `parent_commit` and each predecessor's claims are proved *from committed
   bytes* at that commit. This repair is deliberately left unstaged, so a link
   meeting the chain's own evidentiary standard cannot be constructed yet.

**Consequently no successor freeze artifact was rewritten.**
`docs/successor_frozen_execution_inputs.json` was deliberately left stale rather
than recomputed: `successor_qualification_protocol.offline_preflight()` currently
reports exactly one failure — that stale tree digest — and it performs no
independent instrument-chain check. Recomputing it in isolation would turn the
successor preflight green over an instrument state repository governance has not
approved, silencing the only remaining signal. A partial re-freeze would be a
worse outcome than an honest failure, so the fail-closed state is preserved.

Nothing was renamed. The candidate identifier
`prospective-candidate-i5-m1-b76f40da2` is unaffected: the frozen naming rule
binds benchmark selection `b76f40da2`, instrument `i5` and measurement `m1`, none
of which this repair moves, so no mechanical rename is required. Benchmark bytes,
canonical exposure and the candidate scientific change set are unchanged.

### 8.1 Required order of operations to complete the re-freeze

1. Human authorization admitting this instrumentation repair to the instrument
   record.
2. Commit the repair, so a `parent_commit` exists.
3. Write the fifth instrument-revision link (`INSTRUMENT_VERSION` stays `5` and
   `RAW_SCHEMA_VERSION` stays `6` — see §5; the chain's own precedent in
   `docs/post_phaseP_confirmatory_instrument_revision.json` is explicit that
   *"no boundary is bumped merely because the tree changed"*).
4. Re-run `scripts/successor_candidate_freeze.py`; all gates should then pass.
5. Recompute `docs/successor_frozen_execution_inputs.json` from
   `successor_qualification_protocol.compute_frozen_inputs()`.

## 9. Coverage

`tests/integration/test_runtime_snapshot_benchmark_identity.py` exercises the
production directory-valued shape the previous fixtures never reached:
capture succeeds on a directory root; the digest is deterministic and
enumeration-order independent; one changed bound byte, an added case, a removed
case and a pure rename each move it; an out-of-source-set file does not; missing,
empty, source-free and unreadable roots each fail closed; the file-valued fixture
stays defined; config/policy/models/ablations digests keep their semantics; the
key set is pinned; self-digest validation holds; repeated captures share
`runtime_identity_digest` across differing `captured_at` and `self_digest`; no
caller can override the benchmark digest; and no look-alike config or hand-built
snapshot is accepted.

---

## 10. Authorization state after this repair

| Act | State |
|---|---|
| Qualification execution | **NOT AUTHORIZED** |
| Model inference | **NOT AUTHORIZED** |
| Confirmatory execution | **NOT AUTHORIZED** |
| Provider contact | **NOT PERFORMED** |
| Production randomization | **NOT REALIZED** |

The structural blocker to a runtime-snapshot preflight is removed: the
production directory-valued `ExperimentConfig` now captures a valid
`RuntimeSnapshotV1` under a deterministic no-network stub provider.

Two barriers to execution remain, and this record clears neither:

1. the withheld human execution authorization; and
2. the unwritten fifth instrument-revision chain link (§8), without which the
   successor candidate freeze and frozen-input record cannot be re-frozen.
