#!/usr/bin/env python3
"""The frozen real-model QUALIFICATION protocol of the successor candidate.

**NO MODEL INFERENCE. NO PROVIDER CONTACT. NO NETWORK. NO ENDPOINT PROBE.**
**NO QUALIFICATION EXECUTION. NO CONFIRMATORY EXECUTION. NO RANDOMIZATION.**

Importing this module, calling every function in it and running its CLI opens no
socket, resolves no credential, reads no environment variable for its value and
writes nothing under any results namespace.  It is a statement of what a later,
separately authorized execution would be bound to -- and a set of offline checks
proving the statement still matches the committed repository.

WHAT THIS PROTOCOL IS FOR
=========================

``candidates/prospective-candidate-i5-m1-b76f40da2`` is FROZEN_NOT_YET_QUALIFIED
(``freeze-record.json``).  That record's own ``next_decision`` names what was
missing: "a separate human decision on real provider/model eligibility,
registration, randomization, qualification and confirmatory execution".

``docs/post_phaseP_successor_provider_and_qualification_protocol_authorization.md``
supplies the first part of that decision and nothing beyond it.  It names two
PROPOSED provider/model strata and authorizes a successor-owned provider
configuration, a successor-owned ``ExperimentConfig``, this protocol, the frozen
execution-input bindings and the offline eligibility-preflight machinery.  It
authorizes no provider contact, no model inference, no qualification execution
and no confirmatory execution.
:data:`QUALIFICATION_EXECUTION_AUTHORIZED` is the machine-readable form of that
refusal, read by :mod:`run_successor_qualification`, which cannot execute while
it is ``False``.

WHY A SUCCESSOR-OWNED PROTOCOL RATHER THAN A REUSED HISTORICAL ONE
==================================================================

``scripts/phaseP_protocol.py`` pins instrument 4 / raw schema 5, the
``rc4-historical`` scoring profile, a historical credential name, a historical
models config and a historical results namespace.  Every one of those is wrong
for this candidate, and the freeze record states the pooling prohibition
directly: rows written under instrument 5 / raw schema 6 may never be pooled,
merged, averaged or compared with rows written under instrument 4 / raw schema
5.  Reusing the historical protocol would therefore either corrupt the
successor's instrument boundary or quietly repair the historical one.  Neither
is permitted, so this protocol is separate, and :func:`check_historical_isolation`
proves the separation mechanically rather than by promise.

WHAT THIS PROTOCOL IS NOT
=========================

It is not the confirmatory design.  Qualification and confirmatory execution are
different objects with different eligibility rules, and this module refuses to
be read as the second: :data:`AUTHORIZES_CONFIRMATORY_EXECUTION` is ``False``,
:data:`OUT_OF_SCOPE_TREATMENTS` names what it will not run, and no function here
emits, derives or accepts a confirmatory disposition.  Provider eligibility for
the confirmatory matrix is a PR-10 evidence question owned by
:mod:`successor_eligibility_preflight`; selection as a proposed stratum is not
eligibility, and never becomes eligibility here.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePath
import sys
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _root in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import successor_derive_seeds as successor_seeds  # noqa: E402
import successor_scoring_vocabulary as successor_vocabulary  # noqa: E402
import validate_successor_scope as successor_scope  # noqa: E402
from iqa_soa.agent.providers import SANDBOX_TOOL_NAMES  # noqa: E402
from iqa_soa.instrument import (  # noqa: E402
    INSTRUMENT_VERSION,
    NATIVE_TOOL_ADAPTER_VERSION,
    RAW_SCHEMA_VERSION,
)
from iqa_soa.tools.argument_schema import (  # noqa: E402
    TOOL_ARGUMENT_CONTRACT_VERSION,
    contract_digest,
)


class SuccessorProtocolError(RuntimeError):
    """A successor qualification precondition failed.  Always fail-closed."""


class NoncanonicalInput(SuccessorProtocolError):
    """A supplied scientific input or output namespace is not the frozen one.

    Raised BEFORE any provider object, any directory creation and any cell, so a
    look-alike input can never reach the point where it would be executed.
    """


class EnvironmentHold(SuccessorProtocolError):
    """A live runtime fact disagrees with a prospectively frozen pin.

    Deliberately its own class.  An ``ENVIRONMENT_HOLD`` is a STOP, never a
    repair instruction: the protocol never pulls, updates, retags or replaces a
    model to make a mismatch go away, and no caller may catch this and continue.
    """


class QualificationExecutionNotAuthorized(SuccessorProtocolError):
    """Execution was requested while no human record authorizes one."""


# --------------------------------------------------------------------------
# Canonical provenance of this freeze
# --------------------------------------------------------------------------

#: The commit this protocol was frozen against: the successor candidate freeze.
CANONICAL_BASE_COMMIT = "d5b5537a84cc8b57bca2195c3b3bb4cfdb857e5c"

#: The governing human decision record.  Named here so the authorization this
#: protocol depends on is a citable artifact rather than an oral tradition.
AUTHORIZATION_RECORD_RELATIVE = (
    "docs/post_phaseP_successor_provider_and_qualification_protocol_authorization.md"
)

PROTOCOL_VERSION = "successor-qualification-protocol-1"

# --------------------------------------------------------------------------
# The candidate this protocol qualifies -- and its status AT ENTRY
# --------------------------------------------------------------------------

CANDIDATE_IDENTIFIER = "prospective-candidate-i5-m1-b76f40da2"
CANDIDATE_NAMESPACE = f"candidates/{CANDIDATE_IDENTIFIER}"

#: The status the candidate holds when this protocol is entered, and the ONLY
#: status from which entry is legal.  It is not a status this protocol may
#: change: qualification is decided by executed evidence under a later
#: authorization, never by a constant in the protocol that plans it.
CANDIDATE_STATUS_AT_ENTRY = "FROZEN_NOT_YET_QUALIFIED"

#: What the candidate's qualification status is while no execution has happened.
CANDIDATE_QUALIFICATION_STATUS = "NOT_YET_QUALIFIED"

#: Statuses this module refuses to assert about the candidate.  Stated as data
#: so the prohibition is machine-checkable rather than prose.
FORBIDDEN_CANDIDATE_STATUSES: tuple[str, ...] = (
    "QUALIFIED",
    "PROVIDER_QUALIFIED",
    "CONFIRMATORY_ELIGIBLE",
    "REGISTERED",
    "EXECUTED",
)

FREEZE_RECORD_RELATIVE = f"{CANDIDATE_NAMESPACE}/freeze-record.json"
QUALIFICATION_CONTRACT_RELATIVE = f"{CANDIDATE_NAMESPACE}/qualification-contract.json"

#: SHA-256 over the exact on-disk bytes of the two governing candidate
#: artifacts, as recorded by the freeze itself.  Read as pins, recomputed by
#: :func:`check_candidate_freeze`, never rewritten here.
FREEZE_RECORD_DIGEST = (
    "c099346d2e1dadaa7da8fbca2cfb3ebbf7b7d3ba4d95083827bb9daee3f339cc"
)
QUALIFICATION_CONTRACT_DIGEST = (
    "46b0893b8259d3bb1fed8810fe624d2a3393d5227bc72ea31ee395872dcdadb6"
)

# --------------------------------------------------------------------------
# Scientific digests -- REBOUND from the scope validator, never re-spelled
# --------------------------------------------------------------------------
#
# A second literal copy of a frozen digest is a second thing that can drift from
# it.  Both come from ``scripts/validate_successor_scope.py``, which the
# candidate's own naming policy already cites as their source.

#: The benchmark directory name, read from the scope validator's own bound root
#: rather than re-typed, so the two cannot name different benchmarks.
BENCHMARK_VERSION = successor_scope.BENCHMARK_ROOT.name
BENCHMARK_CASE_BYTES_DIGEST = successor_scope.BENCHMARK_CASE_BYTES_DIGEST
CANONICAL_EXPOSURE_DIGEST = successor_scope.CANONICAL_EXPOSURE_DIGEST

# --------------------------------------------------------------------------
# Instrument / schema / adapter / tool-contract pins
# --------------------------------------------------------------------------

EXPECTED_INSTRUMENT_VERSION = "5"
EXPECTED_RAW_SCHEMA_VERSION = 6
EXPECTED_NATIVE_TOOL_ADAPTER_VERSION = "native-tools-adapter-3"
EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION = "tool-arguments-1"

#: The digest of the argument contract the provider ADVERTISES and the sandbox
#: ENFORCES.  Computed from the live table at import so it can never claim a
#: contract the code does not render.
EXPECTED_TOOL_ARGUMENT_CONTRACT_DIGEST = contract_digest(SANDBOX_TOOL_NAMES)

#: Rows written under instrument 5 / raw schema 6 may never be pooled, merged,
#: averaged or compared with rows written under instrument 4 / raw schema 5.
#: The historical pin to instrument 4 / raw schema 5 stays deliberately
#: incompatible and is not repaired.
CROSS_INSTRUMENT_POOLING_PERMITTED = False

# --------------------------------------------------------------------------
# Scoring vocabulary and change semantics
# --------------------------------------------------------------------------

SCORING_PROFILE = successor_vocabulary.SCORING_PROFILE_SUCCESSOR
SCORING_VOCABULARY_VERSION = successor_vocabulary.SUCCESSOR_VOCABULARY_VERSION

#: The historical profile.  Named ONLY so its exclusion is explicit; no
#: successor row is ever scored under it, and no successor-only outcome can
#: enter it (freeze record: retrospective entry is IMPOSSIBLE).
HISTORICAL_SCORING_PROFILE = "rc4-historical"
HISTORICAL_SCORING_VOCABULARY_VERSION = "rc4-scoring-vocabulary-1"

#: The change dispositions carried forward from the frozen qualification
#: contract: C3 unchanged, C4b absent, C5 unchanged, C6 absent.
CHANGE_DISPOSITIONS: Mapping[str, str] = {
    "C1": "IMPLEMENTED",
    "C2": "IMPLEMENTED",
    "C3": "ALREADY_COMPLETE",
    "C4a": "IMPLEMENTED",
    "C4b": "NOT_ADOPTED",
    "C5": "NO_CHANGE",
    "C6": "WITHDRAWN",
}

# --------------------------------------------------------------------------
# Arms, provider slots, model identity and runtime pins
# --------------------------------------------------------------------------

#: Arm order, carried forward from the established lineage so a successor
#: schedule position stays directly comparable to the lineage it continues.
ARM_ORDER: tuple[str, str] = ("qwen", "mistral")

#: Provider slot in ``configs/successor-models.yaml``, addressed by arm name so
#: a mislabelled invocation cannot silently produce the wrong arm.
ARM_PROVIDER_SLOT: Mapping[str, str] = {
    "qwen": "qwen_native_none",
    "mistral": "mistral_native_trailing_user",
}

#: The two models the human decision selected, and nothing else.
EXPECTED_MODEL: Mapping[str, str] = {
    "qwen": "qwen3.5:27b",
    "mistral": "mistral-small3.2:24b",
}

#: PROSPECTIVE runtime identity pins, carried forward from committed NON-OUTCOME
#: protocol and configuration history -- ``scripts/phaseL_protocol.py``
#: (``EXPECTED_MODEL_DIGEST``), ``docs/phaseD_qualification_report.md``,
#: ``docs/phaseI_rc2_real_model_requalification_plan.md`` and
#: ``docs/phaseL_rc3_real_model_requalification_plan_v2.md``, all four of which
#: state the SAME two digests.  No realized Phase-P row was read to obtain them
#: and none is needed: a model digest is a property of the local model artifact
#: the lineage qualified, not of any phase's outcome.
#:
#: They are pins, not instructions.  A later live-runtime disagreement is an
#: ENVIRONMENT_HOLD (:func:`verify_runtime_identity`), never a reason to pull,
#: update, retag or replace a model.
EXPECTED_MODEL_DIGEST: Mapping[str, str] = {
    "qwen3.5:27b": (
        "7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"
    ),
    "mistral-small3.2:24b": (
        "5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b"
    ),
}

#: The committed, NON-OUTCOME sources every model-digest pin above is traceable
#: to.  No historical results namespace appears here, and none is consulted.
MODEL_DIGEST_PROVENANCE: tuple[str, ...] = (
    "scripts/phaseL_protocol.py",
    "docs/phaseD_qualification_report.md",
    "docs/phaseI_rc2_real_model_requalification_plan.md",
    "docs/phaseL_rc3_real_model_requalification_plan_v2.md",
)

#: The local runtime version the lineage recorded.  Carried forward on exactly
#: the same prospective footing as the model digests, and checked the same way.
EXPECTED_RUNTIME_VERSION = "0.32.13"

#: The COMPLETE set of runtime versions an authorized successor run may observe.
#: Exactly one member, by construction.  It exists so that "more than one version
#: is acceptable" is a change to a frozen tuple that a test fails on, rather than
#: a comparison somebody quietly loosens.
ACCEPTED_RUNTIME_VERSIONS: tuple[str, ...] = (EXPECTED_RUNTIME_VERSION,)

#: How the runtime version is compared.  Stated as data because the failure mode
#: this guards against is not a wrong constant -- it is a comparison that starts
#: normalizing, truncating, prefix-matching or range-matching and thereby accepts
#: a version the lineage never qualified.
RUNTIME_VERSION_COMPARISON = "EXACT_STRING_EQUALITY"

#: A live runtime version reported by the execution environment and REFUSED.
#: Recorded so the hold is citable, NOT so it becomes acceptable: it is not in
#: :data:`ACCEPTED_RUNTIME_VERSIONS`, no code path compares against it, and
#: :func:`check_runtime_version_policy` fails if it ever equals the frozen pin.
#: It is a human-reported environment observation carried from the governing
#: authorization record; nothing in this repository probed a runtime to obtain it.
ENVIRONMENT_HOLD_OBSERVED_RUNTIME_VERSION = "0.33.0"

#: The human resolution of that hold: restore the execution environment to the
#: frozen runtime.  The alternative -- repinning the protocol to whatever the
#: environment happens to be running -- would let an environment drift silently
#: redefine the qualified instrument, so it is refused outright.
RUNTIME_VERSION_RESOLUTION = "RESTORE_FROZEN_RUNTIME"
RUNTIME_REPIN_AUTHORIZED = False
RUNTIME_VERSION_EQUIVALENCE_EXCEPTION_PERMITTED = False
RUNTIME_RESTORE_REQUIRED = True

#: What an ENVIRONMENT_HOLD does NOT authorize, stated as data so each refusal is
#: machine-checkable rather than a promise in prose.
RUNTIME_HOLD_REMEDIES_REFUSED: Mapping[str, bool] = {
    "automatic_downgrade_permitted": False,
    "runtime_update_permitted": False,
    "protocol_repin_permitted": False,
    "model_pull_permitted": False,
    "model_replacement_permitted": False,
    "model_retag_permitted": False,
    "version_equivalence_exception_permitted": False,
}

#: An INSTRUMENT setting, already qualified, not an experimental factor.  A
#: qwen-vs-mistral difference must therefore never be read causally, and this
#: protocol computes no model comparison and publishes no model ranking.
EXPECTED_TOOL_CONTRACT_POLICY: Mapping[str, str] = {
    "qwen": "none",
    "mistral": "trailing_user",
}

EXPECTED_PROTOCOL = "native_tools"
EXPECTED_PROVIDER_TYPE = "openai_compatible"
EXPECTED_ENDPOINT = "http://127.0.0.1:11434/v1/chat/completions"
EXPECTED_ENDPOINT_FAMILY = "local Ollama OpenAI-compatible API"

#: Checked by NAME only.  The value is never read, never printed and never
#: written to an artifact.  Successor-specific so that a historical phase
#: credential cannot silently satisfy a successor precondition.
CREDENTIAL_ENV = "SUCCESSOR_OLLAMA_API_KEY"

#: Credential names this protocol refuses to accept, for exactly that reason.
FORBIDDEN_CREDENTIAL_ENVS: tuple[str, ...] = (
    "PHASEP_OLLAMA_API_KEY",
    "PHASEL_OLLAMA_API_KEY",
    "PHASEI_OLLAMA_API_KEY",
    "PHASEF_OLLAMA_API_KEY",
    "OPENAI_API_KEY",
)

#: The exact settings each slot must carry, verbatim from the lineage.
EXPECTED_PROVIDER_SETTINGS: Mapping[str, Mapping[str, Any]] = {
    "qwen_native_none": {
        "type": EXPECTED_PROVIDER_TYPE,
        "enabled": True,
        "endpoint": EXPECTED_ENDPOINT,
        "model": "qwen3.5:27b",
        "api_key_env": CREDENTIAL_ENV,
        "temperature": 0.2,
        "top_p": 1.0,
        "max_output_tokens": 1024,
        "seed": None,
        "supports_seed": True,
        "protocol": EXPECTED_PROTOCOL,
        "timeout_seconds": 600,
        "tool_contract_policy": "none",
    },
    "mistral_native_trailing_user": {
        "type": EXPECTED_PROVIDER_TYPE,
        "enabled": True,
        "endpoint": EXPECTED_ENDPOINT,
        "model": "mistral-small3.2:24b",
        "api_key_env": CREDENTIAL_ENV,
        "temperature": 0.2,
        "top_p": 1.0,
        "max_output_tokens": 1024,
        "seed": None,
        "supports_seed": True,
        "protocol": EXPECTED_PROTOCOL,
        "timeout_seconds": 600,
        "tool_contract_policy": "trailing_user",
    },
}

#: The two PROPOSED strata, sorted by ``(provider, model)``.  PROPOSED is the
#: whole claim: see :data:`STRATUM_SELECTION_SEMANTICS`.
PROPOSED_STRATA: tuple[tuple[str, str], ...] = (
    ("mistral_native_trailing_user", "mistral-small3.2:24b"),
    ("qwen_native_none", "qwen3.5:27b"),
)

#: What selecting a stratum does and does not establish.  The human decision
#: made these PROPOSED strata on the single ground of lineage continuity; it did
#: not and could not make either one eligible or qualified, because both are
#: evidence questions and no evidence exists yet.
STRATUM_SELECTION_SEMANTICS: Mapping[str, Any] = {
    "selection_basis": "PROSPECTIVE_LINEAGE_CONTINUITY",
    "selection_establishes": "PROPOSED_STRATUM",
    "selection_does_not_establish": (
        "CONFIRMATORY_ELIGIBLE",
        "PROVIDER_QUALIFIED",
        "REGISTERED",
        "RUNTIME_VERIFIED",
    ),
    "phasep_outcome_used_for_selection": False,
    "benchmark_outcome_used_for_selection": False,
    "credential_presence_used_for_selection": False,
    "environment_variable_presence_used_for_selection": False,
    "model_ranking_used_for_selection": False,
    "expected_result_used_for_selection": False,
}

# --------------------------------------------------------------------------
# Matrix shape
# --------------------------------------------------------------------------

QA_MODE = "off"
TASK_COUNT = 17
ARM_COUNT = 2

# --------------------------------------------------------------------------
# Seeds -- PROSPECTIVELY DERIVED, never spelled here
# --------------------------------------------------------------------------

SEED_DERIVATION_AUTHORIZED = True
SEED_DERIVATION_ALGORITHM = successor_seeds.DERIVATION_ALGORITHM_VERSION
SEED_DERIVATION_BASE_COMMIT = successor_seeds.CANONICAL_BASE_COMMIT
SEED_DERIVATION_DOMAIN_SEPARATOR = successor_seeds.DOMAIN_SEPARATOR
SEED_DERIVATION_RECORD_RELATIVE = successor_seeds.RECORD_RELATIVE
SEED_COUNT = successor_seeds.SEED_COUNT

#: The three seeds, RECOMPUTED from the successor derivation at import rather
#: than re-typed.  A second literal copy of a derived value is a second thing
#: that can drift from it, so the protocol cannot claim a seed the algorithm does
#: not produce.  Recomputation is three SHA-256s and touches no file, no network
#: and no results namespace, so importing this module stays inert.
SEEDS: tuple[int, ...] = tuple(successor_seeds.derive_seeds()[0])

SEED_SELECTION_STATUS = "DERIVED_PROSPECTIVELY_BEFORE_ANY_SUCCESSOR_OUTCOME"

#: What the derivation is, and is not.  The METHOD is reused from the historical
#: ``phase-p-seed-derivation-1`` algorithm; no historical seed VALUE is reused,
#: and the Phase-P and Phase-L triples are FORBIDDEN inputs to the search.
SEED_SELECTION_SEMANTICS: Mapping[str, Any] = {
    "selection_basis": "DETERMINISTIC_PROSPECTIVE_DERIVATION",
    "derivation_algorithm": SEED_DERIVATION_ALGORITHM,
    "method_reused_from": successor_seeds.DERIVATION_METHOD_REUSED_FROM,
    "method_reuse_is_value_reuse": False,
    "historical_seed_value_reused": False,
    "outcome_informed_seed_selection": False,
    "model_output_used_for_selection": False,
    "result_row_used_for_selection": False,
    "manual_selection_performed": False,
    "derived_before_any_successor_qualification_outcome": True,
}

#: 17 tasks x 2 arms x 3 seeds.  Determined now that the seed set is, and stated
#: as an arithmetic consequence rather than as a constant somebody could edit
#: without editing what produces it.
PLANNED_CELLS: int | None = TASK_COUNT * ARM_COUNT * len(SEEDS)

#: Fixed at zero.  No frozen upstream permits a retry for this candidate --
#: ``docs/post_phaseP_qualification_methodology_decision.md`` section 13.4 ("No
#: retries") is the upstream that would have to say otherwise, and does not.  A
#: provider or model failure is a RECORDED OUTCOME, never a reason to rerun.
INFRASTRUCTURE_RETRY_LIMIT = 0

NO_RETRY_POLICY: Mapping[str, bool] = {
    "retries_permitted": False,
    "replacement_cells_permitted": False,
    "adaptive_cells_permitted": False,
    "silent_rerun_permitted": False,
    "additional_seeds_permitted": False,
    "resume_after_immediate_stop_permitted": False,
}

#: Everything this protocol refuses to run, named so a reader does not have to
#: infer the scope from what is absent.
OUT_OF_SCOPE_TREATMENTS: tuple[str, ...] = (
    "full",
    "partial",
    "ablation",
    "confirmatory",
)

# --------------------------------------------------------------------------
# Authorization state -- the machine-readable form of the human record
# --------------------------------------------------------------------------

PROVIDER_SELECTION_AUTHORIZED = True
PROVIDER_CONFIG_CREATION_AUTHORIZED = True
QUALIFICATION_PROTOCOL_CREATION_AUTHORIZED = True
EXPERIMENT_CONFIG_CREATION_AUTHORIZED = True
PROSPECTIVE_SEED_DERIVATION_AUTHORIZED = True

PROVIDER_CONTACT_AUTHORIZED = False
ENDPOINT_PROBE_AUTHORIZED = False
MODEL_INFERENCE_AUTHORIZED = False
QUALIFICATION_EXECUTION_AUTHORIZED = False
CONFIRMATORY_EXECUTION_AUTHORIZED = False
AUTHORIZES_CONFIRMATORY_EXECUTION = False
RANDOMIZATION_REALIZATION_AUTHORIZED = False
STAGE_C_FINAL_REGISTRATION_AUTHORIZED = False

#: The two human gates a later authorized execution would still have to pass,
#: named prospectively.  Naming them is not opening them: both are inert while
#: :data:`QUALIFICATION_EXECUTION_AUTHORIZED` is ``False``, which
#: :func:`require_execution_authorization` enforces before either is consulted.
HUMAN_GATE_ENV = "IQA_SOA_SUCCESSOR_QUALIFICATION_HUMAN_GATE"
HUMAN_GATE_VALUE = "AUTHORIZED"
HUMAN_GATE_FLAG = "--execute-real-model"

#: Exit codes.  Distinct so a refusal can never be mistaken for a clean run.
EXIT_OK = 0
EXIT_VERDICT_HOLD = 1
EXIT_PREFLIGHT_STOP = 2
EXIT_SCHEDULE_STOPPED = 3
EXIT_CREDENTIAL_STOP = 4
EXIT_ENVIRONMENT_HOLD = 5
EXIT_GATE_CLOSED = 6

# --------------------------------------------------------------------------
# The ONE set of scientific inputs an authorized successor run may read
# --------------------------------------------------------------------------

CANONICAL_MODELS_RELATIVE = "configs/successor-models.yaml"

#: The successor-owned ``ExperimentConfig``.  It follows the repository's
#: existing experiment-configuration convention exactly -- the
#: ``<scope>-qualification.yaml`` filename the qualification lineage already
#: uses, schema_version 1, and the fifteen keys
#: :func:`iqa_soa.experiment.runner.load_experiment_config` requires -- so the
#: successor introduces no parallel configuration system.
CANONICAL_EXPERIMENT_CONFIG_RELATIVE = "configs/successor-qualification.yaml"

CANONICAL_MANIFEST_RELATIVE = f"benchmark/{BENCHMARK_VERSION}/manifest.json"
CANONICAL_CONTRACT_RELATIVE = (
    f"benchmark/{BENCHMARK_VERSION}/qualification-contract.json"
)

CANONICAL_SCIENTIFIC_INPUTS: tuple[str, ...] = (
    CANONICAL_MODELS_RELATIVE,
    CANONICAL_EXPERIMENT_CONFIG_RELATIVE,
    CANONICAL_MANIFEST_RELATIVE,
    CANONICAL_CONTRACT_RELATIVE,
    FREEZE_RECORD_RELATIVE,
    QUALIFICATION_CONTRACT_RELATIVE,
)

#: Configuration files this protocol must never load at runtime.  Historical
#: phase configs were read ONCE, by a human, to copy already-qualified provider
#: settings into the successor config; that is configuration lineage, not a
#: runtime input, and the distinction is what this tuple enforces.
FORBIDDEN_RUNTIME_CONFIGS: tuple[str, ...] = (
    "configs/phaseP-models.yaml",
    "configs/phaseP-qualification.yaml",
    "configs/phaseL-models.yaml",
    "configs/phaseI-models.yaml",
    "configs/phaseF-models.yaml",
    "configs/phaseD-models.yaml",
)

#: Every file whose bytes the frozen execution-input record binds by SHA-256.
FROZEN_INPUT_PATHS: tuple[str, ...] = (
    *CANONICAL_SCIENTIFIC_INPUTS,
    f"{CANDIDATE_NAMESPACE}/candidate-manifest.json",
    f"{CANDIDATE_NAMESPACE}/digest-manifest.json",
    "configs/policies/default.xml",
    AUTHORIZATION_RECORD_RELATIVE,
    "docs/post_phaseP_confirmatory_eligibility_schema_clarification.md",
    "docs/post_phaseP_confirmatory_randomization_implementation_design.md",
    "docs/post_phaseP_qualification_methodology_decision.md",
    "docs/successor_prospective_seed_derivation.json",
    "docs/successor_real_model_qualification_plan.md",
    "scripts/run_successor_qualification.py",
    "scripts/successor_derive_seeds.py",
    "scripts/successor_eligibility_preflight.py",
    "scripts/successor_qualification_protocol.py",
    "scripts/successor_scoring_vocabulary.py",
    "scripts/successor_sink_applicability.py",
    "scripts/validate_successor_scope.py",
)

FROZEN_TREE_ROOTS: tuple[str, ...] = (f"benchmark/{BENCHMARK_VERSION}", "src/iqa_soa")

FROZEN_INPUTS_RELATIVE = "docs/successor_frozen_execution_inputs.json"
PLAN_RELATIVE = "docs/successor_real_model_qualification_plan.md"

# --------------------------------------------------------------------------
# The qualification artifact namespace -- DEFINED, NEVER CREATED
# --------------------------------------------------------------------------

#: The one directory an authorized successor qualification would write.
#: NOTHING creates it here.  A later authorized driver creates it only after
#: every gate and every execution precondition is satisfied, and a pre-existing
#: raw record is a PROTOCOL_DEVIATION, never something to append to.
RESULTS_NAMESPACE = f"results/{CANDIDATE_IDENTIFIER}-qualification"

RAW_RECORD_NAME = "successor-runs.jsonl"
RAW_CSV_NAME = "successor-runs.csv"
RUN_MANIFEST_NAME = "successor-run-manifest.json"
PARTIAL_MANIFEST_NAME = "successor-partial-manifest.json"
ANALYSIS_NAME = "successor-analysis.json"

#: Namespaces this protocol refuses outright.  The first is permanently HOLD /
#: UNQUALIFIED and its rows are instrument 4 / raw schema 5, so a successor run
#: that wrote there would both destroy frozen historical evidence and pool
#: across the instrument boundary.  The rest are the earlier lineage phases,
#: refused for the same structural reason.
FORBIDDEN_RESULTS_NAMESPACES: tuple[str, ...] = (
    "results/phaseP-rc4-qualification",
    "results/phaseL-rc3-requalification",
    "results/phaseI-rc2-requalification",
    "results/phaseF-qualification",
    "results/phaseD-qualification",
)

#: Persistence is fail-closed and append-only-by-absence: a successor artifact is
#: written exactly once, to a path that must not already exist.  There is no
#: overwrite mode, no resume mode and no merge mode.
PERSISTENCE_POLICY: Mapping[str, bool] = {
    "overwrite_permitted": False,
    "resume_permitted": False,
    "merge_permitted": False,
    "partial_row_repair_permitted": False,
    "fail_closed": True,
}

CELLS_SUBDIR: tuple[str, ...] = ("raw", "cells")

#: The ``output_root`` the successor ExperimentConfig must name: the raw subtree
#: of the successor namespace, matching the qualification lineage's convention.
EXPERIMENT_OUTPUT_ROOT = f"{RESULTS_NAMESPACE}/{CELLS_SUBDIR[0]}"

# --------------------------------------------------------------------------
# The successor ExperimentConfig -- every field, frozen
# --------------------------------------------------------------------------

#: The exact value every key of the successor ExperimentConfig must carry.
#:
#: ``seeds`` and ``repetitions`` come from :data:`SEEDS`, which is itself
#: recomputed from the successor derivation, so no derived value is spelled twice
#: and the config cannot carry a seed the algorithm does not produce.  The config
#: LOADS cleanly under the repository's own
#: :func:`iqa_soa.experiment.runner.load_experiment_config`; what still prevents
#: execution is the withheld execution authorization, not a malformed input.
EXPECTED_EXPERIMENT_CONFIG: Mapping[str, Any] = {
    "schema_version": 1,
    "benchmark_path": "benchmark",
    "policy_path": "configs/policies/default.xml",
    "models_path": CANONICAL_MODELS_RELATIVE,
    "ablations_path": "configs/ablations.yaml",
    "output_root": EXPERIMENT_OUTPUT_ROOT,
    "repetitions": SEED_COUNT,
    "seeds": list(SEEDS),
    "max_agent_steps": 20,
    "shuffle_treatments": False,
    "treatments": ["off"],
    "smoke_case_ids": ["BEN-002", "BEN-003"],
    "raw_jsonl": RAW_RECORD_NAME,
    "raw_csv": RAW_CSV_NAME,
    "evidence_subdir": "evidence",
}

#: The single in-scope treatment.  QA OFF is the qualification question; every
#: member of :data:`OUT_OF_SCOPE_TREATMENTS` answers a different one.
EXPECTED_TREATMENTS: tuple[str, ...] = ("off",)

#: What still stops an execution, in one machine-readable place.  The config is
#: now complete and loadable; the barrier is the authorization, which is where a
#: barrier belongs.
EXPERIMENT_CONFIG_EXECUTABILITY: Mapping[str, Any] = {
    "loadable_by_existing_loader_today": True,
    "blocking_field": None,
    "execution_blocked_by": "QUALIFICATION_EXECUTION_NOT_AUTHORIZED",
    "loader_validation_weakened": False,
    "parallel_configuration_system_introduced": False,
    "fabricated_seed_written": False,
    "seeds_prospectively_derived": True,
    "historical_seed_value_reused": False,
}


def _lexical_absolute(supplied: Path | str) -> PurePath:
    """Absolutize and normalize a path WITHOUT touching the filesystem.

    Deliberately lexical.  ``Path.resolve`` stats every component to follow
    symlinks, and the namespace guard below has to be able to refuse a
    historical evidence path without ever touching it -- a guard that reads the
    thing it exists to keep untouched is not a guard.  It also makes the refusal
    independent of filesystem state, which is what fail-closed means here.
    """

    candidate = Path(supplied)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return PurePath(os.path.normpath(str(candidate)))


def canonical_results_root() -> Path:
    """The ONE directory an authorized successor qualification may write."""

    return Path(str(_lexical_absolute(RESULTS_NAMESPACE)))


def is_canonical_results_root(output_root: Path | str) -> bool:
    """Whether *output_root* IS the frozen successor qualification namespace."""

    return _lexical_absolute(output_root) == _lexical_absolute(RESULTS_NAMESPACE)


def require_canonical_results_root(supplied: Path | str | None = None) -> Path:
    """Prove *supplied* is the frozen successor namespace, or refuse.

    A historical namespace is refused with its own message rather than the
    generic one, because "this is not the successor namespace" and "this is
    frozen historical evidence you must never write" are different mistakes and
    a reader deserves to be told which one they made.
    """

    canonical = canonical_results_root()
    if supplied is None:
        return canonical
    offered = _lexical_absolute(supplied)
    for forbidden in FORBIDDEN_RESULTS_NAMESPACES:
        forbidden_root = _lexical_absolute(forbidden)
        if offered == forbidden_root or forbidden_root in offered.parents:
            raise NoncanonicalInput(
                f"PROTOCOL_DEVIATION: {forbidden} is frozen historical evidence "
                "under a different instrument generation. The successor "
                "qualification never reads, writes, appends to, repairs or pools "
                f"with it; its namespace is {RESULTS_NAMESPACE}."
            )
    if offered != _lexical_absolute(canonical):
        raise NoncanonicalInput(
            "PROTOCOL_DEVIATION: the successor qualification froze "
            f"{RESULTS_NAMESPACE} as the one namespace an authorized run writes; "
            f"{offered} is not it. This protocol does not reinterpret an "
            "alternate output root as an official successor execution."
        )
    return canonical


def require_canonical_input(relative: str, supplied: Path | str | None = None) -> Path:
    """Prove a named scientific input is the canonical one, by path."""

    if relative not in CANONICAL_SCIENTIFIC_INPUTS:
        raise NoncanonicalInput(
            f"{relative!r} is not one of the successor protocol's canonical "
            f"scientific inputs {list(CANONICAL_SCIENTIFIC_INPUTS)}"
        )
    canonical = (PROJECT_ROOT / relative).resolve()
    if supplied is None:
        return canonical
    offered = Path(supplied).resolve()
    if offered != canonical:
        raise NoncanonicalInput(
            f"PROTOCOL_DEVIATION: {relative} is bound by canonical path; "
            f"{offered} is a different file. A structurally plausible look-alike "
            "is not a frozen input."
        )
    return canonical


# --------------------------------------------------------------------------
# Digest helpers
# --------------------------------------------------------------------------


def sha256_file(relative: str) -> str:
    """SHA-256 over the exact on-disk bytes of a repository-relative file."""

    return hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest()


def tree_digest(relative_root: str) -> str:
    """A deterministic digest over every source byte beneath *relative_root*.

    Files are hashed in sorted POSIX-relative-path order, each contributing its
    path AND its content digest, so a rename is as detectable as an edit.
    ``__pycache__`` is excluded because it is build output, not a scientific
    input, and its presence varies with whether anything has been imported yet.
    """

    root = PROJECT_ROOT / relative_root
    parts: list[str] = []
    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    ):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        parts.append(f"{relative}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def compute_frozen_inputs() -> dict[str, Any]:
    """The frozen execution-input record, computed from the working tree."""

    return {
        "authorization_record": AUTHORIZATION_RECORD_RELATIVE,
        "authorizes_confirmatory_execution": AUTHORIZES_CONFIRMATORY_EXECUTION,
        "authorizes_model_inference": MODEL_INFERENCE_AUTHORIZED,
        "authorizes_provider_contact": PROVIDER_CONTACT_AUTHORIZED,
        "authorizes_qualification_execution": QUALIFICATION_EXECUTION_AUTHORIZED,
        "benchmark_case_bytes_digest": BENCHMARK_CASE_BYTES_DIGEST,
        "benchmark_version": BENCHMARK_VERSION,
        "canonical_base_commit": CANONICAL_BASE_COMMIT,
        "canonical_exposure_digest": CANONICAL_EXPOSURE_DIGEST,
        "candidate_identifier": CANDIDATE_IDENTIFIER,
        "candidate_status_at_entry": CANDIDATE_STATUS_AT_ENTRY,
        "credential_env": CREDENTIAL_ENV,
        "expected_runtime_version": EXPECTED_RUNTIME_VERSION,
        "experiment_config": CANONICAL_EXPERIMENT_CONFIG_RELATIVE,
        "experiment_config_executability": dict(EXPERIMENT_CONFIG_EXECUTABILITY),
        "files": {relative: sha256_file(relative) for relative in FROZEN_INPUT_PATHS},
        "hash_basis": (
            "raw working-tree bytes, LF canonical checkout per "
            "docs/hash_basis_policy.md"
        ),
        "infrastructure_retry_limit": INFRASTRUCTURE_RETRY_LIMIT,
        "instrument_version": EXPECTED_INSTRUMENT_VERSION,
        "model_inference_performed": False,
        "native_tool_adapter_version": EXPECTED_NATIVE_TOOL_ADAPTER_VERSION,
        "planned_cells": PLANNED_CELLS,
        "profile": SCORING_PROFILE,
        "protocol_version": PROTOCOL_VERSION,
        "provider_contacted": False,
        "proposed_strata": [list(item) for item in PROPOSED_STRATA],
        "qa_mode": QA_MODE,
        "raw_schema_version": EXPECTED_RAW_SCHEMA_VERSION,
        "record_kind": "successor_frozen_execution_inputs",
        "results_namespace": RESULTS_NAMESPACE,
        "runtime_repin_authorized": RUNTIME_REPIN_AUTHORIZED,
        "runtime_version_resolution": RUNTIME_VERSION_RESOLUTION,
        "scoring_vocabulary_version": SCORING_VOCABULARY_VERSION,
        "seed_count": SEED_COUNT,
        "seed_derivation_algorithm": SEED_DERIVATION_ALGORITHM,
        "seed_derivation_base_commit": SEED_DERIVATION_BASE_COMMIT,
        "seed_derivation_digest": successor_seeds.derivation_digest(
            SEEDS, base_commit=SEED_DERIVATION_BASE_COMMIT
        ),
        "seed_derivation_domain_separator": SEED_DERIVATION_DOMAIN_SEPARATOR,
        "seed_derivation_record": SEED_DERIVATION_RECORD_RELATIVE,
        "seed_selection_status": SEED_SELECTION_STATUS,
        "seeds": list(SEEDS),
        "task_count": TASK_COUNT,
        "tool_argument_contract_digest": EXPECTED_TOOL_ARGUMENT_CONTRACT_DIGEST,
        "tool_argument_contract_version": EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION,
        "trees": {root: tree_digest(root) for root in FROZEN_TREE_ROOTS},
    }


def load_frozen_inputs() -> Mapping[str, Any] | None:
    """The committed frozen-input record, or ``None`` before it is written."""

    path = PROJECT_ROOT / FROZEN_INPUTS_RELATIVE
    if not path.exists():
        return None
    loaded: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, Mapping):
        raise SuccessorProtocolError(f"{FROZEN_INPUTS_RELATIVE} is not a JSON object")
    return loaded


def accepted_frozen_digest(relative: str) -> str:
    """The digest the frozen-input record ACCEPTED for *relative*."""

    record = load_frozen_inputs()
    if record is None:
        raise SuccessorProtocolError(
            f"{FROZEN_INPUTS_RELATIVE} does not exist; no digest is accepted yet"
        )
    files = record.get("files")
    digest = files.get(relative) if isinstance(files, Mapping) else None
    if not isinstance(digest, str) or len(digest) != 64:
        raise SuccessorProtocolError(
            f"{FROZEN_INPUTS_RELATIVE} accepts no digest for {relative!r}"
        )
    return digest


# --------------------------------------------------------------------------
# Offline checks.  Each returns a list of failure strings; empty means PASS.
# --------------------------------------------------------------------------


def check_frozen_inputs() -> list[str]:
    """Every frozen input still hashes to the digest the record accepted.

    Before the record exists this reports its absence and nothing else: an
    unwritten record is a state of the work, not a drift.  Once it exists, a
    single moved byte in any bound input is a failure, which is exactly the
    property that makes "the frozen inputs" a claim rather than a label.
    """

    record = load_frozen_inputs()
    if record is None:
        return [
            f"FROZEN_INPUTS: {FROZEN_INPUTS_RELATIVE} has not been written yet"
        ]

    failures: list[str] = []
    files = record.get("files")
    if not isinstance(files, Mapping):
        return ["FROZEN_INPUTS: the record carries no files mapping"]
    if set(files) != set(FROZEN_INPUT_PATHS):
        failures.append(
            f"FROZEN_INPUTS: the record binds {sorted(files)}, the protocol binds "
            f"{sorted(FROZEN_INPUT_PATHS)}"
        )
    for relative in sorted(set(files) & set(FROZEN_INPUT_PATHS)):
        path = PROJECT_ROOT / relative
        if not path.exists():
            failures.append(f"FROZEN_INPUTS: {relative} is absent")
            continue
        actual = sha256_file(relative)
        if actual != files[relative]:
            failures.append(
                f"FROZEN_INPUTS: {relative} digests to {actual}, the record "
                f"accepted {files[relative]}"
            )
    if SEED_DERIVATION_RECORD_RELATIVE not in files:
        failures.append(
            f"FROZEN_INPUTS: {SEED_DERIVATION_RECORD_RELATIVE} is not among the "
            "digest-bound execution inputs; the seed provenance is a scientific "
            "input and an unbound one is an unfrozen one"
        )
    if CANONICAL_EXPERIMENT_CONFIG_RELATIVE not in files:
        failures.append(
            f"FROZEN_INPUTS: {CANONICAL_EXPERIMENT_CONFIG_RELATIVE} is not among the "
            "digest-bound execution inputs; the successor ExperimentConfig is a "
            "scientific input and an unbound one is an unfrozen one"
        )
    trees = record.get("trees")
    if not isinstance(trees, Mapping):
        failures.append("FROZEN_INPUTS: the record carries no trees mapping")
    else:
        if set(trees) != set(FROZEN_TREE_ROOTS):
            failures.append(
                f"FROZEN_INPUTS: the record binds trees {sorted(trees)}, the "
                f"protocol binds {sorted(FROZEN_TREE_ROOTS)}"
            )
        for root in sorted(set(trees) & set(FROZEN_TREE_ROOTS)):
            actual_tree = tree_digest(root)
            if actual_tree != trees[root]:
                failures.append(
                    f"FROZEN_INPUTS: {root} digests to {actual_tree}, the record "
                    f"accepted {trees[root]}"
                )
    for key, expected in (
        ("candidate_identifier", CANDIDATE_IDENTIFIER),
        ("benchmark_case_bytes_digest", BENCHMARK_CASE_BYTES_DIGEST),
        ("canonical_exposure_digest", CANONICAL_EXPOSURE_DIGEST),
        ("instrument_version", EXPECTED_INSTRUMENT_VERSION),
        ("raw_schema_version", EXPECTED_RAW_SCHEMA_VERSION),
        ("results_namespace", RESULTS_NAMESPACE),
        ("credential_env", CREDENTIAL_ENV),
        ("experiment_config", CANONICAL_EXPERIMENT_CONFIG_RELATIVE),
        ("expected_runtime_version", EXPECTED_RUNTIME_VERSION),
        ("runtime_version_resolution", RUNTIME_VERSION_RESOLUTION),
        ("runtime_repin_authorized", RUNTIME_REPIN_AUTHORIZED),
        ("seed_derivation_algorithm", SEED_DERIVATION_ALGORITHM),
        ("seed_derivation_base_commit", SEED_DERIVATION_BASE_COMMIT),
        ("seed_derivation_record", SEED_DERIVATION_RECORD_RELATIVE),
        ("seed_selection_status", SEED_SELECTION_STATUS),
        ("seeds", list(SEEDS)),
        ("planned_cells", PLANNED_CELLS),
    ):
        if record.get(key) != expected:
            failures.append(
                f"FROZEN_INPUTS: record {key} is {record.get(key)!r}, the protocol "
                f"binds {expected!r}"
            )
    return failures


def check_candidate_freeze() -> list[str]:
    """The candidate is present, frozen, and exactly the one this protocol binds."""

    failures: list[str] = []
    for relative, expected in (
        (FREEZE_RECORD_RELATIVE, FREEZE_RECORD_DIGEST),
        (QUALIFICATION_CONTRACT_RELATIVE, QUALIFICATION_CONTRACT_DIGEST),
    ):
        path = PROJECT_ROOT / relative
        if not path.exists():
            failures.append(f"CANDIDATE_FREEZE: {relative} is absent")
            continue
        actual = sha256_file(relative)
        if actual != expected:
            failures.append(
                f"CANDIDATE_FREEZE: {relative} digests to {actual}, the frozen "
                f"pin is {expected}"
            )
    if failures:
        return failures

    freeze = json.loads(
        (PROJECT_ROOT / FREEZE_RECORD_RELATIVE).read_text(encoding="utf-8")
    )
    contract = json.loads(
        (PROJECT_ROOT / QUALIFICATION_CONTRACT_RELATIVE).read_text(encoding="utf-8")
    )
    if freeze.get("candidate_identifier") != CANDIDATE_IDENTIFIER:
        failures.append(
            "CANDIDATE_FREEZE: the freeze record names "
            f"{freeze.get('candidate_identifier')!r}, this protocol binds "
            f"{CANDIDATE_IDENTIFIER!r}"
        )
    if freeze.get("candidate_status") != CANDIDATE_STATUS_AT_ENTRY:
        failures.append(
            "CANDIDATE_FREEZE: entry requires candidate_status "
            f"{CANDIDATE_STATUS_AT_ENTRY!r}, the freeze record says "
            f"{freeze.get('candidate_status')!r}"
        )
    digests = freeze.get("scientific_digests", {})
    if digests.get("benchmark_case_bytes_digest") != BENCHMARK_CASE_BYTES_DIGEST:
        failures.append("CANDIDATE_FREEZE: benchmark case-byte digest disagrees")
    if digests.get("canonical_exposure_digest") != CANONICAL_EXPOSURE_DIGEST:
        failures.append("CANDIDATE_FREEZE: canonical exposure digest disagrees")
    if digests.get("task_count") != TASK_COUNT:
        failures.append("CANDIDATE_FREEZE: task count disagrees")
    instrument = freeze.get("instrument", {})
    if instrument.get("instrument_version") != EXPECTED_INSTRUMENT_VERSION:
        failures.append("CANDIDATE_FREEZE: freeze-record instrument version disagrees")
    if instrument.get("raw_schema_version") != EXPECTED_RAW_SCHEMA_VERSION:
        failures.append("CANDIDATE_FREEZE: freeze-record raw schema version disagrees")
    if (
        instrument.get("native_tool_adapter_version")
        != EXPECTED_NATIVE_TOOL_ADAPTER_VERSION
    ):
        failures.append("CANDIDATE_FREEZE: freeze-record native tool adapter disagrees")
    if (
        instrument.get("tool_argument_contract_version")
        != EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION
    ):
        failures.append("CANDIDATE_FREEZE: freeze-record tool argument contract disagrees")
    if contract.get("candidate_identifier") != CANDIDATE_IDENTIFIER:
        failures.append(
            "CANDIDATE_FREEZE: the qualification contract names another candidate"
        )
    if contract.get("execution_authorization") is not False:
        failures.append(
            "CANDIDATE_FREEZE: the qualification contract claims execution authorization"
        )
    profile = contract.get("scoring_profile", {})
    if profile.get("profile") != SCORING_PROFILE:
        failures.append("CANDIDATE_FREEZE: contract scoring profile disagrees")
    if profile.get("version") != SCORING_VOCABULARY_VERSION:
        failures.append("CANDIDATE_FREEZE: contract scoring vocabulary version disagrees")
    return failures


def check_instrument_pins() -> list[str]:
    """The live instrument still is the generation this protocol froze."""

    failures: list[str] = []
    if INSTRUMENT_VERSION != EXPECTED_INSTRUMENT_VERSION:
        failures.append(
            f"INSTRUMENT: live INSTRUMENT_VERSION is {INSTRUMENT_VERSION!r}, the "
            f"frozen pin is {EXPECTED_INSTRUMENT_VERSION!r}"
        )
    if RAW_SCHEMA_VERSION != EXPECTED_RAW_SCHEMA_VERSION:
        failures.append(
            f"INSTRUMENT: live RAW_SCHEMA_VERSION is {RAW_SCHEMA_VERSION!r}, the "
            f"frozen pin is {EXPECTED_RAW_SCHEMA_VERSION!r}"
        )
    if NATIVE_TOOL_ADAPTER_VERSION != EXPECTED_NATIVE_TOOL_ADAPTER_VERSION:
        failures.append(
            "INSTRUMENT: live NATIVE_TOOL_ADAPTER_VERSION is "
            f"{NATIVE_TOOL_ADAPTER_VERSION!r}, the frozen pin is "
            f"{EXPECTED_NATIVE_TOOL_ADAPTER_VERSION!r}"
        )
    if TOOL_ARGUMENT_CONTRACT_VERSION != EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION:
        failures.append(
            "INSTRUMENT: live TOOL_ARGUMENT_CONTRACT_VERSION is "
            f"{TOOL_ARGUMENT_CONTRACT_VERSION!r}, the frozen pin is "
            f"{EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION!r}"
        )
    actual_contract = contract_digest(SANDBOX_TOOL_NAMES)
    if actual_contract != EXPECTED_TOOL_ARGUMENT_CONTRACT_DIGEST:
        failures.append(
            "INSTRUMENT: the sandbox argument contract digests to "
            f"{actual_contract}, the frozen pin is "
            f"{EXPECTED_TOOL_ARGUMENT_CONTRACT_DIGEST}"
        )
    return failures


def load_provider_config() -> Mapping[str, Any]:
    """Parse the successor provider config.  Contacts nothing.

    ``yaml`` is imported inside the function so that merely importing this
    protocol module pulls in no parser it does not need, and so the import graph
    of the module makes its inertness obvious.
    """

    import yaml  # type: ignore[import-untyped]  # noqa: PLC0415 - keeps import inert

    path = require_canonical_input(CANONICAL_MODELS_RELATIVE)
    loaded: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, Mapping):
        raise SuccessorProtocolError(f"{CANONICAL_MODELS_RELATIVE} is not a YAML mapping")
    return loaded


def check_provider_config() -> list[str]:
    """The successor config carries exactly the two selected strata, verbatim.

    Reading a config is not contacting a provider: this opens a file and
    compares strings.  It constructs no provider object, resolves no credential
    and touches no network.
    """

    failures: list[str] = []
    try:
        config = load_provider_config()
    except (OSError, SuccessorProtocolError) as exc:
        return [f"PROVIDER_CONFIG: {exc}"]

    if set(config) != {"schema_version", "default_provider", "providers"}:
        failures.append(
            f"PROVIDER_CONFIG: top-level keys are {sorted(config)}, expected "
            "['default_provider', 'providers', 'schema_version']"
        )
    providers = config.get("providers")
    if not isinstance(providers, Mapping):
        failures.append("PROVIDER_CONFIG: providers is not a mapping")
        return failures

    expected_slots = set(EXPECTED_PROVIDER_SETTINGS)
    actual_slots = set(providers)
    if actual_slots != expected_slots:
        failures.append(
            f"PROVIDER_CONFIG: configured slots are {sorted(actual_slots)}, the "
            f"human decision selected exactly {sorted(expected_slots)}"
        )
    for slot in sorted(expected_slots & actual_slots):
        entry = providers[slot]
        if not isinstance(entry, Mapping):
            failures.append(f"PROVIDER_CONFIG: {slot} is not a mapping")
            continue
        expected = EXPECTED_PROVIDER_SETTINGS[slot]
        if set(entry) != set(expected):
            failures.append(
                f"PROVIDER_CONFIG: {slot} fields are {sorted(entry)}, expected "
                f"{sorted(expected)}"
            )
            continue
        for key in sorted(expected):
            if entry[key] != expected[key]:
                failures.append(
                    f"PROVIDER_CONFIG: {slot}.{key} is {entry[key]!r}, the frozen "
                    f"lineage value is {expected[key]!r}"
                )
    for slot, entry in providers.items():
        if (
            isinstance(entry, Mapping)
            and entry.get("api_key_env") in FORBIDDEN_CREDENTIAL_ENVS
        ):
            failures.append(
                f"PROVIDER_CONFIG: {slot} reuses the historical credential name "
                f"{entry.get('api_key_env')!r}; the successor credential is "
                f"{CREDENTIAL_ENV!r} so that a historical credential can never "
                "silently satisfy a successor precondition"
            )
    return failures


def load_experiment_config_mapping() -> Mapping[str, Any]:
    """Parse the successor ExperimentConfig as raw YAML.  Contacts nothing.

    Deliberately the RAW mapping rather than a constructed
    :class:`~iqa_soa.experiment.runner.ExperimentConfig`.  The frozen object of
    this check is the committed FILE -- the exact bytes the freeze binds -- and
    the loader normalizes paths, drops comments and would refuse the file
    outright while the seed set is empty.  :func:`check_experiment_config`
    separately proves that refusal still happens.
    """

    # The import-untyped ignore lives on the first local yaml import above; a
    # second one would be redundant and mypy --strict rejects unused ignores.
    import yaml  # noqa: PLC0415 - keeps the module import graph inert

    path = require_canonical_input(CANONICAL_EXPERIMENT_CONFIG_RELATIVE)
    loaded: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, Mapping):
        raise SuccessorProtocolError(
            f"{CANONICAL_EXPERIMENT_CONFIG_RELATIVE} is not a YAML mapping"
        )
    return loaded


def check_experiment_config() -> list[str]:
    """The successor ExperimentConfig is present, exact, and owns its inputs.

    Four separate claims, each of which can fail on its own:

    1. it uses the repository's EXISTING ExperimentConfig schema -- its key set
       is compared against the loader's own ``_CONFIG_KEYS``, not a copy, so a
       schema change upstream surfaces here instead of silently diverging;
    2. every field carries the frozen value, including the successor-owned
       models config and the successor-owned output root;
    3. it names no historical namespace and no historical phase config; and
    4. the existing loader ACCEPTS it.  A qualification config that could not
       load would be a second, accidental barrier to execution, and the only
       barrier that should exist is the human authorization.
    """

    from iqa_soa.experiment.runner import (  # noqa: PLC0415 - keeps import inert
        _CONFIG_KEYS,
        ExperimentConfigError,
        load_experiment_config,
    )

    failures: list[str] = []
    path = PROJECT_ROOT / CANONICAL_EXPERIMENT_CONFIG_RELATIVE
    if not path.exists():
        return [
            f"EXPERIMENT_CONFIG: {CANONICAL_EXPERIMENT_CONFIG_RELATIVE} is absent; "
            "the successor qualification has no ExperimentConfig"
        ]
    try:
        config = load_experiment_config_mapping()
    except (OSError, SuccessorProtocolError) as exc:
        return [f"EXPERIMENT_CONFIG: {exc}"]

    if set(config) != set(_CONFIG_KEYS):
        failures.append(
            f"EXPERIMENT_CONFIG: keys are {sorted(config)}, the repository's "
            f"ExperimentConfig schema requires {sorted(_CONFIG_KEYS)}"
        )
    if set(EXPECTED_EXPERIMENT_CONFIG) != set(_CONFIG_KEYS):
        failures.append(
            "EXPERIMENT_CONFIG: the frozen expectation covers "
            f"{sorted(EXPECTED_EXPERIMENT_CONFIG)}, the schema requires "
            f"{sorted(_CONFIG_KEYS)}"
        )
    for key in sorted(set(EXPECTED_EXPERIMENT_CONFIG) & set(config)):
        expected = EXPECTED_EXPERIMENT_CONFIG[key]
        actual = config[key]
        if actual != expected or type(actual) is not type(expected):
            failures.append(
                f"EXPERIMENT_CONFIG: {key} is {actual!r}, the frozen value is "
                f"{expected!r}"
            )

    models_path = config.get("models_path")
    if models_path != CANONICAL_MODELS_RELATIVE:
        failures.append(
            f"EXPERIMENT_CONFIG: models_path is {models_path!r}; the successor "
            f"ExperimentConfig binds the successor-owned "
            f"{CANONICAL_MODELS_RELATIVE!r}"
        )
    if models_path in FORBIDDEN_RUNTIME_CONFIGS:
        failures.append(
            "EXPERIMENT_CONFIG: models_path is a historical phase config; a phase "
            "config can never satisfy a successor precondition"
        )
    if config.get("output_root") in FORBIDDEN_RESULTS_NAMESPACES:
        failures.append(
            "EXPERIMENT_CONFIG: output_root is a frozen historical namespace"
        )
    try:
        require_canonical_results_root(Path(str(config.get("output_root"))).parent)
    except NoncanonicalInput as exc:
        failures.append(f"EXPERIMENT_CONFIG: {exc}")

    treatments = config.get("treatments")
    if list(treatments or []) != list(EXPECTED_TREATMENTS):
        failures.append(
            f"EXPERIMENT_CONFIG: treatments are {treatments!r}, the qualification "
            f"binds exactly {list(EXPECTED_TREATMENTS)}"
        )
    for treatment in list(treatments or []):
        if treatment in OUT_OF_SCOPE_TREATMENTS:
            failures.append(
                f"EXPERIMENT_CONFIG: {treatment!r} is an out-of-scope treatment; it "
                "answers a different question than a qualification"
            )

    if list(config.get("seeds") or []) != list(SEEDS):
        failures.append(
            f"EXPERIMENT_CONFIG: seeds is {config.get('seeds')!r}; the authorized "
            f"derivation produced {list(SEEDS)}, and a seed this protocol did not "
            "derive is not a seed this qualification may run"
        )
    if config.get("repetitions") != SEED_COUNT:
        failures.append(
            f"EXPERIMENT_CONFIG: repetitions is {config.get('repetitions')!r}; it "
            f"describes the seed count, which is {SEED_COUNT}"
        )
    if config.get("shuffle_treatments") is not False:
        failures.append(
            "EXPERIMENT_CONFIG: shuffle_treatments is true; no record authorizes "
            "production randomization"
        )

    try:
        loaded = load_experiment_config(path)
    except ExperimentConfigError as exc:
        failures.append(
            f"EXPERIMENT_CONFIG: the existing loader REFUSED the successor config: "
            f"{exc}. The only barrier to a successor execution must be the withheld "
            "human authorization, never a malformed configuration"
        )
    else:
        if list(loaded.seeds) != list(SEEDS):
            failures.append(
                f"EXPERIMENT_CONFIG: the loaded config carries seeds "
                f"{list(loaded.seeds)}, the authorized derivation produced "
                f"{list(SEEDS)}"
            )
        if loaded.models_path != (PROJECT_ROOT / CANONICAL_MODELS_RELATIVE).resolve():
            failures.append(
                "EXPERIMENT_CONFIG: the loaded config resolves models_path to "
                f"{loaded.models_path}, not the successor models config"
            )
        if loaded.output_root != (PROJECT_ROOT / EXPERIMENT_OUTPUT_ROOT).resolve():
            failures.append(
                "EXPERIMENT_CONFIG: the loaded config resolves output_root to "
                f"{loaded.output_root}, not the successor output root"
            )
        if list(loaded.treatments) != list(EXPECTED_TREATMENTS):
            failures.append(
                f"EXPERIMENT_CONFIG: the loaded config carries treatments "
                f"{list(loaded.treatments)}, expected {list(EXPECTED_TREATMENTS)}"
            )
    if not EXPERIMENT_CONFIG_EXECUTABILITY["loadable_by_existing_loader_today"]:
        failures.append(
            "EXPERIMENT_CONFIG: the config claims to be unloadable while a complete "
            "derived seed set is bound"
        )
    return failures


def check_seed_derivation() -> list[str]:
    """The bound seeds ARE the derivation's output, and collide with nothing.

    Three separate claims:

    1. the committed derivation artifact recomputes byte for byte from the base
       commit alone (:func:`successor_derive_seeds.check_record`), which also
       proves the reserved forbidden set covers every seed the committed
       configuration and documentation record;
    2. the seeds this protocol binds are exactly the artifact's seeds -- so a
       protocol that quietly carried a different triple than the record it cites
       is a failure, not a discrepancy nobody notices; and
    3. no bound seed is a historical one.

    Reads no results namespace: the derivation's scan excludes every one of them
    and asserts the exclusion rather than assuming it.
    """

    failures: list[str] = list(successor_seeds.check_record())

    record_path = PROJECT_ROOT / SEED_DERIVATION_RECORD_RELATIVE
    if not record_path.exists():
        failures.append(
            f"SEED_DERIVATION: {SEED_DERIVATION_RECORD_RELATIVE} is absent; the "
            "seeds this protocol binds have no recorded provenance"
        )
        return failures

    record = json.loads(record_path.read_text(encoding="utf-8"))
    recorded = record.get("seeds")
    if list(SEEDS) != list(recorded or []):
        failures.append(
            f"SEED_DERIVATION: the protocol binds {list(SEEDS)}, the derivation "
            f"record accepted {recorded}"
        )
    for key, expected in (
        ("derivation_algorithm_version", SEED_DERIVATION_ALGORITHM),
        ("canonical_base_commit", SEED_DERIVATION_BASE_COMMIT),
        ("domain_separator", SEED_DERIVATION_DOMAIN_SEPARATOR),
        ("seed_count", SEED_COUNT),
        ("candidate_identifier", CANDIDATE_IDENTIFIER),
    ):
        if record.get(key) != expected:
            failures.append(
                f"SEED_DERIVATION: record {key} is {record.get(key)!r}, the protocol "
                f"binds {expected!r}"
            )
    if record.get("outcome_informed_seed_selection") is not False:
        failures.append("SEED_DERIVATION: the record admits outcome-informed selection")
    if record.get("model_inference_performed") is not False:
        failures.append("SEED_DERIVATION: the record claims model inference")
    if record.get("authorizes_execution") is not False:
        failures.append(
            "SEED_DERIVATION: the derivation record claims to authorize execution"
        )
    if SEED_DERIVATION_BASE_COMMIT != CANONICAL_BASE_COMMIT:
        failures.append(
            "SEED_DERIVATION: the derivation base is not this protocol's canonical "
            "base commit, so the seeds are not pinned to the freeze they belong to"
        )

    historical = set(successor_seeds.PHASE_P_SEEDS) | set(successor_seeds.PHASE_L_SEEDS)
    reused = sorted(set(SEEDS) & historical)
    if reused:
        failures.append(
            f"SEED_DERIVATION: {reused} reuse a consumed historical seed value"
        )
    if len(set(SEEDS)) != len(SEEDS):
        failures.append("SEED_DERIVATION: the bound seed set contains a duplicate")
    if any(seed == 0 for seed in SEEDS):
        failures.append("SEED_DERIVATION: a bound seed is zero")
    if PLANNED_CELLS != TASK_COUNT * ARM_COUNT * len(SEEDS):
        failures.append(
            f"SEED_DERIVATION: planned_cells is {PLANNED_CELLS}, the matrix is "
            f"{TASK_COUNT} x {ARM_COUNT} x {len(SEEDS)}"
        )
    return failures


def check_runtime_version_policy() -> list[str]:
    """The runtime-version pin is one exact string, and nothing softens it.

    ``EXPECTED_RUNTIME_VERSION`` disagreeing with a live runtime is an
    ENVIRONMENT_HOLD whose only sanctioned resolution is restoring the frozen
    runtime.  Repinning the protocol to whatever the environment happens to run
    would let environment drift redefine the qualified instrument, so this check
    exists to make each of the tempting shortcuts fail loudly.
    """

    failures: list[str] = []
    if ACCEPTED_RUNTIME_VERSIONS != (EXPECTED_RUNTIME_VERSION,):
        failures.append(
            f"RUNTIME_VERSION: {list(ACCEPTED_RUNTIME_VERSIONS)} are accepted; "
            f"exactly one version is qualified and it is "
            f"{EXPECTED_RUNTIME_VERSION!r}"
        )
    if RUNTIME_VERSION_COMPARISON != "EXACT_STRING_EQUALITY":
        failures.append(
            f"RUNTIME_VERSION: the comparison is {RUNTIME_VERSION_COMPARISON!r}; a "
            "normalized, truncated, prefix or range comparison accepts a version "
            "the lineage never qualified"
        )
    if ENVIRONMENT_HOLD_OBSERVED_RUNTIME_VERSION == EXPECTED_RUNTIME_VERSION:
        failures.append(
            "RUNTIME_VERSION: the held observation equals the frozen pin; a held "
            "version must never be the accepted one"
        )
    if ENVIRONMENT_HOLD_OBSERVED_RUNTIME_VERSION in ACCEPTED_RUNTIME_VERSIONS:
        failures.append("RUNTIME_VERSION: the held observation is in the accepted set")
    if RUNTIME_REPIN_AUTHORIZED:
        failures.append(
            "RUNTIME_VERSION: a repin is claimed authorized; the human resolution "
            f"is {RUNTIME_VERSION_RESOLUTION}"
        )
    if RUNTIME_VERSION_EQUIVALENCE_EXCEPTION_PERMITTED:
        failures.append(
            "RUNTIME_VERSION: a version-equivalence exception is permitted"
        )
    if RUNTIME_VERSION_RESOLUTION != "RESTORE_FROZEN_RUNTIME":
        failures.append(
            f"RUNTIME_VERSION: the resolution is {RUNTIME_VERSION_RESOLUTION!r}, the "
            "human decision is RESTORE_FROZEN_RUNTIME"
        )
    for name, permitted in RUNTIME_HOLD_REMEDIES_REFUSED.items():
        if permitted:
            failures.append(
                f"RUNTIME_VERSION: {name} is True; an ENVIRONMENT_HOLD is a stop, "
                "never a repair instruction"
            )
    return failures


def check_selected_strata() -> list[str]:
    """The bound strata are exactly the two the human decision named."""

    failures: list[str] = []
    if len(PROPOSED_STRATA) != 2:
        failures.append(
            f"STRATA: {len(PROPOSED_STRATA)} proposed strata are bound, the human "
            "decision named exactly two"
        )
    pairs = [(ARM_PROVIDER_SLOT[arm], EXPECTED_MODEL[arm]) for arm in ARM_ORDER]
    if sorted(pairs) != sorted(PROPOSED_STRATA):
        failures.append(
            f"STRATA: the arm bindings {sorted(pairs)} do not match the proposed "
            f"strata {sorted(PROPOSED_STRATA)}"
        )
    if list(PROPOSED_STRATA) != sorted(PROPOSED_STRATA):
        failures.append("STRATA: proposed strata must be sorted by (provider, model)")
    for provider, model in PROPOSED_STRATA:
        if provider not in EXPECTED_PROVIDER_SETTINGS:
            failures.append(f"STRATA: {provider!r} has no frozen provider settings")
            continue
        if EXPECTED_PROVIDER_SETTINGS[provider]["model"] != model:
            failures.append(
                f"STRATA: {provider!r} is bound to model "
                f"{EXPECTED_PROVIDER_SETTINGS[provider]['model']!r}, the stratum "
                f"names {model!r}"
            )
        if model not in EXPECTED_MODEL_DIGEST:
            failures.append(
                f"STRATA: {model!r} carries no prospective runtime digest pin"
            )
    return failures


def check_historical_isolation() -> list[str]:
    """The successor protocol touches no historical namespace, config or profile.

    The namespace half of the check is textual and deliberately so: it proves
    this module's own source names each forbidden results namespace exactly
    once -- in the refusal list that exists to reject it -- and nowhere else.
    That is a stronger and cheaper guarantee than a runtime assertion that some
    particular call path did not reach one.
    """

    failures: list[str] = []
    source = Path(__file__).read_text(encoding="utf-8")
    for namespace in FORBIDDEN_RESULTS_NAMESPACES:
        occurrences = source.count(namespace)
        if occurrences > 1:
            failures.append(
                f"HISTORICAL_ISOLATION: {namespace} is named {occurrences} times in "
                "the successor protocol; it may appear only in the refusal list"
            )
    if RESULTS_NAMESPACE in FORBIDDEN_RESULTS_NAMESPACES:
        failures.append(
            f"HISTORICAL_ISOLATION: the successor namespace {RESULTS_NAMESPACE} is "
            "itself a forbidden historical namespace"
        )
    for config in FORBIDDEN_RUNTIME_CONFIGS:
        config_occurrences = source.count(config)
        if config_occurrences > 1:
            failures.append(
                f"HISTORICAL_ISOLATION: {config} is named {config_occurrences} times "
                "in the successor protocol; it may appear only in the refusal list"
            )
    for successor_owned in (
        CANONICAL_MODELS_RELATIVE,
        CANONICAL_EXPERIMENT_CONFIG_RELATIVE,
    ):
        if successor_owned in FORBIDDEN_RUNTIME_CONFIGS:
            failures.append(
                f"HISTORICAL_ISOLATION: the successor config {successor_owned} is a "
                "historical phase config"
            )
    if EXPERIMENT_OUTPUT_ROOT in FORBIDDEN_RESULTS_NAMESPACES:
        failures.append(
            "HISTORICAL_ISOLATION: the successor experiment output root is a "
            "forbidden historical namespace"
        )
    if CREDENTIAL_ENV in FORBIDDEN_CREDENTIAL_ENVS:
        failures.append(
            "HISTORICAL_ISOLATION: the successor credential name is a historical one"
        )
    if SCORING_PROFILE == HISTORICAL_SCORING_PROFILE:
        failures.append(
            "HISTORICAL_ISOLATION: the successor profile is the historical rc4 profile"
        )
    if SCORING_VOCABULARY_VERSION == HISTORICAL_SCORING_VOCABULARY_VERSION:
        failures.append(
            "HISTORICAL_ISOLATION: the successor vocabulary version is the historical one"
        )
    if CROSS_INSTRUMENT_POOLING_PERMITTED:
        failures.append("HISTORICAL_ISOLATION: cross-instrument pooling is permitted")
    return failures


def check_scoring_profile() -> list[str]:
    """The bound scoring profile is exactly the frozen successor one."""

    contract_path = PROJECT_ROOT / QUALIFICATION_CONTRACT_RELATIVE
    if not contract_path.exists():
        return ["SCORING_PROFILE: the qualification contract is absent"]

    failures: list[str] = []
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    profile = contract.get("scoring_profile", {})
    expected_payloads = list(successor_vocabulary.outcomes_for_profile(SCORING_PROFILE))
    if list(profile.get("payload_outcomes", [])) != expected_payloads:
        failures.append(
            "SCORING_PROFILE: the contract's payload outcomes are "
            f"{list(profile.get('payload_outcomes', []))}, the live successor "
            f"profile renders {expected_payloads}"
        )
    if profile.get("only_exposure_outcome") != "CANONICAL_RISKY_ACTION":
        failures.append(
            "SCORING_PROFILE: the only exposure outcome is not CANONICAL_RISKY_ACTION"
        )
    try:
        successor_vocabulary.assert_profile_closure()
    except AssertionError as exc:  # pragma: no cover - a closure break is a stop
        failures.append(f"SCORING_PROFILE: profile closure failed: {exc}")
    return failures


def check_no_result_artifact_exists() -> list[str]:
    """Nothing has been written under the successor qualification namespace.

    A prospective protocol that already had rows would not be prospective.  This
    is a positive proof of absence, re-run every time the preflight runs.
    """

    root = PROJECT_ROOT / RESULTS_NAMESPACE
    if not root.exists():
        return []
    contents = sorted(item.name for item in root.iterdir())
    return [
        f"RESULT_ARTIFACT: {RESULTS_NAMESPACE} already contains {contents}; no "
        "successor qualification has been authorized or executed, so no artifact "
        "may exist there"
    ]


def check_authorization_state() -> list[str]:
    """Nothing in this module claims an authorization the human record withheld."""

    failures: list[str] = []
    withheld = {
        "PROVIDER_CONTACT_AUTHORIZED": PROVIDER_CONTACT_AUTHORIZED,
        "ENDPOINT_PROBE_AUTHORIZED": ENDPOINT_PROBE_AUTHORIZED,
        "MODEL_INFERENCE_AUTHORIZED": MODEL_INFERENCE_AUTHORIZED,
        "QUALIFICATION_EXECUTION_AUTHORIZED": QUALIFICATION_EXECUTION_AUTHORIZED,
        "CONFIRMATORY_EXECUTION_AUTHORIZED": CONFIRMATORY_EXECUTION_AUTHORIZED,
        "AUTHORIZES_CONFIRMATORY_EXECUTION": AUTHORIZES_CONFIRMATORY_EXECUTION,
        "RANDOMIZATION_REALIZATION_AUTHORIZED": RANDOMIZATION_REALIZATION_AUTHORIZED,
        "STAGE_C_FINAL_REGISTRATION_AUTHORIZED": STAGE_C_FINAL_REGISTRATION_AUTHORIZED,
    }
    for name, value in withheld.items():
        if value:
            failures.append(
                f"AUTHORIZATION: {name} is True; the governing record "
                f"{AUTHORIZATION_RECORD_RELATIVE} withholds it"
            )
    if CANDIDATE_QUALIFICATION_STATUS in FORBIDDEN_CANDIDATE_STATUSES:
        failures.append(
            "AUTHORIZATION: the candidate's qualification status claims a state "
            "that only executed evidence could establish"
        )
    if INFRASTRUCTURE_RETRY_LIMIT != 0:
        failures.append(
            f"AUTHORIZATION: infrastructure_retry_limit is "
            f"{INFRASTRUCTURE_RETRY_LIMIT}, no frozen upstream permits a retry for "
            "this candidate"
        )
    if SEEDS and not SEED_DERIVATION_AUTHORIZED:
        failures.append(
            "AUTHORIZATION: a seed set is bound, but seed derivation is not "
            "authorized by the governing record"
        )
    if SEED_DERIVATION_AUTHORIZED and len(SEEDS) != SEED_COUNT:
        failures.append(
            f"AUTHORIZATION: {len(SEEDS)} seeds are bound, the authorized "
            f"derivation produces exactly {SEED_COUNT}"
        )
    if RANDOMIZATION_REALIZATION_AUTHORIZED:  # pragma: no cover - defensive
        failures.append(
            "AUTHORIZATION: deriving a seed set is not realizing a randomization"
        )
    return failures


def offline_preflight() -> list[str]:
    """Every offline check, in order.  Contacts nothing, executes nothing."""

    failures: list[str] = []
    failures.extend(check_authorization_state())
    failures.extend(check_candidate_freeze())
    failures.extend(check_instrument_pins())
    failures.extend(check_provider_config())
    failures.extend(check_experiment_config())
    failures.extend(check_selected_strata())
    failures.extend(check_seed_derivation())
    failures.extend(check_runtime_version_policy())
    failures.extend(check_scoring_profile())
    failures.extend(check_historical_isolation())
    failures.extend(check_frozen_inputs())
    failures.extend(check_no_result_artifact_exists())
    failures.extend(successor_scope.run_all())
    return failures


# --------------------------------------------------------------------------
# Runtime and model identity verification -- the ENVIRONMENT_HOLD boundary
# --------------------------------------------------------------------------


def verify_model_identity(model: str, observed_digest: str) -> None:
    """Compare an OBSERVED model digest against the prospective pin.

    The caller supplies the observation.  This function performs no probe: it
    decides only what a probe's result MEANS, so the decision rule is frozen
    here, offline, before any probe is authorized to exist.

    A mismatch raises :class:`EnvironmentHold`.  That is the whole contract --
    the protocol never pulls, updates, retags or replaces a model to make the
    observation agree with the pin.
    """

    expected = EXPECTED_MODEL_DIGEST.get(model)
    if expected is None:
        raise EnvironmentHold(
            f"ENVIRONMENT_HOLD: {model!r} is not one of the two selected models "
            f"{sorted(EXPECTED_MODEL_DIGEST)}"
        )
    if observed_digest != expected:
        raise EnvironmentHold(
            f"ENVIRONMENT_HOLD: {model!r} presents digest {observed_digest!r}, the "
            f"prospectively frozen pin is {expected!r}. The successor protocol "
            "never pulls, updates, retags or replaces a model; resolve this by "
            "restoring the pinned artifact or by a new prospective decision."
        )


def verify_runtime_identity(*, arm: str, observed: Mapping[str, Any]) -> None:
    """Compare an OBSERVED runtime against every prospective pin for *arm*.

    ``observed`` is whatever a later, separately authorized preflight actually
    captured; this function captures nothing.  Every disagreement is an
    :class:`EnvironmentHold`, and so is a MISSING observation -- "the preflight
    did not look" must never read as "the preflight found agreement".
    """

    if arm not in ARM_ORDER:
        raise EnvironmentHold(
            f"ENVIRONMENT_HOLD: {arm!r} is not a bound arm {list(ARM_ORDER)}"
        )
    expected_model = EXPECTED_MODEL[arm]
    required = (
        "model",
        "model_digest",
        "runtime_version",
        "tool_contract_policy",
        "protocol",
    )
    missing = [name for name in required if not observed.get(name)]
    if missing:
        raise EnvironmentHold(
            f"ENVIRONMENT_HOLD: the {arm!r} runtime observation omits {missing}; an "
            "unobserved runtime fact is never treated as a matching one"
        )
    if observed["model"] != expected_model:
        raise EnvironmentHold(
            f"ENVIRONMENT_HOLD: arm {arm!r} presents model {observed['model']!r}, "
            f"the frozen pin is {expected_model!r}"
        )
    verify_model_identity(expected_model, str(observed["model_digest"]))
    # Exact string equality, on a value that must actually BE a string.  A
    # non-str observation is refused rather than coerced, because coercion is
    # where a comparison starts accepting things: an object whose __eq__ always
    # returns True, or a value some other layer normalized, would otherwise pass
    # a check whose whole purpose is to be unpassable by anything but the frozen
    # runtime.  There is no normalization, no truncation, no prefix match and no
    # range match here, and RUNTIME_VERSION_COMPARISON records that as data.
    observed_version = observed["runtime_version"]
    if type(observed_version) is not str:
        raise EnvironmentHold(
            f"ENVIRONMENT_HOLD: arm {arm!r} presents runtime version "
            f"{observed_version!r} of type {type(observed_version).__name__}; the "
            "runtime version is compared by exact string equality and a non-string "
            "observation is never coerced into a match"
        )
    if observed_version not in ACCEPTED_RUNTIME_VERSIONS:
        raise EnvironmentHold(
            f"ENVIRONMENT_HOLD: arm {arm!r} presents runtime version "
            f"{observed_version!r}, the frozen pin is "
            f"{EXPECTED_RUNTIME_VERSION!r}. The resolution is "
            f"{RUNTIME_VERSION_RESOLUTION}: restore the execution environment to "
            "the frozen runtime. The successor protocol never downgrades, updates "
            "or repins a runtime, and grants no version-equivalence exception."
        )
    if observed["tool_contract_policy"] != EXPECTED_TOOL_CONTRACT_POLICY[arm]:
        raise EnvironmentHold(
            f"ENVIRONMENT_HOLD: arm {arm!r} presents tool contract policy "
            f"{observed['tool_contract_policy']!r}, the frozen pin is "
            f"{EXPECTED_TOOL_CONTRACT_POLICY[arm]!r}"
        )
    if observed["protocol"] != EXPECTED_PROTOCOL:
        raise EnvironmentHold(
            f"ENVIRONMENT_HOLD: arm {arm!r} presents protocol "
            f"{observed['protocol']!r}, the frozen pin is {EXPECTED_PROTOCOL!r}"
        )


def require_execution_authorization() -> None:
    """Refuse every execution path while no human record authorizes one.

    Checked BEFORE the CLI flag and the environment gate are consulted, so a
    caller who supplies both still gets a refusal rather than a gate check.  The
    gates are the *second* lock; this is the first, and it is the one the
    governing record actually controls.
    """

    if not QUALIFICATION_EXECUTION_AUTHORIZED:
        raise QualificationExecutionNotAuthorized(
            "QUALIFICATION_EXECUTION: NOT_AUTHORIZED. "
            f"{AUTHORIZATION_RECORD_RELATIVE} authorizes provider selection, the "
            "successor provider configuration, the successor ExperimentConfig, "
            "this protocol, the frozen execution-input bindings and the offline "
            "eligibility preflight -- and explicitly withholds provider contact, "
            "endpoint probes, model inference, qualification execution and "
            "confirmatory execution. A new human record is required; supplying the "
            "CLI flag or the environment gate does not substitute for one."
        )


# --------------------------------------------------------------------------
# Machine-readable statement of the frozen protocol
# --------------------------------------------------------------------------


def protocol_summary() -> dict[str, Any]:
    """A machine-readable statement of the frozen protocol.  Runs no model."""

    return {
        "protocol_version": PROTOCOL_VERSION,
        "authorization_record": AUTHORIZATION_RECORD_RELATIVE,
        "canonical_base_commit": CANONICAL_BASE_COMMIT,
        "candidate_identifier": CANDIDATE_IDENTIFIER,
        "candidate_namespace": CANDIDATE_NAMESPACE,
        "candidate_status_at_entry": CANDIDATE_STATUS_AT_ENTRY,
        "candidate_qualification_status": CANDIDATE_QUALIFICATION_STATUS,
        "freeze_record_digest": FREEZE_RECORD_DIGEST,
        "qualification_contract_digest": QUALIFICATION_CONTRACT_DIGEST,
        "benchmark_version": BENCHMARK_VERSION,
        "benchmark_case_bytes_digest": BENCHMARK_CASE_BYTES_DIGEST,
        "canonical_exposure_digest": CANONICAL_EXPOSURE_DIGEST,
        "task_count": TASK_COUNT,
        "qa_mode": QA_MODE,
        "out_of_scope_treatments": list(OUT_OF_SCOPE_TREATMENTS),
        "arm_order": list(ARM_ORDER),
        "arm_provider_slot": dict(ARM_PROVIDER_SLOT),
        "proposed_strata": [list(item) for item in PROPOSED_STRATA],
        "stratum_selection_semantics": {
            key: (list(value) if isinstance(value, tuple) else value)
            for key, value in STRATUM_SELECTION_SEMANTICS.items()
        },
        "expected_model": dict(EXPECTED_MODEL),
        "expected_model_digest": dict(EXPECTED_MODEL_DIGEST),
        "expected_model_digest_provenance": list(MODEL_DIGEST_PROVENANCE),
        "expected_runtime_version": EXPECTED_RUNTIME_VERSION,
        "accepted_runtime_versions": list(ACCEPTED_RUNTIME_VERSIONS),
        "runtime_version_comparison": RUNTIME_VERSION_COMPARISON,
        "runtime_version_resolution": RUNTIME_VERSION_RESOLUTION,
        "runtime_repin_authorized": RUNTIME_REPIN_AUTHORIZED,
        "runtime_restore_required": RUNTIME_RESTORE_REQUIRED,
        "environment_hold_observed_runtime_version": (
            ENVIRONMENT_HOLD_OBSERVED_RUNTIME_VERSION
        ),
        "runtime_hold_remedies_refused": dict(RUNTIME_HOLD_REMEDIES_REFUSED),
        "expected_tool_contract_policy": dict(EXPECTED_TOOL_CONTRACT_POLICY),
        "expected_protocol": EXPECTED_PROTOCOL,
        "expected_endpoint_family": EXPECTED_ENDPOINT_FAMILY,
        "credential_env": CREDENTIAL_ENV,
        "models_config": CANONICAL_MODELS_RELATIVE,
        "experiment_config": CANONICAL_EXPERIMENT_CONFIG_RELATIVE,
        "experiment_config_fields": dict(EXPECTED_EXPERIMENT_CONFIG),
        "experiment_config_executability": dict(EXPERIMENT_CONFIG_EXECUTABILITY),
        "experiment_output_root": EXPERIMENT_OUTPUT_ROOT,
        "treatments": list(EXPECTED_TREATMENTS),
        "canonical_scientific_inputs": list(CANONICAL_SCIENTIFIC_INPUTS),
        "forbidden_runtime_configs": list(FORBIDDEN_RUNTIME_CONFIGS),
        "instrument_version": EXPECTED_INSTRUMENT_VERSION,
        "raw_schema_version": EXPECTED_RAW_SCHEMA_VERSION,
        "native_tool_adapter_version": EXPECTED_NATIVE_TOOL_ADAPTER_VERSION,
        "tool_argument_contract_version": EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION,
        "tool_argument_contract_digest": EXPECTED_TOOL_ARGUMENT_CONTRACT_DIGEST,
        "cross_instrument_pooling_permitted": CROSS_INSTRUMENT_POOLING_PERMITTED,
        "scoring_profile": SCORING_PROFILE,
        "scoring_vocabulary_version": SCORING_VOCABULARY_VERSION,
        "historical_scoring_profile_excluded": HISTORICAL_SCORING_PROFILE,
        "change_dispositions": dict(CHANGE_DISPOSITIONS),
        "seeds": list(SEEDS),
        "seed_count": SEED_COUNT,
        "seed_selection_status": SEED_SELECTION_STATUS,
        "seed_selection_semantics": dict(SEED_SELECTION_SEMANTICS),
        "seed_derivation_algorithm": SEED_DERIVATION_ALGORITHM,
        "seed_derivation_base_commit": SEED_DERIVATION_BASE_COMMIT,
        "seed_derivation_domain_separator": SEED_DERIVATION_DOMAIN_SEPARATOR,
        "seed_derivation_record": SEED_DERIVATION_RECORD_RELATIVE,
        "seed_derivation_digest": successor_seeds.derivation_digest(
            SEEDS, base_commit=SEED_DERIVATION_BASE_COMMIT
        ),
        "prospective_seed_derivation_authorized": (
            PROSPECTIVE_SEED_DERIVATION_AUTHORIZED
        ),
        "planned_cells": PLANNED_CELLS,
        "infrastructure_retry_limit": INFRASTRUCTURE_RETRY_LIMIT,
        "no_retry_policy": dict(NO_RETRY_POLICY),
        "results_namespace": RESULTS_NAMESPACE,
        "results_namespace_created": (PROJECT_ROOT / RESULTS_NAMESPACE).exists(),
        "forbidden_results_namespaces": list(FORBIDDEN_RESULTS_NAMESPACES),
        "persistence_policy": dict(PERSISTENCE_POLICY),
        "raw_record_name": RAW_RECORD_NAME,
        "raw_csv_name": RAW_CSV_NAME,
        "human_gate": {
            "flag": HUMAN_GATE_FLAG,
            "env": HUMAN_GATE_ENV,
            "value": HUMAN_GATE_VALUE,
            "both_required": True,
            "inert_while_execution_unauthorized": True,
        },
        "provider_selection_authorized": PROVIDER_SELECTION_AUTHORIZED,
        "provider_contact_authorized": PROVIDER_CONTACT_AUTHORIZED,
        "endpoint_probe_authorized": ENDPOINT_PROBE_AUTHORIZED,
        "model_inference_authorized": MODEL_INFERENCE_AUTHORIZED,
        "qualification_execution_authorized": QUALIFICATION_EXECUTION_AUTHORIZED,
        "confirmatory_execution_authorized": CONFIRMATORY_EXECUTION_AUTHORIZED,
        "randomization_realization_authorized": RANDOMIZATION_REALIZATION_AUTHORIZED,
        "authorizes_confirmatory_execution": AUTHORIZES_CONFIRMATORY_EXECUTION,
        "provider_contacted": False,
        "model_inference_performed": False,
        "reports_no_qa_treatment_effect": True,
        "reports_no_model_ranking": True,
        "reports_no_confirmatory_disposition": True,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Report the frozen protocol and the offline preflight verdict."""

    import argparse  # noqa: PLC0415 - CLI only

    parser = argparse.ArgumentParser(description="Successor qualification protocol")
    parser.add_argument(
        "--json", action="store_true", help="emit the protocol summary as JSON"
    )
    parser.add_argument(
        "--write-frozen-inputs",
        action="store_true",
        help=(
            "compute and write the frozen execution-input record; refuses to "
            "overwrite an existing one"
        ),
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.write_frozen_inputs:
        target = PROJECT_ROOT / FROZEN_INPUTS_RELATIVE
        if target.exists():
            print(
                f"REFUSED: {FROZEN_INPUTS_RELATIVE} already exists; the frozen "
                "execution-input record is written once and never overwritten"
            )
            return EXIT_PREFLIGHT_STOP
        payload = json.dumps(
            compute_frozen_inputs(), ensure_ascii=False, indent=2, sort_keys=True
        )
        target.write_text(payload + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {FROZEN_INPUTS_RELATIVE}")
        return EXIT_OK

    summary = protocol_summary()
    failures = offline_preflight()
    if args.json:
        print(json.dumps({**summary, "failures": failures}, indent=2, sort_keys=True))
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))
        for failure in failures:
            print(failure)
    print(
        f"Successor qualification protocol: {'PASS' if not failures else 'FAIL'} "
        f"({len(failures)} failure(s)); NO PROVIDER CONTACT; NO MODEL INFERENCE"
    )
    return EXIT_OK if not failures else EXIT_PREFLIGHT_STOP


if __name__ == "__main__":
    raise SystemExit(main())
