#!/usr/bin/env python3
"""Closed failure taxonomy and machine-enforced stop controller for the NEXT
real-model qualification phase.

This module exists because of a specific, documented protocol failure. The
Phase-I frozen plan said that once inference had begun, discovery of any defect
must stop the schedule immediately and return ``HOLD_POST_FREEZE_DEFECT``. When a
defect was discovered after the first arm completed, the second arm was launched
28.4 seconds later anyway, and the run produced a 102-cell matrix it was not
entitled to produce. The rule was prose; nothing enforced it.

Two things were wrong and both are fixed here.

**1. The taxonomy conflated two very different events.**
Phase I classified ``invalid_action_format`` as an ``INSTRUMENT_DEFECT``, which is
the emergency-stop class. Forensic inspection in Phase K showed the instrument
behaved correctly: the native tool schema advertises ``arguments`` as a required
object, the model emitted a non-object, and the adapter rejected it, classified
it precisely, preserved the row and did not retry. That is a MODEL protocol
violation, not an implementation defect. A model emitting malformed arguments
invalidates a cell; it does not make the remaining evidence uninterpretable, and
it must not trigger an emergency stop.

**2. The stop rule was unenforced.**
``StopController`` below makes the invariant machine-checked: once an
immediate-stop condition is classified, the controller refuses to yield another
cell, records the exact stop reason and cell, writes a partial manifest,
preserves every completed row, and reports a non-zero exit status. A caller
cannot continue the schedule by forgetting to check, because the schedule is
driven through ``run_schedule`` and the controller owns the iteration.

Nothing here performs inference, and nothing here is wired into an executing
qualification phase yet. It is offline-tested infrastructure for a future phase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence

# --------------------------------------------------------------------------
# Closed failure taxonomy
# --------------------------------------------------------------------------

EXPECTED_SCRIPTED_FAULT = "EXPECTED_SCRIPTED_FAULT"
MODEL_REFUSAL = "MODEL_REFUSAL"
MODEL_PROTOCOL_INVALID = "MODEL_PROTOCOL_INVALID"
MODEL_MODALITY_MISS = "MODEL_MODALITY_MISS"
BENCHMARK_PREREQUISITE_MISS = "BENCHMARK_PREREQUISITE_MISS"
CHALLENGE_ZERO_EXPOSURE = "CHALLENGE_ZERO_EXPOSURE"
PROVIDER_INFRA_FAILURE = "PROVIDER_INFRA_FAILURE"
INSTRUMENT_DEFECT = "INSTRUMENT_DEFECT"
FROZEN_ARTIFACT_MISMATCH = "FROZEN_ARTIFACT_MISMATCH"
PROTOCOL_DEVIATION = "PROTOCOL_DEVIATION"
CELL_OK = "CELL_OK"

FAILURE_CLASSES: tuple[str, ...] = (
    CELL_OK,
    EXPECTED_SCRIPTED_FAULT,
    MODEL_REFUSAL,
    MODEL_PROTOCOL_INVALID,
    MODEL_MODALITY_MISS,
    BENCHMARK_PREREQUISITE_MISS,
    CHALLENGE_ZERO_EXPOSURE,
    PROVIDER_INFRA_FAILURE,
    INSTRUMENT_DEFECT,
    FROZEN_ARTIFACT_MISMATCH,
    PROTOCOL_DEVIATION,
)

# --------------------------------------------------------------------------
# Dispositions -- exactly the three the Phase-K specification requires, plus the
# no-op case for a healthy cell.
# --------------------------------------------------------------------------

#: The cell is valid and the schedule continues.
CONTINUE = "CONTINUE"
#: (A) The cell is invalidated for scoring, and the frozen schedule continues.
CELL_INVALID_CONTINUE = "CELL_INVALID_CONTINUE"
#: (B) The schedule runs to completion, and the final verdict is forced to HOLD.
VERDICT_HOLD_AFTER_COMPLETION = "VERDICT_HOLD_AFTER_COMPLETION"
#: (C) Continued evidence generation is scientifically uninterpretable. Stop now.
IMMEDIATE_STOP = "IMMEDIATE_STOP"

DISPOSITIONS: tuple[str, ...] = (
    CONTINUE,
    CELL_INVALID_CONTINUE,
    VERDICT_HOLD_AFTER_COMPLETION,
    IMMEDIATE_STOP,
)

#: The frozen, closed mapping. Defined and tested BEFORE any future inference.
DISPOSITION: Mapping[str, str] = {
    # A healthy cell, and the two model behaviours that are legitimate outcomes
    # rather than faults: the benchmark's own injected fault firing as designed,
    # and a model declining to act.
    CELL_OK: CONTINUE,
    EXPECTED_SCRIPTED_FAULT: CONTINUE,
    MODEL_REFUSAL: CONTINUE,
    # (A) The model, not the harness, produced something unusable. The cell is
    # invalidated; the remaining schedule stays interpretable.
    MODEL_PROTOCOL_INVALID: CELL_INVALID_CONTINUE,
    MODEL_MODALITY_MISS: CELL_INVALID_CONTINUE,
    BENCHMARK_PREREQUISITE_MISS: CELL_INVALID_CONTINUE,
    PROVIDER_INFRA_FAILURE: CELL_INVALID_CONTINUE,
    # (B) A construct-level result that is only knowable once every cell of the
    # task exists, so the schedule must complete before the verdict is taken.
    CHALLENGE_ZERO_EXPOSURE: VERDICT_HOLD_AFTER_COMPLETION,
    # (C) Conditions under which further evidence cannot be interpreted at all.
    INSTRUMENT_DEFECT: IMMEDIATE_STOP,
    FROZEN_ARTIFACT_MISMATCH: IMMEDIATE_STOP,
    PROTOCOL_DEVIATION: IMMEDIATE_STOP,
}

#: Why each immediate-stop class is narrowly reserved.
IMMEDIATE_STOP_RATIONALE: Mapping[str, str] = {
    INSTRUMENT_DEFECT: (
        "A defect confirmed in the harness itself -- a parser or adapter that "
        "mis-handles a well-formed model response, lost or corrupted evidence, "
        "or an analyzer/driver mismatch that changes interpretation. Every "
        "subsequent cell would be measured with a broken instrument."
    ),
    FROZEN_ARTIFACT_MISMATCH: (
        "A frozen input moved: benchmark or plan hash drift, the wrong model or "
        "model digest, the wrong seed, or the wrong treatment. The cells already "
        "collected and the cells still to come would not be the same experiment."
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
# Classification of a raw row into the taxonomy
# --------------------------------------------------------------------------

#: Adapter/parser rejections that indicate the MODEL violated the advertised
#: tool schema. The harness advertises ``arguments`` as a required object and
#: rejects anything else; that rejection is correct behaviour, so these are
#: model-protocol violations rather than implementation defects.
_MODEL_PROTOCOL_FAILURE_CLASSES = frozenset(
    {"invalid_action_format", "invalid_json", "invalid_tool_call"}
)

#: Harness-side regressions. ``multi_call_overflow`` means the harness lost or
#: could not queue a proposal, and a tool-contract regression means the tool
#: definition itself degraded between calls.
_HARNESS_FAILURE_CLASSES = frozenset({"multi_call_overflow"})

#: Sandbox outcomes that are benchmark-designed or model-chosen, never defects.
_SANDBOX_OUTCOME_CLASSES = frozenset(
    {"tool_timeout", "tool_failure", "invalid_resource"}
)


def classify_row(
    row: Mapping[str, Any],
    *,
    expected: Mapping[str, Any] | None = None,
    scripted_fault_task_ids: Iterable[str] = (),
) -> tuple[str, str]:
    """Classify one completed cell into (failure_class, disposition).

    ``expected`` optionally carries the frozen expectations for this cell
    (``benchmark_manifest_sha256``, ``model``, ``model_digest``, ``seed``,
    ``qa_mode``); any mismatch is a FROZEN_ARTIFACT_MISMATCH and stops the run.
    """

    expected = expected or {}
    for key, label in (
        ("benchmark_manifest_sha256", "benchmark hash"),
        ("model", "model identity"),
        ("seed", "seed"),
        ("qa_mode", "treatment"),
    ):
        if key in expected and row.get(key) != expected[key]:
            return FROZEN_ARTIFACT_MISMATCH, IMMEDIATE_STOP
    digest = expected.get("model_digest")
    if digest is not None and row.get("model_digest") not in (None, digest):
        return FROZEN_ARTIFACT_MISMATCH, IMMEDIATE_STOP

    # A harness-side regression is the narrow implementation-defect class.
    if row.get("tool_contract_regression_detected") is True:
        return INSTRUMENT_DEFECT, IMMEDIATE_STOP
    failure_class = str(row.get("failure_class") or "")
    if failure_class in _HARNESS_FAILURE_CLASSES or row.get("multi_call_overflow") is True:
        return INSTRUMENT_DEFECT, IMMEDIATE_STOP
    if not row.get("provider_attempt_count"):
        # No attempt was preserved at all: the evidence for this cell is lost.
        return INSTRUMENT_DEFECT, IMMEDIATE_STOP

    # THE PHASE-I CORRECTION. The model violated the advertised tool schema and
    # the harness correctly rejected and recorded it. The cell is unusable; the
    # instrument is fine; the schedule continues.
    if failure_class in _MODEL_PROTOCOL_FAILURE_CLASSES:
        return MODEL_PROTOCOL_INVALID, CELL_INVALID_CONTINUE
    if row.get("tool_call_parse_failure") is True:
        return MODEL_PROTOCOL_INVALID, CELL_INVALID_CONTINUE

    if failure_class in _SANDBOX_OUTCOME_CLASSES:
        if str(row.get("task_id")) in set(scripted_fault_task_ids):
            return EXPECTED_SCRIPTED_FAULT, CONTINUE
        if failure_class == "invalid_resource":
            return MODEL_MODALITY_MISS, CELL_INVALID_CONTINUE
        return EXPECTED_SCRIPTED_FAULT, CONTINUE

    if row.get("model_refusal") is True:
        return MODEL_REFUSAL, CONTINUE
    return CELL_OK, CONTINUE


# --------------------------------------------------------------------------
# Machine-enforced stop controller
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Cell:
    """One frozen schedule position."""

    index: int
    arm: str
    task_id: str
    seed: int

    @property
    def key(self) -> str:
        return f"{self.arm}|{self.task_id}|{self.seed}"


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
    not_started: list[str] = field(default_factory=list)

    @property
    def stopped(self) -> bool:
        return self.terminal_status == TERMINAL_STATUS_STOPPED


class ScheduleViolation(RuntimeError):
    """The caller tried to advance a schedule the controller had already stopped."""


class StopController:
    """Owns the frozen schedule so an immediate-stop condition cannot be ignored.

    The controller is deliberately the *iterator*. A caller cannot walk the
    schedule itself and forget to consult the stop state, because the only way
    to obtain the next cell is :meth:`cells`, which terminates the moment a stop
    is armed, and :meth:`record` raises if called after that point.
    """

    def __init__(
        self,
        schedule: Sequence[Cell],
        *,
        expected: Mapping[str, Any] | None = None,
        scripted_fault_task_ids: Iterable[str] = (),
    ) -> None:
        self._schedule = tuple(schedule)
        self._expected = dict(expected or {})
        self._fault_tasks = tuple(scripted_fault_task_ids)
        self._executed = 0
        self._stopped = False
        self._stop_reason = ""
        self._stop_failure_class = ""
        self._stop_cell = ""
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
        """Classify a completed cell and update stop state. Returns the class."""

        if self._stopped:
            raise ScheduleViolation(
                f"cell {cell.key} was executed after the schedule stopped at "
                f"{self._stop_cell} ({self._stop_failure_class})"
            )
        if cell.key in self._seen:
            self._arm_stop(
                cell, PROTOCOL_DEVIATION, f"cell {cell.key} was executed more than once"
            )
            return PROTOCOL_DEVIATION
        if cell.index != self._executed:
            self._arm_stop(
                cell,
                PROTOCOL_DEVIATION,
                f"cell {cell.key} ran out of frozen order at position "
                f"{self._executed}, expected schedule index {cell.index}",
            )
            return PROTOCOL_DEVIATION

        self._seen.add(cell.key)
        self._rows.append(row)
        self._executed += 1

        failure_class, disposition = classify_row(
            row, expected=self._expected, scripted_fault_task_ids=self._fault_tasks
        )
        self._classifications.append(
            {
                "cell": cell.key,
                "index": cell.index,
                "failure_class": failure_class,
                "disposition": disposition,
            }
        )
        if disposition == IMMEDIATE_STOP:
            self._arm_stop(
                cell,
                failure_class,
                IMMEDIATE_STOP_RATIONALE.get(failure_class, failure_class),
            )
        elif disposition == CELL_INVALID_CONTINUE:
            self._invalidated.append(cell.key)
        elif disposition == VERDICT_HOLD_AFTER_COMPLETION:
            self._hold_reasons.append(f"{cell.key}: {failure_class}")
        return failure_class

    def _arm_stop(self, cell: Cell, failure_class: str, reason: str) -> None:
        self._stopped = True
        self._stop_cell = cell.key
        self._stop_failure_class = failure_class
        self._stop_reason = reason

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
    expected: Mapping[str, Any] | None = None,
    scripted_fault_task_ids: Iterable[str] = (),
    partial_manifest_path: Path | None = None,
) -> ScheduleResult:
    """Drive a frozen schedule under machine-enforced stop semantics.

    The controller owns the iteration, so an immediate-stop condition prevents
    the next cell from starting without the caller having to remember anything.
    """

    controller = StopController(
        schedule, expected=expected, scripted_fault_task_ids=scripted_fault_task_ids
    )
    for cell in controller.cells():
        row = execute(cell)
        controller.record(cell, row)
    if partial_manifest_path is not None:
        controller.write_partial_manifest(partial_manifest_path)
    return controller.result()


def build_schedule(
    arms: Sequence[str], task_ids: Sequence[str], seeds: Sequence[int]
) -> list[Cell]:
    """The frozen arm-major, task-major, seed-minor schedule."""

    cells: list[Cell] = []
    for arm in arms:
        for task_id in task_ids:
            for seed in seeds:
                cells.append(Cell(len(cells), arm, task_id, seed))
    return cells
