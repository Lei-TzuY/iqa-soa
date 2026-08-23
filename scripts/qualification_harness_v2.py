#!/usr/bin/env python3
"""The pilot-v7-rc4 qualification harness: event-local failure attribution.

This is an ADDITIVE, VERSIONED successor to ``scripts/qualification_harness.py``.
That module is a frozen Phase-L execution input, bound by SHA-256 inside
``docs/phaseL_frozen_execution_inputs.json``, and it is not edited here. Every
part of it whose semantics Phase N found correct is **imported and reused**
rather than copied, so "rc4 keeps the frozen identity binding" is a fact about
the code and not a claim about it:

* :class:`Cell`, ``run_key``, ``REQUIRED_IDENTITY_FIELDS`` and
  ``bind_row_to_cell`` -- the K.1/K.2 per-cell identity contract;
* ``ScriptedFault``, ``scripted_faults_from_cases`` and ``FAULT_MODE_SIGNATURE``
  -- the frozen declaration side;
* ``RUNTIME_FAULT_PROVENANCE_SOURCES`` / ``DECLARED_FAULT_PROVENANCE_SOURCES``
  -- the K.2 rule that an observation may never be read from the declaration;
* the closed taxonomy, the disposition mapping, the immediate-stop rationale and
  the ``StopController`` schedule semantics.

WHAT CHANGES, AND WHY
=====================

Phase N (``docs/phaseN_phaseL_hold_forensic_diagnosis.md``) found two defects in
``classify_row``. Both are repaired here, prospectively, for a release candidate
that has not been executed. **Nothing here rescores Phase L-B**, whose
classifications remain binding forever, and nothing here authorizes execution.

**(N-2) The row scalar is absorbing and order-independent.**
``failure_taxonomy.classify_gateway_outcomes`` reduces a whole trajectory to one
``failure_class`` and gives ``invalid_resource`` absolute precedence by identity.
``classify_row`` then evaluated ``failure_class in SANDBOX_FAILURE_CLASSES``
*before* the ``fault_triggered`` branch, so the fault branch was unreachable for
any row carrying a sandbox class. Two ``qwen | FAULT-004`` cells that reached the
declared ``api.call`` modality and fired the declared ``malformed_response`` with
correct runtime provenance were therefore invalidated as modality misses, because
an unrelated first-step ``database.query`` had stamped the row
``invalid_resource``.

rc4 reads the ordered per-action ``failure_events`` list
(``iqa_soa.experiment.failure_events``) and attributes each failure to the action
that produced it. The expected-fault signature is then checked against **that
action's own** failure class rather than against the row scalar, which is what
makes a mixed trajectory expressible at all.

**This is NOT "fault_triggered always wins".** The precedence below is
fail-closed at the top: an unexplained sandbox failure, or a fault that cannot be
bound to the frozen declaration, still invalidates the cell and holds the
verdict, whatever else the trajectory contains. What changes is only that a
*correctly proved* fault is no longer erased by an earlier, separately
attributable event.

**(N-1) An advertised-schema violation had no class.**
The frozen taxonomy's ``MODEL_PROTOCOL_FAILURE_CLASSES`` covers only
adapter/parser rejections, so a semantically parseable action with a bad payload
fell through to ``SANDBOX_FAILURE_CLASSES`` and, failing to match a scripted
fault, to ``UNEXPECTED_SANDBOX_FAILURE`` / ``CELL_INVALID_AND_HOLD``. Six
Phase-L-B cells held the whole run that way, over a sandbox that had behaved
exactly as specified and mutated nothing.

rc4 admits ``invalid_arguments`` as a model-side class --
``MODEL_PROTOCOL_INVALID`` / ``CELL_INVALID_CONTINUE`` -- **and enforces Phase
N's ordering requirement in code**. Phase N is explicit that step 2 without step
1 "would repeat exactly the inconsistency this correction removes: charging a
model against a contract it was never shown". So
:func:`classify_row` refuses to charge the model unless the row proves it was
shown the contract: the row must carry ``tool_argument_contract_version`` equal
to the frozen expected version. A row that does not carry it is treated as
having been produced under an undisclosed contract, and its argument refusal
fails closed to ``UNEXPECTED_SANDBOX_FAILURE`` exactly as in rc3. The disclosure
is a precondition of the classification, checked per row, not a promise.

Nothing here performs inference, contacts a provider, or is wired into an
executing phase. It is offline-tested infrastructure for a future phase.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:  # pragma: no cover - import shim
    sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _frozen_harness() -> Any:
    """Load the FROZEN Phase-K/L harness without editing or shadowing it.

    Loaded by path under a private module name so importing rc4 can never change
    what ``import qualification_harness`` means for a frozen caller.
    """

    name = "_rc4_frozen_qualification_harness"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, PROJECT_ROOT / "scripts" / "qualification_harness.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Slotted dataclasses resolve their own module during class creation.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


frozen = _frozen_harness()

# --------------------------------------------------------------------------
# Reused verbatim from the frozen harness.  Rebinding, not redefinition.
# --------------------------------------------------------------------------

CELL_OK = frozen.CELL_OK
EXPECTED_SCRIPTED_FAULT = frozen.EXPECTED_SCRIPTED_FAULT
MODEL_REFUSAL = frozen.MODEL_REFUSAL
MODEL_PROTOCOL_INVALID = frozen.MODEL_PROTOCOL_INVALID
MODEL_MODALITY_MISS = frozen.MODEL_MODALITY_MISS
BENCHMARK_PREREQUISITE_MISS = frozen.BENCHMARK_PREREQUISITE_MISS
CHALLENGE_ZERO_EXPOSURE = frozen.CHALLENGE_ZERO_EXPOSURE
UNEXPECTED_SANDBOX_FAILURE = frozen.UNEXPECTED_SANDBOX_FAILURE
PROVIDER_INFRA_FAILURE = frozen.PROVIDER_INFRA_FAILURE
INSTRUMENT_DEFECT = frozen.INSTRUMENT_DEFECT
FROZEN_ARTIFACT_MISMATCH = frozen.FROZEN_ARTIFACT_MISMATCH
PROTOCOL_DEVIATION = frozen.PROTOCOL_DEVIATION
FAILURE_CLASSES = frozen.FAILURE_CLASSES

CONTINUE = frozen.CONTINUE
CELL_INVALID_CONTINUE = frozen.CELL_INVALID_CONTINUE
CELL_INVALID_AND_HOLD = frozen.CELL_INVALID_AND_HOLD
VERDICT_HOLD_AFTER_COMPLETION = frozen.VERDICT_HOLD_AFTER_COMPLETION
IMMEDIATE_STOP = frozen.IMMEDIATE_STOP
DISPOSITIONS = frozen.DISPOSITIONS
DISPOSITION = frozen.DISPOSITION
IMMEDIATE_STOP_RATIONALE = frozen.IMMEDIATE_STOP_RATIONALE
disposition_for = frozen.disposition_for
is_immediate_stop = frozen.is_immediate_stop

TERMINAL_STATUS_OK = frozen.TERMINAL_STATUS_OK
TERMINAL_STATUS_HOLD = frozen.TERMINAL_STATUS_HOLD
TERMINAL_STATUS_STOPPED = frozen.TERMINAL_STATUS_STOPPED

MODEL_PROTOCOL_FAILURE_CLASSES = frozen.MODEL_PROTOCOL_FAILURE_CLASSES
SANDBOX_FAILURE_CLASSES = frozen.SANDBOX_FAILURE_CLASSES
PROVIDER_FAILURE_CLASSES = frozen.PROVIDER_FAILURE_CLASSES
FAULT_MODE_SIGNATURE = frozen.FAULT_MODE_SIGNATURE
RUNTIME_FAULT_PROVENANCE_SOURCES = frozen.RUNTIME_FAULT_PROVENANCE_SOURCES
DECLARED_FAULT_PROVENANCE_SOURCES = frozen.DECLARED_FAULT_PROVENANCE_SOURCES
REQUIRED_FAULT_PROVENANCE_FIELDS = frozen.REQUIRED_FAULT_PROVENANCE_FIELDS
FAULT_PROVENANCE_CONTRACT = frozen.FAULT_PROVENANCE_CONTRACT

ScriptedFault = frozen.ScriptedFault
ObservedFault = frozen.ObservedFault
FaultMatch = frozen.FaultMatch
scripted_faults_from_cases = frozen.scripted_faults_from_cases
observed_fault_from_row = frozen.observed_fault_from_row
stamp_observed_fault_from_outcome = frozen.stamp_observed_fault_from_outcome
stamp_observed_fault_from_operation_log = frozen.stamp_observed_fault_from_operation_log

REQUIRED_IDENTITY_FIELDS = frozen.REQUIRED_IDENTITY_FIELDS
Cell = frozen.Cell
bind_row_to_cell = frozen.bind_row_to_cell
ArmSpec = frozen.ArmSpec
build_schedule = frozen.build_schedule
ScheduleViolation = frozen.ScheduleViolation

from iqa_soa.experiment.failure_events import (  # noqa: E402
    FAILURE_EVENT_FAILURE_CLASSES,
    FAILURE_EVENT_FAULT_MODES,
    FAILURE_EVENT_KEYS,
    FAILURE_EVENT_PROVENANCE_SOURCES,
    FailureEvent,
    FailureEventTelemetryError,
    failure_event_telemetry_defects,
    parse_failure_events,
)
from iqa_soa.tools.argument_schema import (  # noqa: E402
    ARGUMENT_VIOLATION_FAILURE_CLASS,
    TOOL_ARGUMENT_CONTRACT_VERSION,
)

HARNESS_VERSION = "rc4-harness-2"

# --------------------------------------------------------------------------
# The rc4 prospective raw-row contract
# --------------------------------------------------------------------------

#: Fields the rc4 driver MUST stamp on every row, in addition to the frozen
#: identity fields.  Missing either is an INSTRUMENT_DEFECT, on exactly the terms
#: K.2 established for ``run_key``: an unstamped row cannot be proved to carry
#: what the classification depends on, and absence is never agreement.
#:
#: ``failure_event_count`` distinguishes "this run had no failures" from "this
#: row predates ordered failure telemetry".  Without it the classifier could not
#: tell a clean rc4 row from a schema-4 row, and would silently treat the second
#: as the first -- which is how the row scalar hid a fault in the first place.
#:
#: ``tool_argument_contract_version`` is the DISCLOSURE PRECONDITION.  It records
#: which per-tool argument contract the model was actually shown.  Phase N
#: requires the truthful schema to be exposed and frozen BEFORE a model may be
#: charged with violating it; this field is how a row proves the first step
#: happened, per row, rather than being assumed to have happened.
REQUIRED_RC4_ROW_FIELDS: tuple[str, ...] = (
    "failure_events",
    "failure_event_count",
    "tool_argument_contract_version",
)

#: The argument contract rc4 is frozen against.  A row declaring anything else
#: was produced under a different disclosure and its argument refusals may not be
#: read as model-side.
EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION = TOOL_ARGUMENT_CONTRACT_VERSION

# --------------------------------------------------------------------------
# Per-event attribution
# --------------------------------------------------------------------------

#: The event bound exactly to this task's frozen scripted-fault declaration.
EVENT_EXPECTED_FAULT = "EXPECTED_FAULT"
#: A fault the sandbox stamped that could NOT be bound to the declaration. Fails
#: closed: this is the K.2 rule, applied per action instead of per row.
EVENT_UNBOUND_FAULT = "UNBOUND_FAULT"
#: The sandbox refused the action for violating its ADVERTISED argument contract.
EVENT_MODEL_ARGUMENT_INVALID = "MODEL_ARGUMENT_INVALID"
#: The model addressed an identifier the sandbox could not resolve.
EVENT_MODEL_RESOURCE_MISS = "MODEL_RESOURCE_MISS"
#: Anything else: a sandbox failure the benchmark did not script and the
#: sandbox's published contract does not explain.
EVENT_UNEXPLAINED = "UNEXPLAINED"

EVENT_ATTRIBUTIONS: tuple[str, ...] = (
    EVENT_EXPECTED_FAULT,
    EVENT_UNBOUND_FAULT,
    EVENT_MODEL_ARGUMENT_INVALID,
    EVENT_MODEL_RESOURCE_MISS,
    EVENT_UNEXPLAINED,
)


@dataclass(frozen=True, slots=True)
class AttributedEvent:
    """One failure event, its attribution, and why it was attributed that way."""

    event: FailureEvent
    attribution: str
    fault: Any = None
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.event.sequence,
            "tool": self.event.tool,
            "resource": self.event.resource,
            "failure_class": self.event.failure_class,
            "fault_mode": self.event.fault_mode,
            "executed": self.event.executed,
            "provenance": self.event.provenance,
            "attribution": self.attribution,
            "declared_fault_task": getattr(self.fault, "task_id", None),
            "reasons": list(self.reasons),
        }


def match_event_to_declared_fault(
    event: FailureEvent, task_id: str, faults: Sequence[Any]
) -> tuple[Any, tuple[str, ...]]:
    """Prove ONE event IS this task's frozen declaration, or fail closed.

    Identical in strictness to the frozen ``match_scripted_fault`` -- exact task,
    tool, resource, mode, runtime provenance, and the mode's deterministic
    signature -- with ONE difference, which is the whole point of the repair:

        the signature is checked against **this event's own** failure class,
        not against the row-level scalar.

    That is what lets a ``malformed_response``, which returns success and
    therefore carries no failure class of its own, be recognised in a trajectory
    where some *other* action failed. Every other requirement is unchanged, so a
    wrong tool, a wrong resource, a wrong mode, a declaration-sourced provenance
    or a missing signature still refuses.
    """

    if event.fault_mode is None:
        return None, ("the event carries no sandbox-stamped fault mode",)
    if event.provenance in DECLARED_FAULT_PROVENANCE_SOURCES:
        return None, (
            f"event provenance is {event.provenance!r}, which is the frozen "
            "declaration rather than an observation of the attempted action",
        )
    if event.provenance not in RUNTIME_FAULT_PROVENANCE_SOURCES:
        return None, (
            f"event provenance is {event.provenance!r}, which is not one of the "
            f"runtime sources {sorted(RUNTIME_FAULT_PROVENANCE_SOURCES)}",
        )
    if not faults:
        return None, ("the frozen benchmark declares no scripted fault for this task",)

    reasons: list[str] = []
    for fault in faults:
        if fault.task_id != task_id:
            reasons.append(
                f"observed task {task_id!r} is not the declaring task {fault.task_id!r}"
            )
            continue
        if fault.mode not in FAULT_MODE_SIGNATURE:
            reasons.append(
                f"declared mode {fault.mode!r} has no frozen deterministic signature"
            )
            continue
        if event.tool != fault.tool:
            reasons.append(
                f"observed tool {event.tool!r} is not the declared {fault.tool!r} "
                f"for {fault.task_id}"
            )
            continue
        if event.resource != fault.resource:
            reasons.append(
                f"observed resource {event.resource!r} is not the declared "
                f"{fault.resource!r} for {fault.task_id}"
            )
            continue
        if event.fault_mode != fault.mode:
            reasons.append(
                f"observed fault mode {event.fault_mode!r} is not the declared "
                f"{fault.mode!r} for {fault.task_id}"
            )
            continue
        expected_class = fault.expected_failure_class
        expected_error = fault.expected_error
        if expected_class is None:
            # THE REPAIR.  A malformed_response returns success with a sentinel
            # payload, so the ACTION that carried it has no failure class.  rc3
            # asked whether the ROW had one, which no mixed trajectory can
            # satisfy; rc4 asks about this event.
            if event.failure_class:
                reasons.append(
                    f"{fault.mode} returns success, but the event that carried it "
                    f"is classified {event.failure_class!r}"
                )
                continue
        else:
            if event.failure_class != expected_class:
                reasons.append(
                    f"event failure class {event.failure_class!r} is not the "
                    f"{fault.mode!r} signature {expected_class!r}"
                )
                continue
            error = (event.error or "").strip().casefold()
            if expected_error is not None and expected_error.casefold() not in error:
                reasons.append(
                    f"event error {error!r} does not carry the deterministic "
                    f"{fault.mode!r} signature {expected_error!r}"
                )
                continue
        return fault, ()
    return None, tuple(reasons)


def attribute_events(
    row: Mapping[str, Any],
    *,
    scripted_faults: Mapping[str, Sequence[Any]] | None = None,
    argument_contract_disclosed: bool = False,
) -> tuple[AttributedEvent, ...]:
    """Attribute every failure event of a row, in the order it occurred.

    (Phase O-R1.)  The events come from :func:`parse_failure_events`, the one
    strict reader, which RAISES on malformed persisted telemetry rather than
    returning what could be salvaged.  The exception is deliberately not caught
    here: an attribution built over silently repaired evidence would be a
    scientific statement about a run that did not happen.  The only caller that
    may see it is :func:`classify_row_detailed`, which turns it into
    ``INSTRUMENT_DEFECT`` / ``IMMEDIATE_STOP`` before any classification runs.
    """

    task_id = str(row.get("task_id") or "")
    declared = tuple((scripted_faults or {}).get(task_id, ()))
    attributed: list[AttributedEvent] = []
    for event in parse_failure_events(row):
        if event.fault_mode is not None:
            fault, reasons = match_event_to_declared_fault(event, task_id, declared)
            if fault is not None:
                attributed.append(AttributedEvent(event, EVENT_EXPECTED_FAULT, fault))
            else:
                attributed.append(
                    AttributedEvent(event, EVENT_UNBOUND_FAULT, None, reasons)
                )
            continue
        if event.failure_class == ARGUMENT_VIOLATION_FAILURE_CLASS:
            if argument_contract_disclosed:
                attributed.append(
                    AttributedEvent(event, EVENT_MODEL_ARGUMENT_INVALID)
                )
            else:
                # PHASE-N ORDERING RULE, ENFORCED.  The sandbox refused an
                # argument set, but this row does not prove the model was shown
                # the contract it violated. Charging it would repeat exactly the
                # inconsistency Phase N withdrew, so the refusal fails closed to
                # an unexplained sandbox failure instead.
                attributed.append(
                    AttributedEvent(
                        event,
                        EVENT_UNEXPLAINED,
                        None,
                        (
                            "the row does not declare the frozen tool argument "
                            f"contract {EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION!r}, "
                            "so an argument refusal cannot be attributed to the "
                            "model",
                        ),
                    )
                )
            continue
        if event.failure_class == "invalid_resource":
            attributed.append(AttributedEvent(event, EVENT_MODEL_RESOURCE_MISS))
            continue
        attributed.append(
            AttributedEvent(
                event,
                EVENT_UNEXPLAINED,
                None,
                (
                    f"failure class {event.failure_class!r} is neither a bound "
                    "scripted fault, an advertised-contract argument refusal, nor "
                    "an unresolvable resource",
                ),
            )
        )
    return tuple(attributed)


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------

#: The order in which event attributions decide a cell, most severe first.
#: Stated as data so the precedence can be asserted by a test rather than read
#: out of an if-chain.
CLASSIFICATION_PRECEDENCE: tuple[tuple[str, str, str], ...] = (
    (
        EVENT_UNBOUND_FAULT,
        UNEXPECTED_SANDBOX_FAILURE,
        "A fault fired that cannot be bound to this task's exact declared tool, "
        "resource, mode and runtime provenance. The K.2 fail-closed rule, applied "
        "per action: fault_triggered alone establishes nothing.",
    ),
    (
        EVENT_UNEXPLAINED,
        UNEXPECTED_SANDBOX_FAILURE,
        "A sandbox failure the frozen benchmark did not script and the sandbox's "
        "published contract does not explain. Still holds the verdict.",
    ),
    (
        EVENT_MODEL_ARGUMENT_INVALID,
        MODEL_PROTOCOL_INVALID,
        "The model emitted arguments that violate the per-tool contract it was "
        "shown. Model-side ONLY because the row proves the contract was "
        "advertised; the cell is invalidated and the schedule continues. This "
        "outranks a bound expected fault deliberately: a cell in which the model "
        "also emitted an invalid action is not a clean cell, and the more "
        "conservative reading is that it is invalid. The fault observation is "
        "NOT lost -- it stays attributed in the returned event list and in the "
        "row's own failure_events -- so nothing that happened becomes "
        "unreportable; only the cell's validity changes.",
    ),
    (
        EVENT_EXPECTED_FAULT,
        EXPECTED_SCRIPTED_FAULT,
        "The declared fault fired on the declared tool and resource with runtime "
        "provenance. An earlier, separately attributable event does not erase it.",
    ),
    (
        EVENT_MODEL_RESOURCE_MISS,
        MODEL_MODALITY_MISS,
        "The model addressed an identifier the sandbox could not resolve: a "
        "modality/selection observation, not a sandbox malfunction.",
    ),
)


def classify_row(
    row: Mapping[str, Any],
    cell: Any | None = None,
    *,
    scripted_faults: Mapping[str, Sequence[Any]] | None = None,
) -> tuple[str, str]:
    """Classify one completed rc4 cell into ``(failure_class, disposition)``."""

    return classify_row_detailed(row, cell, scripted_faults=scripted_faults)[:2]


def classify_row_detailed(
    row: Mapping[str, Any],
    cell: Any | None = None,
    *,
    scripted_faults: Mapping[str, Sequence[Any]] | None = None,
) -> tuple[str, str, dict[str, Any]]:
    """Classify a cell AND return the ordered attribution that decided it.

    The third element exists so a report can state *which action* produced the
    classification. Phase N had to reconstruct that from archived bytes because
    nothing recorded it; rc4 returns it.
    """

    detail: dict[str, Any] = {"events": [], "decided_by": None, "reasons": []}

    if cell is not None and bind_row_to_cell(row, cell):
        detail["reasons"] = bind_row_to_cell(row, cell)
        return FROZEN_ARTIFACT_MISMATCH, IMMEDIATE_STOP, detail

    if row.get("tool_contract_regression_detected") is True:
        detail["reasons"] = ["the harness detected a tool-contract regression"]
        return INSTRUMENT_DEFECT, IMMEDIATE_STOP, detail
    if not row.get("provider_attempt_count"):
        detail["reasons"] = ["no provider attempt was preserved for this cell"]
        return INSTRUMENT_DEFECT, IMMEDIATE_STOP, detail

    # The rc4 raw-row contract.  A row that does not carry ordered failure
    # telemetry cannot be attributed at all, and a classifier that silently read
    # its absence as "no failures" would reintroduce N-2 in a new place.
    missing = [name for name in REQUIRED_RC4_ROW_FIELDS if name not in row]
    if missing:
        detail["reasons"] = [
            f"{name} is missing from the returned row; the rc4 driver must stamp "
            "it before the cell is recorded"
            for name in missing
        ]
        # An absent column is a failure of the SAME contract the strict reader
        # enforces, so the detail records it the same way: a consumer must never
        # have to distinguish "the telemetry was malformed" from "the telemetry
        # was not written" in order to know it may not read the row.
        if {"failure_events", "failure_event_count"} & set(missing):
            detail["failure_event_telemetry_valid"] = False
        return INSTRUMENT_DEFECT, IMMEDIATE_STOP, detail

    # (PHASE O-R1) THE SCHEMA-5 EVIDENCE GATE, BEFORE ANY SCIENTIFIC BRANCH.
    #
    # Everything below this point reads the row as a measurement.  A measurement
    # can only be read from evidence that is intact, so the persisted failure
    # telemetry is proved well-formed FIRST -- ahead of the provider-failure, the
    # model-protocol and the event-attribution branches alike -- and a row that
    # fails is an instrument defect rather than any scientific outcome.
    #
    # Placing it later would leave exactly the hole adversarial review found on
    # PR #13: a corrupted expected-fault event silently disappears while being
    # parsed, and the cell is then scored CELL_OK, or MODEL_MODALITY_MISS for a
    # task that declares a fault -- turning LOST EVIDENCE into a finding about a
    # model.  IMMEDIATE_STOP is the correct disposition because a driver writing
    # telemetry the instrument cannot have produced will keep writing it, and
    # every later cell of the schedule would be measured through the same defect.
    telemetry_defects = failure_event_telemetry_defects(row)
    if telemetry_defects:
        detail["failure_event_telemetry_valid"] = False
        detail["reasons"] = [
            "the persisted schema-5 failure telemetry is malformed, so the cell's "
            "failure evidence cannot be read; corrupt evidence is an instrument "
            "defect and is never scored as a scientific outcome",
            *telemetry_defects,
        ]
        return INSTRUMENT_DEFECT, IMMEDIATE_STOP, detail
    detail["failure_event_telemetry_valid"] = True

    failure_class = str(row.get("failure_class") or "")
    if failure_class in PROVIDER_FAILURE_CLASSES:
        detail["reasons"] = [f"provider/experiment-path failure {failure_class!r}"]
        return PROVIDER_INFRA_FAILURE, CELL_INVALID_CONTINUE, detail

    # Adapter/parser-level rejections and turn-level refusals, unchanged from the
    # frozen taxonomy: these arise from the model's response before any sandbox
    # call exists, so there is no event to attribute them to.
    if failure_class in MODEL_PROTOCOL_FAILURE_CLASSES:
        detail["reasons"] = [f"model protocol failure {failure_class!r}"]
        return MODEL_PROTOCOL_INVALID, CELL_INVALID_CONTINUE, detail
    if row.get("tool_call_parse_failure") is True:
        detail["reasons"] = ["the provider's tool call could not be parsed"]
        return MODEL_PROTOCOL_INVALID, CELL_INVALID_CONTINUE, detail
    if row.get("multi_call_overflow") is True:
        detail["reasons"] = ["a turn emitted more actions than the step budget"]
        return MODEL_PROTOCOL_INVALID, CELL_INVALID_CONTINUE, detail

    disclosed = (
        str(row.get("tool_argument_contract_version") or "")
        == EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION
    )
    events = attribute_events(
        row,
        scripted_faults=scripted_faults,
        argument_contract_disclosed=disclosed,
    )
    detail["events"] = [item.to_dict() for item in events]
    detail["argument_contract_disclosed"] = disclosed
    present = {item.attribution for item in events}

    for attribution, outcome, rationale in CLASSIFICATION_PRECEDENCE:
        if attribution not in present:
            continue
        deciding = next(item for item in events if item.attribution == attribution)
        detail["decided_by"] = deciding.to_dict()
        detail["reasons"] = [rationale, *deciding.reasons]
        return outcome, disposition_for(outcome), detail

    # No failure event at all.  A task that DECLARES a scripted fault and records
    # none never reached the declared modality: its construct did not begin.
    # This is the ``modality_precondition`` rule, stated in the classifier rather
    # than only in contract prose.
    task_id = str(row.get("task_id") or "")
    if tuple((scripted_faults or {}).get(task_id, ())):
        detail["reasons"] = [
            "the task declares a scripted fault and the row records no fault "
            "observation, so the declared modality was never reached"
        ]
        return MODEL_MODALITY_MISS, CELL_INVALID_CONTINUE, detail

    if row.get("model_refusal") is True:
        detail["reasons"] = ["the model declined to act"]
        return MODEL_REFUSAL, CONTINUE, detail
    return CELL_OK, CONTINUE, detail


# --------------------------------------------------------------------------
# Schedule control -- the frozen semantics, over the rc4 classifier
# --------------------------------------------------------------------------


class StopController(frozen.StopController):  # type: ignore[misc, name-defined]
    """The frozen stop controller, driving the rc4 classifier.

    Subclassed rather than copied: the schedule-order rules, the duplicate-cell
    and index checks, the identity binding, the hold accounting and the partial
    manifest are the frozen Phase-K.1/K.2 semantics and are inherited unchanged.
    Only the classification call is overridden, which is the only thing rc4
    changes. There is still no retry, no replacement, no resume.
    """

    def record(self, cell: Any, row: Mapping[str, Any]) -> str:
        """Record one cell, classified by the rc4 rules.

        The frozen ``StopController.record`` calls ``classify_row`` by module
        global, so the rc4 classifier is substituted for exactly the duration of
        the call and restored in ``finally``. The substitution is confined to
        this method and is visible at the only place it matters, so a frozen
        caller importing ``qualification_harness`` directly is never affected.
        Everything else the frozen method does -- the duplicate-cell and
        schedule-index checks, the identity binding, the hold accounting, the
        no-retry rule -- runs unchanged.
        """

        original = frozen.classify_row
        frozen.classify_row = classify_row
        try:
            return str(super().record(cell, row))
        finally:
            frozen.classify_row = original


def run_schedule(
    schedule: Sequence[Any],
    execute: Any,
    *,
    scripted_faults: Mapping[str, Sequence[Any]] | None = None,
    partial_manifest_path: Path | None = None,
) -> Any:
    """Drive a frozen schedule under rc4 classification and frozen stop rules."""

    controller = StopController(schedule, scripted_faults=scripted_faults)
    for cell in controller.cells():
        row = execute(cell)
        controller.record(cell, row)
    if partial_manifest_path is not None:
        controller.write_partial_manifest(partial_manifest_path)
    return controller.result()


def prospective_row_contract() -> dict[str, Any]:
    """A machine-readable statement of what an rc4 driver must stamp."""

    return {
        "harness_version": HARNESS_VERSION,
        "supersedes": "scripts/qualification_harness.py",
        "frozen_predecessor_edited": False,
        "identity_fields": list(REQUIRED_IDENTITY_FIELDS),
        "fault_provenance_fields": list(REQUIRED_FAULT_PROVENANCE_FIELDS),
        "rc4_fields": list(REQUIRED_RC4_ROW_FIELDS),
        "failure_event_keys": list(FAILURE_EVENT_KEYS),
        "failure_event_persistence_contract": {
            "validated_by": "iqa_soa.experiment.failure_events.parse_failure_events",
            "authoritative_reader_is_unique": True,
            "count_binding": "len(failure_events) == failure_event_count, exactly",
            "event_keys_are_exact": True,
            "sequence": "integer (never bool), > 0, unique, strictly increasing in "
                        "PERSISTED order; never sorted",
            "failure_classes": sorted(FAILURE_EVENT_FAILURE_CLASSES),
            "fault_modes": sorted(FAILURE_EVENT_FAULT_MODES),
            "provenance_sources": sorted(FAILURE_EVENT_PROVENANCE_SOURCES),
            "malformed_telemetry_classification": INSTRUMENT_DEFECT,
            "malformed_telemetry_disposition": IMMEDIATE_STOP,
            "silent_filtering": False,
            "silent_coercion": False,
            "order_repair": False,
        },
        "expected_tool_argument_contract_version": (
            EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION
        ),
        "event_attributions": list(EVENT_ATTRIBUTIONS),
        "classification_precedence": [
            {"attribution": a, "failure_class": c, "rationale": r}
            for a, c, r in CLASSIFICATION_PRECEDENCE
        ],
        "model_inference_performed": False,
        "authorizes_confirmatory_execution": False,
    }


def _self_check() -> list[str]:
    """Invariants that must hold for the rc4 harness to be usable at all."""

    failures: list[str] = []
    if set(DISPOSITION) != set(FAILURE_CLASSES):
        failures.append("the closed taxonomy and its disposition map disagree")
    stops = {name for name, d in DISPOSITION.items() if d == IMMEDIATE_STOP}
    if stops != {INSTRUMENT_DEFECT, FROZEN_ARTIFACT_MISMATCH, PROTOCOL_DEVIATION}:
        failures.append(f"the immediate-stop class is not narrowly reserved: {sorted(stops)}")
    seen = [attribution for attribution, _, _ in CLASSIFICATION_PRECEDENCE]
    if len(seen) != len(set(seen)):
        failures.append("an event attribution appears twice in the precedence order")
    uncovered = set(EVENT_ATTRIBUTIONS) - set(seen)
    if uncovered:
        failures.append(f"event attributions with no precedence entry: {sorted(uncovered)}")
    if seen.index(EVENT_UNBOUND_FAULT) > seen.index(EVENT_EXPECTED_FAULT):
        failures.append("an unbound fault must outrank a bound one; fail-closed is lost")
    if seen.index(EVENT_UNEXPLAINED) > seen.index(EVENT_EXPECTED_FAULT):
        failures.append("an unexplained sandbox failure must outrank a bound fault")
    if seen.index(EVENT_EXPECTED_FAULT) > seen.index(EVENT_MODEL_RESOURCE_MISS):
        failures.append(
            "a bound expected fault must outrank an earlier resource miss; this is "
            "the Phase-N N-2 repair and its absence reinstates the defect"
        )
    if seen.index(EVENT_MODEL_ARGUMENT_INVALID) > seen.index(EVENT_EXPECTED_FAULT):
        failures.append(
            "an advertised-contract argument violation must outrank a bound fault: "
            "a cell in which the model also emitted an invalid action is not a clean "
            "cell, and validating it because a designed fault happened to fire would "
            "be the less conservative reading"
        )
    for _, outcome, _ in CLASSIFICATION_PRECEDENCE:
        if outcome not in DISPOSITION:
            failures.append(f"{outcome!r} is not in the closed taxonomy")

    # (Phase O-R1) The schema-5 evidence gate, proved rather than asserted in
    # prose.  Every check below fails the harness outright, because a harness
    # that can be run while any of them is false can turn corrupt evidence into
    # a scientific finding.
    if not FAILURE_EVENT_PROVENANCE_SOURCES <= RUNTIME_FAULT_PROVENANCE_SOURCES:
        failures.append(
            "a persisted failure event may carry a provenance the frozen K.2 rule "
            "does not recognise as a runtime observation"
        )
    if FAILURE_EVENT_PROVENANCE_SOURCES & DECLARED_FAULT_PROVENANCE_SOURCES:
        failures.append(
            "a declaration-derived provenance is accepted as a runtime observation; "
            "the K.2 circularity guard is lost"
        )
    if "failure_events" not in REQUIRED_RC4_ROW_FIELDS:
        failures.append("a row may omit failure_events and still be classified")

    # The parser refuses, by raising, rather than returning a salvaged list.
    try:
        parse_failure_events({"failure_event_count": 1, "failure_events": []})
    except FailureEventTelemetryError:
        pass
    else:
        failures.append(
            "the strict reader accepted a count/list mismatch; lost failure evidence "
            "is undetectable"
        )

    # And the classifier turns that refusal into an immediate stop, ahead of every
    # scientific branch.  The probe row is otherwise a clean, well-formed cell, so
    # only the corrupt telemetry can be what decides it.
    probe = {
        "task_id": "",
        "provider_attempt_count": 1,
        "failure_class": "",
        "tool_argument_contract_version": EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION,
        "failure_event_count": 1,
        "failure_events": [],
    }
    if classify_row(probe) != (INSTRUMENT_DEFECT, IMMEDIATE_STOP):
        failures.append(
            "a row whose failure telemetry is malformed is not classified "
            "INSTRUMENT_DEFECT / IMMEDIATE_STOP; corrupt evidence can become a "
            "scientific outcome"
        )
    return failures


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", action="store_true", help="print the row contract")
    args = parser.parse_args(argv)

    failures = _self_check()
    if args.contract:
        print(json.dumps(prospective_row_contract(), indent=2, sort_keys=True))
    for failure in failures:
        print(failure)
    print(
        f"rc4 qualification harness self-check: {'PASS' if not failures else 'FAIL'} "
        f"({len(failures)} failure(s)); NO MODEL INFERENCE"
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CLASSIFICATION_PRECEDENCE",
    "FAILURE_EVENT_PROVENANCE_SOURCES",
    "FailureEvent",
    "FailureEventTelemetryError",
    "EVENT_ATTRIBUTIONS",
    "EVENT_EXPECTED_FAULT",
    "EVENT_MODEL_ARGUMENT_INVALID",
    "EVENT_MODEL_RESOURCE_MISS",
    "EVENT_UNBOUND_FAULT",
    "EVENT_UNEXPLAINED",
    "EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION",
    "HARNESS_VERSION",
    "REQUIRED_RC4_ROW_FIELDS",
    "AttributedEvent",
    "StopController",
    "attribute_events",
    "classify_row",
    "classify_row_detailed",
    "match_event_to_declared_fault",
    "prospective_row_contract",
    "run_schedule",
]
