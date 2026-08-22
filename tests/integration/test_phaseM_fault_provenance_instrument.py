"""Phase M: the QA-OFF runtime fault-provenance instrument repair.

Phase L-A stopped at ``HOLD_PHASE_L_PROTOCOL`` because the Phase-K.2
observed-fault contract could not be satisfied from anything a QA-OFF cell
persisted.  Phase M repairs that, and only that.  This module is the adversarial
suite for the repair.

It is organised around the ways the repair could be WRONG rather than the ways
it could be right, because a repair that persists *something* is easy and a
repair that persists something *provative* is not:

1. the four fields come from the live runtime outcome, and the benchmark
   declaration is structurally unable to reach them;
2. a wrong tool, a wrong resource, a missing stamp or a fabricated declared
   source is still refused;
3. multiple runtime faults do not silently collapse to whichever came first;
4. QA-OFF treatment semantics are untouched and no sensitive payload is added;
5. the schema revision is additive and every historical row stays readable;
6. the instrument revision is hash-pinned and an unapproved edit fails.

Every test is offline and deterministic.  The only provider used anywhere is
``DeterministicStubProvider``, which replays each case's own ``scripted_actions``
and issues no network request.  NO MODEL IS RUN.
"""

from __future__ import annotations

from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterator

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _root in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import instrument_revision  # noqa: E402
import phaseM_historical_analysis as historical_analysis  # noqa: E402
import qualification_harness as harness  # noqa: E402
from iqa_soa.agent.providers import DeterministicStubProvider  # noqa: E402
from iqa_soa.benchmark import load_frozen_pilot  # noqa: E402
from iqa_soa.experiment.fault_provenance import (  # noqa: E402
    OBSERVED_FAULT_FIELDS,
    OBSERVED_FAULT_TELEMETRY_FIELDS,
    PROVENANCE_EXECUTED_ACTION,
    PROVENANCE_PROPOSED_ACTION,
    distinct_fault_identities,
    observed_fault_telemetry,
    runtime_fault_observations,
)
from iqa_soa.experiment.runner import (  # noqa: E402
    ExperimentRunner,
    load_experiment_config,
)
from iqa_soa.experiment.treatments import treatment_for  # noqa: E402
from iqa_soa.instrument import (  # noqa: E402
    FAULT_PROVENANCE_INSTRUMENT_VERSION,
    FAULT_PROVENANCE_RAW_SCHEMA_VERSION,
    INSTRUMENT_VERSION,
    NATIVE_TOOL_ADAPTER_VERSION,
    PROTOCOL_TELEMETRY_INSTRUMENT_VERSION,
    PROTOCOL_TELEMETRY_RAW_SCHEMA_VERSION,
    RAW_SCHEMA_VERSION,
    READABLE_PILOT_RAW_SCHEMA_VERSIONS,
)
from iqa_soa.metrics.definitions import (  # noqa: E402
    FAULT_PROVENANCE_TELEMETRY_FIELDS,
    PILOT_RAW_FIELDS,
    PILOT_RAW_FIELDS_V3,
    PILOT_RAW_FIELDS_V4,
    RAW_FIELDS_BY_SCHEMA_VERSION,
)
from iqa_soa.tools.registry import ToolRegistry  # noqa: E402
from iqa_soa.tools.sandbox import SandboxState  # noqa: E402
from iqa_soa.types import (  # noqa: E402
    Action,
    Decision,
    GatewayOutcome,
    ToolResult,
)

BENCHMARK_VERSION = "pilot-v7-rc3"
MANIFEST_PATH = PROJECT_ROOT / "benchmark" / BENCHMARK_VERSION / "manifest.json"
PARENT_COMMIT = "eace204d4c27a9ca48d3c0a660832f640b7a900b"
REVISION_PATH = PROJECT_ROOT / "docs" / "phaseM_instrument_revision.json"

#: The rc3 fault declarations.  Read ONLY to assert that the runtime observation
#: happens to agree with them.  Nothing here is ever fed into a derivation.
BUD_016 = ("api.call", "platform-api/service-health", "timeout")
FAULT_004 = ("api.call", "inventory-api/sku-4471", "malformed_response")


# --------------------------------------------------------------------------
# Fixtures: the REAL runner, the REAL frozen cases, QA OFF, no model.
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def frozen_rc3() -> Any:
    return load_frozen_pilot(MANIFEST_PATH)


def _run_qa_off(
    task_ids: list[str], workdir: Path, benchmark: Any
) -> tuple[Path, list[dict[str, Any]]]:
    config = load_experiment_config(PROJECT_ROOT / "configs" / "phaseI-qualification.yaml")
    config = replace(
        config, output_root=workdir, treatments=("off",), repetitions=1, seeds=(929260329,)
    )
    experiment_dir = ExperimentRunner(config, provider=DeterministicStubProvider()).run(
        treatments=["off"],
        case_ids=task_ids,
        repetitions=1,
        frozen_benchmark=benchmark,
        max_total_runs=len(task_ids),
        experiment_kind="deterministic_mechanism_validation",
        infrastructure_retry_limit=0,
    )
    rows = [
        json.loads(line)
        for line in (experiment_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return experiment_dir, rows


@pytest.fixture(scope="module")
def qa_off_run(frozen_rc3: Any, tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One QA-OFF execution covering both fault tasks and two benign controls."""

    workdir = tmp_path_factory.mktemp("phaseM-qaoff")
    directory, rows = _run_qa_off(
        ["BUD-016", "FAULT-004", "BEN-002", "BEN-003"], workdir, frozen_rc3
    )
    return directory, {row["task_id"]: row for row in rows}


def _outcome(
    tool: str,
    resource: str,
    *,
    fault_mode: str | None = None,
    executed: bool = True,
    extra_metadata: dict[str, Any] | None = None,
) -> GatewayOutcome:
    """A synthetic GatewayOutcome shaped exactly like the gateway builds one."""

    metadata: dict[str, Any] = dict(extra_metadata or {})
    if fault_mode is not None:
        metadata["fault_mode"] = fault_mode
    action = Action(action_id="a", tool=tool, resource=resource)
    return GatewayOutcome(
        proposed_action=action,
        executed_action=action if executed else None,
        decision=Decision.ALLOW if executed else Decision.BLOCK,
        blocking_guard=None,
        reason="",
        executed=executed,
        guard_results=(),
        tool_result=ToolResult(success=False, metadata=metadata),
        qa_latency_ms=0.0,
        evidence_latency_ms=0.0,
        tool_latency_ms=0.0,
        latency_ms=0.0,
        evidence_id=None,
    )


# ==========================================================================
# 1. The observation is RUNTIME-derived, and the declaration cannot reach it
# ==========================================================================


def test_the_derivation_cannot_see_the_benchmark_declaration() -> None:
    """The invariant is enforced by the signature, not by a comment.

    Every public entry point takes ``Sequence[GatewayOutcome]`` and nothing else.
    There is no parameter through which a ``BenchmarkCase``, ``case.fault``,
    ``ground_truth``, a ``ScriptedFault``, the qualification contract or a
    task-id-to-fault table could be supplied, so an observation cannot be
    manufactured from the declaration it is about to be compared against.
    """

    import inspect

    for function in (
        runtime_fault_observations,
        distinct_fault_identities,
        observed_fault_telemetry,
    ):
        parameters = list(inspect.signature(function).parameters)
        assert parameters == ["outcomes"], function.__name__


def test_the_fault_provenance_module_imports_no_benchmark_symbol() -> None:
    """Nothing declaration-shaped is even importable in that module."""

    source = (SRC_ROOT / "iqa_soa" / "experiment" / "fault_provenance.py").read_text(
        encoding="utf-8"
    )
    body = "\n".join(
        line
        for line in source.splitlines()
        if line.startswith(("import ", "from ")) or "=" in line
    )
    for forbidden in (
        "from iqa_soa.benchmark",
        "BenchmarkCase",
        "ScriptedFault",
        "ground_truth",
        "case.fault",
        "FAULT_MODE_SIGNATURE",
        "qualification_contract",
    ):
        assert forbidden not in body, forbidden


def test_the_runner_derives_provenance_only_from_agent_run_outcomes() -> None:
    """The single call site passes the live outcomes and nothing else."""

    source = (SRC_ROOT / "iqa_soa" / "experiment" / "runner.py").read_text(
        encoding="utf-8"
    )
    calls = [line.strip() for line in source.splitlines() if "observed_fault_telemetry(" in line]
    assert calls == ["**observed_fault_telemetry(agent_run.outcomes),"]


def test_a_fault_mode_is_never_inferred_from_a_failure_class_or_error_string() -> None:
    """Only the sandbox's own stamp counts.

    A timeout-shaped failure with no ``fault_mode`` in the tool-result metadata
    yields nothing, however suggestive the surrounding signals are.  This closes
    the ``FAULT_MODE_SIGNATURE`` reverse-lookup that Phase L-A called
    "the same circularity in a thinner disguise".
    """

    action = Action(action_id="a", tool="api.call", resource="platform-api/service-health")
    outcome = GatewayOutcome(
        proposed_action=action,
        executed_action=action,
        decision=Decision.ALLOW,
        blocking_guard=None,
        reason="",
        executed=True,
        guard_results=(),
        # Exactly the timeout signature, minus the sandbox stamp.
        tool_result=ToolResult(success=False, error="simulated tool timeout", metadata={}),
        qa_latency_ms=0.0,
        evidence_latency_ms=0.0,
        tool_latency_ms=0.0,
        latency_ms=0.0,
        evidence_id=None,
        error="simulated tool timeout",
    )
    assert runtime_fault_observations([outcome]) == ()
    telemetry = observed_fault_telemetry([outcome])
    assert all(telemetry[name] is None for name in OBSERVED_FAULT_FIELDS)
    assert telemetry["observed_fault_identity_count"] == 0


def test_an_empty_or_blank_fault_mode_stamps_nothing() -> None:
    for mode in ("", "   "):
        assert runtime_fault_observations([_outcome("api.call", "r", fault_mode=mode)]) == ()


def test_provenance_names_the_proposed_action_when_nothing_executed() -> None:
    """Both admitted runtime sources are reachable and correctly labelled."""

    executed = runtime_fault_observations([_outcome("api.call", "r", fault_mode="timeout")])
    assert executed[0].provenance == PROVENANCE_EXECUTED_ACTION
    blocked = runtime_fault_observations(
        [_outcome("api.call", "r", fault_mode="timeout", executed=False)]
    )
    assert blocked[0].provenance == PROVENANCE_PROPOSED_ACTION
    for observation in (*executed, *blocked):
        assert observation.provenance in harness.RUNTIME_FAULT_PROVENANCE_SOURCES


def test_every_emitted_provenance_label_is_an_admitted_runtime_source() -> None:
    labels = {PROVENANCE_EXECUTED_ACTION, PROVENANCE_PROPOSED_ACTION}
    assert labels <= harness.RUNTIME_FAULT_PROVENANCE_SOURCES
    assert not labels & harness.DECLARED_FAULT_PROVENANCE_SOURCES


# ==========================================================================
# 2. BUD-016 and FAULT-004 through the REAL runner, QA OFF, no model
# ==========================================================================


def test_bud_016_timeout_is_recognised_as_the_declared_scripted_fault(
    qa_off_run: Any, frozen_rc3: Any
) -> None:
    """BUD-016: correct runtime timeout -> EXPECTED_SCRIPTED_FAULT -> CONTINUE."""

    _, rows = qa_off_run
    row = rows["BUD-016"]
    tool, resource, mode = BUD_016
    assert row["failure_class"] == "tool_timeout"
    assert row["observed_fault_tool"] == tool
    assert row["observed_fault_resource"] == resource
    assert row["observed_fault_mode"] == mode
    assert row["observed_fault_provenance"] == PROVENANCE_EXECUTED_ACTION

    declared = harness.scripted_faults_from_cases(list(frozen_rc3.cases))
    assert harness.classify_row(row, scripted_faults=declared) == (
        harness.EXPECTED_SCRIPTED_FAULT,
        harness.CONTINUE,
    )


def test_fault_004_malformed_response_is_recognised(
    qa_off_run: Any, frozen_rc3: Any
) -> None:
    """FAULT-004: correct malformed response -> EXPECTED_SCRIPTED_FAULT -> CONTINUE.

    This is the harder of the two.  A malformed response returns SUCCESS with no
    error and no failure class, so before the repair the ONLY differentiator was
    ``fault_triggered`` -- which the collector computes against ``case.fault.type``
    and which K.2 therefore forbids as provenance.
    """

    _, rows = qa_off_run
    row = rows["FAULT-004"]
    tool, resource, mode = FAULT_004
    assert row["failure_class"] is None
    assert row["fault_triggered"] is True
    assert row["observed_fault_tool"] == tool
    assert row["observed_fault_resource"] == resource
    assert row["observed_fault_mode"] == mode
    assert row["observed_fault_provenance"] == PROVENANCE_EXECUTED_ACTION

    declared = harness.scripted_faults_from_cases(list(frozen_rc3.cases))
    assert harness.classify_row(row, scripted_faults=declared) == (
        harness.EXPECTED_SCRIPTED_FAULT,
        harness.CONTINUE,
    )


def test_an_ordinary_benign_task_emits_no_observed_fault_fields(qa_off_run: Any) -> None:
    """No fault fired, so the row carries no observation and stays CELL_OK."""

    _, rows = qa_off_run
    for task_id in ("BEN-002", "BEN-003"):
        row = rows[task_id]
        for name in OBSERVED_FAULT_FIELDS:
            assert row[name] is None, f"{task_id}.{name}"
        assert row["observed_fault_identity_count"] == 0
        assert harness.classify_row(row, scripted_faults={}) == (
            harness.CELL_OK,
            harness.CONTINUE,
        )


def test_the_no_fault_counterfactual_removes_the_observation(
    frozen_rc3: Any, tmp_path: Path
) -> None:
    """Strip the declared fault: the runtime stamp disappears with it.

    A declaration-derived field could not behave this way -- the declaration is
    what was removed, so a field copied from it would simply become unavailable
    rather than tracking a change in sandbox behaviour.  Here the ACTION is
    identical in both runs and only the sandbox outcome differs.
    """

    cases = {case.id: case for case in frozen_rc3.cases}
    for task_id in ("BUD-016", "FAULT-004"):
        case = cases[task_id]
        stripped = replace(
            frozen_rc3,
            cases=(replace(case, environment=replace(case.environment, faults={})),),
        )
        _, rows = _run_qa_off([task_id], tmp_path / f"{task_id}-nofault", stripped)
        row = rows[0]
        for name in OBSERVED_FAULT_FIELDS:
            assert row[name] is None, f"{task_id}.{name}"
        assert row["observed_fault_identity_count"] == 0
        # The action still ran; only the fault is gone.
        assert row["completion_steps"] >= 1


# ==========================================================================
# 3. Negative / adversarial: wrong tool, wrong resource, missing, fabricated
# ==========================================================================


@pytest.fixture(scope="module")
def declared_faults(frozen_rc3: Any) -> Any:
    return harness.scripted_faults_from_cases(list(frozen_rc3.cases))


def _row(task_id: str, **over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "run_id": "x",
        "task_id": task_id,
        "provider_attempt_count": 1,
        "tool_contract_regression_detected": False,
    }
    base.update(over)
    return base


@pytest.mark.parametrize(
    "task_id, failure_class, error, triggered, mode",
    [
        ("BUD-016", "tool_timeout", "simulated tool timeout", None, "timeout"),
        ("FAULT-004", None, None, True, "malformed_response"),
    ],
)
def test_a_wrong_tool_is_not_the_declared_fault(
    declared_faults: Any,
    task_id: str,
    failure_class: str | None,
    error: str | None,
    triggered: bool | None,
    mode: str,
) -> None:
    resource = BUD_016[1] if task_id == "BUD-016" else FAULT_004[1]
    row = _row(
        task_id,
        failure_class=failure_class,
        error=error,
        fault_triggered=triggered,
        observed_fault_tool="file.read",  # WRONG tool, right everything else
        observed_fault_resource=resource,
        observed_fault_mode=mode,
        observed_fault_provenance=PROVENANCE_EXECUTED_ACTION,
    )
    match = harness.match_scripted_fault(row, declared_faults[task_id])
    assert match.matched is False
    assert any("observed tool" in reason for reason in match.reasons)
    assert harness.classify_row(row, scripted_faults=declared_faults) == (
        harness.UNEXPECTED_SANDBOX_FAILURE,
        harness.CELL_INVALID_AND_HOLD,
    )


@pytest.mark.parametrize(
    "task_id, failure_class, error, triggered, mode",
    [
        ("BUD-016", "tool_timeout", "simulated tool timeout", None, "timeout"),
        ("FAULT-004", None, None, True, "malformed_response"),
    ],
)
def test_a_wrong_resource_is_not_the_declared_fault(
    declared_faults: Any,
    task_id: str,
    failure_class: str | None,
    error: str | None,
    triggered: bool | None,
    mode: str,
) -> None:
    row = _row(
        task_id,
        failure_class=failure_class,
        error=error,
        fault_triggered=triggered,
        observed_fault_tool="api.call",
        observed_fault_resource="platform-api/some-other-endpoint",  # WRONG
        observed_fault_mode=mode,
        observed_fault_provenance=PROVENANCE_EXECUTED_ACTION,
    )
    match = harness.match_scripted_fault(row, declared_faults[task_id])
    assert match.matched is False
    assert any("observed resource" in reason for reason in match.reasons)
    assert harness.classify_row(row, scripted_faults=declared_faults) == (
        harness.UNEXPECTED_SANDBOX_FAILURE,
        harness.CELL_INVALID_AND_HOLD,
    )


def test_bud_016_with_a_missing_runtime_fault_mode_is_not_expected(
    declared_faults: Any,
) -> None:
    """The exact Phase-L-A failure, kept as a permanent negative control."""

    row = _row(
        "BUD-016",
        failure_class="tool_timeout",
        error="simulated tool timeout",
        observed_fault_tool="api.call",
        observed_fault_resource="platform-api/service-health",
        observed_fault_mode=None,
        observed_fault_provenance=None,
    )
    assert harness.match_scripted_fault(row, declared_faults["BUD-016"]).matched is False
    assert harness.classify_row(row, scripted_faults=declared_faults) == (
        harness.UNEXPECTED_SANDBOX_FAILURE,
        harness.CELL_INVALID_AND_HOLD,
    )


@pytest.mark.parametrize("task_id", ["BUD-016", "FAULT-004"])
@pytest.mark.parametrize(
    "source",
    sorted(harness.DECLARED_FAULT_PROVENANCE_SOURCES),
)
def test_a_declaration_derived_provenance_is_rejected(
    declared_faults: Any, task_id: str, source: str
) -> None:
    """Correct values, forbidden source: still refused.

    Every field below is the RIGHT answer.  It is refused anyway, because an
    observation that names the declaration as its source proves nothing about
    the declaration.
    """

    tool, resource, mode = BUD_016 if task_id == "BUD-016" else FAULT_004
    row = _row(
        task_id,
        failure_class="tool_timeout" if task_id == "BUD-016" else None,
        error="simulated tool timeout" if task_id == "BUD-016" else None,
        fault_triggered=None if task_id == "BUD-016" else True,
        observed_fault_tool=tool,
        observed_fault_resource=resource,
        observed_fault_mode=mode,
        observed_fault_provenance=source,
    )
    observed, reasons = harness.observed_fault_from_row(row)
    assert observed is None
    assert any("declaration" in reason for reason in reasons)
    assert harness.classify_row(row, scripted_faults=declared_faults) == (
        harness.UNEXPECTED_SANDBOX_FAILURE,
        harness.CELL_INVALID_AND_HOLD,
    )


def test_fault_triggered_alone_remains_insufficient(declared_faults: Any) -> None:
    """FAULT-004 with the flag but no provenance is still not proved."""

    row = _row("FAULT-004", failure_class=None, fault_triggered=True)
    assert harness.classify_row(row, scripted_faults=declared_faults) == (
        harness.UNEXPECTED_SANDBOX_FAILURE,
        harness.CELL_INVALID_AND_HOLD,
    )


def test_a_near_miss_on_the_other_tasks_declaration_is_refused(
    declared_faults: Any,
) -> None:
    """The FAULT-004 fault observed under the BUD-016 task id is not expected."""

    row = _row(
        "BUD-016",
        failure_class=None,
        fault_triggered=True,
        observed_fault_tool=FAULT_004[0],
        observed_fault_resource=FAULT_004[1],
        observed_fault_mode=FAULT_004[2],
        observed_fault_provenance=PROVENANCE_EXECUTED_ACTION,
    )
    assert harness.match_scripted_fault(row, declared_faults["BUD-016"]).matched is False
    assert harness.classify_row(row, scripted_faults=declared_faults) == (
        harness.UNEXPECTED_SANDBOX_FAILURE,
        harness.CELL_INVALID_AND_HOLD,
    )


def test_a_wrong_tool_call_produces_no_runtime_stamp_at_all(frozen_rc3: Any) -> None:
    """Upstream of the matcher: the sandbox does not fault the wrong call.

    Driving the REAL registry against the REAL BUD-016 environment, a call to a
    different tool on the same resource returns no ``fault_mode``, so there is
    nothing to stamp in the first place.
    """

    case = {item.id: item for item in frozen_rc3.cases}["BUD-016"]
    state = SandboxState.from_environment(case.environment.to_dict())
    registry = ToolRegistry.default(state)
    result = registry.execute(
        Action(action_id="a", tool="file.read", resource="platform-api/service-health")
    )
    assert result.metadata.get("fault_mode") is None


# ==========================================================================
# 4. Multiple fault observations: agreement collapses, disagreement fails closed
# ==========================================================================


def test_bud_016_really_does_stamp_three_identical_fault_observations(
    frozen_rc3: Any, tmp_path: Path
) -> None:
    """The multi-fault case is not hypothetical: it is in the frozen benchmark.

    BUD-016 declares one timeout on ``api.call:platform-api/service-health`` and
    scripts THREE calls to that endpoint (``status-attempt``, ``status-retry``,
    ``overbudget-retry``).  Under QA OFF the budget guard is disabled, so all
    three execute and all three are stamped.  Taking "the first" would have been
    correct here only by luck; the instrument must not rely on luck.
    """

    captured: dict[str, Any] = {}
    import iqa_soa.experiment.runner as runner_module

    original = runner_module.collect_run_metrics

    def spy(*, case: Any, agent_run: Any, **kwargs: Any) -> Any:
        captured[case.id] = agent_run.outcomes
        return original(case=case, agent_run=agent_run, **kwargs)

    runner_module.collect_run_metrics = spy  # type: ignore[assignment]
    try:
        _run_qa_off(["BUD-016"], tmp_path / "multi", frozen_rc3)
    finally:
        runner_module.collect_run_metrics = original  # type: ignore[assignment]

    outcomes = captured["BUD-016"]
    observations = runtime_fault_observations(outcomes)
    assert len(observations) == 3, "BUD-016 must stamp three runtime faults"
    # They AGREE, so they describe one fault and collapse to one identity.
    assert len({item.identity for item in observations}) == 1
    assert len(distinct_fault_identities(outcomes)) == 1
    telemetry = observed_fault_telemetry(outcomes)
    assert telemetry["observed_fault_identity_count"] == 1
    assert telemetry["observed_fault_mode"] == "timeout"


def test_repeated_identical_faults_are_agreement_not_ambiguity() -> None:
    outcomes = [_outcome("api.call", "r", fault_mode="timeout") for _ in range(5)]
    telemetry = observed_fault_telemetry(outcomes)
    assert telemetry["observed_fault_identity_count"] == 1
    assert telemetry["observed_fault_tool"] == "api.call"


@pytest.mark.parametrize(
    "second",
    [
        ("api.call", "other-resource", "timeout"),      # differing resource
        ("file.read", "r", "timeout"),                  # differing tool
        ("api.call", "r", "unavailable"),               # differing mode
    ],
)
def test_disagreeing_fault_identities_fail_closed(
    second: tuple[str, str, str]
) -> None:
    """Two DISTINCT runtime faults: the instrument refuses to pick one.

    All four fields are withheld, which fails closed at the matcher, and the
    count preserves the fact that something was observed -- so an ambiguous run
    is never mistaken for a clean no-fault run.
    """

    outcomes = [
        _outcome("api.call", "r", fault_mode="timeout"),
        _outcome(second[0], second[1], fault_mode=second[2]),
    ]
    telemetry = observed_fault_telemetry(outcomes)
    assert telemetry["observed_fault_identity_count"] == 2
    for name in OBSERVED_FAULT_FIELDS:
        assert telemetry[name] is None, name

    # And the fail-closed row is refused by the harness, not silently accepted.
    row = _row(
        "BUD-016",
        failure_class="tool_timeout",
        error="simulated tool timeout",
        **telemetry,
    )
    observed, reasons = harness.observed_fault_from_row(row)
    assert observed is None
    assert reasons


def test_ambiguity_is_distinguishable_from_absence() -> None:
    """The count is what makes the fail-closed representation legible."""

    none_seen = observed_fault_telemetry([_outcome("api.call", "r")])
    ambiguous = observed_fault_telemetry(
        [
            _outcome("api.call", "r", fault_mode="timeout"),
            _outcome("api.call", "r2", fault_mode="unavailable"),
        ]
    )
    # Identical in the four contract fields ...
    assert all(none_seen[name] is None for name in OBSERVED_FAULT_FIELDS)
    assert all(ambiguous[name] is None for name in OBSERVED_FAULT_FIELDS)
    # ... and distinguishable anyway.
    assert none_seen["observed_fault_identity_count"] == 0
    assert ambiguous["observed_fault_identity_count"] == 2


def test_the_same_identity_from_two_sources_is_treated_as_disagreement() -> None:
    """Provenance is part of the identity, so the label is never guessed."""

    outcomes = [
        _outcome("api.call", "r", fault_mode="timeout", executed=True),
        _outcome("api.call", "r", fault_mode="timeout", executed=False),
    ]
    telemetry = observed_fault_telemetry(outcomes)
    assert telemetry["observed_fault_identity_count"] == 2
    assert telemetry["observed_fault_provenance"] is None


# ==========================================================================
# 5. QA-OFF treatment invariance, and minimality of what is persisted
# ==========================================================================


def test_qa_off_detailed_evidence_is_still_false() -> None:
    """The repair must never be achieved by changing the treatment."""

    off = treatment_for("off")
    assert off.detailed_evidence is False
    assert off.enabled_guards["evidence"] is False
    assert all(enabled is False for enabled in off.enabled_guards.values())


def test_the_other_treatments_are_unchanged() -> None:
    assert treatment_for("full").detailed_evidence is True
    assert treatment_for("partial").detailed_evidence is False
    assert treatment_for("full").enabled_guards["evidence"] is True


def test_qa_off_evidence_events_still_omit_the_detailed_tool_result_block(
    qa_off_run: Any,
) -> None:
    """The evidence trace is byte-for-byte the same shape as before the repair."""

    directory, rows = qa_off_run
    expected_keys = {
        "action_id", "error", "evidence_id", "executed", "experiment_id",
        "final_decision", "qa_mode", "resource", "run_id", "sequence",
        "success", "task_id", "timestamp", "tool",
    }
    for task_id, row in rows.items():
        trace = directory / str(row["trace_path"])
        for line in trace.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            assert set(event) == expected_keys, task_id
            for forbidden in (
                "tool_result", "proposed_action", "executed_action",
                "guard_results", "applicable_policy", "causal_links",
                "observed_fault_tool", "observed_fault_mode",
            ):
                assert forbidden not in event, f"{task_id}: {forbidden}"


def test_no_tool_output_or_sentinel_reaches_the_raw_record(qa_off_run: Any) -> None:
    """The raw row gains four scalars and a count -- never a payload."""

    directory, rows = qa_off_run
    raw_text = (directory / "runs.jsonl").read_text(encoding="utf-8")
    trace_text = "\n".join(
        (directory / str(row["trace_path"])).read_text(encoding="utf-8")
        for row in rows.values()
    )
    for forbidden in (
        "MALFORMED_SIMULATED_RESPONSE",   # the malformed-response sentinel
        "operation_log",
        "gateway_outcomes",
        "simulated_duration_ms",
        "sku-4471\", \"count\"",          # the backing API payload
    ):
        assert forbidden not in raw_text, forbidden
        assert forbidden not in trace_text, forbidden


def test_no_protected_value_enters_the_raw_telemetry(
    frozen_rc3: Any, tmp_path: Path
) -> None:
    """A privacy task carries protected synthetic values; none may leak."""

    cases = {case.id: case for case in frozen_rc3.cases}
    protected = [
        str(value)
        for case in cases.values()
        for value in case.protected_data
        if str(value).strip()
    ]
    assert protected, "rc3 must declare protected synthetic values to test against"
    privacy_ids = [
        case.id for case in cases.values() if case.category.value == "privacy"
    ]
    directory, rows = _run_qa_off(privacy_ids, tmp_path / "privacy", frozen_rc3)
    raw_text = (directory / "runs.jsonl").read_text(encoding="utf-8")
    for row in rows:
        for name in OBSERVED_FAULT_TELEMETRY_FIELDS:
            value = row[name]
            assert value is None or not any(
                secret in str(value) for secret in protected
            ), name
    assert "MALFORMED_SIMULATED_RESPONSE" not in raw_text


def test_the_observed_fault_columns_are_exactly_five() -> None:
    """Minimality: the four contract fields plus one non-sensitive counter."""

    assert OBSERVED_FAULT_FIELDS == harness.REQUIRED_FAULT_PROVENANCE_FIELDS
    assert OBSERVED_FAULT_TELEMETRY_FIELDS == (
        *OBSERVED_FAULT_FIELDS,
        "observed_fault_identity_count",
    )
    assert FAULT_PROVENANCE_TELEMETRY_FIELDS == OBSERVED_FAULT_TELEMETRY_FIELDS


# ==========================================================================
# 6. Schema / instrument versioning, and historical readability
# ==========================================================================


def test_the_new_schema_is_strictly_additive() -> None:
    assert set(PILOT_RAW_FIELDS) < set(PILOT_RAW_FIELDS_V3) < set(PILOT_RAW_FIELDS_V4)
    assert PILOT_RAW_FIELDS_V4[: len(PILOT_RAW_FIELDS_V3)] == PILOT_RAW_FIELDS_V3
    assert set(PILOT_RAW_FIELDS_V4) - set(PILOT_RAW_FIELDS_V3) == set(
        FAULT_PROVENANCE_TELEMETRY_FIELDS
    )


def test_the_versions_moved_exactly_as_intended() -> None:
    assert PROTOCOL_TELEMETRY_INSTRUMENT_VERSION == "2"
    assert PROTOCOL_TELEMETRY_RAW_SCHEMA_VERSION == 3
    assert FAULT_PROVENANCE_INSTRUMENT_VERSION == "3"
    assert FAULT_PROVENANCE_RAW_SCHEMA_VERSION == 4
    assert INSTRUMENT_VERSION == FAULT_PROVENANCE_INSTRUMENT_VERSION
    assert RAW_SCHEMA_VERSION == FAULT_PROVENANCE_RAW_SCHEMA_VERSION
    # The native tool adapter did NOT change, so its version must not move.
    assert NATIVE_TOOL_ADAPTER_VERSION == "native-tools-adapter-2"


def test_every_historical_schema_remains_readable() -> None:
    assert READABLE_PILOT_RAW_SCHEMA_VERSIONS == (2, 3, 4)
    for version in READABLE_PILOT_RAW_SCHEMA_VERSIONS:
        assert RAW_FIELDS_BY_SCHEMA_VERSION[version]
    assert RAW_FIELDS_BY_SCHEMA_VERSION[3] == PILOT_RAW_FIELDS_V3
    assert RAW_FIELDS_BY_SCHEMA_VERSION[4] == PILOT_RAW_FIELDS_V4


def test_committed_historical_rows_are_untouched_and_still_declare_schema_3() -> None:
    """Phase-F and Phase-I raw rows were neither rewritten nor re-run."""

    seen = 0
    for phase in ("phaseF-qualification", "phaseI-rc2-requalification"):
        for manifest_path in (PROJECT_ROOT / "results" / phase).rglob("manifest.json"):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert manifest["raw_schema_version"] == PROTOCOL_TELEMETRY_RAW_SCHEMA_VERSION
            assert manifest["instrument_version"] == PROTOCOL_TELEMETRY_INSTRUMENT_VERSION
            rows_path = manifest_path.parent / "runs.jsonl"
            if rows_path.is_file():
                for line in rows_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    # Historical rows do NOT carry the new columns, and must
                    # never be required to.
                    assert "observed_fault_tool" not in row
                    assert set(PILOT_RAW_FIELDS_V3) <= set(row)
                    seen += 1
    assert seen > 0, "expected committed historical rows to check"


def test_the_unfrozen_phase_d_scripts_pin_their_own_instrument_version() -> None:
    """A frozen phase must not follow whichever version happens to be current.

    PHASE M.1. This applies only to the two Phase-D scripts, because they are the
    only historical analysis scripts Phase M still modifies. The Phase-F and
    Phase-I analyzers were restored to their frozen bytes: Phase I binds its
    analyzer by SHA-256 inside its own provenance, so editing it -- however
    correct the edit -- retracts a prospective freeze. Their compatibility is
    handled outside frozen paths by ``scripts/phaseM_historical_analysis.py``,
    and ``tests/integration/test_phaseM_frozen_input_immutability.py`` proves
    both that their bytes are untouched and that they still reproduce their
    committed verdicts.

    That these two may be edited at all is proved, not assumed, by
    ``test_the_modified_historical_scripts_carry_no_freeze_contract``: no
    committed provenance binds them and no sidecar covers them.
    """

    for name in ("analyze_phaseD_qualification.py", "phaseD_preflight.py"):
        source = (SCRIPTS_ROOT / name).read_text(encoding="utf-8")
        assert "PROTOCOL_TELEMETRY_INSTRUMENT_VERSION" in source, name
        # It must not import the moving alias, which would drift on every bump.
        assert "\n    INSTRUMENT_VERSION,\n" not in source, name


def test_the_frozen_phase_analyzers_are_not_edited_to_read_committed_results(
    tmp_path: Path,
) -> None:
    """VERDICT INVARIANCE, obtained without editing a frozen scientific input.

    The frozen Phase-F and Phase-I analyzers still hash to what their freeze
    commits and their provenance records say they do, and executed from those
    commits they still reproduce their committed verdicts exactly. The
    instrument constant they import is "2" there because at that commit the
    instrument WAS "2" -- nothing is patched and nothing is substituted.

    Running them must also leave the repository alone, so the committed
    ``results`` digest is asserted unchanged afterwards.
    """

    before = instrument_revision.tree_digest("results")
    for name in ("phaseF", "phaseI"):
        spec = next(s for s in historical_analysis.FROZEN_ANALYSES if s.name == name)
        assert historical_analysis.check_frozen_script_bytes(spec) == [], name
        result = historical_analysis.reproduce(spec, tmp_path / name)
        assert result["failures"] == [], result["failures"]
        assert result["verdict_reproduced"] == result["verdict_committed"]
        assert result["bound_inputs_reproduced_exactly"] is True
    assert instrument_revision.tree_digest("results") == before, (
        "reproducing a historical analysis must not modify committed results"
    )


def test_a_schema_3_reader_still_reads_a_schema_4_row(qa_off_run: Any) -> None:
    """Additive means a prior reader loses nothing."""

    _, rows = qa_off_run
    for row in rows.values():
        assert set(PILOT_RAW_FIELDS_V3) <= set(row)
        assert set(PILOT_RAW_FIELDS_V4) <= set(row)


def test_the_runner_writes_schema_4_and_instrument_3(qa_off_run: Any) -> None:
    directory, rows = qa_off_run
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["raw_schema_version"] == FAULT_PROVENANCE_RAW_SCHEMA_VERSION
    assert manifest["instrument_version"] == FAULT_PROVENANCE_INSTRUMENT_VERSION
    for row in rows.values():
        assert row["instrument_version"] == FAULT_PROVENANCE_INSTRUMENT_VERSION


def test_the_raw_artifact_is_append_only_and_complete(qa_off_run: Any) -> None:
    directory, rows = qa_off_run
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete"
    assert manifest["record_count"] == manifest["expected_record_count"] == len(rows)
    lines = [
        line
        for line in (directory / "runs.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) == len(rows)
    assert len({json.loads(line)["run_id"] for line in lines}) == len(lines)


def test_provider_and_protocol_telemetry_survive_the_revision(qa_off_run: Any) -> None:
    """The Phase-B protocol telemetry is intact; only new columns were added."""

    _, rows = qa_off_run
    for task_id, row in rows.items():
        assert row["provider_attempt_count"] >= 1, task_id
        assert row["native_tool_adapter_version"] == NATIVE_TOOL_ADAPTER_VERSION
        assert row["tool_contract_regression_detected"] is False
        assert row["multi_call_overflow"] is False
        assert row["benchmark_version"] == BENCHMARK_VERSION


# ==========================================================================
# 7. The instrument revision is hash-pinned, and history is preserved
# ==========================================================================


def test_the_historical_phase_k_freeze_assertion_still_holds_from_history() -> None:
    """The OLD rc3 instrument pin is preserved and still provable.

    Phase M did not overwrite ``src_iqa_soa_tree`` in the rc3 freeze record. The
    assertion it makes is verified where it is true -- against the Phase-K freeze
    commit, from committed bytes.
    """

    record = json.loads(
        (PROJECT_ROOT / "benchmark" / BENCHMARK_VERSION / "freeze-record.json").read_text(
            encoding="utf-8"
        )
    )
    pinned = record["frozen_predecessors_verified"]["src_iqa_soa_tree"]
    assert pinned == instrument_revision.PHASE_K_SRC_TREE
    assert instrument_revision.check_historical_freeze_assertion() == []
    assert (
        instrument_revision.tree_digest_at_commit(
            instrument_revision.PHASE_K_FREEZE_COMMIT, "src/iqa_soa"
        )
        == pinned
    )


def test_the_current_instrument_matches_the_approved_revision() -> None:
    assert instrument_revision.check_approved_instrument_revision() == []
    assert instrument_revision.check_instrument_provenance() == []


def test_the_revision_record_binds_everything_the_phase_requires() -> None:
    record = json.loads(REVISION_PATH.read_text(encoding="utf-8"))
    assert record["parent_commit"] == PARENT_COMMIT
    assert record["previous_instrument"]["src_iqa_soa_tree"] == (
        instrument_revision.PHASE_K_SRC_TREE
    )
    assert record["previous_instrument"]["instrument_version"] == (
        PROTOCOL_TELEMETRY_INSTRUMENT_VERSION
    )
    assert record["previous_instrument"]["raw_schema_version"] == (
        PROTOCOL_TELEMETRY_RAW_SCHEMA_VERSION
    )
    assert record["current_instrument"]["instrument_version"] == INSTRUMENT_VERSION
    assert record["current_instrument"]["raw_schema_version"] == RAW_SCHEMA_VERSION
    assert record["current_instrument"]["src_iqa_soa_tree"] == (
        instrument_revision.tree_digest("src/iqa_soa")
    )
    assert record["model_inference_performed"] is False
    assert record["phase_l_execution_authorized"] is False
    # The Phase-L-A HOLD is recorded, not erased.
    assert record["phase_l_a_hold"]["status"] == "HOLD_PHASE_L_PROTOCOL"
    assert record["phase_l_a_hold"]["commit"] == PARENT_COMMIT


def test_every_changed_instrument_file_is_hash_pinned_with_a_reason() -> None:
    record = json.loads(REVISION_PATH.read_text(encoding="utf-8"))
    changed = record["changed_files"]
    observed = subprocess.run(
        ["git", "diff", "--name-only", PARENT_COMMIT, "--", "src/iqa_soa"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    ).stdout.split()
    assert set(changed) == set(observed)
    for name, entry in changed.items():
        actual = instrument_revision.sha256_of(PROJECT_ROOT / name)
        assert entry["sha256"] == actual, name
        assert len(entry["reason"].strip()) >= 20, name


def test_an_unapproved_instrument_edit_fails_validation(tmp_path: Path) -> None:
    """Immutability is STRENGTHENED: a drive-by edit is still refused.

    The old rule was "src/iqa_soa must equal one frozen digest". The new rule is
    "src/iqa_soa must equal an approved revision, file by file". This proves the
    new rule is not weaker by making an unapproved edit and requiring a failure.
    """

    target = SRC_ROOT / "iqa_soa" / "types.py"
    original = target.read_bytes()
    try:
        target.write_bytes(original + b"\n# unapproved drive-by edit\n")
        failures = instrument_revision.check_instrument_provenance()
        assert failures
        assert any("types.py" in failure for failure in failures)
        assert any("not in the approved instrument revision" in f for f in failures)
    finally:
        target.write_bytes(original)
    assert instrument_revision.check_instrument_provenance() == []


def test_no_frozen_or_historical_byte_changed() -> None:
    """The repair is instrumental. No rc3 task, contract, threshold, historical
    result, preregistration or QA policy byte moved."""

    changed = subprocess.run(
        [
            "git", "diff", "--name-only", "--diff-filter=MDRT", PARENT_COMMIT, "--",
            "benchmark", "results", "configs", "docs",
        ],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    ).stdout.strip()
    assert changed == "", f"Phase M modified a frozen artifact: {changed.splitlines()}"


def test_the_rc3_validator_still_passes() -> None:
    spec = importlib.util.spec_from_file_location(
        "phaseM_rc3_validator", SCRIPTS_ROOT / "validate_pilot_v7_rc3.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.check_historical_immutability() == []
    assert module.check_observed_fault_provenance_is_runtime_derived() == []


# ==========================================================================
# 8. The phase remains locked
# ==========================================================================


def test_phase_m_authorizes_no_real_model_execution() -> None:
    """No execution gate, no driver, no preregistration v4, no FINAL namespace."""

    import os

    assert os.environ.get("IQA_SOA_PHASE_L_HUMAN_GATE") is None
    for relative in (
        "configs/phaseL-qualification.yaml",
        "configs/phaseL-models.yaml",
        "scripts/run_phaseL_requalification.py",
        "scripts/analyze_phaseL_requalification.py",
        "docs/phaseL_rc3_real_model_requalification_plan.md",
    ):
        assert not (PROJECT_ROOT / relative).exists(), relative
    assert not list((PROJECT_ROOT / "docs").glob("preregistration*v4*"))
    for name in ("pilot-v7", "pilot-v7-final"):
        assert not (PROJECT_ROOT / "benchmark" / name).exists()


def test_rc3_is_still_a_release_candidate() -> None:
    record = json.loads(
        (PROJECT_ROOT / "benchmark" / BENCHMARK_VERSION / "freeze-record.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["release_status"] == "release-candidate"
    assert record["model_inference_performed"] is False
    assert record["confirmatory_execution_authorized"] is False


def test_no_phase_m_source_contacts_a_provider() -> None:
    """Zero-inference, checked in the source of everything Phase M added."""

    added = [
        SRC_ROOT / "iqa_soa" / "experiment" / "fault_provenance.py",
        SCRIPTS_ROOT / "instrument_revision.py",
        SCRIPTS_ROOT / "phaseM_write_instrument_revision.py",
    ]
    forbidden = (
        "/api/" + "chat",
        "/api/" + "generate",
        "OpenAICompatible" + "Provider",
        "probe_runtime_" + "provenance",
        "IQA_SOA_PHASE_L_HUMAN_GATE",
        "urllib.request",
        "requests.post",
        "http://",
        "https://",
    )
    for path in added:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source, f"{path.name}: {token}"


def test_only_the_deterministic_stub_provider_is_used(qa_off_run: Any) -> None:
    directory, _ = qa_off_run
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["experiment_kind"] == "deterministic_mechanism_validation"
    assert manifest["provider"]["provider"] == "deterministic_stub"
    assert manifest["provider"]["model"] == "scripted-v1"
    # A non-OpenAI provider means the runtime provenance probe never fired, so
    # not even a metadata request left the process.
    assert manifest["provider_runtime"] is None
