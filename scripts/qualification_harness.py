#!/usr/bin/env python3
"""Closed failure taxonomy and machine-enforced stop controller for the NEXT
real-model qualification phase.

This module exists because of a specific, documented protocol failure. The
Phase-I frozen plan said that once inference had begun, discovery of any defect
must stop the schedule immediately and return ``HOLD_POST_FREEZE_DEFECT``. When a
defect was discovered after the first arm completed, the second arm was launched
28.4 seconds later anyway, and the run produced a 102-cell matrix it was not
entitled to produce. The rule was prose; nothing enforced it.

Three things were wrong. The first was fixed in Phase K; the second and third
were found by adversarial review and are fixed in Phase K.1.

**1. The taxonomy conflated model behaviour with implementation defects.**
Phase I classified ``invalid_action_format`` as an ``INSTRUMENT_DEFECT``, which is
the emergency-stop class. The instrument had behaved correctly: the native tool
schema advertises ``arguments`` as a required object, the model emitted a
non-object, and the adapter rejected it, classified it precisely, preserved the
row and did not retry. That is a MODEL protocol violation. It invalidates a cell;
it does not make the remaining evidence uninterpretable.

**2. (K.1) The taxonomy still mis-placed two things.**
``multi_call_overflow`` was treated as a harness defect. Canonical
``src/iqa_soa/failure_taxonomy.py`` documents it as a SCIENTIFIC failure class
that "arises from the model's response, and the turn is refused whole rather than
partially executed, so no proposal is silently discarded". It is model-side and
must not stop the schedule. Separately, ``tool_timeout`` and ``tool_failure``
were accepted as EXPECTED_SCRIPTED_FAULT for any task, which would let a genuinely
unexpected sandbox failure masquerade as a designed one. Expectation is now
proved against frozen per-task fault metadata.

**3. (K.1) Rows were not bound to their cells.**
The controller owned schedule ORDER but never checked that a returned row
actually belonged to the cell being recorded. A row for the wrong task, seed,
model, digest, treatment or benchmark could be accepted silently. Every identity
field is now bound per cell, taken from the frozen schedule rather than from the
row, and a missing field is a mismatch rather than a pass.

Nothing here performs inference, and nothing here is wired into an executing
qualification phase yet. It is offline-tested infrastructure for a future phase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence

# --------------------------------------------------------------------------
# Closed failure taxonomy
# --------------------------------------------------------------------------

CELL_OK = "CELL_OK"
EXPECTED_SCRIPTED_FAULT = "EXPECTED_SCRIPTED_FAULT"
MODEL_REFUSAL = "MODEL_REFUSAL"
MODEL_PROTOCOL_INVALID = "MODEL_PROTOCOL_INVALID"
MODEL_MODALITY_MISS = "MODEL_MODALITY_MISS"
BENCHMARK_PREREQUISITE_MISS = "BENCHMARK_PREREQUISITE_MISS"
CHALLENGE_ZERO_EXPOSURE = "CHALLENGE_ZERO_EXPOSURE"
UNEXPECTED_SANDBOX_FAILURE = "UNEXPECTED_SANDBOX_FAILURE"
PROVIDER_INFRA_FAILURE = "PROVIDER_INFRA_FAILURE"
INSTRUMENT_DEFECT = "INSTRUMENT_DEFECT"
FROZEN_ARTIFACT_MISMATCH = "FROZEN_ARTIFACT_MISMATCH"
PROTOCOL_DEVIATION = "PROTOCOL_DEVIATION"

FAILURE_CLASSES: tuple[str, ...] = (
    CELL_OK,
    EXPECTED_SCRIPTED_FAULT,
    MODEL_REFUSAL,
    MODEL_PROTOCOL_INVALID,
    MODEL_MODALITY_MISS,
    BENCHMARK_PREREQUISITE_MISS,
    CHALLENGE_ZERO_EXPOSURE,
    UNEXPECTED_SANDBOX_FAILURE,
    PROVIDER_INFRA_FAILURE,
    INSTRUMENT_DEFECT,
    FROZEN_ARTIFACT_MISMATCH,
    PROTOCOL_DEVIATION,
)

# --------------------------------------------------------------------------
# Dispositions
# --------------------------------------------------------------------------

#: The cell is valid and the schedule continues.
CONTINUE = "CONTINUE"
#: (A) The cell is invalidated for scoring, and the frozen schedule continues.
CELL_INVALID_CONTINUE = "CELL_INVALID_CONTINUE"
#: (A+B) The cell is invalidated AND the final verdict is forced to HOLD. Used
#: where a cell is unusable for a reason that also impugns the run as a whole.
CELL_INVALID_AND_HOLD = "CELL_INVALID_AND_HOLD"
#: (B) The schedule runs to completion, and the final verdict is forced to HOLD.
VERDICT_HOLD_AFTER_COMPLETION = "VERDICT_HOLD_AFTER_COMPLETION"
#: (C) Continued evidence generation is scientifically uninterpretable. Stop now.
IMMEDIATE_STOP = "IMMEDIATE_STOP"

DISPOSITIONS: tuple[str, ...] = (
    CONTINUE,
    CELL_INVALID_CONTINUE,
    CELL_INVALID_AND_HOLD,
    VERDICT_HOLD_AFTER_COMPLETION,
    IMMEDIATE_STOP,
)

#: The frozen, closed mapping. Defined and tested BEFORE any future inference.
DISPOSITION: Mapping[str, str] = {
    # Healthy cell, and the two model behaviours that are legitimate outcomes:
    # the benchmark's own injected fault firing exactly as designed, and a model
    # declining to act.
    CELL_OK: CONTINUE,
    EXPECTED_SCRIPTED_FAULT: CONTINUE,
    MODEL_REFUSAL: CONTINUE,
    # (A) The MODEL, not the harness, produced something unusable. The cell is
    # invalidated; the remaining schedule stays interpretable.
    MODEL_PROTOCOL_INVALID: CELL_INVALID_CONTINUE,
    MODEL_MODALITY_MISS: CELL_INVALID_CONTINUE,
    BENCHMARK_PREREQUISITE_MISS: CELL_INVALID_CONTINUE,
    PROVIDER_INFRA_FAILURE: CELL_INVALID_CONTINUE,
    # (A+B) A sandbox failure the frozen benchmark did NOT script. The cell is
    # unusable, and an unexplained sandbox failure is serious enough that the run
    # may not be reported as a clean pass -- but it does not, on its own, prove
    # the instrument is broken, so the schedule still completes.
    UNEXPECTED_SANDBOX_FAILURE: CELL_INVALID_AND_HOLD,
    # (B) A construct-level result knowable only once every cell of the task
    # exists, so the schedule must complete before the verdict is taken.
    CHALLENGE_ZERO_EXPOSURE: VERDICT_HOLD_AFTER_COMPLETION,
    # (C) Conditions under which further evidence cannot be interpreted at all.
    INSTRUMENT_DEFECT: IMMEDIATE_STOP,
    FROZEN_ARTIFACT_MISMATCH: IMMEDIATE_STOP,
    PROTOCOL_DEVIATION: IMMEDIATE_STOP,
}

#: Why each immediate-stop class is narrowly reserved.
IMMEDIATE_STOP_RATIONALE: Mapping[str, str] = {
    INSTRUMENT_DEFECT: (
        "A defect confirmed in the harness itself -- a tool-contract regression, "
        "lost or corrupted evidence, or an analyzer/driver mismatch that changes "
        "interpretation. Every subsequent cell would be measured with a broken "
        "instrument."
    ),
    FROZEN_ARTIFACT_MISMATCH: (
        "A frozen input moved, or a returned row does not belong to the cell it "
        "was recorded against: benchmark or plan hash drift, the wrong or a "
        "missing model identity or digest, the wrong seed, task or treatment. The "
        "cells already collected and the cells still to come would not be the "
        "same experiment."
    ),
    PROTOCOL_DEVIATION: (
        "The frozen schedule itself was violated -- a reordered, duplicated, "
        "skipped, retried or replaced cell. Continuing would compound the "
        "deviation, which is exactly what Phase I did."
    ),
}

TERMINAL_STATUS_OK = "SCHEDULE_COMPLETE"
TERMINAL_STATUS_HOLD = "SCHEDULE_COMPLETE_VERDICT_HOLD"
TERMINAL_STATUS_STOPPED = "HOLD_POST_FREEZE_DEFECT"


def disposition_for(failure_class: str) -> str:
    """Return the frozen disposition for a taxonomy class, refusing unknowns."""

    if failure_class not in DISPOSITION:
        raise ValueError(
            f"{failure_class!r} is not in the closed Phase-K failure taxonomy; "
            "an unrecognised class must never be silently treated as benign"
        )
    return DISPOSITION[failure_class]


def is_immediate_stop(failure_class: str) -> bool:
    return disposition_for(failure_class) == IMMEDIATE_STOP


# --------------------------------------------------------------------------
# Failure-class groupings, aligned to canonical src/iqa_soa/failure_taxonomy.py
# --------------------------------------------------------------------------

#: Adapter/parser rejections and turn-level refusals that arise from the MODEL's
#: response. Canonical ``SCIENTIFIC_FAILURE_CLASSES`` documents every one of
#: these as model-side, including ``multi_call_overflow``, whose docstring states
#: it "arises from the model's response, and the turn is refused whole rather
#: than partially executed, so no proposal is silently discarded". The harness
#: advertises its schema and its step budget and refuses violations of either;
#: that refusal is correct behaviour, so these invalidate a cell rather than
#: indicting the instrument.
MODEL_PROTOCOL_FAILURE_CLASSES = frozenset(
    {"invalid_action_format", "invalid_json", "invalid_tool_call", "multi_call_overflow"}
)

#: Sandbox outcomes. Whether one of these is EXPECTED depends entirely on the
#: frozen benchmark metadata for that task; it is never assumed.
SANDBOX_FAILURE_CLASSES = frozenset({"tool_timeout", "tool_failure", "invalid_resource"})

#: Provider/experiment-path failures, from canonical INFRASTRUCTURE_FAILURE_CLASSES.
PROVIDER_FAILURE_CLASSES = frozenset(
    {"provider_error", "rate_limit", "timeout", "benchmark_failure", "qa_failure",
     "analysis_failure"}
)

#: The sandbox's deterministic per-mode signatures (src/iqa_soa/tools/registry.py).
#: A malformed_response returns success with a sentinel payload and therefore has
#: no failure class; the other modes return a fixed error string.
FAULT_MODE_SIGNATURE: Mapping[str, tuple[str | None, str | None]] = {
    "timeout": ("tool_timeout", "simulated tool timeout"),
    "unavailable": ("tool_failure", "simulated tool unavailable"),
    "partial_failure": ("tool_failure", "simulated partial tool failure"),
    "malformed_response": (None, None),
}


@dataclass(frozen=True, slots=True)
class ScriptedFault:
    """One task's frozen fault declaration, read from the benchmark case."""

    task_id: str
    tool: str
    resource: str
    mode: str

    @property
    def expected_failure_class(self) -> str | None:
        return FAULT_MODE_SIGNATURE.get(self.mode, (None, None))[0]

    @property
    def expected_error(self) -> str | None:
        return FAULT_MODE_SIGNATURE.get(self.mode, (None, None))[1]

    @property
    def fault_key(self) -> str:
        return f"{self.tool}:{self.resource}"


def scripted_faults_from_cases(cases: Iterable[Any]) -> dict[str, tuple[ScriptedFault, ...]]:
    """Extract frozen fault declarations from loaded benchmark cases."""

    declared: dict[str, tuple[ScriptedFault, ...]] = {}
    for case in cases:
        faults: list[ScriptedFault] = []
        for key, spec in getattr(case.environment, "faults", {}).items():
            tool, _, resource = str(key).partition(":")
            mode = spec.get("mode") if isinstance(spec, Mapping) else getattr(spec, "mode", "")
            faults.append(
                ScriptedFault(task_id=case.id, tool=tool, resource=resource, mode=str(mode))
            )
        if faults:
            declared[case.id] = tuple(faults)
    return declared


def _matches_scripted_fault(
    row: Mapping[str, Any], faults: Sequence[ScriptedFault]
) -> ScriptedFault | None:
    """Prove a sandbox failure is the task's DECLARED fault, as precisely as the
    stored telemetry permits.

    Matching uses task identity (the caller passes only this task's faults), the
    declared mode's deterministic failure class, and the sandbox's exact
    deterministic error string. For a malformed_response fault, which returns
    success rather than an error, the row must positively record
    ``fault_triggered``.
    """

    failure_class = str(row.get("failure_class") or "")
    error = str(row.get("error") or "").strip().casefold()
    triggered = row.get("fault_triggered") is True
    for fault in faults:
        expected_class = fault.expected_failure_class
        expected_error = fault.expected_error
        if expected_class is None:
            # malformed_response: no failure class, so require positive evidence.
            if not failure_class and triggered:
                return fault
            continue
        if failure_class != expected_class:
            continue
        if expected_error is not None and expected_error.casefold() not in error:
            continue
        return fault
    return None


# --------------------------------------------------------------------------
# Frozen per-cell identity
# --------------------------------------------------------------------------

#: Every identity field a returned row MUST carry and match. A missing field is a
#: mismatch, never a pass: an unstamped row cannot be proved to belong to its cell.
REQUIRED_IDENTITY_FIELDS: tuple[str, ...] = (
    "task_id",
    "seed",
    "model",
    "model_digest",
    "qa_mode",
    "benchmark_manifest_sha256",
)


@dataclass(frozen=True, slots=True)
class Cell:
    """One frozen schedule position, carrying its own complete expectation.

    The expectation is built from the frozen schedule and the frozen model
    configuration. It is never derived from the row being checked.
    """

    index: int
    arm: str
    task_id: str
    seed: int
    model: str
    model_digest: str
    qa_mode: str
    benchmark_manifest_sha256: str

    @property
    def key(self) -> str:
        return f"{self.arm}|{self.task_id}|{self.seed}"

    @property
    def run_key(self) -> str:
        """Deterministic cell identifier derived only from frozen inputs.

        A future driver stamps this on the row it returns, so the binding can be
        checked on a single opaque value as well as field by field.
        """

        material = "|".join(
            [
                str(self.index), self.arm, self.task_id, str(self.seed), self.model,
                self.model_digest, self.qa_mode, self.benchmark_manifest_sha256,
            ]
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]

    def expectation(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "seed": self.seed,
            "model": self.model,
            "model_digest": self.model_digest,
            "qa_mode": self.qa_mode,
            "benchmark_manifest_sha256": self.benchmark_manifest_sha256,
        }


def bind_row_to_cell(row: Mapping[str, Any], cell: Cell) -> list[str]:
    """Return the identity mismatches between a returned row and its frozen cell.

    An empty list means the row provably belongs to this cell. Every required
    field must be PRESENT and EQUAL; ``None`` and absence are both mismatches.
    """

    mismatches: list[str] = []
    expected = cell.expectation()
    for field_name in REQUIRED_IDENTITY_FIELDS:
        if field_name not in row or row.get(field_name) is None:
            mismatches.append(f"{field_name} is missing from the returned row")
            continue
        actual = row[field_name]
        want = expected[field_name]
        if field_name == "seed":
            try:
                actual = int(actual)
            except (TypeError, ValueError):
                mismatches.append(f"seed {actual!r} is not an integer")
                continue
        if actual != want:
            mismatches.append(f"{field_name} is {actual!r}, frozen schedule expects {want!r}")
    # Optional but checked when present: the derived cell identifier.
    stamped = row.get("run_key")
    if stamped is not None and stamped != cell.run_key:
        mismatches.append(f"run_key is {stamped!r}, frozen schedule expects {cell.run_key!r}")
    return mismatches


# --------------------------------------------------------------------------
# Classification of a raw row into the taxonomy
# --------------------------------------------------------------------------


def classify_row(
    row: Mapping[str, Any],
    cell: Cell | None = None,
    *,
    scripted_faults: Mapping[str, Sequence[ScriptedFault]] | None = None,
) -> tuple[str, str]:
    """Classify one completed cell into (failure_class, disposition).

    When ``cell`` is supplied, the row must first be proved to belong to it. A
    row that cannot be bound is a FROZEN_ARTIFACT_MISMATCH and stops the run.
    """

    if cell is not None and bind_row_to_cell(row, cell):
        return FROZEN_ARTIFACT_MISMATCH, IMMEDIATE_STOP

    # A harness-side regression is the narrow implementation-defect class.
    if row.get("tool_contract_regression_detected") is True:
        return INSTRUMENT_DEFECT, IMMEDIATE_STOP
    if not row.get("provider_attempt_count"):
        # No attempt was preserved at all: the evidence for this cell is lost.
        return INSTRUMENT_DEFECT, IMMEDIATE_STOP

    failure_class = str(row.get("failure_class") or "")

    if failure_class in PROVIDER_FAILURE_CLASSES:
        return PROVIDER_INFRA_FAILURE, CELL_INVALID_CONTINUE

    # Model-side protocol violations. Includes multi_call_overflow, which
    # canonical failure_taxonomy documents as arising from the model's response.
    if failure_class in MODEL_PROTOCOL_FAILURE_CLASSES:
        return MODEL_PROTOCOL_INVALID, CELL_INVALID_CONTINUE
    if row.get("tool_call_parse_failure") is True:
        return MODEL_PROTOCOL_INVALID, CELL_INVALID_CONTINUE
    if row.get("multi_call_overflow") is True:
        return MODEL_PROTOCOL_INVALID, CELL_INVALID_CONTINUE

    if failure_class in SANDBOX_FAILURE_CLASSES:
        task_id = str(row.get("task_id") or "")
        declared = tuple((scripted_faults or {}).get(task_id, ()))
        if declared and _matches_scripted_fault(row, declared) is not None:
            return EXPECTED_SCRIPTED_FAULT, CONTINUE
        if failure_class == "invalid_resource":
            # The model addressed an identifier the sandbox could not resolve --
            # a modality/selection observation, not a sandbox malfunction.
            return MODEL_MODALITY_MISS, CELL_INVALID_CONTINUE
        return UNEXPECTED_SANDBOX_FAILURE, CELL_INVALID_AND_HOLD

    # A malformed_response fault fires without a failure class, so recognise it
    # only against the task's own declaration.
    if row.get("fault_triggered") is True:
        task_id = str(row.get("task_id") or "")
        declared = tuple((scripted_faults or {}).get(task_id, ()))
        if declared and _matches_scripted_fault(row, declared) is not None:
            return EXPECTED_SCRIPTED_FAULT, CONTINUE

    if row.get("model_refusal") is True:
        return MODEL_REFUSAL, CONTINUE
    return CELL_OK, CONTINUE


# --------------------------------------------------------------------------
# Machine-enforced stop controller
# --------------------------------------------------------------------------


@dataclass(slots=True)
class ScheduleResult:
    terminal_status: str
    exit_code: int
    planned: int
    executed: int
    completed_rows: list[Mapping[str, Any]] = field(default_factory=list)
    classifications: list[dict[str, Any]] = field(default_factory=list)
    invalidated_cells: list[str] = field(default_factory=list)
    hold_reasons: list[str] = field(default_factory=list)
    stop_reason: str = ""
    stop_failure_class: str = ""
    stop_cell: str = ""
    stop_detail: list[str] = field(default_factory=list)
    not_started: list[str] = field(default_factory=list)

    @property
    def stopped(self) -> bool:
        return self.terminal_status == TERMINAL_STATUS_STOPPED


class ScheduleViolation(RuntimeError):
    """The caller tried to advance a schedule the controller had already stopped."""


class StopController:
    """Owns the frozen schedule so an immediate-stop condition cannot be ignored.

    The controller is deliberately the *iterator*. A caller cannot walk the
    schedule itself and forget to consult the stop state, because the only way to
    obtain the next cell is :meth:`cells`, which terminates the moment a stop is
    armed, and :meth:`record` raises if called after that point.
    """

    def __init__(
        self,
        schedule: Sequence[Cell],
        *,
        scripted_faults: Mapping[str, Sequence[ScriptedFault]] | None = None,
    ) -> None:
        self._schedule = tuple(schedule)
        self._faults = dict(scripted_faults or {})
        self._executed = 0
        self._stopped = False
        self._stop_reason = ""
        self._stop_failure_class = ""
        self._stop_cell = ""
        self._stop_detail: list[str] = []
        self._rows: list[Mapping[str, Any]] = []
        self._classifications: list[dict[str, Any]] = []
        self._invalidated: list[str] = []
        self._hold_reasons: list[str] = []
        self._seen: set[str] = set()

    # -- state ---------------------------------------------------------------

    @property
    def stopped(self) -> bool:
        return self._stopped

    @property
    def executed(self) -> int:
        return self._executed

    def remaining(self) -> list[str]:
        return [cell.key for cell in self._schedule[self._executed :]]

    # -- iteration -----------------------------------------------------------

    def cells(self) -> Iterator[Cell]:
        """Yield schedule positions, terminating immediately once stopped."""

        for cell in self._schedule:
            if self._stopped:
                return
            yield cell

    # -- recording -----------------------------------------------------------

    def record(self, cell: Cell, row: Mapping[str, Any]) -> str:
        """Bind, classify and update stop state. Returns the failure class."""

        if self._stopped:
            raise ScheduleViolation(
                f"cell {cell.key} was executed after the schedule stopped at "
                f"{self._stop_cell} ({self._stop_failure_class})"
            )
        # Schedule-order violations are protocol deviations, not identity drift.
        if cell.key in self._seen:
            self._arm_stop(cell, PROTOCOL_DEVIATION,
                           IMMEDIATE_STOP_RATIONALE[PROTOCOL_DEVIATION],
                           [f"cell {cell.key} was executed more than once"])
            return PROTOCOL_DEVIATION
        if cell.index != self._executed:
            self._arm_stop(cell, PROTOCOL_DEVIATION,
                           IMMEDIATE_STOP_RATIONALE[PROTOCOL_DEVIATION],
                           [f"cell {cell.key} ran at schedule position {self._executed}, "
                            f"frozen index is {cell.index}"])
            return PROTOCOL_DEVIATION

        self._seen.add(cell.key)
        self._rows.append(row)
        self._executed += 1

        # THE K.1 BINDING. The row must provably belong to this exact cell.
        mismatches = bind_row_to_cell(row, cell)
        if mismatches:
            self._classifications.append(
                {"cell": cell.key, "index": cell.index,
                 "failure_class": FROZEN_ARTIFACT_MISMATCH,
                 "disposition": IMMEDIATE_STOP, "detail": mismatches}
            )
            self._arm_stop(cell, FROZEN_ARTIFACT_MISMATCH,
                           IMMEDIATE_STOP_RATIONALE[FROZEN_ARTIFACT_MISMATCH], mismatches)
            return FROZEN_ARTIFACT_MISMATCH

        failure_class, disposition = classify_row(
            row, cell, scripted_faults=self._faults
        )
        self._classifications.append(
            {"cell": cell.key, "index": cell.index,
             "failure_class": failure_class, "disposition": disposition}
        )
        if disposition == IMMEDIATE_STOP:
            self._arm_stop(cell, failure_class,
                           IMMEDIATE_STOP_RATIONALE.get(failure_class, failure_class), [])
        elif disposition == CELL_INVALID_CONTINUE:
            self._invalidated.append(cell.key)
        elif disposition == CELL_INVALID_AND_HOLD:
            self._invalidated.append(cell.key)
            self._hold_reasons.append(f"{cell.key}: {failure_class}")
        elif disposition == VERDICT_HOLD_AFTER_COMPLETION:
            self._hold_reasons.append(f"{cell.key}: {failure_class}")
        return failure_class

    def _arm_stop(
        self, cell: Cell, failure_class: str, reason: str, detail: Sequence[str]
    ) -> None:
        self._stopped = True
        self._stop_cell = cell.key
        self._stop_failure_class = failure_class
        self._stop_reason = reason
        self._stop_detail = list(detail)

    # -- results -------------------------------------------------------------

    def result(self) -> ScheduleResult:
        if self._stopped:
            status, code = TERMINAL_STATUS_STOPPED, 3
        elif self._hold_reasons or self._invalidated:
            status, code = TERMINAL_STATUS_HOLD, 1
        else:
            status, code = TERMINAL_STATUS_OK, 0
        return ScheduleResult(
            terminal_status=status,
            exit_code=code,
            planned=len(self._schedule),
            executed=self._executed,
            completed_rows=list(self._rows),
            classifications=list(self._classifications),
            invalidated_cells=list(self._invalidated),
            hold_reasons=list(self._hold_reasons),
            stop_reason=self._stop_reason,
            stop_failure_class=self._stop_failure_class,
            stop_cell=self._stop_cell,
            stop_detail=list(self._stop_detail),
            not_started=self.remaining(),
        )

    def write_partial_manifest(self, path: Path) -> Path:
        """Persist the partial manifest a stopped schedule must leave behind."""

        result = self.result()
        payload = {
            "terminal_status": result.terminal_status,
            "exit_code": result.exit_code,
            "stopped": result.stopped,
            "planned_cells": result.planned,
            "executed_cells": result.executed,
            "stop_cell": result.stop_cell,
            "stop_failure_class": result.stop_failure_class,
            "stop_reason": result.stop_reason,
            "stop_detail": result.stop_detail,
            "invalidated_cells": result.invalidated_cells,
            "hold_reasons": result.hold_reasons,
            "cells_not_started": result.not_started,
            "classifications": result.classifications,
            "preserved_row_ids": [str(r.get("run_id") or "") for r in result.completed_rows],
            "note": (
                "Partial manifest written by the Phase-K stop controller. Every "
                "completed row is preserved exactly. No cell was retried, "
                "replaced or rerun."
            ),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return path


def run_schedule(
    schedule: Sequence[Cell],
    execute: Callable[[Cell], Mapping[str, Any]],
    *,
    scripted_faults: Mapping[str, Sequence[ScriptedFault]] | None = None,
    partial_manifest_path: Path | None = None,
) -> ScheduleResult:
    """Drive a frozen schedule under machine-enforced stop semantics."""

    controller = StopController(schedule, scripted_faults=scripted_faults)
    for cell in controller.cells():
        row = execute(cell)
        controller.record(cell, row)
    if partial_manifest_path is not None:
        controller.write_partial_manifest(partial_manifest_path)
    return controller.result()


@dataclass(frozen=True, slots=True)
class ArmSpec:
    """One frozen arm: its name and the exact model identity it must run."""

    arm: str
    model: str
    model_digest: str


def build_schedule(
    arms: Sequence[ArmSpec],
    task_ids: Sequence[str],
    seeds: Sequence[int],
    *,
    qa_mode: str,
    benchmark_manifest_sha256: str,
) -> list[Cell]:
    """The frozen arm-major, task-major, seed-minor schedule.

    Every cell carries its complete expectation, so the binding check never has
    to consult a global mapping that cannot distinguish one arm from another.
    """

    cells: list[Cell] = []
    for spec in arms:
        for task_id in task_ids:
            for seed in seeds:
                cells.append(
                    Cell(
                        index=len(cells),
                        arm=spec.arm,
                        task_id=task_id,
                        seed=seed,
                        model=spec.model,
                        model_digest=spec.model_digest,
                        qa_mode=qa_mode,
                        benchmark_manifest_sha256=benchmark_manifest_sha256,
                    )
                )
    return cells
