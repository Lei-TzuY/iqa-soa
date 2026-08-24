#!/usr/bin/env python3
"""Phase-P driver: the frozen 102-cell pilot-v7-rc4 QA-OFF qualification.

**THIS SCRIPT REFUSES TO RUN BY DEFAULT AND AUTHORIZES NOTHING.**

Real-model execution requires BOTH of:

* the command-line flag ``--execute-real-model``; and
* the environment variable ``IQA_SOA_PHASE_P_HUMAN_GATE=AUTHORIZED``, at exactly
  that case.

Neither condition alone is sufficient.  If either is absent the driver exits
non-zero having issued no provider request, no Ollama metadata query, no
inference, no output cell and no results directory.  Neither gate is set
anywhere in this repository, in any test, in any configuration file or in any CI
definition; opening them is a deliberate human act performed once, by a person,
after the Phase-P protocol has been independently reviewed.

THE GATE IS A PROPERTY OF THE EXECUTION PATH, NOT OF ONE CALLER (PHASE P-R2)
===========================================================================

Stating the rule in :func:`main` is not enforcing it.  Until P-R2 the
lower-level entry point defaulted ``probe`` to :func:`probe_ollama_metadata` and
``execute_cell`` to :func:`make_cell_executor`, so a Python caller that skipped
:func:`main` could reach the live runtime and the real frozen schedule having
proved neither human gate.  The refusal was documented, not machine-enforced,
and a documented refusal is not one.

The capability is now the gate.  :func:`grant_real_execution_authorization` is
the ONLY thing that mints a :class:`RealExecutionAuthorization`, it mints one
only after BOTH conditions are proved, and :func:`execute_authorized_real_run`
-- the ONLY function in this module that can select the real metadata probe or
construct the real runner-backed executor -- REQUIRES one and re-verifies it.
The capability cannot be forged by passing ``True``: its constructor demands a
module-private token object by identity AND re-evaluates the dual gate against
the environment it is handed.

    NO DUAL GATE -> NO CAPABILITY
    NO CAPABILITY -> NO REAL METADATA PROBE, NO REAL PROVIDER, NO INFERENCE

The offline regression suite drives everything beyond the gate through
:func:`execute_offline_bound_run`, which is a DIFFERENT function: it requires an
injected probe and an injected executor, has no defaults to fall back to,
refuses the real probe and the real executor by identity, and refuses to write
the official ``results/phaseP-rc4-qualification`` namespace at all.  The two
paths are disjoint by construction rather than by convention.

Phase P is a BENCHMARK QUALIFICATION, not an experiment.  Its only question is
whether pilot-v7-rc4's intended safe paths, challenge routes, multi-step causal
prerequisites, resource modality, benign controls, deliberate negative control
and fault opportunity are actually REACHABLE under the two qualified local
real-model providers with QA OFF.  It estimates no QA effectiveness, runs no FULL
arm, computes no treatment effect and ranks no model.

WHAT THIS DRIVER DOES, IN ORDER, AND NEVER OUT OF ORDER
=======================================================

0. ``--verify-frozen-inputs``, if given, runs the complete OFFLINE protocol
   validation and exits.  It contacts nothing, creates nothing and needs no gate.
1. **Human gate.**  Both conditions, or nothing whatsoever happens.  This is
   evaluated before the frozen-input binding, before the offline preflight,
   before any configuration is loaded, before any provider object exists, before
   any metadata probe and before any directory is created.  Passing it MINTS a
   :class:`RealExecutionAuthorization`; the real-model path refuses to start
   without one, so the gate is enforced by the capability rather than by this
   ordering alone.
1b. **Frozen scientific input binding** (Phase P-R1).  ``--config``,
   ``--manifest`` and ``--output-root`` are ASSERTIONS, not choices.  Each is
   proven to be the frozen Phase-P artifact by resolved canonical PATH equality
   AND by the SHA-256 that ``docs/phaseP_frozen_execution_inputs.json``
   accepted, and ``--output-root`` is required to be the frozen
   ``results/phaseP-rc4-qualification`` namespace.  The offline preflight proves
   the canonical TREE is intact; it says nothing about which files a given
   invocation was pointed at, so a structurally valid 17-case pilot-v7-rc4
   look-alike, a Phase-P-shaped config with a changed runtime setting, or an
   arbitrary output namespace would otherwise have executed under canonical
   provenance.  Any of them is now an IMMEDIATE_STOP with zero metadata probes,
   zero cells and no results namespace.  This CLI has NO noncanonical
   Phase-P execution mode.
2. **Offline preflight** (``scripts/phaseP_protocol.py``).  The frozen plan
   matches its sidecar; every frozen scientific execution input matches its
   recorded SHA-256; the instrument is version ``4`` with raw schema ``5``,
   ``tool-arguments-1`` and ``native-tools-adapter-3``; the ``src/iqa_soa`` tree
   equals the approved Phase-O revision digest and every individually recorded
   Phase-O file matches its own hash; the approved revision CHAIN verifies link
   by link; the historical bound-input audit and the Phase-O supersession both
   pass; the rc4 benchmark bytes are exactly what its freeze record pins; the
   seed triple is exactly what the Phase-P derivation recorded and reuses no
   historical seed; and the model/runtime pins are unanimous in committed
   evidence.  Any mismatch is an IMMEDIATE_STOP before a provider is contacted.
3. **Configuration assertion.**  Each arm's declared model, tool-contract policy,
   protocol, adapter version, argument-contract version and credential
   environment are read from the provider slot and required to equal the frozen
   pins.  This is a local read; it contacts nothing.
4. **Output-namespace precondition.**  A pre-existing raw record is a
   ``PROTOCOL_DEVIATION``: Phase-P evidence is append-only and a run is never
   resumed, repaired or replaced.  Checked before the runtime is probed.
5. **Metadata-only preflight.**  BOTH arms' live model presence, model digest and
   runtime version are probed, and BOTH are required to equal the frozen pins,
   before EITHER arm executes a cell.  A difference is an ``ENVIRONMENT_HOLD``
   with zero cells executed.  This driver never pulls, downloads, updates,
   retags, repairs, substitutes or replaces a model.
6. **The frozen schedule.**  ``phaseP_protocol.StopController`` OWNS advancement:
   the only way to obtain the next cell is its iterator, which terminates the
   moment a stop is armed, so an immediate-stop condition cannot be ignored and
   arm 2 cannot start after arm 1 stopped.  One cell is one invocation of the
   canonical ``ExperimentRunner`` on exactly one (task, seed) pair, so there is
   no parallel loop to bypass.

WHAT THIS DRIVER DOES NOT DO
============================

* It does not retry.  ``infrastructure_retry_limit`` is fixed at ``0`` and the
  runner independently refuses any other value.  A provider or model failure is a
  recorded outcome, never a reason to rerun.
* It does not replace, repair, resume or deduplicate a cell.  Raw evidence is
  append-only, a cell invalidation never deletes its raw trace, and an invalid
  row is never removed.
* It does not manufacture fault provenance or failure events.  The schema-4
  ``observed_fault_*`` columns and the schema-5 ordered ``failure_events`` list
  arise inside ``ExperimentRunner`` from the live ``GatewayOutcome`` sequence.
  This driver TRANSPORTS the row it is given; it reads no benchmark declaration
  and writes no observation.
* It stamps exactly TWO identity fields, ``model_digest`` and ``run_key``, from
  the frozen cell, because the canonical runner emits neither and both are frozen
  inputs rather than runtime observations.  Every other bound identity field --
  ``task_id``, ``seed``, ``model``, ``qa_mode``, ``benchmark_manifest_sha256`` --
  comes from the runner, so the binding check is a real check and not a tautology.
  Three further fields are TRANSPORTED from the cell's own persisted
  ``manifest.json`` -- ``raw_schema_version``, ``tool_argument_contract_version``
  and ``tool_argument_contract_digest`` -- because they are observations the
  runner records there rather than on the row.  Copying a constant instead would
  make the Phase-N disclosure precondition a tautology.
* It computes no verdict.  Scoring is the analyzer's job and is driven by
  ``benchmark/pilot-v7-rc4/qualification-contract.json`` and
  ``scripts/rc4_scoring_vocabulary.py``.

NO PART OF PHASE P ITSELF RUNS THIS DRIVER AGAINST A REAL PROVIDER.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import functools
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _root in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import phaseP_protocol as protocol  # noqa: E402
import qualification_harness_v2 as harness  # noqa: E402
import yaml  # type: ignore[import-untyped]  # noqa: E402
from iqa_soa.agent.providers import SANDBOX_TOOL_NAMES  # noqa: E402
from iqa_soa.experiment.runner import (  # noqa: E402
    ExperimentConfigError,
    ExperimentRunner,
    load_experiment_config,
    load_provider,
)
from iqa_soa.instrument import NATIVE_TOOL_ADAPTER_VERSION  # noqa: E402
from iqa_soa.tools.argument_schema import (  # noqa: E402
    TOOL_ARGUMENT_CONTRACT_VERSION,
    contract_digest,
)


@dataclass(frozen=True, slots=True)
class RuntimeMetadata:
    """What a metadata-only probe observed about one model.

    ``model_present`` is carried separately from ``model_digest`` so that "the
    runtime does not have this model" and "the runtime has it under a different
    digest" are two distinguishable environment holds rather than one.
    """

    runtime_version: str
    model_present: bool
    model_digest: str


#: ``(model) -> RuntimeMetadata``.  The shape :func:`metadata_preflight`
#: consumes.  Note that :func:`probe_ollama_metadata` DELIBERATELY does not have
#: this shape: it additionally requires a keyword-only
#: :class:`RealExecutionAuthorization`, so it cannot be handed anywhere a bare
#: ``MetadataProbe`` is expected and silently work (Phase P-R2).  The real path
#: binds the capability into it before passing it on.
MetadataProbe = Callable[[str], RuntimeMetadata]

#: ``(cell) -> raw row``.  Injected in tests for the same reason.  The
#: runner-backed executor :func:`make_cell_executor` builds is the only one that
#: spends inference, and it is reachable only through
#: :func:`execute_authorized_real_run`.
CellExecutor = Callable[[Any], Mapping[str, Any]]

#: ``(config_path, manifest_path, output_root) -> CellExecutor``.  The core run
#: loop is handed a FACTORY rather than an optional executor, so there is no
#: ``None`` for it to resolve into a real-model default (Phase P-R2).
CellExecutorFactory = Callable[[Path, Path, Path], CellExecutor]

#: The attribute every executor from :func:`make_cell_executor` carries.  The
#: offline seam refuses a callable that has it, so "the real executor" is a
#: checkable property of the object rather than a claim about the caller.
REAL_EXECUTOR_MARKER = "phase_p_real_model_executor"


# --------------------------------------------------------------------------
# 1. The machine-enforced human execution gate
# --------------------------------------------------------------------------


def human_gate_refusal(*, execute_flag: bool, env: Mapping[str, str]) -> str | None:
    """Return the refusal reason, or ``None`` when BOTH gates are open.

    Both conditions are evaluated independently and both are reported, so a
    partial gate can never be mistaken for a near miss that "almost" authorized a
    run.  The environment comparison is EXACT and case-sensitive: ``authorized``,
    ``AUTHORIZED `` and ``Authorized`` are all refusals.
    """

    reasons: list[str] = []
    if not execute_flag:
        reasons.append(f"the {protocol.HUMAN_GATE_FLAG} command-line flag was not given")
    actual = env.get(protocol.HUMAN_GATE_ENV)
    if actual != protocol.HUMAN_GATE_VALUE:
        reasons.append(
            f"{protocol.HUMAN_GATE_ENV} is {actual!r}, it must be exactly "
            f"{protocol.HUMAN_GATE_VALUE!r}"
        )
    if not reasons:
        return None
    return (
        "EXECUTION REFUSED: Phase-P real-model execution requires BOTH the "
        f"{protocol.HUMAN_GATE_FLAG} flag AND "
        f"{protocol.HUMAN_GATE_ENV}={protocol.HUMAN_GATE_VALUE}. "
        + "; ".join(reasons)
        + ". No provider was contacted, no metadata was probed, no inference was "
        "performed, no cell was produced and no results directory was created."
    )


# --------------------------------------------------------------------------
# 2. The authorization CAPABILITY every real primitive requires (Phase P-R2)
# --------------------------------------------------------------------------


class UnauthorizedRealExecution(protocol.ProtocolError):
    """A real-runtime primitive was entered without both human gates.

    A subclass of :class:`phaseP_protocol.ProtocolError`, so every caller that
    already refuses a protocol error refuses this too.  It is RAISED rather than
    turned into an exit code: an exit code is a result, and a caller that
    reached a real primitive unauthorized has not produced a result.
    """


#: The ONE object that identifies a genuine grant.  Module-private and compared
#: BY IDENTITY.  It is a necessary condition and nowhere near a sufficient one:
#: holding it still mints nothing unless :func:`_process_gate_refusal` passes.
_GRANT_TOKEN: object = object()


def _process_gate_refusal() -> str | None:
    """Evaluate the dual gate against THIS PROCESS'S OWN STATE.  Nothing is passed in.

    PHASE P-R2 COMPLETION.  This is the difference between a gate and a
    parameter.  The previous version of the mint took ``execute_flag`` and
    ``env`` FROM ITS CALLER, which meant its effective interface was "pass
    ``True`` and a two-key dict" -- a capability any Python caller could
    manufacture at the call site, which is precisely what a capability must not
    be.

    Both halves are therefore read from the process and cannot be supplied:

    * the flag is looked for on ``sys.argv`` -- the command line THIS PROCESS was
      actually started with, not a list handed to :func:`main`; and
    * the environment variable is read from ``os.environ`` -- the environment
      THIS PROCESS actually has, not a mapping handed to anything.

    A caller who wants to satisfy this has to genuinely put
    ``--execute-real-model`` on the process command line and genuinely export
    ``IQA_SOA_PHASE_P_HUMAN_GATE=AUTHORIZED`` into the process environment.
    Those two acts ARE the dual human gate; performing them is not a bypass of
    it, it is the thing the gate asks for.
    """

    return human_gate_refusal(
        execute_flag=protocol.HUMAN_GATE_FLAG in sys.argv[1:],
        env=os.environ,
    )


class RealExecutionAuthorization:
    """Machine-verified proof that BOTH Phase-P human gates are open RIGHT NOW.

    PHASE P-R2.  This is a CAPABILITY, and every Phase-P primitive that can
    contact the live runtime, construct a real provider, or invoke a real cell
    executor demands one and VALIDATES it -- not merely the two entry points.

    It carries no state at all.  There is nothing in it for a caller to set,
    nothing to copy out of one and into another, and nothing that could go stale
    into something permissive: :meth:`verify` re-evaluates
    :func:`_process_gate_refusal` every single time it is called, so a grant
    minted while both gates were open stops validating the moment either closes.

    Two independent properties make it unforgeable at the call site:

    * the constructor demands :data:`_GRANT_TOKEN` **by identity**, so passing
      ``True``, ``None``, ``"AUTHORIZED"`` or a fresh ``object()`` raises; and
    * the constructor evaluates the dual gate against PROCESS state, which a
      caller cannot pass in, so even holding the token mints nothing in a
      process whose command line and environment do not carry both halves.
    """

    __slots__ = ()

    def __init__(self, token: object) -> None:
        if token is not _GRANT_TOKEN:
            raise UnauthorizedRealExecution(
                "EXECUTION REFUSED: a RealExecutionAuthorization is minted only by "
                "grant_real_execution_authorization(), and only in a process whose "
                "own command line and environment carry BOTH Phase-P human gates. "
                "It is a capability, not a flag: no boolean, no string, no mapping "
                "and no hand-built stand-in is one."
            )
        refusal = _process_gate_refusal()
        if refusal is not None:
            raise UnauthorizedRealExecution(refusal)

    def verify(self) -> None:
        """Re-prove the grant against process state.  Called at EVERY use."""

        refusal = _process_gate_refusal()
        if refusal is not None:
            raise UnauthorizedRealExecution(refusal)

    def __repr__(self) -> str:
        return "RealExecutionAuthorization(<both Phase-P human gates proved open>)"


def grant_real_execution_authorization() -> RealExecutionAuthorization:
    """Mint the capability, or raise.  IT TAKES NO ARGUMENTS.

    There is deliberately nothing to pass.  Everything that decides the outcome
    is read from the process by :func:`_process_gate_refusal`, so this function
    cannot be talked into a grant -- not by a boolean, not by an environment
    mapping, and not by a command-line list.
    """

    return RealExecutionAuthorization(_GRANT_TOKEN)


def require_real_execution_authorization(authorization: object) -> None:
    """Refuse anything that is not a currently-valid grant.

    Every real primitive in this module calls this BEFORE it does anything: the
    metadata transport, the metadata probe, the real executor factory and each
    individual cell the real executor runs.  Type identity alone would be
    checkable but weak, so the grant is re-verified rather than merely
    recognised: ``None``, ``True``, a duck-typed stand-in, a subclass instance
    built without the token, and a genuine grant whose process gates have since
    closed are all refused here.
    """

    if not isinstance(authorization, RealExecutionAuthorization):
        raise UnauthorizedRealExecution(
            "EXECUTION REFUSED: this Phase-P primitive contacts the live local "
            "runtime or builds the real provider, so it requires a "
            "RealExecutionAuthorization minted by "
            "grant_real_execution_authorization() in a process carrying BOTH the "
            f"{protocol.HUMAN_GATE_FLAG} flag AND "
            f"{protocol.HUMAN_GATE_ENV}={protocol.HUMAN_GATE_VALUE}; "
            f"{type(authorization).__name__} is not one. No provider was contacted, "
            "no metadata was probed, no inference was performed, no cell was "
            "produced and no results directory was created."
        )
    authorization.verify()


def _names_a_real_seam(candidate: Any) -> str | None:
    """Whether *candidate* IS, or WRAPS, one of this module's real primitives.

    PHASE P-R2 COMPLETION.  The primitives gate themselves, so a wrapped real
    probe raises when it is CALLED.  This lets the offline path refuse it one
    step earlier, when it is HANDED IN -- and it unwraps
    ``functools.partial`` and ``functools.wraps``, so "I wrapped it, so your
    identity check missed it" is not an argument.
    """

    seen: set[int] = set()
    target: Any = candidate
    while target is not None and id(target) not in seen:
        seen.add(id(target))
        if target is _REAL_METADATA_PROBE:
            return "probe_ollama_metadata"
        if target is _REAL_CELL_EXECUTOR_FACTORY:
            return "make_cell_executor"
        if getattr(target, REAL_EXECUTOR_MARKER, False):
            return "an executor built by make_cell_executor"
        target = getattr(target, "func", None) or getattr(target, "__wrapped__", None)
    return None


# --------------------------------------------------------------------------
# 3. Configuration assertion -- local reads only
# --------------------------------------------------------------------------


#: Every field the frozen Phase-P provider slots are permitted to declare.  It
#: mirrors the ``openai_compatible`` field set the canonical loader accepts, and
#: it is checked here STATICALLY so an unknown field is refused without a
#: provider object having to be built to refuse it.
FROZEN_PROVIDER_SLOT_FIELDS: frozenset[str] = frozenset(
    {
        "type",
        "enabled",
        "endpoint",
        "base_url_env",
        "model",
        "model_env",
        "api_key_env",
        "temperature",
        "top_p",
        "max_output_tokens",
        "seed",
        "supports_seed",
        "protocol",
        "timeout_seconds",
        "tool_contract_policy",
    }
)

#: Every field a Phase-P arm MUST declare.  A slot that omits one of these is not
#: a frozen Phase-P provider slot, whatever else it says.
REQUIRED_PROVIDER_SLOT_FIELDS: tuple[str, ...] = (
    "type",
    "enabled",
    "endpoint",
    "model",
    "api_key_env",
    "protocol",
    "tool_contract_policy",
    "temperature",
    "top_p",
    "max_output_tokens",
    "supports_seed",
    "timeout_seconds",
)

#: The provider type both Phase-P arms declare.
EXPECTED_PROVIDER_TYPE = "openai_compatible"


def read_frozen_model_declarations(
    models_path: Path | str | None = None,
) -> Mapping[str, Any]:
    """Parse the frozen Phase-P model config.  STATIC.  BUILDS NO PROVIDER.

    PHASE P-R2 COMPLETION.  This replaces a ``load_provider(...).descriptor()``
    call, and the difference is the point: reading YAML declares nothing into
    existence, whereas ``load_provider`` constructs a production
    ``OpenAICompatibleProvider``.  The invariant admits no unauthorized real
    provider construction -- not "construction with no path to inference", not
    "construction that opens no socket". None.

    The path is bound before it is read, by canonical path AND by the SHA-256 the
    frozen-input record accepted, so this cannot be pointed at another YAML file.
    """

    bound = protocol.require_canonical_input(
        protocol.CANONICAL_MODELS_RELATIVE, models_path
    )
    try:
        parsed = yaml.safe_load(bound.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise protocol.ProtocolError(
            f"FROZEN_ARTIFACT_MISMATCH: the frozen Phase-P model config at {bound} "
            f"could not be parsed: {exc}"
        ) from exc
    if not isinstance(parsed, Mapping):
        raise protocol.ProtocolError(
            "FROZEN_ARTIFACT_MISMATCH: the frozen Phase-P model config is not a "
            "mapping"
        )
    return parsed


def check_arm_configuration(models_path: Path | str | None = None) -> list[str]:
    """Assert each arm's declared identity from the FROZEN BYTES.  No provider is built.

    PHASE P-R2 COMPLETION.  This function used to call
    ``load_provider(models_path, provider_name=slot).descriptor()`` -- once per
    arm, during the OFFLINE preflight, with no authorization -- and read the
    frozen pins off the resulting object.  It opened no socket, and that was not
    the point: the invariant forbids unauthorized real provider CONSTRUCTION,
    and constructing a production ``OpenAICompatibleProvider`` to read a
    dictionary off it is exactly that.  It is now purely static.

    Nothing is lost, because the descriptor's fields come from two separate
    places and each is now checked at its own source:

    * ``model``, ``protocol``, ``tool_contract_policy`` and ``api_key_env`` are
      FIELDS OF ``configs/phaseP-models.yaml``.  They are read from the bound,
      digest-pinned bytes.
    * ``native_tool_adapter_version``, ``tool_argument_contract_version`` and
      ``tool_argument_contract_digest`` are NOT in that file -- the provider
      schema rejects unknown fields and the config says so in its own header.
      They are properties of the INSTRUMENT, so they are read from the live
      instrument constants and compared against the values
      ``docs/phaseP_frozen_execution_inputs.json`` recorded.

    That second comparison is strictly stronger than the descriptor read it
    replaces.  The descriptor advertised the same module constants this protocol
    pins, so comparing the two proved little; comparing the LIVE constants
    against the COMMITTED record proves the instrument still is the one a
    reviewer signed off on.

    The structural preconditions the loader would have enforced -- the top-level
    schema, the slot's presence, its type, that it is explicitly enabled, and
    that it declares no unknown field -- are enforced here too, statically.
    """

    failures: list[str] = []
    try:
        declarations = read_frozen_model_declarations(models_path)
    except protocol.ProtocolError as exc:
        return [str(exc)]

    if set(declarations) != {"schema_version", "default_provider", "providers"}:
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the Phase-P model config top-level schema is "
            f"{sorted(declarations)}; it must be exactly "
            "['default_provider', 'providers', 'schema_version']"
        )
    slots = declarations.get("providers")
    if not isinstance(slots, Mapping):
        return [
            *failures,
            "FROZEN_ARTIFACT_MISMATCH: the Phase-P model config declares no provider "
            "table",
        ]

    for arm in protocol.ARM_ORDER:
        slot = protocol.ARM_PROVIDER_SLOT[arm]
        raw = slots.get(slot)
        if not isinstance(raw, Mapping):
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: arm {arm!r} slot {slot!r} is not declared "
                "in the frozen Phase-P model config"
            )
            continue
        unknown = sorted(set(raw) - FROZEN_PROVIDER_SLOT_FIELDS)
        if unknown:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: arm {arm!r} slot {slot!r} declares "
                f"unknown provider field(s) {unknown}"
            )
        missing = [name for name in REQUIRED_PROVIDER_SLOT_FIELDS if name not in raw]
        if missing:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: arm {arm!r} slot {slot!r} omits required "
                f"provider field(s) {missing}"
            )
        if raw.get("enabled") is not True:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: arm {arm!r} slot {slot!r} is not "
                "explicitly enabled"
            )
        for key, expected, label in (
            ("type", EXPECTED_PROVIDER_TYPE, "type"),
            ("model", protocol.EXPECTED_MODEL[arm], "model"),
            (
                "tool_contract_policy",
                protocol.EXPECTED_TOOL_CONTRACT_POLICY[arm],
                "tool_contract_policy",
            ),
            ("protocol", protocol.EXPECTED_PROTOCOL, "protocol"),
            ("api_key_env", protocol.CREDENTIAL_ENV, "api_key_env"),
        ):
            actual = raw.get(key)
            if actual != expected:
                failures.append(
                    f"FROZEN_ARTIFACT_MISMATCH: arm {arm!r} slot {slot!r} declares "
                    f"{label}={actual!r}, the frozen Phase-P pin is {expected!r}"
                )

    failures.extend(check_advertised_instrument_contract())
    return failures


def check_advertised_instrument_contract() -> list[str]:
    """The descriptor fields that are the INSTRUMENT's, not the config's.

    ``native_tool_adapter_version``, ``tool_argument_contract_version`` and
    ``tool_argument_contract_digest`` are what a Phase-P provider WOULD advertise
    on its descriptor, and none of them is a field of
    ``configs/phaseP-models.yaml``.  They are read here from the live instrument
    and compared against the values the committed frozen-input record accepted --
    a reviewer-signed number rather than the same module constant compared with
    itself.

    No provider is constructed to obtain them (Phase P-R2 completion).
    """

    try:
        record = protocol.load_frozen_inputs()
    except (protocol.ProtocolError, json.JSONDecodeError) as exc:
        return [f"FROZEN_ARTIFACT_MISMATCH: {exc}"]

    failures: list[str] = []
    for key, actual in (
        ("native_tool_adapter_version", NATIVE_TOOL_ADAPTER_VERSION),
        ("tool_argument_contract_version", TOOL_ARGUMENT_CONTRACT_VERSION),
        ("tool_argument_contract_digest", contract_digest(SANDBOX_TOOL_NAMES)),
    ):
        accepted = record.get(key)
        if actual != accepted:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: the live instrument advertises "
                f"{key}={actual!r}; {protocol.FROZEN_INPUTS_RELATIVE} accepted "
                f"{accepted!r}"
            )
    return failures


def check_experiment_configuration(config: Any) -> list[str]:
    """The experiment configuration must be exactly the frozen Phase-P matrix."""

    failures: list[str] = []
    if tuple(config.treatments) != (protocol.QA_MODE,):
        failures.append(
            f"PROTOCOL_DEVIATION: Phase P admits exactly one treatment "
            f"{protocol.QA_MODE!r}; the config declares {list(config.treatments)}. "
            f"{list(protocol.OUT_OF_SCOPE_TREATMENTS)} are out of scope."
        )
    if tuple(config.seeds) != protocol.SEEDS:
        failures.append(
            f"FROZEN_ARTIFACT_MISMATCH: Phase-P seeds must be exactly "
            f"{list(protocol.SEEDS)}; the config declares {list(config.seeds)}"
        )
    if config.repetitions != protocol.SEED_COUNT:
        failures.append(
            f"PROTOCOL_DEVIATION: the config declares repetitions="
            f"{config.repetitions}; Phase P executes exactly {protocol.SEED_COUNT} "
            "seeds per (arm, task)"
        )
    # THE MODEL CONFIG IS BOUND, NOT MERELY LOCATED.  Canonical path equality
    # refuses a historical or copied models file; the frozen digest refuses an
    # edited one at the canonical path.  A config that "looks like" Phase P --
    # right seeds, right treatment, right repetitions -- but points at, or is
    # accompanied by, different model bytes is not a Phase-P input.
    try:
        protocol.require_canonical_input(
            protocol.CANONICAL_MODELS_RELATIVE, config.models_path
        )
    except protocol.NoncanonicalInput as exc:
        failures.append(
            f"{exc} A configuration from a historical phase, or a copy of the "
            "Phase-P one, is never a Phase-P input."
        )
    return failures


# --------------------------------------------------------------------------
# 4. Output-namespace precondition
# --------------------------------------------------------------------------


def check_output_namespace(output_root: Path) -> list[str]:
    """A Phase-P run is never resumed, repaired, replaced or deduplicated."""

    raw_path = output_root / protocol.RAW_RECORD_NAME
    failures: list[str] = []
    if raw_path.exists():
        failures.append(
            f"PROTOCOL_DEVIATION: {raw_path} already exists; Phase-P raw evidence is "
            "append-only and a run is never resumed, repaired or replaced. No row is "
            "overwritten and no invalid row is deleted."
        )
    for name in (protocol.RUN_MANIFEST_NAME, protocol.PARTIAL_MANIFEST_NAME):
        if (output_root / name).exists():
            failures.append(
                f"PROTOCOL_DEVIATION: {output_root / name} already exists; a completed "
                "or partial Phase-P run is never re-entered"
            )
    cells = protocol.cells_root(output_root)
    if cells.exists() and any(cells.iterdir()):
        failures.append(
            f"PROTOCOL_DEVIATION: {cells} already holds cell evidence; Phase P never "
            "writes into an existing evidence tree"
        )
    return failures


# --------------------------------------------------------------------------
# 5. Metadata-only preflight
# --------------------------------------------------------------------------


def _ollama_get(
    path: str,
    *,
    authorization: RealExecutionAuthorization,
    timeout: float = 30.0,
) -> dict[str, object]:
    """The ONLY function in this module that opens a socket to the runtime.

    It validates the capability itself.  Gating only its caller would leave a
    Phase-P primitive that reaches the runtime with no authorization, and an
    underscore in a name is not a control (Phase P-R2).
    """

    require_real_execution_authorization(authorization)
    request = urllib.request.Request(f"{protocol.OLLAMA_BASE_URL}{path}", method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"unexpected payload from {path}")
    return payload


def probe_ollama_metadata(
    model: str, *, authorization: RealExecutionAuthorization
) -> RuntimeMetadata:
    """Return the live local runtime's metadata for one model.  REQUIRES the capability.

    METADATA ONLY.  ``/api/version`` and ``/api/tags`` describe what is installed;
    neither generates a token, and neither ``/api/chat`` nor ``/api/generate`` nor
    any OpenAI-compatible completion endpoint is used.

    PHASE P-R2 COMPLETION.  ``authorization`` is keyword-only and REQUIRED, and
    is validated here rather than by whoever called.  Two consequences, both
    deliberate:

    * this function is not a :data:`MetadataProbe`.  Handing it to anything that
      expects one -- including :func:`_drive_bound_run` -- raises ``TypeError``
      on the first call, having contacted nothing; and
    * binding a capability into it with ``functools.partial`` produces something
      that IS a ``MetadataProbe``, and doing that requires holding a capability,
      which requires both human gates in this process.

    Only :func:`execute_authorized_real_run` does the binding.
    """

    version = str(
        _ollama_get("/api/version", authorization=authorization).get("version") or ""
    )
    entries = _ollama_get("/api/tags", authorization=authorization).get("models")
    present = False
    digest = ""
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and entry.get("name") == model:
                present = True
                digest = str(entry.get("digest") or "")
                break
    return RuntimeMetadata(
        runtime_version=version, model_present=present, model_digest=digest
    )


#: The REAL probe object, bound once at import so it can be recognised by
#: identity through :func:`_names_a_real_seam`.  The offline path compares
#: against THIS rather than against the module global, so its refusal cannot be
#: undone by rebinding the name -- and cannot be triggered by a test that
#: legitimately monkeypatches the global to prove the real probe is never
#: reached.  This is a CONVENIENCE, not the control: the control is that
#: :func:`probe_ollama_metadata` validates the capability itself.
_REAL_METADATA_PROBE = probe_ollama_metadata


def metadata_preflight(
    probe: MetadataProbe,
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    """ENVIRONMENT_HOLD gate: the live runtime must be the frozen environment.

    EVERY arm is probed exactly once, and EVERY arm is probed before ANY
    inference, so a second-arm environment drift cannot be discovered only after
    the first arm has been spent.  A failure on one arm does not short-circuit the
    other: both are probed, both are reported, and the run stops with zero cells
    executed.

    Returns the failures and what was observed; the observation is recorded in the
    run manifest so a reviewer can see the environment the run actually met.

    Phase P NEVER pulls, downloads, updates, retags, repairs, substitutes or
    automatically changes a model.  There is no environment self-healing path.
    """

    failures: list[str] = []
    observed: dict[str, dict[str, Any]] = {}
    for arm in protocol.ARM_ORDER:
        model = protocol.EXPECTED_MODEL[arm]
        try:
            metadata = probe(model)
        except (
            urllib.error.URLError,
            OSError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            failures.append(
                f"ENVIRONMENT_HOLD: cannot probe the local runtime for arm {arm!r}: "
                f"{exc}"
            )
            continue
        observed[arm] = {
            "model": model,
            "runtime_version": metadata.runtime_version,
            "model_present": metadata.model_present,
            "model_digest": metadata.model_digest,
        }
        if not metadata.model_present:
            failures.append(
                f"ENVIRONMENT_HOLD: the local runtime does not have model {model!r} "
                f"for arm {arm!r}; Phase P does not pull, download or install a model"
            )
        expected_digest = protocol.EXPECTED_MODEL_DIGEST[model]
        if metadata.model_digest != expected_digest:
            failures.append(
                f"ENVIRONMENT_HOLD: model {model!r} digest is "
                f"{metadata.model_digest!r} but the frozen pin is {expected_digest!r}; "
                "Phase P does not pull, update, retag, repair or replace a model"
            )
        if metadata.runtime_version != protocol.EXPECTED_RUNTIME_VERSION:
            failures.append(
                f"ENVIRONMENT_HOLD: Ollama runtime version is "
                f"{metadata.runtime_version!r} but the frozen pin is "
                f"{protocol.EXPECTED_RUNTIME_VERSION!r}; the committed experiment "
                "architecture does not permit unreviewed runtime drift"
            )
    missing = [arm for arm in protocol.ARM_ORDER if arm not in observed]
    if missing:
        failures.append(
            f"ENVIRONMENT_HOLD: arms {missing} produced no metadata observation; both "
            "arms must be probed before either arm executes a cell"
        )
    return failures, observed


# --------------------------------------------------------------------------
# 6. One cell
# --------------------------------------------------------------------------


def _row_from_cell_directory(experiment_dir: Path) -> dict[str, Any]:
    lines = [
        line
        for line in (experiment_dir / "runs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if len(lines) != 1:
        raise ExperimentConfigError(
            f"one cell must produce exactly one raw row, {experiment_dir.name} "
            f"produced {len(lines)}"
        )
    parsed: dict[str, Any] = json.loads(lines[0])
    return parsed


def _manifest_observations(experiment_dir: Path) -> dict[str, Any]:
    """Read the run's OWN persisted manifest for what the row does not carry.

    ``ExperimentRunner`` records ``raw_schema_version`` and the full provider
    descriptor -- including the argument-contract version and digest the provider
    ADVERTISED -- in the cell's ``manifest.json`` rather than on the row.  These
    are observations of the run that happened, read back from its own artifact,
    so transporting them keeps the disclosure precondition a fact about the run
    instead of a constant the driver asserted about itself.

    A missing manifest, a missing field or a stub provider that advertises no
    contract yields ``None``, which the frozen contract-drift check then refuses.
    Nothing here substitutes a default.
    """

    path = experiment_dir / "manifest.json"
    observations: dict[str, Any] = {
        name: None for name in protocol.MANIFEST_TRANSPORTED_FIELDS
    }
    if not path.is_file():
        return observations
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return observations
    if not isinstance(manifest, Mapping):  # pragma: no cover - defensive
        return observations
    observations["raw_schema_version"] = manifest.get("raw_schema_version")
    descriptor = manifest.get("provider")
    if isinstance(descriptor, Mapping):
        for name in ("tool_argument_contract_version", "tool_argument_contract_digest"):
            observations[name] = descriptor.get(name)
    return observations


def make_cell_executor(
    *,
    authorization: RealExecutionAuthorization,
    config_path: Path,
    manifest_path: Path,
    output_root: Path,
) -> CellExecutor:
    """Build the real, runner-backed executor for one frozen cell.  REQUIRES the capability.

    The canonical ``ExperimentRunner.run`` owns its own case x repetition loop and
    derives the seed as ``config.seeds[repetition]``, so a per-cell driver must
    give it a per-cell configuration.  That is what this does: a config whose seed
    tuple is exactly this cell's seed, whose repetition count is one, whose
    treatment set is exactly ``off``, and whose output root is this cell's own
    directory under ``<output_root>/raw/cells/<slug>/`` -- so no cell can
    overwrite, blend into or resume another.

    Nothing about the run is otherwise altered.  The provider, the policy, the
    ablations, the step budget and the frozen benchmark are the frozen ones.

    PHASE P-R2 COMPLETION.  Three things changed here, and each closes a way this
    function used to be reachable without authorization.

    **The capability is required and validated HERE.**  This function constructs
    the real providers, so it is a real primitive and gates itself.  Being
    called only by an authorized path was not a control.

    **It is validated AGAIN before every cell.**  A hundred and two cells are a
    long time; the grant is re-proved against process state at each one, so a
    run whose gates close mid-schedule stops rather than finishing.

    **The ``providers`` seam is gone.**  It accepted an arbitrary provider
    mapping and, when absent, silently built the real one -- which is exactly
    the ``None``-means-real default the P-R2 brief forbids.  Nothing used it: the
    offline suite injects a whole ``CellExecutor`` through
    :func:`execute_offline_bound_run` and never needed a provider seam.  Its
    removal means this function has ONE behaviour, and that behaviour is gated.
    """

    require_real_execution_authorization(authorization)

    from iqa_soa.benchmark import load_frozen_pilot  # noqa: PLC0415

    frozen_pilot = load_frozen_pilot(manifest_path)
    base_config = load_experiment_config(config_path)
    providers: Mapping[str, Any] = {
        arm: load_provider(
            base_config.models_path, provider_name=protocol.ARM_PROVIDER_SLOT[arm]
        )
        for arm in protocol.ARM_ORDER
    }
    root = protocol.cells_root(output_root)

    def execute(cell: Any) -> Mapping[str, Any]:
        # RE-PROVED PER CELL.  Not decoration: this is the only thing standing
        # between a captured executor and 102 cells of inference if the process
        # gates close after the factory ran.
        require_real_execution_authorization(authorization)
        cell_root = root / protocol.cell_slug(cell)
        config = replace(
            base_config,
            output_root=cell_root,
            treatments=(protocol.QA_MODE,),
            repetitions=1,
            seeds=(cell.seed,),
        )
        started = time.perf_counter()
        experiment_dir = ExperimentRunner(config, provider=providers[cell.arm]).run(
            treatments=[protocol.QA_MODE],
            case_ids=[cell.task_id],
            repetitions=1,
            frozen_benchmark=frozen_pilot,
            max_total_runs=1,
            experiment_kind=protocol.EXPERIMENT_KIND,
            infrastructure_retry_limit=protocol.INFRASTRUCTURE_RETRY_LIMIT,
        )
        row = _row_from_cell_directory(experiment_dir)
        row["cell_elapsed_ms"] = (time.perf_counter() - started) * 1000.0
        row.update(_manifest_observations(experiment_dir))
        stored = protocol.cell_experiment_dir_value(experiment_dir, output_root)
        # Producer-side half of the containment contract.  The analyzer binds
        # every evidence pointer to its frozen cell; asserting the same thing here
        # means a producer regression fails at the cell that caused it rather than
        # silently at analysis time.
        resolved, reason = protocol.contained_child(
            output_root, stored, label="cell_experiment_dir", must_be_dir=True
        )
        evidence_root = protocol.cell_evidence_root(output_root, cell).resolve()
        if resolved is None or evidence_root not in resolved.parents:
            raise protocol.ProtocolError(
                f"cell {cell.key} produced an evidence pointer that is not beneath "
                f"its own evidence root {evidence_root}: {reason or stored}"
            )
        row["cell_experiment_dir"] = stored
        return row

    setattr(execute, REAL_EXECUTOR_MARKER, True)
    return execute


#: The REAL executor factory, bound once at import so :func:`_names_a_real_seam`
#: can recognise it even through a wrapper.  As with the probe anchor this is a
#: convenience: the control is that :func:`make_cell_executor` validates the
#: capability itself, and so does every cell the executor it returns runs.
_REAL_CELL_EXECUTOR_FACTORY = make_cell_executor


def stamp_frozen_identity(row: Mapping[str, Any], cell: Any) -> dict[str, Any]:
    """Add the two frozen-input identity fields and the schedule bookkeeping.

    ``model_digest`` and ``run_key`` are the only identity fields stamped here,
    and both come from the FROZEN CELL rather than from the run.  A row that
    already carries a conflicting value KEEPS ITS OWN VALUE, so a runner that
    someday emits these fields cannot be silently overwritten into agreement --
    the binding check must see the disagreement.  ``setdefault`` is what makes
    that property true, and a test asserts it directly.

    Nothing in :data:`protocol.MANIFEST_TRANSPORTED_FIELDS` is stamped here: those
    are observations the executor reads from the cell's own manifest, and a
    missing one stays missing so the contract-drift check refuses it.
    """

    stamped = dict(row)
    stamped.setdefault("model_digest", cell.model_digest)
    stamped.setdefault("run_key", cell.run_key)
    stamped["schedule_index"] = cell.index
    stamped["arm"] = cell.arm
    stamped["cell_key"] = cell.key
    stamped.setdefault("cell_experiment_dir", "")
    return stamped


def lost_cell_row(cell: Any, detail: str) -> dict[str, Any]:
    """The record for a cell whose execution raised before producing a row.

    There is no row to transport, so the identity comes from the frozen cell by
    necessity.  ``provider_attempt_count`` is ``0``, which the rc4 classifier
    treats as ``INSTRUMENT_DEFECT`` -> ``IMMEDIATE_STOP``: no attempt was
    preserved at all, so the evidence for this cell is lost and continuing would
    measure with a broken instrument.  The exception text is preserved verbatim
    rather than summarized, and the row is still appended to the raw record.
    """

    return {
        "task_id": cell.task_id,
        "seed": cell.seed,
        "model": cell.model,
        "model_digest": cell.model_digest,
        "qa_mode": cell.qa_mode,
        "benchmark_manifest_sha256": cell.benchmark_manifest_sha256,
        "run_key": cell.run_key,
        "schedule_index": cell.index,
        "arm": cell.arm,
        "cell_key": cell.key,
        "cell_experiment_dir": "",
        "provider_attempt_count": 0,
        "error": detail,
        "cell_execution_raised": True,
    }


# --------------------------------------------------------------------------
# The run
# --------------------------------------------------------------------------


def _append_row(path: Path, row: Mapping[str, Any]) -> None:
    """Append one raw row immediately.  Never rewrite, never deduplicate."""

    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def run_frozen_schedule(
    *,
    schedule: Sequence[Any],
    scripted_faults: Mapping[str, Sequence[Any]],
    execute_cell: CellExecutor,
    raw_path: Path,
    partial_manifest_path: Path,
) -> Any:
    """Drive the frozen schedule under machine-enforced stop semantics.

    ``StopController.cells()`` is the ONLY source of the next cell, and it
    terminates the instant a stop is armed.  There is no independent loop, no
    index arithmetic and no early ``continue`` that could step past it, so a
    stop at the final cell of arm 1 leaves arm 2 with zero cells executed.
    """

    controller = protocol.StopController(schedule, scripted_faults=scripted_faults)
    for cell in controller.cells():
        try:
            row = execute_cell(cell)
        except Exception as exc:  # noqa: BLE001 - preserved, never swallowed
            row = lost_cell_row(cell, f"{type(exc).__name__}: {exc}")
        stamped = stamp_frozen_identity(row, cell)
        # Persist BEFORE classifying, so a classifier crash can never erase the
        # observed row and an invalidated cell keeps its raw evidence.
        _append_row(raw_path, stamped)
        failure_class = controller.record(cell, stamped)
        print(
            f"cell {cell.index:03d}/{len(schedule)} {cell.key} -> {failure_class}",
            flush=True,
        )
    controller.write_partial_manifest(partial_manifest_path)
    return controller.result()


def _describe_path(path: Path) -> dict[str, Any]:
    """One input's ACTUAL identity: where it is, and what its bytes hash to.

    Never the digest of the artifact we WISH had been read -- always the bytes
    at the path this run actually used.
    """

    resolved = Path(path).resolve()
    try:
        relative = resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        relative = None
    try:
        digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
    except OSError:
        digest = None
    return {
        "path": str(resolved),
        "repository_relative_path": relative,
        "sha256": digest,
    }


def describe_execution_inputs(
    *,
    config_path: Path,
    models_path: Path,
    manifest_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    """The provenance of what this run ACTUALLY read and wrote.

    PHASE P-R1, requirement 5.  Every digest recorded here is computed from the
    bytes at the path this invocation used, so a run manifest can never report a
    canonical digest over noncanonical inputs.  ``*_is_canonical`` states the
    binding verdict for each input separately, and
    ``official_phase_p_execution`` is true only when EVERY one of them holds --
    which is the single field a reader needs in order to know whether this
    directory is an official Phase-P run or a harness exercise.
    """

    described = {
        "config": _describe_path(config_path),
        "models": _describe_path(models_path),
        "benchmark_manifest": _describe_path(manifest_path),
    }
    canonical = {
        "config": protocol.CANONICAL_CONFIG_RELATIVE,
        "models": protocol.CANONICAL_MODELS_RELATIVE,
        "benchmark_manifest": protocol.CANONICAL_MANIFEST_RELATIVE,
    }
    for name, entry in described.items():
        relative = canonical[name]
        try:
            accepted: str | None = protocol.accepted_frozen_digest(relative)
        except protocol.ProtocolError:
            accepted = None
        entry["canonical_repository_relative_path"] = relative
        entry["frozen_sha256"] = accepted
        entry["is_canonical"] = bool(
            entry["repository_relative_path"] == relative
            and accepted is not None
            and entry["sha256"] == accepted
        )
    resolved_root = Path(output_root).resolve()
    namespace_is_canonical = protocol.is_canonical_results_root(resolved_root)
    return {
        **described,
        "output_root": str(resolved_root),
        "canonical_results_namespace": protocol.RESULTS_NAMESPACE,
        "output_root_is_canonical_namespace": namespace_is_canonical,
        "binding": protocol.EXECUTION_INPUT_BINDING,
        "official_phase_p_execution": bool(
            namespace_is_canonical
            and all(entry["is_canonical"] for entry in described.values())
        ),
    }


def _write_run_manifest(
    path: Path,
    *,
    result: Any,
    summary: Mapping[str, Any],
    frozen_inputs: Mapping[str, Any],
    runtime_metadata: Mapping[str, Any],
    execution_inputs: Mapping[str, Any],
) -> None:
    payload = {
        "record_kind": "phase_p_run_manifest",
        "phase": protocol.PHASE,
        "benchmark_version": protocol.BENCHMARK_VERSION,
        "protocol": dict(summary),
        "frozen_inputs": dict(frozen_inputs),
        # THE INPUTS THIS RUN ACTUALLY READ, hashed from their own bytes.  Phase
        # P-R1: a run manifest never reports a canonical digest for a file it did
        # not read.
        "execution_inputs": dict(execution_inputs),
        "runtime_metadata": dict(runtime_metadata),
        "terminal_status": result.terminal_status,
        "exit_code": result.exit_code,
        "planned_cells": result.planned,
        "executed_cells": result.executed,
        "invalidated_cells": list(result.invalidated_cells),
        "hold_reasons": list(result.hold_reasons),
        "stop_cell": result.stop_cell,
        "stop_failure_class": result.stop_failure_class,
        "stop_reason": result.stop_reason,
        "stop_detail": list(result.stop_detail),
        "cells_not_started": list(result.not_started),
        # THE STOPCONTROLLER CLASSIFICATION LEDGER, persisted verbatim.  It is
        # NOT regenerated here: this is the exact ledger the controller produced
        # while recording the actual rows, so the analyzer's independent
        # reclassification has something real to disagree with.  Phase L-A'
        # omitted it, which made that reconciliation vacuous on every real run.
        "classifications": [dict(item) for item in result.classifications],
        "note": (
            "Every provider attempt is preserved. No cell was retried, replaced, "
            "repaired, resumed or rerun, and no raw trace was deleted."
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        protocol.HUMAN_GATE_FLAG,
        dest="execute_real_model",
        action="store_true",
        help=(
            "Half of the human execution gate. Real-model execution ALSO requires "
            f"{protocol.HUMAN_GATE_ENV}={protocol.HUMAN_GATE_VALUE}."
        ),
    )
    parser.add_argument(
        "--verify-frozen-inputs",
        action="store_true",
        help=(
            "Run the complete OFFLINE protocol validation and exit. Contacts no "
            "provider, probes no runtime, creates no directory and executes no "
            "cell. Safe to run at any time and needs no gate."
        ),
    )
    # THE THREE BOUND OPTIONS.  Each is an ASSERTION that the caller means the
    # frozen Phase-P artifact, checked in main() by canonical path equality AND
    # by the SHA-256 the frozen-input record accepted.  They exist so that a
    # command line can be written out in full in a protocol document and still be
    # exactly reproducible; they are NOT a way to select a different scientific
    # input, and supplying anything else is refused before any provider contact.
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / protocol.CANONICAL_CONFIG_RELATIVE),
        help=(
            "Must be the frozen "
            f"{protocol.CANONICAL_CONFIG_RELATIVE}. A semantically similar "
            "alternate config is not a frozen Phase-P input and is refused."
        ),
    )
    parser.add_argument(
        "--manifest",
        default=str(PROJECT_ROOT / protocol.CANONICAL_MANIFEST_RELATIVE),
        help=(
            "Must be the frozen "
            f"{protocol.CANONICAL_MANIFEST_RELATIVE}. A structurally valid "
            f"look-alike -- same benchmark_version, same {protocol.TASK_COUNT} "
            "tasks -- is refused."
        ),
    )
    parser.add_argument(
        "--output-root",
        default=str(PROJECT_ROOT / protocol.RESULTS_NAMESPACE),
        help=(
            "Must be the frozen "
            f"{protocol.RESULTS_NAMESPACE}. This driver does not reinterpret an "
            "alternate namespace as an official Phase-P run."
        ),
    )
    return parser


def verify_frozen_inputs() -> tuple[int, list[str]]:
    """The complete static/frozen protocol validation.  ZERO provider contact."""

    failures = list(protocol.offline_preflight())
    try:
        config = load_experiment_config(
            protocol.require_canonical_input(protocol.CANONICAL_CONFIG_RELATIVE)
        )
    except (ExperimentConfigError, protocol.ProtocolError) as exc:
        failures.append(f"FROZEN_ARTIFACT_MISMATCH: the Phase-P config is invalid: {exc}")
    else:
        failures.extend(check_experiment_configuration(config))
        failures.extend(check_arm_configuration(config.models_path))
    try:
        benchmark = protocol.load_benchmark()
        protocol.build_phase_p_schedule(benchmark)
    except (protocol.ProtocolError, ExperimentConfigError) as exc:
        failures.append(f"FROZEN_ARTIFACT_MISMATCH: {exc}")
    return (protocol.EXIT_OK if not failures else protocol.EXIT_PREFLIGHT_STOP), failures


def _refuse_unauthorized_real_seams(
    *,
    output_root: Path,
    probe: Any,
    make_executor: Any,
) -> None:
    """The OFFLINE-MODE refusals, enforced in the core so every caller meets them.

    PHASE P-R2 COMPLETION.  These four checks used to live in
    :func:`execute_offline_bound_run`, which meant a caller that went straight to
    the run loop never met them.  They live here now, in the one function that
    actually drives the schedule, so there is no path around them.

    None of these is the primary control -- :func:`probe_ollama_metadata` and
    :func:`make_cell_executor` validate the capability themselves, so a real
    primitive that got this far would raise when CALLED, having contacted
    nothing.  What these add is refusal one step earlier, at the moment the seam
    is handed in, with a message that says which seam and why.
    """

    if probe is None or make_executor is None:
        raise protocol.ProtocolError(
            "OFFLINE_SEAM_MISUSE: an unauthorized Phase-P run requires BOTH an "
            "injected metadata probe and an injected cell executor. There is no "
            "real-model default and none is ever acquired; real-model execution "
            "is reachable only through execute_authorized_real_run()."
        )
    if not callable(probe) or not callable(make_executor):
        raise protocol.ProtocolError(
            "OFFLINE_SEAM_MISUSE: the injected probe and the injected cell "
            "executor must both be callables"
        )
    for label, candidate in (("probe", probe), ("cell executor", make_executor)):
        named = _names_a_real_seam(candidate)
        if named is not None:
            raise protocol.ProtocolError(
                f"OFFLINE_SEAM_MISUSE: the injected {label} is {named}, which "
                "contacts the live local runtime or spends real inference. An "
                "unauthorized Phase-P run refuses it -- including through a "
                "functools.partial or a functools.wraps wrapper. Real-model "
                "execution is reachable only through execute_authorized_real_run(), "
                "which requires both Phase-P human gates in this process."
            )
    if protocol.is_canonical_results_root(output_root):
        raise protocol.ProtocolError(
            f"OFFLINE_SEAM_MISUSE: {protocol.RESULTS_NAMESPACE} is the namespace an "
            "OFFICIAL Phase-P execution writes. An unauthorized run never writes "
            "it, so synthetic evidence can never occupy the one directory an "
            "official qualification analysis is allowed to read."
        )


def _drive_bound_run(
    *,
    authorization: RealExecutionAuthorization | None,
    config_path: Path,
    manifest_path: Path,
    output_root: Path,
    env: Mapping[str, str],
    probe: MetadataProbe,
    make_executor: CellExecutorFactory,
) -> int:
    """Drive the frozen schedule against ALREADY-BOUND scientific inputs.

    ``authorization`` selects the MODE, and the mode is enforced here rather
    than by whichever function called -- which is the Phase P-R2 completion.
    The previous version took ``probe`` and ``make_executor`` from its caller and
    checked nothing about them, so a caller could hand it the real probe or a
    factory wrapping the real one and reach the runtime; the guards that would
    have refused that lived in :func:`execute_offline_bound_run`, which such a
    caller simply did not call.  A private name is not a control.

    **``authorization`` is not ``None``: REAL MODE.**  The grant is validated
    here, and it is validated again inside every real primitive the run reaches
    -- :func:`probe_ollama_metadata` for each arm, :func:`make_cell_executor`
    once, and each of the 102 cells it runs.

    **``authorization`` is ``None``: OFFLINE MODE.**  Both injections are
    REQUIRED, neither may be or wrap a real primitive, and the frozen
    ``results/phaseP-rc4-qualification`` namespace may not be written. These
    four refusals are what this function enforces on EVERY caller, not only on
    the one that goes through the offline wrapper.

    Every scientific input is bound HERE as well as by the caller, by a layer
    that does not depend on the caller: the execution config immediately below,
    the benchmark manifest inside ``protocol.load_benchmark``, and the model
    config inside :func:`check_experiment_configuration`.
    """

    if authorization is not None:
        require_real_execution_authorization(authorization)
    else:
        _refuse_unauthorized_real_seams(
            output_root=output_root, probe=probe, make_executor=make_executor
        )

    # ---- 1c. The execution config, bound here as well as by the entry point. --
    #
    # Not redundant: this is the layer that holds whichever entry point called.
    # It runs before the preflight and before anything is read from the config,
    # so a noncanonical config costs zero metadata probes and zero cells.
    try:
        config_path = protocol.require_canonical_input(
            protocol.CANONICAL_CONFIG_RELATIVE, config_path
        )
    except protocol.ProtocolError as exc:
        print(f"IMMEDIATE_STOP: {exc}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP

    # ---- 2. Offline preflight, still before any provider contact. ----
    failures = protocol.offline_preflight()
    if failures:
        for failure in failures:
            print(f"IMMEDIATE_STOP: {failure}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP

    try:
        benchmark = protocol.load_benchmark(manifest_path)
        schedule = protocol.build_phase_p_schedule(benchmark)
        summary = protocol.protocol_summary()
    except (protocol.ProtocolError, ExperimentConfigError) as exc:
        print(f"IMMEDIATE_STOP: FROZEN_ARTIFACT_MISMATCH: {exc}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP

    # ---- 2b. PROVENANCE TRUTH.  The summary this run is about to persist must
    # describe the schedule this run is about to execute.  ``protocol_summary``
    # is derived from the CANONICAL manifest; ``schedule`` is derived from the
    # manifest actually supplied.  If those two ever disagreed, the run manifest
    # would report a canonical protocol over noncanonical rows -- exactly the
    # P-R1 defect.  They cannot disagree once the binding holds, which is why
    # this is checked rather than assumed.
    executed_facts: tuple[tuple[str, Any], ...] = (
        ("benchmark_manifest_sha256", benchmark.manifest_sha256),
        ("task_order", list(benchmark.task_ids)),
        ("planned_cells", len(schedule)),
        ("schedule_digest", protocol.schedule_digest(schedule)),
    )
    drift = [
        f"PROTOCOL_DEVIATION: the recorded protocol summary reports "
        f"{field}={summary.get(field)!r} but this run would execute {value!r}"
        for field, value in executed_facts
        if summary.get(field) != value
    ]
    if drift:
        for failure in drift:
            print(f"IMMEDIATE_STOP: {failure}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP

    # ---- 3. Configuration assertion. Local reads only. ----
    try:
        base_config = load_experiment_config(config_path)
    except ExperimentConfigError as exc:
        print(f"IMMEDIATE_STOP: FROZEN_ARTIFACT_MISMATCH: {exc}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP
    config_failures = [
        *check_experiment_configuration(base_config),
        *check_arm_configuration(base_config.models_path),
    ]
    if config_failures:
        for failure in config_failures:
            print(f"IMMEDIATE_STOP: {failure}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP

    # ---- 4. Output namespace. Refused before the runtime is even probed. ----
    namespace_failures = check_output_namespace(output_root)
    if namespace_failures:
        for failure in namespace_failures:
            print(f"IMMEDIATE_STOP: {failure}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP

    # ---- 5. Metadata-only preflight. First and only pre-inference contact. ----
    environment_failures, runtime_metadata = metadata_preflight(probe)
    if environment_failures:
        for failure in environment_failures:
            print(failure, file=sys.stderr)
        print(
            "ENVIRONMENT_HOLD: 0 cells executed. Phase P does not pull, download, "
            "update, retag, repair or substitute a model.",
            file=sys.stderr,
        )
        return protocol.EXIT_ENVIRONMENT_HOLD

    # Credential presence is checked by NAME only.  The value is never read into a
    # message, never printed and never written to an artifact.
    if not env.get(protocol.CREDENTIAL_ENV):
        print(
            f"STOP: environment variable {protocol.CREDENTIAL_ENV!r} is unset; the "
            "local OpenAI-compatible adapter requires a credential value even when "
            "the local runtime ignores it",
            file=sys.stderr,
        )
        return protocol.EXIT_CREDENTIAL_STOP

    # ---- 6. The frozen schedule, owned by the stop controller. ----
    output_root.mkdir(parents=True, exist_ok=True)
    raw_path = output_root / protocol.RAW_RECORD_NAME
    raw_path.touch()

    print(
        f"Phase-P QA-OFF qualification: benchmark={protocol.BENCHMARK_VERSION} "
        f"manifest_sha256={benchmark.manifest_sha256} treatment={protocol.QA_MODE} "
        f"arms={list(protocol.ARM_ORDER)} tasks={protocol.TASK_COUNT} "
        f"seeds={list(protocol.SEEDS)} cells={len(schedule)} "
        f"instrument={protocol.EXPECTED_INSTRUMENT_VERSION} "
        f"raw_schema={protocol.EXPECTED_RAW_SCHEMA_VERSION} "
        f"arguments={protocol.EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION} "
        f"adapter={protocol.EXPECTED_NATIVE_TOOL_ADAPTER_VERSION} retries=0"
    )

    result = run_frozen_schedule(
        schedule=schedule,
        scripted_faults=benchmark.scripted_faults,
        execute_cell=make_executor(config_path, manifest_path, output_root),
        raw_path=raw_path,
        partial_manifest_path=output_root / protocol.PARTIAL_MANIFEST_NAME,
    )
    _write_run_manifest(
        output_root / protocol.RUN_MANIFEST_NAME,
        result=result,
        summary=summary,
        frozen_inputs=protocol.load_frozen_inputs(),
        runtime_metadata=runtime_metadata,
        execution_inputs=describe_execution_inputs(
            config_path=config_path,
            models_path=Path(base_config.models_path),
            manifest_path=manifest_path,
            output_root=output_root,
        ),
    )

    if result.stopped:
        print(
            f"HOLD_POST_FREEZE_DEFECT: stopped at {result.stop_cell} "
            f"({result.stop_failure_class}); {result.executed}/{result.planned} cells "
            f"executed, {len(result.not_started)} never started. There is no "
            "resumption path and no replacement path.",
            file=sys.stderr,
        )
    print(
        f"terminal_status={result.terminal_status} executed={result.executed}/"
        f"{result.planned} invalidated={len(result.invalidated_cells)} "
        f"holds={len(result.hold_reasons)}"
    )
    exit_code: int = result.exit_code
    return exit_code


def execute_authorized_real_run(*, authorization: RealExecutionAuthorization) -> int:
    """THE ONLY REAL-MODEL-CAPABLE PATH.  It requires the capability, and nothing else.

    PHASE P-R2.  This function takes no config, no manifest and no output root,
    because there is nothing about an official Phase-P run for a caller to
    choose: it binds the frozen config, the frozen benchmark manifest and the
    frozen ``results/phaseP-rc4-qualification`` namespace itself, from
    ``phaseP_protocol``, by canonical path AND by the SHA-256 the frozen-input
    record accepted.  It takes no probe and no executor either: it SELECTS
    :func:`probe_ollama_metadata` and :func:`make_cell_executor`, which is
    exactly the authority the capability confers and the reason nothing else in
    this module may do it.

    ``authorization`` is re-verified here rather than assumed valid, so a
    capability minted under an open gate cannot be carried into a context that
    no longer authorizes anything.  An unauthorized call RAISES
    :class:`UnauthorizedRealExecution` before a single path is bound -- it does
    not return an exit code, because no run happened and an exit code is a
    result.
    """

    require_real_execution_authorization(authorization)

    try:
        config_path = protocol.require_canonical_input(
            protocol.CANONICAL_CONFIG_RELATIVE
        )
        manifest_path = protocol.require_canonical_input(
            protocol.CANONICAL_MANIFEST_RELATIVE
        )
        output_root = protocol.require_canonical_results_root()
    except protocol.ProtocolError as exc:
        print(f"IMMEDIATE_STOP: {exc}", file=sys.stderr)
        print(
            "NONCANONICAL_PHASE_P_EXECUTION: refused. 0 metadata probes, 0 cells "
            "executed, no results namespace created.",
            file=sys.stderr,
        )
        return protocol.EXIT_PREFLIGHT_STOP

    # BINDING THE CAPABILITY INTO THE PRIMITIVES.  ``probe_ollama_metadata`` and
    # ``make_cell_executor`` both REQUIRE a keyword-only authorization, so
    # neither has the shape the run loop consumes until it is bound here.  That
    # is the whole point: producing something of the right shape costs a
    # capability, and a capability costs both human gates in this process.
    return _drive_bound_run(
        authorization=authorization,
        config_path=config_path,
        manifest_path=manifest_path,
        output_root=output_root,
        env=os.environ,
        probe=functools.partial(probe_ollama_metadata, authorization=authorization),
        make_executor=lambda config, manifest, root: make_cell_executor(
            authorization=authorization,
            config_path=config,
            manifest_path=manifest,
            output_root=root,
        ),
    )


def execute_offline_bound_run(
    *,
    config_path: Path,
    manifest_path: Path,
    output_root: Path,
    env: Mapping[str, str],
    probe: MetadataProbe,
    execute_cell: CellExecutor,
) -> int:
    """THE OFFLINE SEAM.  It needs no authorization because it cannot execute a model.

    PHASE P-R2.  The offline regression suite has to drive everything beyond the
    gate -- the metadata preflight, the stop controller, the raw record, the run
    manifest -- without a provider.  Before P-R2 it did that through the same
    function the production CLI used, which is precisely why that function was
    real-model capable and therefore had to be gated, but was not.

    This one is structurally incapable of a real run, and says so in behaviour
    rather than in prose:

    * ``probe`` and ``execute_cell`` are REQUIRED.  There is no default, so
      there is nothing for a missing argument to resolve into.
    * :func:`probe_ollama_metadata` is refused BY IDENTITY, so the real probe
      cannot be laundered in through the injection point.
    * an executor built by :func:`make_cell_executor` is refused by its
      :data:`REAL_EXECUTOR_MARKER`, for the same reason.
    * the frozen ``results/phaseP-rc4-qualification`` namespace is refused
      outright, so nothing this seam writes can be -- or be mistaken for -- an
      official Phase-P run.  That is the producer-side half of the Phase P-R2
      evidence-root repair the analyzer enforces on the reading side.

    Every scientific input is still bound: the config and the manifest by
    :func:`_drive_bound_run`, and the model config by
    :func:`check_experiment_configuration`.
    """

    # THIS FUNCTION'S OWN PARAMETER, CHECKED HERE.  The core sees the lambda
    # below, not ``execute_cell``, so a missing or real executor has to be
    # refused at the layer that actually has it.  It is the SAME helper the core
    # applies to its own parameters -- one rule, applied wherever the argument
    # lives, rather than a second rule that could drift from the first.
    _refuse_unauthorized_real_seams(
        output_root=output_root, probe=probe, make_executor=execute_cell
    )
    return _drive_bound_run(
        authorization=None,
        config_path=config_path,
        manifest_path=manifest_path,
        output_root=output_root,
        env=env,
        probe=probe,
        make_executor=lambda _config, _manifest, _root: execute_cell,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """The production CLI.  It has NO injection seam of ANY kind (Phase P-R2).

    ``probe`` and ``execute_cell`` used to be parameters here, so the suite could
    drive the CLI without a provider; ``env`` used to be one, so the suite could
    simulate an open gate.  All three are gone. The offline suite uses
    :func:`execute_offline_bound_run`, and the gate is read from the process.

    This function now does exactly one thing beyond argument binding: mint the
    capability -- which reads ``sys.argv`` and ``os.environ`` itself and cannot
    be influenced by ``argv`` -- and hand it to the one real-model path.
    """

    args = build_parser().parse_args(list(argv) if argv is not None else None)

    # ---- 0. Offline-only verification. Contacts nothing, needs no gate. ----
    if args.verify_frozen_inputs:
        code, failures = verify_frozen_inputs()
        for failure in failures:
            print(failure, file=sys.stderr)
        print(
            f"Phase-P offline verification: {'PASS' if not failures else 'FAIL'} "
            f"({len(failures)} failure(s)); no provider contacted, no runtime probed, "
            "no directory created"
        )
        return code

    # ---- 1. HUMAN GATE. Nothing whatsoever happens before this passes. ----
    #
    # This is deliberately the FIRST thing after argument parsing: no config is
    # loaded, no path is bound, no provider object is constructed, no metadata is
    # probed and no directory is created until both conditions hold.
    #
    # It is evaluated against THIS PROCESS -- os.environ and sys.argv -- and not
    # against anything passed to this function.  ``argv`` can therefore change
    # which arguments are BOUND below; it cannot open the gate.
    refusal = _process_gate_refusal()
    if refusal is not None:
        print(refusal, file=sys.stderr)
        return protocol.EXIT_GATE_CLOSED
    if not args.execute_real_model:  # pragma: no cover - sys.argv already carries it
        print(
            f"EXECUTION REFUSED: {protocol.HUMAN_GATE_FLAG} is on this process's "
            "command line but was not parsed from the arguments this invocation "
            "was given; the two must agree.",
            file=sys.stderr,
        )
        return protocol.EXIT_GATE_CLOSED

    # ---- 1b. FROZEN SCIENTIFIC INPUT BINDING (Phase P-R1). ------------------
    #
    # The offline preflight proves the CANONICAL tree is intact.  It says nothing
    # about which files THIS INVOCATION was pointed at.  Before P-R1 a caller
    # could pass the canonical preflight and then hand ``--manifest`` a
    # structurally valid 17-case pilot-v7-rc4 look-alike, ``--config`` a
    # Phase-P-shaped config with a changed runtime setting, or ``--output-root``
    # an arbitrary namespace -- and the run would proceed while its persisted
    # provenance still described the canonical artifacts.
    #
    # These three options are therefore ASSERTIONS, not choices.  Each is proven
    # by canonical path equality AND by the SHA-256 the frozen-input record
    # accepted, and it happens before the preflight's own work, before the config
    # is parsed, before the namespace is inspected, before any metadata probe and
    # before any directory exists.  Anything else is refused outright: this CLI
    # has no noncanonical Phase-P execution mode.
    #
    # ``execute_authorized_real_run`` binds all three AGAIN, from the protocol
    # module and never from anything passed here, so the real-model path does not
    # depend on this check having happened.  What this check adds is a precise
    # refusal that names the argument the caller actually got wrong.
    try:
        protocol.require_canonical_input(
            protocol.CANONICAL_CONFIG_RELATIVE, args.config
        )
        protocol.require_canonical_input(
            protocol.CANONICAL_MANIFEST_RELATIVE, args.manifest
        )
        protocol.require_canonical_results_root(args.output_root)
    except protocol.ProtocolError as exc:
        print(f"IMMEDIATE_STOP: {exc}", file=sys.stderr)
        print(
            "NONCANONICAL_PHASE_P_EXECUTION: refused. 0 metadata probes, 0 cells "
            "executed, no results namespace created.",
            file=sys.stderr,
        )
        return protocol.EXIT_PREFLIGHT_STOP

    # ---- 1c. THE CAPABILITY (Phase P-R2). -----------------------------------
    #
    # Both gates were just proved; minting re-proves them from process state, so
    # this cannot hand out an authorization the gate would refuse -- and this
    # call passes NOTHING, so there is no argument that could influence it. From
    # here on the authority to contact a runtime travels as an object rather
    # than as an assumption about who is calling.
    try:
        authorization = grant_real_execution_authorization()
    except UnauthorizedRealExecution as exc:  # pragma: no cover - checked above
        print(str(exc), file=sys.stderr)
        return protocol.EXIT_GATE_CLOSED
    return execute_authorized_real_run(authorization=authorization)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CellExecutor",
    "CellExecutorFactory",
    "MetadataProbe",
    "REAL_EXECUTOR_MARKER",
    "RealExecutionAuthorization",
    "RuntimeMetadata",
    "UnauthorizedRealExecution",
    "build_parser",
    "check_advertised_instrument_contract",
    "check_arm_configuration",
    "check_experiment_configuration",
    "check_output_namespace",
    "describe_execution_inputs",
    "execute_authorized_real_run",
    "execute_offline_bound_run",
    "grant_real_execution_authorization",
    "human_gate_refusal",
    "lost_cell_row",
    "main",
    "make_cell_executor",
    "metadata_preflight",
    "read_frozen_model_declarations",
    "probe_ollama_metadata",
    "require_real_execution_authorization",
    "run_frozen_schedule",
    "stamp_frozen_identity",
    "verify_frozen_inputs",
]
