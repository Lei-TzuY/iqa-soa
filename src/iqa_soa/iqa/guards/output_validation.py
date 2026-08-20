"""Lightweight deterministic action-payload and tool-result validation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from time import perf_counter
from typing import TYPE_CHECKING, Any

from iqa_soa.iqa.guards.base import QAGuard
from iqa_soa.iqa.guards.privacy import OUTBOUND_TOOLS
from iqa_soa.types import Action, Decision, GuardResult, RuntimeContext, ToolResult

if TYPE_CHECKING:  # pragma: no cover
    from iqa_soa.iqa.policy import Policy


def _dump(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return str(value)


def _payload(action: Action) -> Any:
    for key in ("payload", "body", "message", "content", "data"):
        if key in action.arguments:
            return action.arguments[key]
    return action.arguments


class OutputValidationGuard(QAGuard):
    name = "output_validation"
    order = 50
    phases = frozenset({"pre", "post"})

    def evaluate(
        self,
        action: Action,
        context: RuntimeContext,
        policy: Policy,
        *,
        tool_result: ToolResult | None = None,
        phase: str = "pre",
    ) -> GuardResult:
        started = perf_counter()
        output_policy = getattr(policy, "output_validation", None)
        forbidden = tuple(getattr(output_policy, "forbidden_values", ())) + tuple(
            context.metadata.get("forbidden_output_values", ())
        )
        required_fields = tuple(getattr(output_policy, "required_fields", ())) + tuple(
            context.metadata.get("required_output_fields", ())
        )
        policy_id = getattr(policy, "policy_id", None)
        policy_format = getattr(output_policy, "required_format", None)
        require_tool_support = bool(
            getattr(output_policy, "require_tool_support", False)
        )

        referenced_ids = {
            str(item)
            for item in context.metadata.get("referenced_tool_result_ids", ())
        }
        supported_ids = {
            str(item)
            for item in context.metadata.get("supported_tool_result_ids", ())
        }
        unsupported_ids = sorted(referenced_ids.difference(supported_ids))
        unsupported_signal = bool(context.metadata.get("unsupported_tool_result", False))

        if phase == "pre" or tool_result is None:
            if require_tool_support and (unsupported_signal or unsupported_ids):
                return self.result(
                    Decision.BLOCK,
                    "outbound claim references an unsupported tool result",
                    started_at=started,
                    severity="high",
                    matched_policy=(
                        f"{policy_id}:output:tool-support"
                        if policy_id
                        else "output:tool-support"
                    ),
                    metadata={
                        "phase": "pre",
                        "unsupported_reference": True,
                        "unsupported_result_ids": unsupported_ids,
                    },
                )
            if action.tool in OUTBOUND_TOOLS:
                serialized = _dump(_payload(action))
                if any(str(item) and str(item) in serialized for item in forbidden):
                    return self.result(
                        Decision.BLOCK,
                        "outbound payload contains a forbidden deterministic value",
                        started_at=started,
                        severity="high",
                        matched_policy=(
                            f"{policy_id}:output:forbidden-value"
                            if policy_id
                            else "output:forbidden-value"
                        ),
                        metadata={"forbidden_value_matched": True, "phase": "pre"},
                    )
                expected_outbound_format = context.metadata.get(
                    "outbound_payload_format", policy_format
                )
                if expected_outbound_format and not self._format_valid(
                    _payload(action), str(expected_outbound_format)
                ):
                    return self.result(
                        Decision.BLOCK,
                        f"outbound payload violates {expected_outbound_format} format",
                        started_at=started,
                        severity="high",
                        matched_policy=(
                            f"{policy_id}:output:format" if policy_id else "output:format"
                        ),
                        metadata={"phase": "pre", "expected_format": expected_outbound_format},
                    )
            return self.result(
                Decision.ALLOW,
                "outbound payload checks passed",
                started_at=started,
                matched_policy=(f"{policy_id}:output" if policy_id else None),
                metadata={"phase": "pre"},
            )

        fault_mode = tool_result.metadata.get("fault_mode")
        if require_tool_support and tool_result.metadata.get("supported") is False:
            return self.result(
                Decision.BLOCK,
                "tool result is explicitly marked unsupported",
                started_at=started,
                severity="high",
                matched_policy=(
                    f"{policy_id}:output:tool-support"
                    if policy_id
                    else "output:tool-support"
                ),
                metadata={"phase": "post", "unsupported_tool_result": True},
            )
        if tool_result.metadata.get("malformed") or fault_mode == "malformed_response":
            return self.result(
                Decision.BLOCK,
                "tool returned a deterministically malformed response",
                started_at=started,
                severity="high",
                matched_policy=(f"{policy_id}:output:well-formed" if policy_id else "output:well-formed"),
                metadata={"phase": "post", "fault_mode": fault_mode},
            )
        if not tool_result.success or tool_result.error is not None:
            return self.result(
                Decision.ESCALATE,
                "tool result reports an execution error",
                started_at=started,
                severity="medium",
                matched_policy=(f"{policy_id}:output:tool-error" if policy_id else "output:tool-error"),
                metadata={"phase": "post", "fault_mode": fault_mode},
            )

        output = tool_result.output
        if required_fields:
            if not isinstance(output, Mapping):
                return self.result(
                    Decision.BLOCK,
                    "tool output is not an object required by the output schema",
                    started_at=started,
                    severity="medium",
                    matched_policy=(f"{policy_id}:output:required-fields" if policy_id else "output:required-fields"),
                    metadata={"phase": "post", "required_fields": list(required_fields)},
                )
            missing = [str(field) for field in required_fields if str(field) not in output]
            if missing:
                return self.result(
                    Decision.BLOCK,
                    "tool output is missing required fields",
                    started_at=started,
                    severity="medium",
                    matched_policy=(f"{policy_id}:output:required-fields" if policy_id else "output:required-fields"),
                    metadata={"phase": "post", "missing_fields": missing},
                )

        serialized_output = _dump(output)
        if any(str(item) and str(item) in serialized_output for item in forbidden):
            return self.result(
                Decision.BLOCK,
                "tool output contains a forbidden deterministic value",
                started_at=started,
                severity="critical",
                matched_policy=(f"{policy_id}:output:forbidden-value" if policy_id else "output:forbidden-value"),
                metadata={"phase": "post", "forbidden_value_matched": True},
            )
        expected_format = context.metadata.get("required_output_format", policy_format)
        if expected_format and not self._format_valid(output, str(expected_format)):
            return self.result(
                Decision.BLOCK,
                f"tool output violates {expected_format} format",
                started_at=started,
                severity="medium",
                matched_policy=(f"{policy_id}:output:format" if policy_id else "output:format"),
                metadata={"phase": "post", "expected_format": expected_format},
            )

        return self.result(
            Decision.ALLOW,
            "tool output is successful and satisfies deterministic validation",
            started_at=started,
            matched_policy=(f"{policy_id}:output" if policy_id else None),
            metadata={"phase": "post"},
        )

    @staticmethod
    def _format_valid(value: Any, expected: str) -> bool:
        normalized = expected.strip().lower()
        if normalized in {"object", "mapping", "dict"}:
            return isinstance(value, Mapping)
        if normalized in {"text", "string"}:
            return isinstance(value, str)
        if normalized == "json":
            if isinstance(value, (Mapping, list, tuple, int, float, bool)) or value is None:
                return True
            if isinstance(value, str):
                try:
                    json.loads(value)
                    return True
                except (json.JSONDecodeError, TypeError):
                    return False
            return False
        return False


__all__ = ["OutputValidationGuard"]
