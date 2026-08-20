"""Stable, outcome-preserving failure classes for real-model experiments."""

from __future__ import annotations

from collections.abc import Iterable

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
        "invalid_resource",
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


def classify_tool_error(error: str | None) -> str | None:
    """Classify a sandbox failure without reinterpreting its safety metrics."""

    if error is None or not error.strip():
        return None
    normalized = error.casefold()
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
    """Return the first classified tool failure and its preserved error text."""

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
    "SCIENTIFIC_FAILURE_CLASSES",
    "classify_gateway_outcomes",
    "infer_legacy_failure_class",
    "classify_tool_error",
]
