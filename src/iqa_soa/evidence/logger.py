"""Exclusive, append-only JSONL logger for experimental evidence fragments."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from iqa_soa.evidence.events import causal_links, evidence_completeness
from iqa_soa.types import (
    Action,
    Decision,
    GuardResult,
    RuntimeContext,
    ToolResult,
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _redact(value: Any, protected_values: Sequence[Any]) -> Any:
    secrets = tuple(str(item) for item in protected_values if str(item))
    if isinstance(value, str):
        redacted = value
        for secret in secrets:
            redacted = redacted.replace(secret, "[REDACTED]")
        return redacted
    if isinstance(value, Mapping):
        return {str(key): _redact(item, protected_values) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_redact(item, protected_values) for item in value]
    return _jsonable(value)


def _policy_summary(policy: Any) -> dict[str, Any]:
    permissions = []
    for rule in getattr(policy, "permissions", ()):
        permissions.append(
            {
                "effect": str(getattr(rule, "effect", "")),
                "tool": getattr(rule, "tool", None),
                "resource": getattr(rule, "resource", None),
                "rule_id": getattr(rule, "rule_id", None),
            }
        )
    privacy = getattr(policy, "privacy", None)
    budget = getattr(policy, "budget", None)
    risk = getattr(policy, "risk", None)
    injection = getattr(policy, "injection", None)
    output = getattr(policy, "output_validation", None)
    return {
        "policy_id": getattr(policy, "policy_id", None),
        "version": getattr(policy, "version", None),
        "permissions": permissions,
        "privacy": {
            "protected_resources": list(getattr(privacy, "protected_resources", ())),
            # Protected values themselves must never be copied into evidence.
            "protected_value_count": len(getattr(privacy, "protected_values", ())),
        },
        "budget": {
            name: getattr(budget, name, None)
            for name in (
                "max_tool_calls",
                "max_model_calls",
                "max_tokens",
                "max_cost",
                "max_runtime_ms",
            )
        },
        "risk": {
            "require_confirmation": list(getattr(risk, "require_confirmation", ()))
        },
        "injection": {"pattern_count": len(getattr(injection, "patterns", ()))},
        "output_validation": {
            "required_fields": list(getattr(output, "required_fields", ())),
            "forbidden_value_count": len(getattr(output, "forbidden_values", ())),
            "require_evidence": getattr(output, "require_evidence", False),
            "required_format": getattr(output, "required_format", None),
            "require_tool_support": getattr(output, "require_tool_support", False),
        },
    }


class EvidenceLogger:
    """Write one JSON object per line to a newly created evidence path.

    The constructor uses exclusive creation and therefore refuses to overwrite or
    silently append to a prior experiment.  Subsequent calls append within the same
    logger instance.  IDs are stable for a fixed event order and experiment input.
    """

    def __init__(self, path: str | Path, *, detailed: bool = True) -> None:
        requested = Path(path)
        self.path = requested / "evidence.jsonl" if requested.is_dir() else requested
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation establishes a new experiment artifact.  Do not replace
        # this with write mode: preservation of failed/inconvenient runs is required.
        with self.path.open("x", encoding="utf-8", newline="\n"):
            pass
        self.detailed = detailed
        self._sequence = 0
        self._lock = threading.Lock()

    def __enter__(self) -> EvidenceLogger:
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def log_gateway(
        self,
        *,
        context: RuntimeContext,
        action: Action,
        policy: Any,
        guard_results: Sequence[GuardResult],
        decision: Decision,
        executed: bool,
        tool_result: ToolResult | None,
        reason: str,
        blocking_guard: str | None,
        qa_latency_ms: float,
        latency_ms: float,
        detailed: bool | None = None,
        executed_action: Action | None = None,
        error: str | None = None,
    ) -> str:
        """Append a gateway observation and return its stable evidence ID."""

        use_detail = self.detailed if detailed is None else bool(detailed and self.detailed)
        protected_values = tuple(
            getattr(getattr(policy, "privacy", None), "protected_values", ())
        ) + tuple(context.metadata.get("protected_data", ()))
        base: dict[str, Any] = {
            "experiment_id": context.experiment_id,
            "run_id": context.run_id,
            "task_id": context.task_id,
            "qa_mode": context.qa_mode.value,
            "action_id": action.action_id,
            "tool": action.tool,
            "resource": action.resource,
            "final_decision": decision.value,
            "executed": executed,
            "success": tool_result.success if tool_result is not None else None,
            "error": error or (tool_result.error if tool_result is not None else None),
        }
        if use_detail:
            policy_id = getattr(policy, "policy_id", None)
            policy_version = getattr(policy, "version", None)
            completeness = evidence_completeness(
                guard_results=guard_results,
                policy_id=policy_id,
                reason=reason,
                executed=executed,
                tool_result=tool_result,
            )
            base.update(
                {
                    "proposed_action": _redact(action.to_dict(), protected_values),
                    "executed_action": (
                        _redact(executed_action.to_dict(), protected_values)
                        if executed_action is not None
                        else None
                    ),
                    "applicable_policy": _policy_summary(policy),
                    "guard_results": [
                        _redact(result.to_dict(), protected_values)
                        for result in guard_results
                    ],
                    "reason": reason,
                    "blocking_guard": blocking_guard,
                    "tool_result": (
                        _redact(tool_result.to_dict(), protected_values)
                        if tool_result is not None
                        else None
                    ),
                    "qa_latency_ms": qa_latency_ms,
                    "latency_ms": latency_ms,
                    "causal_links": causal_links(
                        policy_id=policy_id,
                        policy_version=policy_version,
                        guard_results=guard_results,
                        decision=decision,
                        blocking_guard=blocking_guard,
                        metadata=context.metadata,
                    ),
                    "completeness": completeness.to_dict(),
                    "storage_claims": {
                        "qa_ium_compatible_fragment": True,
                        "graph_database": False,
                        "tamper_proof": False,
                    },
                }
            )
        return self.append(_redact(base, protected_values))

    def ensure_writable(self) -> None:
        """Fail before a governed side effect when detailed evidence is required."""

        with self._lock:
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.flush()

    def append(self, event: Mapping[str, Any]) -> str:
        """Append an arbitrary structured event using the same ID/sequence rules."""

        with self._lock:
            normalized = _jsonable(dict(event))
            reserved = {"evidence_id", "sequence", "timestamp"}.intersection(normalized)
            if reserved:
                raise ValueError(
                    "evidence event cannot override logger-controlled fields: "
                    + ", ".join(sorted(reserved))
                )
            self._sequence += 1
            identity = {
                "sequence": self._sequence,
                "experiment_id": normalized.get("experiment_id"),
                "run_id": normalized.get("run_id"),
                "task_id": normalized.get("task_id"),
                "action_id": normalized.get("action_id"),
                "final_decision": normalized.get("final_decision"),
                "executed": normalized.get("executed"),
            }
            digest = hashlib.sha256(
                json.dumps(
                    identity,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()[:20]
            record = {
                **normalized,
                "evidence_id": f"evidence-{digest}",
                "sequence": self._sequence,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            line = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line)
                handle.write("\n")
            return str(record["evidence_id"])

    # Friendly aliases used by small experiments and extension code.
    log = append
    log_event = append


__all__ = ["EvidenceLogger"]
