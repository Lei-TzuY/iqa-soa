"""Immutable, hash-verified benchmark selections for real-model pilots."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, cast

from iqa_soa.benchmark.loader import BenchmarkValidationError, load_benchmark_cases
from iqa_soa.benchmark.schema import BenchmarkBudget, BenchmarkCase, BenchmarkCategory


_MANIFEST_KEYS_V1 = {
    "schema_version",
    "benchmark_version",
    "created_at",
    "frozen",
    "selection_policy",
    "selected_task_ids",
    "cases",
}
_MANIFEST_KEYS_V2 = _MANIFEST_KEYS_V1 | {"resource_budget_policy"}
_CASE_KEYS = {"task_id", "path", "sha256", "selection_rationale"}
_RESOURCE_POLICY_KEYS = {
    "policy_id",
    "strict_budget_categories",
    "telemetry_only_limits",
}
_TELEMETRY_LIMITS = frozenset({"max_tokens", "max_runtime_ms", "max_cost"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MINIMUM_COVERAGE = {
    BenchmarkCategory.BENIGN: 2,
    BenchmarkCategory.PROMPT_INJECTION: 2,
    BenchmarkCategory.UNAUTHORIZED_ACTION: 2,
    BenchmarkCategory.PRIVACY: 2,
    BenchmarkCategory.KNOWLEDGE_POISONING: 1,
    BenchmarkCategory.BUDGET: 1,
    BenchmarkCategory.FAULT_INJECTION: 1,
}


@dataclass(frozen=True, slots=True)
class ResourceBudgetPolicy:
    """Versioned resource accounting rule bound into a frozen pilot manifest."""

    policy_id: str
    strict_budget_categories: tuple[BenchmarkCategory, ...]
    telemetry_only_limits: tuple[str, ...]

    def effective_budget(self, case: BenchmarkCase) -> BenchmarkBudget:
        """Return the runtime budget without mutating the frozen case definition."""

        if case.category in self.strict_budget_categories:
            return case.budget
        limits = {name: None for name in self.telemetry_only_limits}
        return replace(case.budget, **limits)

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "strict_budget_categories": [
                category.value for category in self.strict_budget_categories
            ],
            "telemetry_only_limits": list(self.telemetry_only_limits),
        }


@dataclass(frozen=True, slots=True)
class FrozenPilotBenchmark:
    """A fully validated benchmark version and its immutable case objects."""

    benchmark_version: str
    created_at: str
    selection_policy: str
    selected_task_ids: tuple[str, ...]
    cases: tuple[BenchmarkCase, ...]
    case_paths: Mapping[str, Path]
    case_hashes: Mapping[str, str]
    selection_rationales: Mapping[str, str]
    resource_budget_policy: ResourceBudgetPolicy | None
    manifest_path: Path
    manifest_sha256: str


def load_frozen_pilot(path: str | Path) -> FrozenPilotBenchmark:
    """Load a frozen pilot manifest and reject any changed or missing case byte."""

    source = Path(path).resolve()
    try:
        raw_bytes = source.read_bytes()
        value = json.loads(raw_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BenchmarkValidationError(f"cannot read frozen pilot manifest {source}: {exc}") from exc
    data = _mapping(value, "pilot manifest")
    schema_version = data.get("schema_version")
    keys = _MANIFEST_KEYS_V1 if schema_version == 1 else _MANIFEST_KEYS_V2
    if set(data) != keys:
        unknown = sorted(set(data) - keys)
        missing = sorted(keys - set(data))
        raise BenchmarkValidationError(
            f"pilot manifest unknown={unknown} missing={missing}"
        )
    if schema_version not in {1, 2}:
        raise BenchmarkValidationError("pilot manifest schema_version must be 1 or 2")
    if data["frozen"] is not True:
        raise BenchmarkValidationError("pilot manifest must set frozen=true")
    benchmark_version = _nonempty(data["benchmark_version"], "benchmark_version")
    created_at = _nonempty(data["created_at"], "created_at")
    try:
        parsed_timestamp = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BenchmarkValidationError("pilot manifest created_at must be ISO-8601") from exc
    if parsed_timestamp.tzinfo is None:
        raise BenchmarkValidationError("pilot manifest created_at must include a timezone")
    selection_policy = _nonempty(data["selection_policy"], "selection_policy")
    resource_budget_policy = (
        _resource_budget_policy(data["resource_budget_policy"])
        if schema_version == 2
        else None
    )
    selected_task_ids = _string_tuple(data["selected_task_ids"], "selected_task_ids")
    entries = data["cases"]
    if not isinstance(entries, list) or not entries:
        raise BenchmarkValidationError("pilot manifest cases must be a non-empty list")
    if len(entries) != len(selected_task_ids):
        raise BenchmarkValidationError("pilot manifest cases and selected_task_ids differ in size")

    benchmark_root = source.parent.parent.resolve()
    cases: list[BenchmarkCase] = []
    case_paths: dict[str, Path] = {}
    case_hashes: dict[str, str] = {}
    rationales: dict[str, str] = {}
    entry_ids: list[str] = []
    for index, item in enumerate(entries):
        entry = _mapping(item, f"cases[{index}]")
        if set(entry) != _CASE_KEYS:
            raise BenchmarkValidationError(f"pilot manifest cases[{index}] has invalid fields")
        task_id = _nonempty(entry["task_id"], f"cases[{index}].task_id")
        relative_text = _nonempty(entry["path"], f"cases[{index}].path")
        relative_path = Path(relative_text)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise BenchmarkValidationError(
                f"pilot case path must stay within the benchmark root: {relative_text!r}"
            )
        candidate = (benchmark_root / relative_path).resolve()
        try:
            candidate.relative_to(benchmark_root)
        except ValueError as exc:
            raise BenchmarkValidationError(
                f"pilot case path escapes benchmark root: {relative_text!r}"
            ) from exc
        expected_hash = _nonempty(entry["sha256"], f"cases[{index}].sha256").lower()
        if not _SHA256.fullmatch(expected_hash):
            raise BenchmarkValidationError(f"cases[{index}].sha256 is invalid")
        try:
            actual_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
        except OSError as exc:
            raise BenchmarkValidationError(f"cannot read frozen case {candidate}: {exc}") from exc
        if actual_hash != expected_hash:
            raise BenchmarkValidationError(
                f"frozen case hash mismatch for {task_id}: expected {expected_hash}, got {actual_hash}"
            )
        loaded = load_benchmark_cases(candidate)
        if len(loaded) != 1 or loaded[0].id != task_id:
            raise BenchmarkValidationError(
                f"frozen case {relative_text!r} does not define task {task_id!r} exactly once"
            )
        if task_id in case_paths:
            raise BenchmarkValidationError(f"duplicate frozen task ID: {task_id}")
        entry_ids.append(task_id)
        cases.append(loaded[0])
        case_paths[task_id] = candidate
        case_hashes[task_id] = actual_hash
        rationales[task_id] = _nonempty(
            entry["selection_rationale"], f"cases[{index}].selection_rationale"
        )
    if tuple(entry_ids) != selected_task_ids:
        raise BenchmarkValidationError(
            "pilot manifest selected_task_ids must exactly match cases order"
        )
    _validate_pilot_coverage(cases)
    return FrozenPilotBenchmark(
        benchmark_version=benchmark_version,
        created_at=created_at,
        selection_policy=selection_policy,
        selected_task_ids=selected_task_ids,
        cases=tuple(cases),
        case_paths=case_paths,
        case_hashes=case_hashes,
        selection_rationales=rationales,
        resource_budget_policy=resource_budget_policy,
        manifest_path=source,
        manifest_sha256=hashlib.sha256(raw_bytes).hexdigest(),
    )


def _resource_budget_policy(value: Any) -> ResourceBudgetPolicy:
    data = _mapping(value, "resource_budget_policy")
    if set(data) != _RESOURCE_POLICY_KEYS:
        raise BenchmarkValidationError("resource_budget_policy has invalid fields")
    policy_id = _nonempty(data["policy_id"], "resource_budget_policy.policy_id")
    category_names = _string_tuple(
        data["strict_budget_categories"], "resource_budget_policy.strict_budget_categories"
    )
    try:
        categories = tuple(BenchmarkCategory(name) for name in category_names)
    except ValueError as exc:
        raise BenchmarkValidationError(
            "resource_budget_policy contains an unknown benchmark category"
        ) from exc
    if not categories:
        raise BenchmarkValidationError(
            "resource_budget_policy requires at least one strict budget category"
        )
    limits = _string_tuple(
        data["telemetry_only_limits"], "resource_budget_policy.telemetry_only_limits"
    )
    if set(limits) != _TELEMETRY_LIMITS:
        raise BenchmarkValidationError(
            "resource_budget_policy telemetry_only_limits must be exactly "
            f"{sorted(_TELEMETRY_LIMITS)}"
        )
    return ResourceBudgetPolicy(policy_id, categories, limits)


def _validate_pilot_coverage(cases: list[BenchmarkCase]) -> None:
    # The original pilot-v1..v5 line was a 10--14 task coverage-selected pilot.
    # The pilot-v6 coverage extension deliberately adds independent task
    # clusters (three per previously non-identifiable guard) to make the
    # injection/privacy/budget guards causally identifiable, so the upper
    # bound is a version-level infrastructure requirement rather than a case
    # change. The lower bound and every category minimum are unchanged, and
    # pilot-v5 (12 cases) still validates identically.
    if not 10 <= len(cases) <= 30:
        raise BenchmarkValidationError("frozen pilot must contain 10 through 30 cases")
    counts = Counter(case.category for case in cases)
    missing = {
        category.value: minimum - counts[category]
        for category, minimum in _MINIMUM_COVERAGE.items()
        if counts[category] < minimum
    }
    if missing:
        raise BenchmarkValidationError(f"frozen pilot lacks required category coverage: {missing}")


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise BenchmarkValidationError(f"{where} must be a string-keyed object")
    return cast(Mapping[str, Any], value)


def _nonempty(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkValidationError(f"{where} must be a non-empty string")
    return value.strip()


def _string_tuple(value: Any, where: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise BenchmarkValidationError(f"{where} must be a list")
    result = tuple(_nonempty(item, f"{where}[{index}]") for index, item in enumerate(value))
    if len(result) != len(set(result)):
        raise BenchmarkValidationError(f"{where} contains duplicates")
    return result


__all__ = ["FrozenPilotBenchmark", "ResourceBudgetPolicy", "load_frozen_pilot"]
