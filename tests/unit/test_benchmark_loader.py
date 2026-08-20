from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from iqa_soa.benchmark.loader import (
    BenchmarkValidationError,
    load_benchmark_cases,
    parse_benchmark_case,
)
from iqa_soa.benchmark.schema import BenchmarkCategory, SUPPORTED_TOOL_NAMES


BENCHMARK_ROOT = Path(__file__).resolve().parents[2] / "benchmark"


def test_initial_suite_validates_all_categories_and_smoke_ids() -> None:
    cases = load_benchmark_cases(BENCHMARK_ROOT)
    assert {case.category for case in cases} == set(BenchmarkCategory)
    assert len([case for case in cases if case.category is BenchmarkCategory.BENIGN]) >= 2
    assert {"BEN-001", "UA-001", "PI-001", "BUD-001"} <= {
        case.id for case in cases
    }
    assert all(action.tool in SUPPORTED_TOOL_NAMES for case in cases for action in case.scripted_actions)


def test_injection_and_poisoning_have_controlling_untrusted_provenance() -> None:
    cases = load_benchmark_cases(BENCHMARK_ROOT)
    selected = [
        case
        for case in cases
        if case.category
        in {BenchmarkCategory.PROMPT_INJECTION, BenchmarkCategory.KNOWLEDGE_POISONING}
    ]
    assert selected
    for case in selected:
        assert case.attack is not None
        unsafe = {
            action.action_id: action
            for action in case.scripted_actions
            if action.action_id in case.ground_truth.unsafe_action_ids
        }
        assert any(
            action.derived_from_untrusted
            and action.source in case.attack.untrusted_sources
            for action in unsafe.values()
        )


def test_initial_state_is_a_deep_copy() -> None:
    case = next(case for case in load_benchmark_cases(BENCHMARK_ROOT) if case.id == "BEN-001")
    left = case.initial_state_dict()
    right = case.initial_state_dict()
    left["files"]["report.txt"] = "mutated"
    assert right["files"]["report.txt"] != "mutated"
    assert case.environment.files["report.txt"] != "mutated"


def test_unknown_keys_and_action_references_are_rejected() -> None:
    valid = yaml.safe_load((BENCHMARK_ROOT / "benign" / "BEN-001.yaml").read_text(encoding="utf-8"))
    unknown = dict(valid)
    unknown["surprise"] = True
    with pytest.raises(BenchmarkValidationError, match="unknown keys"):
        parse_benchmark_case(unknown)

    missing = dict(valid)
    missing.pop("budget")
    with pytest.raises(BenchmarkValidationError, match="missing keys"):
        parse_benchmark_case(missing)

    bad_ref = dict(valid)
    bad_ref["ground_truth"] = dict(valid["ground_truth"])
    bad_ref["ground_truth"]["expected_action_ids"] = ["does-not-exist"]
    with pytest.raises(BenchmarkValidationError, match="unknown action IDs"):
        parse_benchmark_case(bad_ref)


def test_duplicate_ids_bad_tools_and_contradictions_fail_before_run(tmp_path: Path) -> None:
    original = (BENCHMARK_ROOT / "benign" / "BEN-001.yaml").read_text(encoding="utf-8")
    (tmp_path / "a.yaml").write_text(original, encoding="utf-8")
    (tmp_path / "b.yaml").write_text(original, encoding="utf-8")
    with pytest.raises(BenchmarkValidationError, match="duplicate case id"):
        load_benchmark_cases(tmp_path)

    data = yaml.safe_load(original)
    data["scripted_actions"][0]["tool"] = "host.shell"
    with pytest.raises(BenchmarkValidationError, match="not registered"):
        parse_benchmark_case(data)

    data = yaml.safe_load(original)
    data["forbidden_actions"] = list(data["allowed_actions"])
    with pytest.raises(BenchmarkValidationError, match="contradictory action rules"):
        parse_benchmark_case(data)


def test_truth_is_not_exposed_by_case_initial_state() -> None:
    case = next(case for case in load_benchmark_cases(BENCHMARK_ROOT) if case.id == "UA-001")
    serialized = repr(case.initial_state_dict())
    assert "unsafe_action_ids" not in serialized
    assert "expected_action_ids" not in serialized


def test_unsupported_and_ambiguous_fault_specs_are_rejected() -> None:
    valid = yaml.safe_load(
        (BENCHMARK_ROOT / "fault_injection" / "FAULT-001.yaml").read_text(
            encoding="utf-8"
        )
    )
    unsupported = dict(valid)
    unsupported["environment"] = dict(valid["environment"])
    unsupported["environment"]["faults"] = {
        "api.call:service/status": {"mode": "silent_corruption"}
    }
    with pytest.raises(BenchmarkValidationError, match="unsupported"):
        parse_benchmark_case(unsupported)

    ambiguous = dict(valid)
    ambiguous["environment"] = dict(valid["environment"])
    ambiguous["environment"]["faults"] = {
        "api.call:service/status": {
            "mode": "timeout",
            "type": "unavailable",
        }
    }
    with pytest.raises(BenchmarkValidationError, match="both mode and type"):
        parse_benchmark_case(ambiguous)
