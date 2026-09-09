from __future__ import annotations

import sys
from pathlib import Path

from iqa_soa.evidence import EvidenceLogger
from iqa_soa.iqa.chain import build_guard_chain
from iqa_soa.iqa.gateway import ServiceGateway
from iqa_soa.iqa.policy import PermissionRule, Policy
from iqa_soa.tools import SandboxState, ToolRegistry
from iqa_soa.types import Action, QAMode, RuntimeContext

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import submission_artifact as artifact  # noqa: E402


def _context(run_id: str) -> RuntimeContext:
    return RuntimeContext(
        experiment_id="submission-regression",
        run_id=run_id,
        task_id="ARTIFACT-BOUNDARY",
        category="mechanism",
        qa_mode=QAMode.OFF,
        provider="deterministic",
        model="fixed",
        repetition=0,
        seed=0,
        user_prompt="fixed proposal",
    )


def test_trace_has_same_proposal_and_distinct_dispatch_dispositions() -> None:
    trace = artifact.derive_trace()
    paired = trace["paired_mechanism_demonstration"]

    assert trace["proposal"]["action_id"] == "trace-proposal-1"
    assert paired["qa_off"]["decision"] == "ALLOW"
    assert paired["qa_off"]["dispatch_count"] == 1
    assert paired["qa_off"]["protected_side_effect_occurred"] is True
    assert paired["qa_full"]["decision"] == "BLOCK"
    assert paired["qa_full"]["blocking_guard"] == "privacy"
    assert paired["qa_full"]["dispatch_count"] == 0
    assert paired["qa_full"]["protected_side_effect_occurred"] is False


def test_alias_and_invalid_payload_do_not_mutate_protected_state(tmp_path: Path) -> None:
    policy = Policy(
        "exact-dispatch",
        permissions=(PermissionRule("allow", "message.send", "audit-endpoint"),),
    )

    alias_state = SandboxState()
    alias_gateway = ServiceGateway(
        ToolRegistry.default(alias_state),
        build_guard_chain(),
        policy,
        EvidenceLogger(tmp_path / "alias.jsonl"),
    )
    alias = alias_gateway.execute(
        Action("alias", "Message.Send", "audit-endpoint", {"message": "x"}),
        _context("alias"),
    )

    payload_state = SandboxState()
    payload_gateway = ServiceGateway(
        ToolRegistry.default(payload_state),
        build_guard_chain(),
        policy,
        EvidenceLogger(tmp_path / "payload.jsonl"),
    )
    invalid_payload = payload_gateway.execute(
        Action("payload", "message.send", "audit-endpoint", {"payload": "x"}),
        _context("payload"),
    )

    assert alias.executed is False
    assert alias.tool_result is not None and alias.tool_result.would_execute is False
    assert alias_state.messages == []
    assert invalid_payload.tool_result is not None
    assert invalid_payload.tool_result.success is False
    assert payload_state.messages == []


def test_unqualified_task_cannot_produce_confirmatory_eligibility() -> None:
    assert artifact.qualification_eligible(
        planned=102,
        executed=102,
        terminal_rows=102,
        blocking_failures=(),
        unqualified_tasks=("PI-015",),
        verdict="QUALIFIED",
        authorized=True,
    ) is False


def test_generated_evidence_is_byte_deterministic() -> None:
    first = artifact.expected_outputs()
    second = artifact.expected_outputs()
    assert first == second
