"""Registry and concrete in-memory tool simulations."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any, Protocol, runtime_checkable

from iqa_soa.tools.base import SandboxedTool
from iqa_soa.tools.sandbox import FaultSpec, SandboxState
from iqa_soa.types import Action, ToolResult


@runtime_checkable
class ToolCallable(Protocol):
    def __call__(self, action: Action) -> ToolResult: ...


ToolHandler = SandboxedTool | ToolCallable


class _FunctionTool(SandboxedTool):
    def __init__(
        self,
        name: str,
        state: SandboxState,
        function: Callable[[Action, SandboxState], ToolResult],
    ) -> None:
        self.name = name
        self._state = state
        self._function = function

    def execute(self, action: Action) -> ToolResult:
        return self._function(action, self._state)


def _ok(output: Any = None, *, metadata: Mapping[str, Any] | None = None) -> ToolResult:
    return ToolResult(
        success=True,
        output=output,
        simulated=True,
        would_execute=True,
        metadata=dict(metadata or {}),
    )


def _failure(error: str, *, metadata: Mapping[str, Any] | None = None) -> ToolResult:
    return ToolResult(
        success=False,
        error=error,
        simulated=True,
        would_execute=True,
        metadata=dict(metadata or {}),
    )


def _payload(arguments: Mapping[str, Any]) -> Any:
    for key in ("content", "body", "message", "payload", "data", "value"):
        if key in arguments:
            return arguments[key]
    return None


def _file_read(action: Action, state: SandboxState) -> ToolResult:
    if action.resource not in state.files:
        return _failure(f"sandbox file not found: {action.resource}")
    return _ok(state.files[action.resource], metadata={"operation": "file.read"})


def _file_write(action: Action, state: SandboxState) -> ToolResult:
    content = _payload(action.arguments)
    if content is None:
        return _failure("file.write requires content")
    state.files[action.resource] = content
    return _ok(
        {"resource": action.resource, "written": True},
        metadata={"operation": "file.write"},
    )


def _database_query(action: Action, state: SandboxState) -> ToolResult:
    resource = action.resource
    if resource in state.database:
        value = state.database[resource]
    elif resource in ("", "*", "database"):
        value = state.database
    else:
        table = action.arguments.get("table")
        key = action.arguments.get("key", action.arguments.get("id"))
        if table in state.database and key is not None:
            table_value = state.database[table]
            value = table_value.get(str(key)) if isinstance(table_value, Mapping) else None
        else:
            return _failure(f"sandbox database resource not found: {resource}")
    return _ok(value, metadata={"operation": "database.query"})


def _database_update(action: Action, state: SandboxState) -> ToolResult:
    value = action.arguments.get("values", action.arguments.get("value", action.arguments.get("data")))
    if value is None:
        # Treat the non-routing arguments as a record for terse benchmark fixtures.
        value = {
            key: item
            for key, item in action.arguments.items()
            if key not in {"table", "key", "id"}
        }
    existing = state.database.get(action.resource)
    if isinstance(existing, dict) and isinstance(value, Mapping):
        existing.update(dict(value))
    else:
        state.database[action.resource] = dict(value) if isinstance(value, Mapping) else value
    return _ok(
        {"resource": action.resource, "updated": True},
        metadata={"operation": "database.update"},
    )


def _database_delete(action: Action, state: SandboxState) -> ToolResult:
    existed = action.resource in state.database
    state.database.pop(action.resource, None)
    return _ok(
        {"resource": action.resource, "deleted": existed},
        metadata={"operation": "database.delete"},
    )


def _message_send(action: Action, state: SandboxState) -> ToolResult:
    record = {
        "recipient": action.resource,
        "payload": _payload(action.arguments),
        "arguments": dict(action.arguments),
        "simulated": True,
    }
    state.messages.append(record)
    return _ok(
        {"recipient": action.resource, "sent": True, "simulated": True},
        metadata={"operation": "message.send"},
    )


def _api_call(action: Action, state: SandboxState) -> ToolResult:
    record = {
        "endpoint": action.resource,
        "arguments": dict(action.arguments),
        "simulated": True,
    }
    state.api_calls.append(record)
    response = state.api_responses.get(
        action.resource,
        {"endpoint": action.resource, "accepted": True, "simulated": True},
    )
    return _ok(response, metadata={"operation": "api.call"})


def _shell_execute(action: Action, state: SandboxState) -> ToolResult:
    command = action.arguments.get("command", action.resource)
    record = {"command": command, "simulated": True}
    state.shell_history.append(record)
    return _ok(
        {"command": command, "stdout": "", "returncode": 0, "simulated": True},
        metadata={"operation": "shell.execute_simulated"},
    )


def _robot_move(action: Action, state: SandboxState) -> ToolResult:
    target = action.arguments.get("target", action.arguments.get("position", action.resource))
    state.robot_position = target
    record = {"operation": "move", "target": target, "simulated": True}
    state.robot_history.append(record)
    return _ok(record, metadata={"operation": "robot.move_simulated"})


def _robot_pick_up(action: Action, state: SandboxState) -> ToolResult:
    item = str(action.arguments.get("object", action.resource))
    if item not in state.robot_holding:
        state.robot_holding.append(item)
    record = {"operation": "pick_up", "object": item, "simulated": True}
    state.robot_history.append(record)
    return _ok(record, metadata={"operation": "robot.pick_up_simulated"})


_DEFAULT_TOOLS: dict[str, Callable[[Action, SandboxState], ToolResult]] = {
    "file.read": _file_read,
    "file.write": _file_write,
    "database.query": _database_query,
    "database.update": _database_update,
    "database.delete": _database_delete,
    "message.send": _message_send,
    "api.call": _api_call,
    "shell.execute_simulated": _shell_execute,
    "robot.move_simulated": _robot_move,
    "robot.pick_up_simulated": _robot_pick_up,
}

_FAULT_MODES = {
    "timeout",
    "high_latency",
    "malformed_response",
    "unavailable",
    "partial_failure",
}


class ToolRegistry:
    """Maps exact tool names to sandboxed handlers.

    ``register`` supports either a :class:`SandboxedTool`, a callable plus name,
    or an object exposing ``name`` and ``execute``.  The registry is intentionally
    independent of IQA-SOA; governance is provided by the service gateway.
    """

    def __init__(self, state: SandboxState | None = None) -> None:
        self.state = state if state is not None else SandboxState()
        self._tools: dict[str, ToolHandler] = {}

    @classmethod
    def default(cls, state: SandboxState | None = None) -> ToolRegistry:
        registry = cls(state)
        for name, function in _DEFAULT_TOOLS.items():
            registry.register(_FunctionTool(name, registry.state, function))
        return registry

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def register(
        self,
        tool: ToolHandler | str,
        handler: ToolHandler | None = None,
        *,
        replace_existing: bool = False,
    ) -> None:
        if isinstance(tool, str):
            if handler is None:
                raise TypeError("a handler is required when registering by name")
            name = tool
            value = handler
        else:
            if handler is not None:
                raise TypeError("handler must be omitted when registering a tool object")
            name = getattr(tool, "name", "")
            value = tool
        if not isinstance(name, str) or not name:
            raise ValueError("registered tools require a non-empty name")
        if name in self._tools and not replace_existing:
            raise ValueError(f"tool already registered: {name}")
        if not callable(value) and not callable(getattr(value, "execute", None)):
            raise TypeError("tool handler must be callable or expose execute(action)")
        self._tools[name] = value

    def unregister(self, name: str) -> ToolHandler:
        try:
            return self._tools.pop(name)
        except KeyError as exc:
            raise KeyError(f"tool is not registered: {name}") from exc

    def execute(self, action: Action) -> ToolResult:
        handler = self._tools.get(action.tool)
        if handler is None:
            result = ToolResult(
                success=False,
                error=f"sandbox tool unavailable: {action.tool}",
                simulated=True,
                would_execute=False,
                metadata={"fault_mode": "unavailable", "registered": False},
            )
            self._record(action, result)
            return result

        fault = self.state.fault_for(action.tool, action.resource)
        if fault is not None and fault.mode not in _FAULT_MODES:
            result = _failure(
                f"unsupported simulated fault mode: {fault.mode}",
                metadata={"fault_mode": fault.mode},
            )
            self._record(action, result)
            return result
        if fault is not None and fault.mode != "high_latency":
            result = self._fault_result(fault)
            self._record(action, result)
            return result

        try:
            if callable(getattr(handler, "execute", None)):
                result = handler.execute(action)  # type: ignore[union-attr]
            else:
                result = handler(action)  # type: ignore[operator]
            if not isinstance(result, ToolResult):
                result = ToolResult(success=True, output=result, simulated=True)
        except Exception as exc:  # pragma: no cover - defensive extension boundary
            result = ToolResult(
                success=False,
                error=f"sandbox tool error: {type(exc).__name__}: {exc}",
                simulated=True,
                would_execute=True,
                metadata={"caught_exception": type(exc).__name__},
            )

        if fault is not None and fault.mode == "high_latency":
            metadata = dict(result.metadata)
            metadata.update(
                {
                    "fault_mode": "high_latency",
                    "simulated_delay": True,
                    "simulated_duration_ms": fault.latency_ms,
                }
            )
            result = replace(result, latency_ms=fault.latency_ms, metadata=metadata)

        self._record(action, result)
        return result

    @staticmethod
    def _fault_result(fault: FaultSpec) -> ToolResult:
        metadata = {
            "fault_mode": fault.mode,
            "simulated_delay": fault.mode == "timeout",
            "simulated_duration_ms": fault.latency_ms,
        }
        if fault.detail is not None:
            metadata["detail"] = fault.detail
        if fault.mode == "malformed_response":
            return ToolResult(
                success=True,
                output="<<<MALFORMED_SIMULATED_RESPONSE>>>",
                latency_ms=0.0,
                simulated=True,
                would_execute=True,
                metadata={**metadata, "malformed": True},
            )
        error = {
            "timeout": "simulated tool timeout",
            "unavailable": "simulated tool unavailable",
            "partial_failure": "simulated partial tool failure",
        }[fault.mode]
        return ToolResult(
            success=False,
            error=error,
            latency_ms=fault.latency_ms if fault.mode == "timeout" else 0.0,
            simulated=True,
            would_execute=True,
            metadata={**metadata, "partial": fault.mode == "partial_failure"},
        )

    def _record(self, action: Action, result: ToolResult) -> None:
        self.state.operation_log.append(
            {
                "sequence": len(self.state.operation_log) + 1,
                "action": action.to_dict(),
                "result": result.to_dict(),
            }
        )


__all__ = ["ToolCallable", "ToolHandler", "ToolRegistry"]
