"""Stable, outcome-preserving failure classes for real-model experiments."""

from __future__ import annotations

from collections.abc import Iterable

# Imported from the module, not the ``iqa_soa.tools`` package, so this stays a
# leaf import: ``iqa_soa.tools.__init__`` pulls in the registry, which would make
# the dependency circular for no benefit.  ``argument_schema`` itself imports
# nothing from the runtime.
from iqa_soa.tools.argument_schema import (
    ARGUMENT_VIOLATION_ERROR_PREFIX,
    ARGUMENT_VIOLATION_FAILURE_CLASS,
)
from iqa_soa.types import GatewayOutcome


# These arise from the model's response or from a sandbox action it requested.
# They remain in descriptive pilot analysis and never become infrastructure
# successes merely because a governed execution did not complete.
SCIENTIFIC_FAILURE_CLASSES = frozenset(
    {
        "model_refusal",
        "invalid_json",
        "invalid_action_format",
        "invalid_tool_call",
        # The model emitted more tool calls in one turn than the
        # remaining agent-step budget could consume.  It arises from the
        # model's response, and the turn is refused whole rather than
        # partially executed, so no proposal is silently discarded.
        "multi_call_overflow",
        "invalid_resource",
        # (Phase O) The sandbox refused a proposal for violating the per-tool
        # argument contract it ADVERTISES.  Phase N showed the frozen taxonomy
        # had no class for "the sandbox correctly refused a model-supplied
        # argument set": such a refusal fell through to the generic
        # ``tool_failure`` and from there to the harness's
        # ``UNEXPECTED_SANDBOX_FAILURE`` / ``CELL_INVALID_AND_HOLD``, which
        # reserves itself for UNEXPLAINED sandbox failures.  Six Phase-L-B cells
        # held the whole run that way.  The class is model-side, and it may only
        # be read as model-side because Phase O publishes the requirement first
        # (``iqa_soa.tools.argument_schema``); classifying a hidden-contract
        # rejection against the model is what Phase N explicitly refused to do.
        "invalid_arguments",
        "tool_failure",
        "tool_timeout",
    }
)

# These identify a failure of the experiment/provider path itself.  They are
# preserved, but prevent an otherwise-complete pilot from entering standard
# descriptive analysis unless explicitly allowed.
INFRASTRUCTURE_FAILURE_CLASSES = frozenset(
    {
        "provider_error",
        "rate_limit",
        "timeout",
        "benchmark_failure",
        "qa_failure",
        "analysis_failure",
    }
)


# (Phase O-R1) The closed set of classes ONE sandbox action can carry.
#
# ``classify_gateway_outcomes`` summarises a whole trajectory and may therefore
# be handed any scientific class; a single ACTION is narrower.  Exactly two
# things can set an event's class: the sandbox's own
# ``metadata["failure_class"]`` stamp, which today is only
# ``invalid_arguments``, and ``classify_tool_error`` below, whose complete
# range is the remaining three.  Every other member of
# ``SCIENTIFIC_FAILURE_CLASSES`` -- ``model_refusal``, ``invalid_json``,
# ``invalid_action_format``, ``invalid_tool_call``, ``multi_call_overflow`` --
# arises from the model's RESPONSE before any sandbox call exists, so no
# per-action failure event can legitimately carry one.
#
# This is the vocabulary ``iqa_soa.experiment.failure_events`` validates a
# PERSISTED event against.  A persisted event naming anything outside it was not
# written by this instrument, and reading it as though it were would be exactly
# the evidence-loss class Phase N found.  ``_self_check`` below proves the set
# stays a subset of the scientific taxonomy and stays equal to what
# ``classify_tool_error`` can actually return.
SANDBOX_ACTION_FAILURE_CLASSES: frozenset[str] = frozenset(
    {
        ARGUMENT_VIOLATION_FAILURE_CLASS,
        "invalid_resource",
        "tool_timeout",
        "tool_failure",
    }
)

assert SANDBOX_ACTION_FAILURE_CLASSES <= SCIENTIFIC_FAILURE_CLASSES, (
    "a per-action failure class must be a member of the closed scientific taxonomy"
)


def classify_tool_error(error: str | None) -> str | None:
    """Classify a sandbox failure without reinterpreting its safety metrics."""

    if error is None or not error.strip():
        return None
    normalized = error.casefold()
    # (Phase O) An advertised-contract violation is matched on the sandbox's own
    # deterministic prefix rather than on prose, so the classification cannot
    # drift with the wording of a message.  The prefix is new in Phase O, so no
    # historical error string can match it and no committed row is reclassified.
    if normalized.startswith(ARGUMENT_VIOLATION_ERROR_PREFIX.casefold()):
        return ARGUMENT_VIOLATION_FAILURE_CLASS
    if "not found" in normalized and (
        "resource" in normalized or "file" in normalized or "database" in normalized
    ):
        return "invalid_resource"
    if "timeout" in normalized:
        return "tool_timeout"
    return "tool_failure"


def infer_legacy_failure_class(error: str | None) -> str | None:
    """Infer only an unambiguous known sandbox error from immutable old rows."""

    if error is None:
        return None
    normalized = error.casefold()
    if "sandbox" not in normalized:
        return None
    if "not found" in normalized and (
        "resource" in normalized or "file" in normalized or "database" in normalized
    ):
        return "invalid_resource"
    return None


def classify_gateway_outcomes(outcomes: Iterable[GatewayOutcome]) -> tuple[str | None, str | None]:
    """Return the first classified tool failure and its preserved error text.

    .. warning::

       **This scalar is lossy, and Phase O did not change it.** Phase N finding
       N-2 established two defects in the rule below: ``invalid_resource``
       outranks every other class purely by identity, and where in a trajectory a
       failure occurred is not represented at all.  A trajectory that missed a
       resource and then fired its declared fault is summarised as
       ``invalid_resource``, which made a proved fault invisible in two Phase-L-B
       cells.

       The rule is deliberately left byte-compatible in behaviour, because every
       committed Phase-B..L row was written under it and re-ranking it now would
       silently change what those rows mean.  A caller that needs to attribute a
       failure to an ACTION rather than to a run must read the ordered events
       from ``iqa_soa.experiment.failure_events`` instead.  This function remains
       the backward-compatible run-level summary and nothing more.
    """

    errors: list[str] = []
    classes: list[str] = []
    for outcome in outcomes:
        tool_result = outcome.tool_result
        error = outcome.error or (tool_result.error if tool_result is not None else None)
        if error is None:
            continue
        errors.append(str(error))
        failure_class = classify_tool_error(str(error))
        if failure_class is not None:
            classes.append(failure_class)
    if not errors:
        return None, None
    # Invalid model resource references are more specific than a generic tool
    # failure; otherwise preserve occurrence order.
    failure_class = "invalid_resource" if "invalid_resource" in classes else classes[0]
    return failure_class, "; ".join(errors)


__all__ = [
    "INFRASTRUCTURE_FAILURE_CLASSES",
    "SANDBOX_ACTION_FAILURE_CLASSES",
    "SCIENTIFIC_FAILURE_CLASSES",
    "classify_gateway_outcomes",
    "infer_legacy_failure_class",
    "classify_tool_error",
]
