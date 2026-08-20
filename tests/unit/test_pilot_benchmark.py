from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from iqa_soa.benchmark import BenchmarkCategory, BenchmarkValidationError, load_frozen_pilot


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PILOT_MANIFEST = PROJECT_ROOT / "benchmark" / "pilot-v1" / "manifest.json"
PILOT_V3_MANIFEST = PROJECT_ROOT / "benchmark" / "pilot-v3" / "manifest.json"


def test_pilot_v1_is_frozen_hashed_and_coverage_complete() -> None:
    pilot = load_frozen_pilot(PILOT_MANIFEST)
    assert pilot.benchmark_version == "pilot-v1"
    assert len(pilot.cases) == 12
    counts = {category: 0 for category in BenchmarkCategory}
    for case in pilot.cases:
        counts[case.category] += 1
        assert hashlib.sha256(pilot.case_paths[case.id].read_bytes()).hexdigest() == (
            pilot.case_hashes[case.id]
        )
    assert counts[BenchmarkCategory.BENIGN] == 2
    assert counts[BenchmarkCategory.PROMPT_INJECTION] == 2
    assert counts[BenchmarkCategory.UNAUTHORIZED_ACTION] == 2
    assert counts[BenchmarkCategory.PRIVACY] == 3
    assert all(counts[category] >= 1 for category in BenchmarkCategory)


def test_frozen_pilot_rejects_changed_case_bytes(tmp_path: Path) -> None:
    benchmark_root = tmp_path / "benchmark"
    pilot_dir = benchmark_root / "pilot-v1"
    case_dir = benchmark_root / "benign"
    pilot_dir.mkdir(parents=True)
    case_dir.mkdir(parents=True)
    original = PROJECT_ROOT / "benchmark" / "benign" / "BEN-001.yaml"
    changed = original.read_text(encoding="utf-8") + "\n# changed after freeze\n"
    case_path = case_dir / "BEN-001.yaml"
    case_path.write_text(changed, encoding="utf-8")
    manifest = json.loads(PILOT_MANIFEST.read_text(encoding="utf-8"))
    local_manifest = pilot_dir / "manifest.json"
    local_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(BenchmarkValidationError, match="hash mismatch"):
        load_frozen_pilot(local_manifest)


def test_pilot_v3_retains_case_bytes_and_scopes_resource_policy_by_category() -> None:
    pilot = load_frozen_pilot(PILOT_V3_MANIFEST)
    v2 = load_frozen_pilot(PROJECT_ROOT / "benchmark" / "pilot-v2" / "manifest.json")
    assert pilot.benchmark_version == "pilot-v3"
    assert pilot.selected_task_ids == v2.selected_task_ids
    assert pilot.case_hashes == v2.case_hashes
    policy = pilot.resource_budget_policy
    assert policy is not None
    benign = next(case for case in pilot.cases if case.id == "BEN-001")
    budget = next(case for case in pilot.cases if case.id == "BUD-001")
    assert policy.effective_budget(benign).max_tokens is None
    assert policy.effective_budget(benign).max_runtime_ms is None
    assert policy.effective_budget(benign).max_cost is None
    assert policy.effective_budget(budget) == budget.budget
