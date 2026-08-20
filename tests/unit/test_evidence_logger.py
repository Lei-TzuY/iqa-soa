from __future__ import annotations

import json

import pytest

from iqa_soa.evidence import EvidenceLogger, read_evidence
from iqa_soa.iqa.policy import Policy, PrivacyPolicy
from iqa_soa.types import Action, Decision, GuardResult, QAMode, RuntimeContext, ToolResult


def runtime(mode: QAMode = QAMode.FULL) -> RuntimeContext:
    return RuntimeContext(
        "exp", "run", "task", "privacy", mode, "stub", "stub", 0, 1, "test"
    )


def test_logger_is_exclusive_append_only_and_ids_are_stable(tmp_path) -> None:
    path = tmp_path / "evidence.jsonl"
    logger = EvidenceLogger(path)
    first = logger.append(
        {
            "experiment_id": "exp",
            "run_id": "run",
            "task_id": "task",
            "action_id": "a",
            "final_decision": "ALLOW",
            "executed": True,
        }
    )
    second = logger.append(
        {
            "experiment_id": "exp",
            "run_id": "run",
            "task_id": "task",
            "action_id": "b",
            "final_decision": "BLOCK",
            "executed": False,
        }
    )
    assert first != second
    records = read_evidence(path)
    assert [item["sequence"] for item in records] == [1, 2]
    assert records[0]["evidence_id"] == first
    with pytest.raises(FileExistsError):
        EvidenceLogger(path)


def test_detailed_event_has_causal_links_completeness_and_redaction(tmp_path) -> None:
    logger = EvidenceLogger(tmp_path / "evidence.jsonl")
    action = Action("a", "message.send", "external/SECRET", {"message": "SECRET"})
    policy = Policy("p", privacy=PrivacyPolicy(protected_values=("SECRET",)))
    guard = GuardResult("privacy", Decision.BLOCK, "blocked", "critical", "p:privacy", 0)
    logger.log_gateway(
        context=runtime(),
        action=action,
        policy=policy,
        guard_results=(guard,),
        decision=Decision.BLOCK,
        executed=False,
        tool_result=ToolResult(False, error="SECRET failed"),
        reason="blocked SECRET",
        blocking_guard="privacy",
        qa_latency_ms=1,
        latency_ms=1,
        detailed=True,
    )
    record = read_evidence(logger.path)[0]
    assert record["causal_links"]["disposition"] == "BLOCK"
    assert record["completeness"]["evidence_completeness"] == 1.0
    assert record["storage_claims"]["tamper_proof"] is False
    assert "SECRET" not in json.dumps(record)


def test_logger_identity_fields_cannot_be_spoofed(tmp_path) -> None:
    logger = EvidenceLogger(tmp_path / "evidence.jsonl")
    with pytest.raises(ValueError, match="logger-controlled"):
        logger.append({"evidence_id": "spoof", "sequence": 999, "timestamp": "fake"})
    evidence_id = logger.append({"run_id": "real"})
    record = read_evidence(logger.path)[0]
    assert evidence_id.startswith("evidence-")
    assert record["sequence"] == 1
    assert record["timestamp"] != "fake"


def test_minimal_observation_omits_policy_guard_reason_and_tool_trace(tmp_path) -> None:
    logger = EvidenceLogger(tmp_path / "evidence.jsonl")
    logger.log_gateway(
        context=runtime(QAMode.OFF),
        action=Action("a", "file.read", "report"),
        policy=Policy("p"),
        guard_results=(),
        decision=Decision.ALLOW,
        executed=True,
        tool_result=ToolResult(True, output="contents"),
        reason="bypassed",
        blocking_guard=None,
        qa_latency_ms=0,
        latency_ms=1,
        detailed=False,
    )
    record = read_evidence(logger.path)[0]
    assert set(record).isdisjoint(
        {"applicable_policy", "guard_results", "reason", "tool_result", "causal_links"}
    )
    assert record["final_decision"] == "ALLOW"
    assert record["executed"] is True
