"""Runtime regressions for the Phase-C Class-P repair.

Covers the agent/gateway side of the repair: queued actions from a multi-call
turn are each reviewed by IQA-SOA, budget accounting stays correct, and the
terminal-no-action telemetry distinguishes the cases Phase B could not.

Everything is deterministic and offline; no model is contacted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typing import Any, Mapping, Sequence

from iqa_soa.agent.agent import ExperimentalAgent
from iqa_soa.agent.providers import (
    AgentProvider,
    ProviderResponse,
    _native_history_messages,
)
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
        self.last_history = list(history)
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


def test_three_call_turn_is_faithfully_represented(tmp_path: Path) -> None:
    """A 3-call turn yields 3 proposals, 3 adjudications, one grouped turn."""

    actions = [
        Action(action_id="read-a", tool="file.read", resource="public/a.txt"),
        Action(action_id="read-b", tool="file.read", resource="secret/b.txt"),
        Action(action_id="read-c", tool="file.read", resource="public/a.txt"),
    ]
    run, _, provider = _run(tmp_path, actions)

    # 3 proposals, counted per emitted action rather than per provider turn.
    assert len(run.proposed_action_bytes) == 3
    assert len(set(run.proposed_action_bytes)) == 3

    # 3 independently adjudicated outcomes, in emission order.
    assert len(run.outcomes) == 3
    assert [o.proposed_action.action_id for o in run.outcomes] == [
        "read-a",
        "read-b",
        "read-c",
    ]
    assert [o.decision for o in run.outcomes] == [
        Decision.ALLOW,
        Decision.BLOCK,
        Decision.ALLOW,
    ]
    assert [o.executed for o in run.outcomes] == [True, False, True]

    # The next provider call sees ONE assistant turn carrying all three calls,
    # followed by the three independently adjudicated results, not three
    # invented assistant turns.
    history = provider.last_history
    assert [item["turn"] for item in history] == [0, 0, 0]
    messages = _native_history_messages(history)
    assert [message["role"] for message in messages] == [
        "assistant",
        "tool",
        "tool",
        "tool",
    ]
    calls = messages[0]["tool_calls"]
    assert len(calls) == 3
    assert [
        json.loads(call["function"]["arguments"])["action_id"] for call in calls
    ] == ["read-a", "read-b", "read-c"]
    # Each tool result is bound to its own call id, in order.
    assert [call["id"] for call in calls] == [
        message["tool_call_id"] for message in messages[1:]
    ]
    # The blocked action's result is faithfully reported as not executed.
    assert json.loads(messages[2]["content"])["executed"] is False


def test_separate_turns_are_not_merged(tmp_path: Path) -> None:
    """Grouping must not collapse genuinely separate single-call turns."""

    history = [
        {"action": {"action_id": "a"}, "decision": "allow", "executed": True,
         "success": True, "output": "x", "error": None, "turn": 0},
        {"action": {"action_id": "b"}, "decision": "allow", "executed": True,
         "success": True, "output": "y", "error": None, "turn": 1},
    ]
    messages = _native_history_messages(history)
    assert [message["role"] for message in messages] == [
        "assistant",
        "tool",
        "assistant",
        "tool",
    ]
    assert len(messages[0]["tool_calls"]) == 1
    assert len(messages[2]["tool_calls"]) == 1


def test_history_without_turn_keys_degrades_to_one_action_per_turn() -> None:
    """Callers predating grouped turns must still encode correctly."""

    history = [
        {"action": {"action_id": "a"}, "decision": "allow", "executed": True,
         "success": True, "output": "x", "error": None},
        {"action": {"action_id": "b"}, "decision": "allow", "executed": True,
         "success": True, "output": "y", "error": None},
    ]
    messages = _native_history_messages(history)
    assert [message["role"] for message in messages] == [
        "assistant",
        "tool",
        "assistant",
        "tool",
    ]
    assert messages[0]["tool_calls"][0]["id"] == "iqa-history-0"
    assert messages[2]["tool_calls"][0]["id"] == "iqa-history-1"


# --------------------------------------------------------------------------
# Pending-queue overflow: no queued action may disappear silently
# --------------------------------------------------------------------------


def test_multi_call_turn_exceeding_step_budget_is_refused_whole(
    tmp_path: Path,
) -> None:
    actions = [
        Action(action_id=f"read-{index}", tool="file.read", resource="public/a.txt")
        for index in range(4)
    ]
    gateway, context = _harness(tmp_path, "overflow")
    provider = ScriptedMultiCallProvider(actions)

    class Executor:
        def execute(self, action: Action, ctx: RuntimeContext) -> Any:
            return gateway.execute(action, ctx)

    # Only two steps are available for a turn emitting four actions.
    run = ExperimentalAgent(
        provider, Executor(), system_prompt="system", max_steps=2
    ).run(user_prompt="user", scripted_actions=(), context=context)

    # Refused whole: nothing partially executed, nothing silently dropped.
    assert run.multi_call_overflow is True
    assert run.failure_class == "multi_call_overflow"
    assert run.error is not None and "refused rather than partially executed" in run.error
    assert run.outcomes == ()
    assert run.proposed_action_bytes == ()
    assert context.usage.tool_calls == 0
    # The emitted proposals remain reconstructable from raw provenance.
    assert run.provider_attempts[-1]["emitted_action_ids"] == [
        "read-0",
        "read-1",
        "read-2",
        "read-3",
    ]


def test_multi_call_turn_exactly_filling_the_budget_is_accepted(
    tmp_path: Path,
) -> None:
    actions = [
        Action(action_id=f"read-{index}", tool="file.read", resource="public/a.txt")
        for index in range(3)
    ]
    gateway, context = _harness(tmp_path, "exact")
    provider = ScriptedMultiCallProvider(actions)

    class Executor:
        def execute(self, action: Action, ctx: RuntimeContext) -> Any:
            return gateway.execute(action, ctx)

    run = ExperimentalAgent(
        provider, Executor(), system_prompt="system", max_steps=3
    ).run(user_prompt="user", scripted_actions=(), context=context)

    assert run.multi_call_overflow is False
    assert len(run.outcomes) == 3
    assert len(run.proposed_action_bytes) == 3


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


# --------------------------------------------------------------------------
# Instrument / adapter version validation (negative cases)
# --------------------------------------------------------------------------


def _v3_pilot(tmp_path: Path, model: str) -> Path:
    from iqa_soa.benchmark import load_frozen_pilot
    from iqa_soa.experiment.runner import ExperimentRunner, load_experiment_config
    from tests.integration.test_real_pilot_runner import SyntheticOnlineProvider

    config = load_experiment_config(
        PROJECT_ROOT / "configs" / "experiment.yaml"
    ).with_overrides(output_root=tmp_path, repetitions=2)
    frozen = load_frozen_pilot(
        PROJECT_ROOT / "benchmark" / "pilot-v1" / "manifest.json"
    )
    return ExperimentRunner(config, provider=SyntheticOnlineProvider(model)).run(
        treatments=["off", "full"],
        repetitions=2,
        frozen_benchmark=frozen,
        max_total_runs=300,
        experiment_kind="real_model_pilot",
    )


def _rewrite_manifest(source: Path, **changes: Any) -> None:
    path = source / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for key, value in changes.items():
        if value is _ABSENT:
            manifest.pop(key, None)
        else:
            manifest[key] = value
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _rewrite_rows(source: Path, **changes: Any) -> None:
    path = source / "runs.jsonl"
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for row in rows:
        row.update(changes)
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )


_ABSENT = object()


def test_v3_run_is_self_consistent(tmp_path: Path) -> None:
    from iqa_soa.metrics.pilot import load_real_pilot_records

    source = _v3_pilot(tmp_path, "synthetic-online-a")
    _, validation = load_real_pilot_records([source])
    assert validation["instrument_version"] == INSTRUMENT_VERSION
    assert validation["native_tool_adapter_version"]


def test_row_instrument_version_must_match_manifest(tmp_path: Path) -> None:
    from iqa_soa.metrics.pilot import AnalysisError, load_real_pilot_records

    source = _v3_pilot(tmp_path, "synthetic-online-a")
    _rewrite_rows(source, instrument_version="99")
    with pytest.raises(AnalysisError, match="instrument_version differs from manifest"):
        load_real_pilot_records([source])


def test_row_adapter_version_must_match_manifest(tmp_path: Path) -> None:
    from iqa_soa.metrics.pilot import AnalysisError, load_real_pilot_records

    source = _v3_pilot(tmp_path, "synthetic-online-a")
    _rewrite_rows(source, native_tool_adapter_version="native-tools-adapter-99")
    with pytest.raises(
        AnalysisError, match="native_tool_adapter_version differs from"
    ):
        load_real_pilot_records([source])


def test_v3_manifest_must_declare_adapter_version(tmp_path: Path) -> None:
    from iqa_soa.metrics.pilot import AnalysisError, load_real_pilot_records

    source = _v3_pilot(tmp_path, "synthetic-online-a")
    _rewrite_manifest(source, native_tool_adapter_version=_ABSENT)
    with pytest.raises(AnalysisError, match="must record native_tool_adapter_version"):
        load_real_pilot_records([source])


def test_v3_manifest_must_declare_instrument_version(tmp_path: Path) -> None:
    from iqa_soa.metrics.pilot import AnalysisError, load_real_pilot_records

    source = _v3_pilot(tmp_path, "synthetic-online-a")
    _rewrite_manifest(source, instrument_version=_ABSENT)
    with pytest.raises(AnalysisError, match="must record instrument_version"):
        load_real_pilot_records([source])


def test_manifest_adapter_must_agree_with_provider_descriptor(
    tmp_path: Path,
) -> None:
    from iqa_soa.metrics.pilot import AnalysisError, load_real_pilot_records

    source = _v3_pilot(tmp_path, "synthetic-online-a")
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    provider = dict(manifest["provider"])
    provider["native_tool_adapter_version"] = "native-tools-adapter-99"
    _rewrite_manifest(source, provider=provider)
    with pytest.raises(AnalysisError, match="disagrees with"):
        load_real_pilot_records([source])


def test_pooling_across_instrument_versions_is_refused(tmp_path: Path) -> None:
    from iqa_soa.metrics.pilot import AnalysisError, load_real_pilot_records

    first = _v3_pilot(tmp_path / "one", "synthetic-online-a")
    second = _v3_pilot(tmp_path / "two", "synthetic-online-b")
    _rewrite_manifest(second, instrument_version="99")
    _rewrite_rows(second, instrument_version="99")
    with pytest.raises(AnalysisError, match="different instrument"):
        load_real_pilot_records([first, second])


def test_pooling_across_adapter_versions_is_refused(tmp_path: Path) -> None:
    """Same instrument_version but a different adapter is still incompatible."""

    from iqa_soa.metrics.pilot import AnalysisError, load_real_pilot_records

    first = _v3_pilot(tmp_path / "one", "synthetic-online-a")
    second = _v3_pilot(tmp_path / "two", "synthetic-online-b")
    manifest = json.loads((second / "manifest.json").read_text(encoding="utf-8"))
    provider = dict(manifest["provider"])
    provider["native_tool_adapter_version"] = "native-tools-adapter-99"
    _rewrite_manifest(
        second,
        native_tool_adapter_version="native-tools-adapter-99",
        provider=provider,
    )
    _rewrite_rows(second, native_tool_adapter_version="native-tools-adapter-99")
    with pytest.raises(AnalysisError, match="different instrument"):
        load_real_pilot_records([first, second])


def test_no_proposal_is_ever_silently_lost(tmp_path: Path) -> None:
    """Across step budgets: either every action is adjudicated, or it overflows.

    There is no combination in which some proposals execute and the rest
    disappear without an explicit machine-readable state.
    """

    for emitted in range(1, 6):
        for max_steps in range(1, 8):
            actions = [
                Action(
                    action_id=f"read-{index}",
                    tool="file.read",
                    resource="public/a.txt",
                )
                for index in range(emitted)
            ]
            gateway, context = _harness(tmp_path, f"inv-{emitted}-{max_steps}")

            class Executor:
                def execute(self, action: Action, ctx: RuntimeContext) -> Any:
                    return gateway.execute(action, ctx)

            run = ExperimentalAgent(
                ScriptedMultiCallProvider(actions),
                Executor(),
                system_prompt="system",
                max_steps=max_steps,
            ).run(user_prompt="user", scripted_actions=(), context=context)

            if run.multi_call_overflow:
                # Refused whole: nothing partially executed.
                assert run.outcomes == ()
                assert run.failure_class == "multi_call_overflow"
            else:
                # Accepted: every emitted proposal was adjudicated and counted.
                assert len(run.outcomes) == emitted, (emitted, max_steps)
                assert len(run.proposed_action_bytes) == emitted, (emitted, max_steps)
