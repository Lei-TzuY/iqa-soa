"""Runtime regressions for the Phase-C Class-P repair.

Covers the agent/gateway side of the repair: queued actions from a multi-call
turn are each reviewed by IQA-SOA, budget accounting stays correct, and the
terminal-no-action telemetry distinguishes the cases Phase B could not.

Everything is deterministic and offline; no model is contacted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from iqa_soa.agent.agent import ExperimentalAgent
from iqa_soa.agent.providers import AgentProvider, ProviderResponse
from iqa_soa.evidence import EvidenceLogger
from iqa_soa.instrument import (
    INSTRUMENT_VERSION,
    PRE_REPAIR_INSTRUMENT_VERSION,
    PRE_REPAIR_RAW_SCHEMA_VERSION,
)
from iqa_soa.iqa.chain import build_guard_chain
from iqa_soa.iqa.gateway import ServiceGateway
from iqa_soa.iqa.policy import Budget, PermissionRule, Policy
from iqa_soa.metrics.definitions import PILOT_RAW_FIELDS
from iqa_soa.tools import SandboxState, ToolRegistry
from iqa_soa.types import Action, Decision, QAMode, RuntimeContext


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ScriptedMultiCallProvider(AgentProvider):
    """Emit several actions in one turn, then a terminal no-action response."""

    name = "scripted_multi_call"

    def __init__(self, actions: Sequence[Action], *, model: str = "multi-call") -> None:
        self.model = model
        self._actions = tuple(actions)
        self.calls = 0

    def generate_action(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        scripted_actions: Sequence[Action],
        step: int,
        seed: int,
        history: Sequence[Mapping[str, Any]] = (),
        canonical_resources: Sequence[str] = (),
    ) -> ProviderResponse | None:
        self.calls += 1
        self.last_step = step
        if self.calls == 1:
            return ProviderResponse(
                action=self._actions[0],
                input_tokens=100,
                output_tokens=10,
                latency_ms=0.0,
                raw_response=json.dumps(self._actions[0].to_dict(), sort_keys=True),
                model=self.model,
                additional_actions=tuple(self._actions[1:]),
                tool_call_count=len(self._actions),
            )
        return ProviderResponse(
            action=None,
            input_tokens=120,
            output_tokens=5,
            latency_ms=0.0,
            raw_response="done",
            model=self.model,
            outcome="no_action",
            tool_call_count=0,
        )


def _harness(tmp_path: Path, name: str) -> tuple[ServiceGateway, RuntimeContext]:
    state = SandboxState(files={"public/a.txt": "alpha", "secret/b.txt": "bravo"})
    policy = Policy(
        "benchmark",
        permissions=(
            PermissionRule("allow", "file.read", "public/*"),
            PermissionRule("deny", "file.read", "secret/*"),
        ),
        budget=Budget(max_tool_calls=5, max_model_calls=5),
    )
    gateway = ServiceGateway(
        ToolRegistry.default(state),
        build_guard_chain(
            {
                "injection": True,
                "permission": True,
                "privacy": True,
                "budget": True,
                "output_validation": True,
                "evidence": True,
            }
        ),
        policy,
        EvidenceLogger(tmp_path / f"{name}.jsonl"),
    )
    context = RuntimeContext(
        "exp-test", f"run-{name}", "TASK-1", "unauthorized_action", QAMode.FULL,
        "stub", "stub", 0, 7, "user",
    )
    return gateway, context


def _run(tmp_path: Path, actions: Sequence[Action]) -> tuple[Any, RuntimeContext, Any]:
    gateway, context = _harness(tmp_path, "case")
    provider = ScriptedMultiCallProvider(actions)

    class Executor:
        def execute(self, action: Action, ctx: RuntimeContext) -> Any:
            return gateway.execute(action, ctx)

    agent = ExperimentalAgent(
        provider, Executor(), system_prompt="system", max_steps=20
    )
    run = agent.run(
        user_prompt="user",
        scripted_actions=(),
        context=context,
    )
    return run, context, provider


# --------------------------------------------------------------------------
# 5. Every accepted action still passes through IQA-SOA separately
# 4. Multiple emitted tool calls do not destroy the whole run
# --------------------------------------------------------------------------


def test_queued_actions_are_each_reviewed_by_iqa_soa(tmp_path: Path) -> None:
    allowed = Action(action_id="read-a", tool="file.read", resource="public/a.txt")
    forbidden = Action(action_id="read-b", tool="file.read", resource="secret/b.txt")
    run, context, _ = _run(tmp_path, [allowed, forbidden])

    # The run survives: the multi-call turn is not discarded wholesale.
    assert run.error is None
    assert run.failure_class is None
    assert len(run.outcomes) == 2

    # Each action was independently adjudicated by the gateway.
    first, second = run.outcomes
    assert first.decision is Decision.ALLOW and first.executed is True
    assert second.decision is Decision.BLOCK and second.executed is False
    assert second.blocking_guard == "permission"

    # Telemetry records that the provider emitted several calls in one turn.
    assert run.provider_multi_tool_call is True
    assert run.provider_max_tool_calls == 2
    assert run.queued_action_count == 1


def test_queued_actions_are_never_silently_discarded(tmp_path: Path) -> None:
    actions = [
        Action(action_id=f"read-{index}", tool="file.read", resource="public/a.txt")
        for index in range(3)
    ]
    run, _, _ = _run(tmp_path, actions)
    assert len(run.outcomes) == 3
    assert run.queued_action_count == 2


# --------------------------------------------------------------------------
# 6. Budget accounting remains correct
# --------------------------------------------------------------------------


def test_budget_accounting_separates_model_calls_from_tool_calls(
    tmp_path: Path,
) -> None:
    actions = [
        Action(action_id="read-a", tool="file.read", resource="public/a.txt"),
        Action(action_id="read-b", tool="file.read", resource="public/a.txt"),
    ]
    run, context, provider = _run(tmp_path, actions)

    # Two actions were executed from a single model turn, plus one terminal
    # call: a queued action must not be charged as a model call.
    assert provider.calls == 2
    assert context.usage.model_calls == 2
    assert context.usage.tool_calls == 2
    assert len(run.outcomes) == 2
    # The provider is told how many actions have actually been taken.
    assert provider.last_step == 2


# --------------------------------------------------------------------------
# 7. Terminal-no-action telemetry semantics
# --------------------------------------------------------------------------


class TerminalOnlyProvider(AgentProvider):
    name = "terminal_only"

    def __init__(self, model: str = "terminal-only") -> None:
        self.model = model

    def generate_action(self, **kwargs: Any) -> ProviderResponse | None:
        return ProviderResponse(
            action=None,
            input_tokens=10,
            output_tokens=2,
            latency_ms=0.0,
            raw_response="done",
            model=self.model,
            outcome="no_action",
        )


def test_terminal_no_action_after_zero_actions(tmp_path: Path) -> None:
    gateway, context = _harness(tmp_path, "case")

    class Executor:
        def execute(self, action: Action, ctx: RuntimeContext) -> Any:
            return gateway.execute(action, ctx)

    run = ExperimentalAgent(
        TerminalOnlyProvider(), Executor(), system_prompt="system", max_steps=5
    ).run(user_prompt="user", scripted_actions=(), context=context)

    assert run.outcomes == ()
    assert run.no_action is True  # legacy semantics preserved
    assert run.terminal_no_action is True
    assert run.terminal_no_action_attempts == 1
    assert run.no_action_after_actions is False


def test_terminal_no_action_after_executed_actions(tmp_path: Path) -> None:
    """The Phase-B undercount: legacy no_action stays False, new fields do not."""

    actions = [Action(action_id="read-a", tool="file.read", resource="public/a.txt")]
    run, _, _ = _run(tmp_path, actions)

    assert len(run.outcomes) == 1
    assert run.no_action is False  # unchanged legacy field
    assert run.terminal_no_action is True
    assert run.terminal_no_action_attempts == 1
    assert run.no_action_after_actions is True


def test_tool_contract_regression_is_detected_from_token_fingerprint(
    tmp_path: Path,
) -> None:
    """Reproduce the Phase-B signature: input tokens shrink as history grows."""

    class ShrinkingProvider(AgentProvider):
        name = "shrinking"
        model = "shrinking"

        def __init__(self) -> None:
            self.calls = 0

        def generate_action(self, **kwargs: Any) -> ProviderResponse | None:
            self.calls += 1
            if self.calls == 1:
                return ProviderResponse(
                    action=Action(
                        action_id="read-a", tool="file.read", resource="public/a.txt"
                    ),
                    input_tokens=332,
                    output_tokens=53,
                    latency_ms=0.0,
                    raw_response="{}",
                    model=self.model,
                    tool_call_count=1,
                )
            return ProviderResponse(
                action=None,
                input_tokens=293,  # fewer tokens despite a longer history
                output_tokens=21,
                latency_ms=0.0,
                raw_response="done",
                model=self.model,
                outcome="no_action",
            )

    gateway, context = _harness(tmp_path, "case")

    class Executor:
        def execute(self, action: Action, ctx: RuntimeContext) -> Any:
            return gateway.execute(action, ctx)

    run = ExperimentalAgent(
        ShrinkingProvider(), Executor(), system_prompt="system", max_steps=5
    ).run(user_prompt="user", scripted_actions=(), context=context)

    assert run.tool_contract_regression_detected is True


# --------------------------------------------------------------------------
# 8. Historical frozen artifact parsing remains backward compatible
# --------------------------------------------------------------------------


def test_frozen_pre_repair_rows_still_satisfy_their_schema() -> None:
    """Frozen Stage-1/Stage-2/Phase-A rows must remain readable unchanged."""

    roots = [
        PROJECT_ROOT / "results" / "pilot-v6.1-stage1" / "raw",
        PROJECT_ROOT / "results" / "phaseA-privacy-ablation" / "raw",
    ]
    checked = 0
    for root in roots:
        if not root.is_dir():
            continue
        for manifest_path in sorted(root.glob("*/manifest.json")):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert manifest["raw_schema_version"] == PRE_REPAIR_RAW_SCHEMA_VERSION
            # Pre-repair manifests predate the field and must read as version 1.
            assert (
                str(manifest.get("instrument_version", PRE_REPAIR_INSTRUMENT_VERSION))
                == PRE_REPAIR_INSTRUMENT_VERSION
            )
            rows = [
                json.loads(line)
                for line in (manifest_path.parent / "runs.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
                if line.strip()
            ]
            assert rows
            for row in rows:
                assert set(PILOT_RAW_FIELDS) <= set(row)
            checked += 1
    assert checked > 0, "expected at least one frozen pre-repair experiment"


def test_instrument_versions_are_distinct() -> None:
    assert INSTRUMENT_VERSION != PRE_REPAIR_INSTRUMENT_VERSION
