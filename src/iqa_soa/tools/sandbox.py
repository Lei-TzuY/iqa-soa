"""In-memory state and independently registerable simulated tools.

None of the implementations in this module access the host filesystem, spawn a
process, send a message, contact a network service, or control a physical robot.
Dangerous-looking actions are deliberately *simulated* so that the experiment can
measure whether an unsafe proposal would have executed without causing harm.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class FaultSpec:
    """A deterministic fault attached to a tool name or ``tool:resource`` key."""

    mode: str
    latency_ms: float = 1_000.0
    detail: str | None = None

    @classmethod
    def from_value(cls, value: FaultSpec | str | Mapping[str, Any]) -> FaultSpec:
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(mode=value)
        if isinstance(value, Mapping):
            return cls(
                mode=str(value.get("mode", value.get("type", "unavailable"))),
                latency_ms=float(value.get("latency_ms", value.get("latency", 1_000.0))),
                detail=(str(value["detail"]) if value.get("detail") is not None else None),
            )
        raise TypeError(f"unsupported fault specification: {type(value).__name__}")


@dataclass(slots=True)
class SandboxState:
    """All observable state for one isolated experimental treatment run."""

    files: dict[str, Any] = field(default_factory=dict)
    database: dict[str, Any] = field(default_factory=dict)
    messages: list[dict[str, Any]] = field(default_factory=list)
    api_responses: dict[str, Any] = field(default_factory=dict)
    api_calls: list[dict[str, Any]] = field(default_factory=list)
    shell_history: list[dict[str, Any]] = field(default_factory=list)
    robot_position: Any = None
    robot_holding: list[str] = field(default_factory=list)
    robot_history: list[dict[str, Any]] = field(default_factory=list)
    faults: dict[str, FaultSpec | str | Mapping[str, Any]] = field(default_factory=dict)
    operation_log: list[dict[str, Any]] = field(default_factory=list)

    def clone(self) -> SandboxState:
        """Return a deep copy suitable for the other member of a paired run."""

        return deepcopy(self)

    @classmethod
    def from_environment(cls, environment: Mapping[str, Any] | None) -> SandboxState:
        """Build state from a benchmark ``environment`` mapping.

        Unknown environment keys are intentionally ignored: benchmark schema
        validation owns their rejection, while this runtime accepts only the state
        that its sandbox can represent.
        """

        data = environment or {}
        database = data.get("database", data.get("database_rows", {}))
        robot_value = data.get("robot", {})
        robot = robot_value if isinstance(robot_value, Mapping) else {}
        return cls(
            files=deepcopy(dict(data.get("files", {}))),
            database=deepcopy(dict(database or {})),
            api_responses=deepcopy(dict(data.get("api_responses", {}))),
            robot_position=deepcopy(
                data.get("robot_position", robot.get("position", robot.get("location")))
            ),
            robot_holding=deepcopy(
                list(data.get("robot_holding", robot.get("holding", ())))
            ),
            robot_history=deepcopy(
                list(data.get("robot_history", robot.get("history", ())))
            ),
            faults=deepcopy(dict(data.get("faults", {}))),
        )

    def fault_for(self, tool: str, resource: str) -> FaultSpec | None:
        """Resolve the most specific configured fault without consuming it."""

        candidates = (f"{tool}:{resource}", tool, resource, "*")
        for key in candidates:
            if key in self.faults:
                return FaultSpec.from_value(self.faults[key])
        return None


__all__ = ["FaultSpec", "SandboxState"]
