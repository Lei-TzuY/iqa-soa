"""Runtime-derived observed-fault provenance for the raw record.

Phase L-A stopped with ``HOLD_PHASE_L_PROTOCOL`` because the Phase-K.2
observed-fault contract could not be satisfied from anything the instrument
persisted for a QA-OFF cell.  ``scripts/qualification_harness.py`` requires four
fields on any row whose cell observed a sandbox fault::

    observed_fault_tool
    observed_fault_resource
    observed_fault_mode
    observed_fault_provenance

and it fails closed when they are absent.  Under QA OFF ``detailed_evidence`` is
unconditionally ``False``, so the evidence trace carries no ``tool_result``;
``SandboxState.operation_log`` reaches disk only inside an irreversible
fingerprint; and ``AgentRun.outcomes`` was never serialized at all.  Two of the
four fields were therefore unreachable, and every BUD-016 and FAULT-004 cell
would have been invalidated before a single token was generated.

This module closes that gap, and nothing else.  It derives the four fields from
the live :class:`~iqa_soa.types.GatewayOutcome` sequence while it is still in
memory in ``ExperimentRunner._run_one``, so the observation is a property of what
the sandbox actually did.

**The scientific invariant is enforced by this module's type signature.** Every
public function here accepts ``Sequence[GatewayOutcome]`` and nothing else.  It
cannot see :class:`~iqa_soa.benchmark.BenchmarkCase`, ``case.fault``,
``ground_truth``, the qualification contract, a ``ScriptedFault``, or a
task-id-to-fault table, because none of them is in scope.  An observation
manufactured from the declaration it is about to be compared against would prove
nothing, so the declaration is placed structurally out of reach rather than
merely discouraged by a comment.

This is RAW PROTOCOL TELEMETRY, not evidence-guard activation.  QA-OFF treatment
semantics are untouched: ``Treatment.detailed_evidence`` still returns ``False``
for :data:`~iqa_soa.types.QAMode.OFF`, the evidence guard is still disabled, and
no tool output, sentinel payload, protected value or operation log is persisted.
Only the tool name, the resource name, the sandbox's own one-word fault mode and
the name of the runtime structure they were read from leave this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from iqa_soa.types import GatewayOutcome

#: The gateway executed the action, and the fault was stamped on its result.
PROVENANCE_EXECUTED_ACTION = "gateway_outcome.executed_action"

#: Governance intercepted the action before execution, so there is no executed
#: action to read and the proposal is the only record of what was attempted.
#: Both labels are members of ``RUNTIME_FAULT_PROVENANCE_SOURCES`` in
#: ``scripts/qualification_harness.py``.
PROVENANCE_PROPOSED_ACTION = "gateway_outcome.proposed_action"

#: The four fields of the Phase-K.2 prospective raw-row contract.
OBSERVED_FAULT_FIELDS: tuple[str, ...] = (
    "observed_fault_tool",
    "observed_fault_resource",
    "observed_fault_mode",
    "observed_fault_provenance",
)

#: The complete set of columns this module contributes to the raw row.  The
#: count is a single non-sensitive integer that makes the collapse in
#: :func:`observed_fault_telemetry` legible: ``0`` means no runtime fault was
#: stamped anywhere in the run, ``1`` means exactly one distinct fault identity
#: was observed and is stamped, and any value ``>= 2`` means the run observed
#: DISAGREEING fault identities and the four fields are deliberately withheld.
#: Without it, a fail-closed ambiguity would be indistinguishable from a clean
#: no-fault run in the persisted record.
OBSERVED_FAULT_TELEMETRY_FIELDS: tuple[str, ...] = OBSERVED_FAULT_FIELDS + (
    "observed_fault_observation_count",
)


@dataclass(frozen=True, slots=True)
class RuntimeFaultObservation:
    """One fault the sandbox stamped on one actually-attempted action.

    Constructed only by :func:`runtime_fault_observations` from a live
    ``GatewayOutcome``.  There is deliberately no constructor path from a
    benchmark declaration.
    """

    tool: str
    resource: str
    mode: str
    provenance: str

    @property
    def identity(self) -> tuple[str, str, str, str]:
        """The full 4-tuple used to decide whether two observations agree.

        Provenance is part of the identity on purpose.  Two occurrences that
        agree on tool, resource and mode but were read from different runtime
        structures do not agree on where the observation came from, and the row
        carries exactly one provenance slot, so collapsing them would have to
        pick a label.  Treating that as a disagreement means the instrument
        never silently picks.
        """

        return (self.tool, self.resource, self.mode, self.provenance)


def _fault_mode(outcome: GatewayOutcome) -> str | None:
    """The sandbox's own fault stamp on this outcome's tool result, if any.

    ``ToolRegistry`` writes ``metadata["fault_mode"]`` at execution time --
    ``_fault_result`` for a declared fault, and the unregistered-tool and
    unsupported-mode branches for the two runtime faults the benchmark never
    declares.  All of them are genuine observations of sandbox behaviour and all
    of them are admitted here.  Filtering by which modes a benchmark happens to
    declare would reintroduce the declaration through the back door; an observed
    mode that does not match the declaration must reach the matcher and be
    refused there, not be suppressed here.

    A fault is never inferred.  A ``tool_timeout`` failure class, a
    ``"simulated tool timeout"`` error string and a ``fault_triggered`` flag are
    all ignored: only the sandbox's explicit stamp counts.
    """

    tool_result = outcome.tool_result
    if tool_result is None:
        return None
    metadata: Mapping[str, Any] = tool_result.metadata
    mode = metadata.get("fault_mode")
    if not isinstance(mode, str) or not mode.strip():
        return None
    return mode.strip()


def runtime_fault_observations(
    outcomes: Sequence[GatewayOutcome],
) -> tuple[RuntimeFaultObservation, ...]:
    """Every runtime-stamped fault in this run, in the order it occurred.

    The action is read from ``executed_action`` when the gateway ran it, and from
    ``proposed_action`` when governance blocked it before execution and there is
    therefore no executed action -- exactly the two runtime sources Phase K.2
    admits, and the provenance label names whichever was used.
    """

    observations: list[RuntimeFaultObservation] = []
    for outcome in outcomes:
        mode = _fault_mode(outcome)
        if mode is None:
            continue
        action = outcome.executed_action
        provenance = PROVENANCE_EXECUTED_ACTION
        if action is None:
            action = outcome.proposed_action
            provenance = PROVENANCE_PROPOSED_ACTION
        if action is None:  # pragma: no cover - GatewayOutcome always proposes
            continue
        if not action.tool or not action.resource:
            continue
        observations.append(
            RuntimeFaultObservation(
                tool=action.tool,
                resource=action.resource,
                mode=mode,
                provenance=provenance,
            )
        )
    return tuple(observations)


def distinct_fault_identities(
    outcomes: Sequence[GatewayOutcome],
) -> tuple[RuntimeFaultObservation, ...]:
    """Runtime fault observations collapsed to distinct identities, in order.

    Repetition of the SAME identity is agreement, not ambiguity.  BUD-016 is the
    concrete case: it declares one timeout on
    ``api.call:platform-api/service-health`` and scripts three calls to that
    endpoint, so a QA-OFF run stamps three identical timeout observations.  All
    three describe one fault, and reporting it once is a faithful summary rather
    than a choice between candidates.
    """

    seen: dict[tuple[str, str, str, str], RuntimeFaultObservation] = {}
    for observation in runtime_fault_observations(outcomes):
        seen.setdefault(observation.identity, observation)
    return tuple(seen.values())


def observed_fault_telemetry(
    outcomes: Sequence[GatewayOutcome],
) -> dict[str, Any]:
    """The observed-fault columns for one raw row, failing closed on ambiguity.

    * **No runtime fault stamped.** All four contract fields are ``None`` and the
      count is ``0``.  The row simply carries no observation, which the harness
      already treats as "cannot prove a designed fault".
    * **Exactly one distinct identity.** The four fields are stamped from it.
    * **Two or more DISTINCT identities.** The four fields are deliberately left
      ``None`` and the count records how many were seen.  The instrument does not
      pick one, because there is no non-arbitrary basis for picking and a chosen
      one would present genuinely ambiguous provenance as a clean single
      observation.  Withholding fails closed at ``observed_fault_from_row``,
      which refuses the row and yields ``UNEXPECTED_SANDBOX_FAILURE`` ->
      ``CELL_INVALID_AND_HOLD``.  A cell that observed two different sandbox
      faults SHOULD hold the verdict; that is the honest outcome, not a
      regression.

    The count is emitted in all three cases so ambiguity is never confused with
    absence by a later reader.
    """

    identities = distinct_fault_identities(outcomes)
    telemetry: dict[str, Any] = {
        "observed_fault_tool": None,
        "observed_fault_resource": None,
        "observed_fault_mode": None,
        "observed_fault_provenance": None,
        "observed_fault_observation_count": len(identities),
    }
    if len(identities) == 1:
        only = identities[0]
        telemetry.update(
            {
                "observed_fault_tool": only.tool,
                "observed_fault_resource": only.resource,
                "observed_fault_mode": only.mode,
                "observed_fault_provenance": only.provenance,
            }
        )
    return telemetry


__all__ = [
    "OBSERVED_FAULT_FIELDS",
    "OBSERVED_FAULT_TELEMETRY_FIELDS",
    "PROVENANCE_EXECUTED_ACTION",
    "PROVENANCE_PROPOSED_ACTION",
    "RuntimeFaultObservation",
    "distinct_fault_identities",
    "observed_fault_telemetry",
    "runtime_fault_observations",
]
