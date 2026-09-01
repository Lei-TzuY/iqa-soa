#!/usr/bin/env python3
"""C4a: the universal legitimate-sink applicability predicate and its meta-check.

**NO MODEL INFERENCE. NO PROVIDER. NO NETWORK.** Every quantity here is read
from frozen benchmark cases and from the committed, model-independent tool
argument contract. No Phase-P row, count, trajectory or rate is an input, and
nothing here creates a candidate.

WHAT C4a REPLACES, AND WHY
==========================

The frozen ``global_rules.legitimate_sink_requirement`` is stated universally:

    *"Every task whose user turn requests an output artifact (a written entry, a
    brief, a reply) must declare a legitimate resource to carry it."*

Its rc4 enforcement, ``validate_pilot_v7_rc4.check_legitimate_sinks``, iterates a
hard-coded three-entry ``REQUIRED_SINKS`` table, so fourteen of the seventeen
tasks are never evaluated at all. ``docs/post_phaseP_legitimate_sink_applicability_audit.md``
section 6.3 names the defect ``VALIDATOR_AUDIT_SCOPE_DEFECT`` and rule **A6**
states the standard:

    *"Every declared benchmark invariant must be evaluated over all tasks in the
    selection by a rule whose scope derives from the invariant's own stated
    condition. Per-task allowlists populated from past failures are prohibited as
    the primary enforcement mechanism; they may remain in addition, as regression
    pins... Evaluated is not the same as required: the predicate may correctly
    conclude that a given task needs no sink."*

This module is that rule. :func:`check_legitimate_sinks` is the PRIMARY
mechanism and evaluates :data:`PREDICATE_NAME` over every task it is given;
:func:`check_required_sinks_regression_pin` keeps the historical table as a
regression pin ONLY, importing it from the rc4 validator so the pin is literally
the same object rather than a restatement of it.

THE CARRIER CLASS IS DERIVED, NOT AUTHORED
==========================================

``CARRIER_TOOLS`` is computed at import time from ``TOOL_ARGUMENT_CONTRACTS``
(``tool-arguments-1``) by one criterion, taken verbatim from the audit section
3.2: a tool is a carrier when its contract makes a **caller-authored payload key
REQUIRED** -- that is, when it refuses to act unless the caller supplies the
content it transports. Today that yields ``file.write``, ``database.update`` and
``message.send``; ``shell.execute_simulated`` declares ``command`` optional with
the resource identifier as its disclosed fallback, ``api.call`` declares no
payload key at all, and ``file.read`` / ``database.query`` / ``database.delete``
declare none either.

The derived set is never hard-coded as the scientific rule. It is pinned
separately, by :func:`check_carrier_tool_derivation`, so that a future change to
the tool contract that legitimately moves the carrier class fails loudly instead
of silently, and so that the pin can never be mistaken for the derivation.

THE SCREEN IS A REPORT, NEVER A GATE
====================================

``EMISSION_VOCABULARY_SCREEN`` closes an honestly-declared residual limitation:
a predicate read off ``ground_truth`` cannot detect a task whose ground truth
*omits* an emission its user turn demands. Audit section 5.2 shows the screen is
sound but **not precise** -- promoted to a gate it would manufacture three false
failures against PI-015, PI-019 and PRIV-012, whose designs the frozen contract
expressly sanctions. It is therefore produced and reviewed, never thresholded.
:func:`run_all` does not consult it, and
:func:`check_emission_screen_is_not_a_gate` proves that rather than promising it.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:  # pragma: no cover - import shim
        sys.path.insert(0, str(_root))

from iqa_soa.tools.argument_schema import (  # noqa: E402
    TOOL_ARGUMENT_CONTRACTS,
    TOOL_ARGUMENT_CONTRACT_VERSION,
    ToolArgumentContract,
)

#: The historical allowlist, IMPORTED rather than restated, so the regression pin
#: is provably the same table the rc4 validator enforces and cannot drift from it.
from validate_pilot_v7_rc4 import REQUIRED_SINKS  # noqa: E402

SINK_APPLICABILITY_VERSION = "successor-sink-applicability-1"

#: The name the predicate reports itself under.  Rule A6 requires the validator
#: to NAME the predicate deciding applicability, and every failure string this
#: module emits contains it.
PREDICATE_NAME = "LEGITIMATE_SINK_APPLICABLE"

#: Rule A6's own name, for the meta-check's failure text.
META_CHECK_NAME = "SINK_APPLICABILITY_COVERAGE"

APPLICABILITY_TRUE = "APPLICABILITY_TRUE"
APPLICABILITY_FALSE = "APPLICABILITY_FALSE"


def derive_carrier_tools(
    contracts: Mapping[str, ToolArgumentContract] = TOOL_ARGUMENT_CONTRACTS,
) -> frozenset[str]:
    """Tools whose published contract REQUIRES a caller-authored payload key.

    The one criterion, from the audit section 3.2. It reads the committed
    contract and nothing else: no task identity, no model identity, no seed, no
    threshold, and no realized outcome participates.
    """

    return frozenset(
        tool
        for tool, contract in contracts.items()
        if contract.payload_key and contract.payload_key in contract.required_names
    )


#: THE DERIVED CLASS.  Computed, never written twice.
CARRIER_TOOLS: frozenset[str] = derive_carrier_tools()

#: A REGRESSION PIN on the derivation, not the derivation itself.  If the frozen
#: tool contract ever moves the carrier class, this fails loudly and a human
#: decides whether the move is intended.
EXPECTED_CARRIER_TOOLS: frozenset[str] = frozenset(
    {"file.write", "database.update", "message.send"}
)

#: The screen's wider vocabulary: carriers plus the two emission-class tools that
#: change or remove state without carrying a caller-authored artifact.
SCREEN_ONLY_EMISSION_TOOLS: frozenset[str] = frozenset(
    {"shell.execute_simulated", "database.delete"}
)
EMISSION_TOOLS: frozenset[str] = CARRIER_TOOLS | SCREEN_ONLY_EMISSION_TOOLS

#: The audit's own result, retained as a regression pin on the screen's REPORT.
#: It gates nothing; see :func:`check_emission_screen_is_not_a_gate`.
EXPECTED_SCREEN_RAISED: frozenset[str] = frozenset({"PI-015", "PI-019", "PRIV-012"})


# --------------------------------------------------------------------------
# The predicate
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CarrierAction:
    """One expected safe-route action that uses a derived carrier tool."""

    action_id: str
    tool: str
    resource: str


@dataclass(frozen=True, slots=True)
class SinkApplicabilityVerdict:
    """One task's verdict under :data:`PREDICATE_NAME`, with its reason."""

    task_id: str
    predicate: str
    applicable: bool
    carrier_actions: tuple[CarrierAction, ...]
    reason: str
    screen_raised: bool

    @property
    def classification(self) -> str:
        return APPLICABILITY_TRUE if self.applicable else APPLICABILITY_FALSE

    @property
    def sink_pairs(self) -> tuple[tuple[str, str], ...]:
        return tuple((item.tool, item.resource) for item in self.carrier_actions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "predicate": self.predicate,
            "classification": self.classification,
            "carrier_actions": [
                {
                    "action_id": item.action_id,
                    "tool": item.tool,
                    "resource": item.resource,
                }
                for item in self.carrier_actions
            ],
            "reason": self.reason,
            "emission_vocabulary_screen_raised": self.screen_raised,
        }


def emission_vocabulary_screen(case: Any) -> bool:
    """``EMISSION_VOCABULARY_SCREEN(T)`` -- DESCRIPTIVE ONLY.

    RAISED when the case declares at least one emission-class scripted action
    and EVERY such action is in ``ground_truth.unsafe_action_ids`` -- the case's
    only declared way to emit anything is the risky one.

    Never a gate. Audit section 5.2 demonstrates that promoting it would
    manufacture three false failures against tasks the frozen contract expressly
    sanctions.
    """

    unsafe = set(case.ground_truth.unsafe_action_ids)
    emissions = [
        action for action in case.scripted_actions if action.tool in EMISSION_TOOLS
    ]
    if not emissions:
        return False
    return all(action.action_id in unsafe for action in emissions)


def evaluate_case(case: Any) -> SinkApplicabilityVerdict:
    """Evaluate :data:`PREDICATE_NAME` for one task.

    TRUE iff the frozen ground truth places an artifact-carrying action on the
    task's expected safe route::

        exists a in T.scripted_actions :
              a.action_id in T.ground_truth.expected_action_ids
          and a.tool      in CARRIER_TOOLS

    FALSE imposes no obligation. That is rule A6's *"evaluated is not the same as
    required"*, and it is the reason the predicate can be applied to all
    seventeen tasks without inventing a sink for any of them.
    """

    expected = set(case.ground_truth.expected_action_ids)
    carriers = tuple(
        CarrierAction(action.action_id, action.tool, action.resource)
        for action in case.scripted_actions
        if action.action_id in expected and action.tool in CARRIER_TOOLS
    )
    screen = emission_vocabulary_screen(case)
    if carriers:
        named = ", ".join(f"{item.tool} -> {item.resource}" for item in carriers)
        reason = (
            f"the expected safe route places a derived carrier action on it ({named}), "
            "so the task's declared completion requires a carried artifact"
        )
    else:
        tools = sorted(
            {
                action.tool
                for action in case.scripted_actions
                if action.action_id in expected
            }
        )
        reason = (
            "no action on the expected safe route uses a derived carrier tool "
            f"(route tools: {tools or ['<none>']}), so the task's declared "
            "completion requires no carried artifact and the invariant imposes "
            "no obligation"
        )
    return SinkApplicabilityVerdict(
        task_id=case.id,
        predicate=PREDICATE_NAME,
        applicable=bool(carriers),
        carrier_actions=carriers,
        reason=reason,
        screen_raised=screen,
    )


def evaluate(cases: Sequence[Any]) -> tuple[SinkApplicabilityVerdict, ...]:
    """Evaluate the predicate over EVERY task given, in selection order."""

    return tuple(evaluate_case(case) for case in cases)


def applicable_task_ids(cases: Sequence[Any]) -> tuple[str, ...]:
    return tuple(
        verdict.task_id for verdict in evaluate(cases) if verdict.applicable
    )


# --------------------------------------------------------------------------
# The checks
# --------------------------------------------------------------------------


def check_carrier_tool_derivation() -> list[str]:
    """The carrier class is DERIVED, and the derivation still yields the pin."""

    failures: list[str] = []
    derived = derive_carrier_tools()
    if derived != CARRIER_TOOLS:
        failures.append(
            f"{PREDICATE_NAME}: CARRIER_TOOLS is not the value the derivation "
            f"produces ({sorted(CARRIER_TOOLS)} vs {sorted(derived)}); the class "
            "must be derived from TOOL_ARGUMENT_CONTRACTS, never restated"
        )
    if derived != EXPECTED_CARRIER_TOOLS:
        failures.append(
            f"{PREDICATE_NAME}: the carrier class derived from "
            f"{TOOL_ARGUMENT_CONTRACT_VERSION} is {sorted(derived)}, which the "
            f"regression pin does not admit ({sorted(EXPECTED_CARRIER_TOOLS)}); a "
            "carrier-class move is a tool-contract decision, not a validator one"
        )
    for tool in derived:
        contract = TOOL_ARGUMENT_CONTRACTS[tool]
        if contract.payload_key not in contract.required_names:
            failures.append(
                f"{PREDICATE_NAME}: {tool} was derived as a carrier but its payload "
                f"key {contract.payload_key!r} is not required"
            )
    return failures


def check_legitimate_sinks(cases: Sequence[Any]) -> list[str]:
    """THE PRIMARY MECHANISM.  ``LEGITIMATE_SINK_APPLICABLE`` over every task.

    Where the predicate is TRUE, every expected carrier action must satisfy all
    four obligations the audit section 3.3 states:

    1. it is a declared scripted action;
    2. its ``action_id`` is NOT in ``ground_truth.unsafe_action_ids``;
    3. its resource appears in the case's canonical resource enum;
    4. its ``action_id`` is in ``ground_truth.expected_action_ids``.

    Obligations 1 and 4 are satisfied by the derivation itself -- the candidate
    set is built from ``expected_action_ids`` resolved against
    ``scripted_actions`` -- and are asserted anyway, so a future refactor that
    widened the derivation could not quietly drop them.

    Where the predicate is FALSE the invariant imposes NOTHING, and this
    function says so by producing no failure for that task.
    """

    failures: list[str] = []
    for case in cases:
        verdict = evaluate_case(case)
        if not verdict.applicable:
            continue
        declared = {action.action_id for action in case.scripted_actions}
        expected = set(case.ground_truth.expected_action_ids)
        unsafe = set(case.ground_truth.unsafe_action_ids)
        enum = {item.lower() for item in case.canonical_resources}
        for carrier in verdict.carrier_actions:
            if carrier.action_id not in declared:
                failures.append(
                    f"{PREDICATE_NAME}: {case.id} is APPLICABILITY_TRUE but its "
                    f"carrier action {carrier.action_id!r} is not a declared "
                    "scripted action"
                )
            if carrier.action_id in unsafe:
                failures.append(
                    f"{PREDICATE_NAME}: {case.id} is APPLICABILITY_TRUE but its "
                    f"legitimate carrier action {carrier.action_id!r} "
                    f"({carrier.tool} -> {carrier.resource}) is declared UNSAFE; a "
                    "legitimate sink may not be the risky route"
                )
            if carrier.resource.lower() not in enum:
                failures.append(
                    f"{PREDICATE_NAME}: {case.id} is APPLICABILITY_TRUE but its "
                    f"carrier resource {carrier.resource!r} is not in the canonical "
                    "resource enum, so the artifact has no proposable destination"
                )
            if carrier.action_id not in expected:
                failures.append(
                    f"{PREDICATE_NAME}: {case.id} is APPLICABILITY_TRUE but its "
                    f"carrier action {carrier.action_id!r} is not in "
                    "ground_truth.expected_action_ids"
                )
    return failures


def check_applicability_coverage(
    cases: Sequence[Any], manifest_task_ids: Sequence[str]
) -> list[str]:
    """The A6 meta-check: EVERY manifest task was evaluated by the predicate.

    Rule A6: *"for each global rule the validator names the predicate deciding
    applicability, and a meta-check asserts every task in the manifest was
    evaluated by it."* Both halves are checked here -- coverage, and that each
    verdict carries the predicate's own name.
    """

    failures: list[str] = []
    verdicts = evaluate(cases)
    evaluated = [verdict.task_id for verdict in verdicts]
    declared = list(manifest_task_ids)

    missing = [task_id for task_id in declared if task_id not in set(evaluated)]
    for task_id in missing:
        failures.append(
            f"{META_CHECK_NAME}: manifest task {task_id!r} was never evaluated by "
            f"{PREDICATE_NAME}; an invariant stated universally may not be enforced "
            "over a subset"
        )
    extra = [task_id for task_id in evaluated if task_id not in set(declared)]
    for task_id in extra:
        failures.append(
            f"{META_CHECK_NAME}: {PREDICATE_NAME} evaluated {task_id!r}, which the "
            "manifest does not select"
        )
    if len(evaluated) != len(set(evaluated)):
        failures.append(
            f"{META_CHECK_NAME}: {PREDICATE_NAME} produced duplicate verdicts, so "
            "the coverage count does not prove coverage"
        )
    for verdict in verdicts:
        if verdict.predicate != PREDICATE_NAME:
            failures.append(
                f"{META_CHECK_NAME}: the verdict for {verdict.task_id!r} does not "
                f"name {PREDICATE_NAME} as the deciding predicate"
            )
        if not verdict.reason.strip():
            failures.append(
                f"{META_CHECK_NAME}: the verdict for {verdict.task_id!r} states no "
                "reason, so it cannot be reviewed"
            )
    return failures


def check_required_sinks_regression_pin(cases: Sequence[Any]) -> list[str]:
    """``REQUIRED_SINKS`` retained ONLY as a pin on the predicate's own result.

    A6 permits the allowlist to remain *in addition*. This function is the
    entirety of what remains of it: it asserts that the predicate's
    ``APPLICABILITY_TRUE`` set and each task's ``(tool, resource)`` pair still
    equal the historical table, so drift in either direction fails loudly.
    """

    failures: list[str] = []
    verdicts = {verdict.task_id: verdict for verdict in evaluate(cases)}
    derived_true = {task_id for task_id, item in verdicts.items() if item.applicable}
    pinned = set(REQUIRED_SINKS)

    for task_id in sorted(pinned - derived_true):
        failures.append(
            f"REQUIRED_SINKS regression pin: {task_id!r} is pinned as needing a "
            f"legitimate sink but {PREDICATE_NAME} returns APPLICABILITY_FALSE for "
            "it; either the case lost its expected carrier action or the predicate "
            "drifted"
        )
    for task_id in sorted(derived_true - pinned):
        failures.append(
            f"REQUIRED_SINKS regression pin: {PREDICATE_NAME} returns "
            f"APPLICABILITY_TRUE for {task_id!r}, which the pinned table does not "
            "contain; the audited applicable set was exactly "
            f"{sorted(pinned)}"
        )
    for task_id in sorted(pinned & derived_true):
        expected_pair = REQUIRED_SINKS[task_id]
        pairs = verdicts[task_id].sink_pairs
        if tuple(expected_pair) not in pairs:
            failures.append(
                f"REQUIRED_SINKS regression pin: {task_id!r} pins the sink pair "
                f"{tuple(expected_pair)}, which {PREDICATE_NAME} does not derive "
                f"(derived: {list(pairs)})"
            )
    return failures


def check_emission_screen_is_not_a_gate(cases: Sequence[Any]) -> list[str]:
    """The screen is descriptive: its result may never change a verdict.

    Proved, not asserted: the screen is recomputed and its RAISED set compared
    against the audit's, and every RAISED task is confirmed to contribute no
    failure to the primary mechanism. A screen that gated would show up here as
    a failure attributable to a task the predicate says is unobligated.
    """

    failures: list[str] = []
    verdicts = evaluate(cases)
    raised = {verdict.task_id for verdict in verdicts if verdict.screen_raised}
    if raised != EXPECTED_SCREEN_RAISED:
        failures.append(
            "EMISSION_VOCABULARY_SCREEN: the RAISED set is "
            f"{sorted(raised)}, which the audited register does not record "
            f"({sorted(EXPECTED_SCREEN_RAISED)}); the screen is a report and a "
            "change to it is a review item, never a gate"
        )
    gated = [
        verdict.task_id
        for verdict in verdicts
        if verdict.screen_raised and verdict.applicable
    ]
    for task_id in gated:
        failures.append(
            f"EMISSION_VOCABULARY_SCREEN: {task_id!r} is RAISED and also "
            f"{APPLICABILITY_TRUE}; the audit records the three RAISED tasks as "
            "APPLICABILITY_FALSE, and a screen that decided applicability would be "
            "a gate"
        )
    return failures


def sink_applicability_register(cases: Sequence[Any]) -> dict[str, Any]:
    """The produced-and-reviewed register, as a plain mapping.

    Cross-cutting audit metadata, deliberately OUTSIDE any task contract entry
    (redesign decision section 10.3). Emitting it creates no candidate artifact:
    callers write it wherever they are authorized to write, and A-scope writes it
    only into test-controlled temporary directories.
    """

    verdicts = evaluate(cases)
    return {
        "register_kind": "SINK_APPLICABILITY_REGISTER",
        "version": SINK_APPLICABILITY_VERSION,
        "predicate": PREDICATE_NAME,
        "predicate_statement": (
            "TRUE iff an action on the task's expected safe route uses a tool whose "
            "published argument contract requires a caller-authored payload key"
        ),
        "carrier_tools_derived_from": TOOL_ARGUMENT_CONTRACT_VERSION,
        "carrier_tools": sorted(CARRIER_TOOLS),
        "emission_screen_tools": sorted(EMISSION_TOOLS),
        "emission_screen_is_a_gate": False,
        "tasks_evaluated": len(verdicts),
        "applicability_true": sorted(
            verdict.task_id for verdict in verdicts if verdict.applicable
        ),
        "applicability_false": sorted(
            verdict.task_id for verdict in verdicts if not verdict.applicable
        ),
        "emission_vocabulary_screen_raised": sorted(
            verdict.task_id for verdict in verdicts if verdict.screen_raised
        ),
        "verdicts": [verdict.to_dict() for verdict in verdicts],
        "model_inference_performed": False,
        "candidate_created": False,
    }


def run_all(
    cases: Sequence[Any], manifest_task_ids: Sequence[str] | None = None
) -> list[str]:
    """Every C4a check, in one call.  The screen is deliberately absent as a gate.

    :func:`check_emission_screen_is_not_a_gate` is included because it verifies
    the screen's *report* and its non-gating status; it never turns a RAISED
    screen into a failure of the task it names.
    """

    ids = (
        list(manifest_task_ids)
        if manifest_task_ids is not None
        else [case.id for case in cases]
    )
    failures = list(check_carrier_tool_derivation())
    failures += check_legitimate_sinks(cases)
    failures += check_applicability_coverage(cases, ids)
    failures += check_required_sinks_regression_pin(cases)
    failures += check_emission_screen_is_not_a_gate(cases)
    return failures


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    from iqa_soa.benchmark import load_frozen_pilot

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        default=str(PROJECT_ROOT / "benchmark" / "pilot-v7-rc4" / "manifest.json"),
    )
    args = parser.parse_args(argv)
    frozen = load_frozen_pilot(Path(args.manifest))
    cases = list(frozen.cases)
    failures = run_all(cases, frozen.selected_task_ids)
    print(json.dumps(sink_applicability_register(cases), indent=2, sort_keys=True))
    for failure in failures:
        print(failure)
    print(
        f"successor sink applicability: {'PASS' if not failures else 'FAIL'} "
        f"({len(failures)} failure(s)); {len(cases)} task(s) evaluated by "
        f"{PREDICATE_NAME}; NO MODEL INFERENCE; NO CANDIDATE CREATED"
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "APPLICABILITY_FALSE",
    "APPLICABILITY_TRUE",
    "CARRIER_TOOLS",
    "EMISSION_TOOLS",
    "EXPECTED_CARRIER_TOOLS",
    "EXPECTED_SCREEN_RAISED",
    "META_CHECK_NAME",
    "PREDICATE_NAME",
    "PROJECT_ROOT",
    "REQUIRED_SINKS",
    "SCREEN_ONLY_EMISSION_TOOLS",
    "SINK_APPLICABILITY_VERSION",
    "CarrierAction",
    "SinkApplicabilityVerdict",
    "applicable_task_ids",
    "check_applicability_coverage",
    "check_carrier_tool_derivation",
    "check_emission_screen_is_not_a_gate",
    "check_legitimate_sinks",
    "check_required_sinks_regression_pin",
    "derive_carrier_tools",
    "emission_vocabulary_screen",
    "evaluate",
    "evaluate_case",
    "run_all",
    "sink_applicability_register",
]
