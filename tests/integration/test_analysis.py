from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from iqa_soa.metrics.statistics import AnalysisError, analyze_before_after


def load_script(name: str) -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_row(task: str, category: str, mode: str, repetition: int = 0) -> dict[str, object]:
    unsafe = mode == "off"
    return {
        "experiment_id": "EXP",
        "run_id": f"{task}-{mode}-{repetition}",
        "task_id": task,
        "category": category,
        "repetition": repetition,
        "seed": 42 + repetition,
        "provider": "stub",
        "model": "scripted-v1",
        "qa_mode": mode,
        "ablation": None,
        "task_success": True,
        "expected_output_satisfied": True,
        "constraint_violation": unsafe,
        "unsafe_action_proposed": unsafe,
        "unsafe_action_executed": unsafe,
        "unsafe_action_blocked": not unsafe,
        "attack_success": unsafe,
        "privacy_leak": category == "privacy" and unsafe,
        "risk_interception": not unsafe,
        "false_rejection": False,
        "unnecessary_interventions": False,
        "escalations": False,
        "completion_steps": 1,
        "end_to_end_latency_ms": 1.0 if unsafe else 1.2,
        "qa_latency_ms": 0.0 if unsafe else 0.2,
        "tool_latency_ms": 0.5,
        "model_latency_ms": 0.1,
        "input_tokens": 5,
        "output_tokens": 3,
        "total_tokens": 8,
        "model_calls": 1,
        "tool_calls": 1 if unsafe else 0,
        "estimated_cost": None,
        "decision_trace_available": not unsafe,
        "policy_reference_available": not unsafe,
        "blocking_reason_available": not unsafe,
        "tool_trace_available": True,
        "evidence_complete": not unsafe,
        "evidence_completeness": 1.0 if not unsafe else 0.25,
        "controlled_input_digest": "controlled",
        "initial_state_fingerprint": "initial",
        "proposed_action_digest": "proposal",
    }


def test_analysis_writer_never_overwrites(tmp_path: Path) -> None:
    analyze_script = load_script("analyze_results")
    rows = [base_row("T", "benign", "off"), base_row("T", "benign", "full")]
    raw_dir = tmp_path / "results" / "raw" / "exp"
    raw_dir.mkdir(parents=True)
    (raw_dir / "runs.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    analysis = analyze_before_after(rows, bootstrap_samples=100)
    paths = analyze_script.write_analysis(analysis, raw_dir, token="fixed")
    assert all(path.is_file() for path in paths.values())
    assert paths["json"].parent == tmp_path / "results" / "processed" / "exp"
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert len(payload["raw_source_digests"]["raw_records_sha256"]) == 64
    with pytest.raises(FileExistsError, match="overwrite"):
        analyze_script.write_analysis(analysis, raw_dir, token="fixed")


def test_figure_generation_requires_real_ablation_data(tmp_path: Path) -> None:
    figures = load_script("generate_figures")
    categories = (
        "prompt_injection",
        "unauthorized_action",
        "privacy",
        "knowledge_poisoning",
        "budget",
        "fault_injection",
    )
    before_rows = []
    for index, category in enumerate(categories):
        before_rows.extend(
            [
                base_row(f"T-{index}", category, "off"),
                base_row(f"T-{index}", category, "full"),
            ]
        )
    before_dir = tmp_path / "results" / "raw" / "before"
    before_dir.mkdir(parents=True)
    (before_dir / "runs.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in before_rows), encoding="utf-8"
    )
    with pytest.raises(AnalysisError, match="Figure C"):
        figures.generate_all(before_dir, before_dir, token="missing-ablation")


def test_all_four_figures_are_generated_from_rows(tmp_path: Path) -> None:
    figures = load_script("generate_figures")
    categories = (
        "prompt_injection",
        "unauthorized_action",
        "privacy",
        "knowledge_poisoning",
        "budget",
        "fault_injection",
    )
    before_rows = []
    for index, category in enumerate(categories):
        before_rows.extend(
            [
                base_row(f"T-{index}", category, "off"),
                base_row(f"T-{index}", category, "full"),
            ]
        )
    ablation_rows = []
    variants = (None, "injection", "permission", "privacy", "budget", "output_validation", "evidence")
    for variant in variants:
        violation = variant not in (None, "evidence")
        row = base_row("A", "prompt_injection", "ablation")
        row["ablation"] = variant
        if variant is None:
            row["qa_mode"] = "full"
        row["constraint_violation"] = violation
        ablation_rows.append(row)
    before_dir = tmp_path / "results" / "raw" / "before"
    ablation_dir = tmp_path / "results" / "raw" / "ablation"
    before_dir.mkdir(parents=True)
    ablation_dir.mkdir(parents=True)
    (before_dir / "runs.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in before_rows), encoding="utf-8"
    )
    (ablation_dir / "runs.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in ablation_rows), encoding="utf-8"
    )
    outputs = figures.generate_all(before_dir, ablation_dir, token="measured")
    assert len(outputs) == 8
    assert all(path.stat().st_size > 0 for path in outputs)
