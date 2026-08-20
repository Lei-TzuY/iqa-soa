from __future__ import annotations

from time import perf_counter

import pytest

from iqa_soa.tools import SandboxState, SandboxedTool, ToolRegistry
from iqa_soa.types import Action, ToolResult


def action(tool: str, resource: str, **arguments: object) -> Action:
    return Action(f"{tool}:{resource}", tool, resource, dict(arguments))


def test_default_registry_has_exact_required_names() -> None:
    assert set(ToolRegistry.default().names) == {
        "file.read",
        "file.write",
        "database.query",
        "database.update",
        "database.delete",
        "message.send",
        "api.call",
        "shell.execute_simulated",
        "robot.move_simulated",
        "robot.pick_up_simulated",
    }


def test_all_tools_mutate_only_in_memory_sandbox() -> None:
    state = SandboxState(
        files={"report.txt": "hello"},
        database={"row/1": {"value": 1}},
        api_responses={"https://fake.invalid": {"value": "stub"}},
    )
    registry = ToolRegistry.default(state)

    assert registry.execute(action("file.read", "report.txt")).output == "hello"
    assert registry.execute(action("file.write", "new.txt", content="new")).success
    assert registry.execute(action("database.query", "row/1")).output == {"value": 1}
    assert registry.execute(action("database.update", "row/1", values={"value": 2})).success
    assert registry.execute(action("database.delete", "row/1")).success
    assert registry.execute(action("message.send", "external", message="hello")).success
    assert registry.execute(action("api.call", "https://fake.invalid")).output == {
        "value": "stub"
    }
    assert registry.execute(
        action("shell.execute_simulated", "remove everything", command="rm -rf /")
    ).success
    assert registry.execute(action("robot.move_simulated", "zone-b")).success
    assert registry.execute(action("robot.pick_up_simulated", "sample")).success

    assert state.files["new.txt"] == "new"
    assert "row/1" not in state.database
    assert state.messages[0]["simulated"] is True
    assert state.api_calls[0]["simulated"] is True
    assert state.shell_history == [{"command": "rm -rf /", "simulated": True}]
    assert state.robot_position == "zone-b"
    assert state.robot_holding == ["sample"]
    assert len(state.operation_log) == 10
    assert all(item["result"]["simulated"] for item in state.operation_log)


@pytest.mark.parametrize(
    ("mode", "success", "metadata_key"),
    [
        ("timeout", False, "simulated_delay"),
        ("high_latency", True, "simulated_delay"),
        ("malformed_response", True, "malformed"),
        ("unavailable", False, "fault_mode"),
        ("partial_failure", False, "partial"),
    ],
)
def test_fault_modes_are_fast_and_recorded(
    mode: str, success: bool, metadata_key: str
) -> None:
    state = SandboxState(
        files={"report.txt": "hello"},
        faults={"file.read:report.txt": {"type": mode, "latency_ms": 60_000}},
    )
    registry = ToolRegistry.default(state)

    started = perf_counter()
    result = registry.execute(action("file.read", "report.txt"))
    wall_ms = (perf_counter() - started) * 1_000

    assert wall_ms < 250
    assert result.success is success
    assert result.metadata["fault_mode"] == mode
    assert metadata_key in result.metadata
    assert state.operation_log[-1]["result"]["metadata"]["fault_mode"] == mode


def test_sandbox_state_clones_nested_robot_and_all_mutable_state() -> None:
    original = SandboxState.from_environment(
        {
            "files": {"a": "x"},
            "database": {"r": {"x": 1}},
            "robot": {"position": "home", "holding": ["part"]},
            "faults": {"api.call": {"type": "unavailable"}},
        }
    )
    clone = original.clone()
    clone.files["a"] = "changed"
    clone.database["r"]["x"] = 2
    clone.robot_holding.append("other")

    assert original.files == {"a": "x"}
    assert original.database == {"r": {"x": 1}}
    assert original.robot_position == "home"
    assert original.robot_holding == ["part"]


def test_tools_are_independently_registerable_and_unknown_tools_fail_safely() -> None:
    class Echo(SandboxedTool):
        name = "test.echo"

        def execute(self, proposed: Action) -> ToolResult:
            return ToolResult(success=True, output=proposed.arguments)

    registry = ToolRegistry()
    registry.register(Echo())
    assert registry.execute(action("test.echo", "x", hello="world")).output == {
        "hello": "world"
    }
    with pytest.raises(ValueError, match="already registered"):
        registry.register(Echo())

    result = registry.execute(action("missing.tool", "x"))
    assert result.success is False
    assert result.would_execute is False
    assert result.metadata["registered"] is False
