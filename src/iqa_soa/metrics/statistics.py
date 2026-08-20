"""Statistical methods for the controlled, paired IQA-SOA experiment.

The unit of pairing is a benchmark case/repetition/seed/provider/model tuple.
Binary outcomes use paired risk differences and an exact McNemar test. Continuous
outcomes use paired differences and a Wilcoxon signed-rank test. Bootstrap
intervals resample pairs, never individual treatment rows.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats  # type: ignore[import-untyped]

from iqa_soa.metrics.definitions import REQUIRED_RAW_FIELDS

PAIR_KEYS = ("task_id", "repetition", "seed", "provider", "model")

BINARY_METRICS = (
    "safety_security_violation",
    "resource_budget_violation",
    "constraint_violation",
    "unsafe_action_proposed",
    "unsafe_action_executed",
    "unsafe_action_blocked",
    "attack_success",
    "privacy_leak",
    "risk_interception",
    "task_success",
    "expected_output_satisfied",
    "false_rejection",
    "model_refusal",
    "no_action",
    "invalid_action_format",
    "tool_call_parse_failure",
    "decision_trace_available",
    "policy_reference_available",
    "blocking_reason_available",
    "tool_trace_available",
    "evidence_complete",
)

CONTINUOUS_METRICS = (
    "completion_steps",
    "unnecessary_interventions",
    "escalations",
    "end_to_end_latency_ms",
    "qa_latency_ms",
    "evidence_latency_ms",
    "tool_latency_ms",
    "model_latency_ms",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "model_calls",
    "tool_calls",
    "estimated_cost",
    "evidence_completeness",
)


class AnalysisError(ValueError):
    """Raised when raw measurements cannot support the requested analysis."""


@dataclass(frozen=True, slots=True)
class PairedRows:
    """One exactly matched QA-OFF / QA-FULL observation pair."""

    key: tuple[Any, ...]
    before: Mapping[str, Any]
    after: Mapping[str, Any]


def aggregate_rate_summary(
    records: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return documented action-denominator rates for each unablated mode."""

    rows = [row for row in records if _is_unablated(row)]
    summaries: list[dict[str, Any]] = []
    definitions = (
        (
            "unauthorized_action_execution_rate",
            "unsafe_executed_count",
            "unsafe_proposed_count",
        ),
        ("risk_interception_recall", "unsafe_blocked_count", "unsafe_proposed_count"),
        ("false_rejection_rate", "expected_blocked_count", "expected_action_count"),
    )
    for mode in ("off", "partial", "full"):
        mode_rows = [row for row in rows if str(row.get("qa_mode", "")).lower() == mode]
        if not mode_rows:
            continue
        for name, numerator_field, denominator_field in definitions:
            numerator = sum(int(_number(row.get(numerator_field)) or 0) for row in mode_rows)
            denominator = sum(int(_number(row.get(denominator_field)) or 0) for row in mode_rows)
            summaries.append(
                {
                    "qa_mode": mode,
                    "metric": name,
                    "numerator": numerator,
                    "denominator": denominator,
                    "rate": numerator / denominator if denominator else None,
                }
            )
    return summaries


def _coerce_scalar(value: str) -> Any:
    stripped = value.strip()
    if stripped == "" or stripped.lower() in {"null", "none", "na", "n/a"}:
        return None
    if stripped.lower() in {"true", "false"}:
        return stripped.lower() == "true"
    try:
        return int(stripped)
    except ValueError:
        try:
            return float(stripped)
        except ValueError:
            return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AnalysisError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(item, dict):
                raise AnalysisError(f"{path}:{line_number}: expected a JSON object")
            rows.append(item)
    return rows


def _load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            {key: _coerce_scalar(value) for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def _discover_run_file(directory: Path) -> Path:
    candidates = (
        directory / "runs.jsonl",
        directory / "raw" / "runs.jsonl",
        directory / "runs.csv",
        directory / "raw" / "runs.csv",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    named_jsonl = sorted(directory.glob("**/runs.jsonl"))
    named_csv = sorted(directory.glob("**/runs.csv"))
    matches = named_jsonl or named_csv
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise AnalysisError(
            f"No aggregate runs.jsonl or runs.csv found beneath {directory}"
        )
    raise AnalysisError(
        f"Multiple aggregate run files found beneath {directory}; pass one explicitly"
    )


def load_run_records(source: str | Path) -> list[dict[str, Any]]:
    """Load immutable raw run rows from an aggregate JSONL or CSV artifact."""

    requested = Path(source).resolve()
    path = requested
    if requested.is_dir():
        path = _discover_run_file(path)
    if not path.is_file():
        raise AnalysisError(f"Raw result source does not exist: {path}")
    if path.suffix.lower() == ".jsonl":
        rows = _load_jsonl(path)
    elif path.suffix.lower() == ".csv":
        rows = _load_csv(path)
    else:
        raise AnalysisError(f"Unsupported result format: {path.suffix}")
    if not rows:
        raise AnalysisError(f"Raw result source contains no records: {path}")
    manifest_path = _find_manifest(requested, path)
    if manifest_path is not None:
        _validate_completed_manifest(manifest_path, rows)
    return rows


def raw_source_digests(source: str | Path) -> dict[str, str]:
    """Return immutable provenance digests for the measured rows and manifest."""

    requested = Path(source).resolve()
    run_file = _discover_run_file(requested) if requested.is_dir() else requested
    if not run_file.is_file():
        raise AnalysisError(f"Raw result source does not exist: {run_file}")
    result = {"raw_records_sha256": hashlib.sha256(run_file.read_bytes()).hexdigest()}
    manifest = _find_manifest(requested, run_file)
    if manifest is not None:
        result["manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    return result


def _find_manifest(requested: Path, run_file: Path) -> Path | None:
    candidates = (
        requested / "manifest.json" if requested.is_dir() else requested.parent / "manifest.json",
        run_file.parent / "manifest.json",
        run_file.parent.parent / "manifest.json",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _validate_completed_manifest(
    manifest_path: Path, rows: Sequence[Mapping[str, Any]]
) -> None:
    """Reject interrupted, truncated, duplicated, or provenance-poor experiments."""

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AnalysisError(f"invalid experiment manifest {manifest_path}: {exc}") from exc
    if not isinstance(manifest, Mapping):
        raise AnalysisError(f"experiment manifest must be an object: {manifest_path}")
    required = {
        "experiment_id",
        "status",
        "completed_at",
        "case_ids",
        "treatments",
        "repetitions",
        "seeds",
        "expected_record_count",
        "record_count",
        "input_digests",
        "software",
    }
    missing_manifest = required - set(manifest)
    if missing_manifest:
        raise AnalysisError(
            "experiment manifest lacks completion/provenance fields: "
            + ", ".join(sorted(missing_manifest))
        )
    if manifest.get("status") != "complete":
        raise AnalysisError(
            f"experiment manifest status is {manifest.get('status')!r}, not 'complete'"
        )
    missing_raw = set(REQUIRED_RAW_FIELDS) - set(rows[0])
    if missing_raw:
        raise AnalysisError(
            "raw records do not satisfy the current schema: "
            + ", ".join(sorted(missing_raw))
        )
    for index, row in enumerate(rows):
        row_missing = set(REQUIRED_RAW_FIELDS) - set(row)
        if row_missing:
            raise AnalysisError(
                f"raw record {index} is missing fields: "
                + ", ".join(sorted(row_missing))
            )
        if row.get("error") not in (None, ""):
            raise AnalysisError(
                f"raw record {row.get('run_id', index)!r} contains an error"
            )

    def manifest_int(name: str) -> int:
        value = manifest.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise AnalysisError(f"manifest field {name} must be a non-negative integer")
        return value

    repetitions = manifest_int("repetitions")
    expected_count = manifest_int("expected_record_count")
    recorded_count = manifest_int("record_count")
    if expected_count != len(rows) or recorded_count != len(rows):
        raise AnalysisError(
            "manifest/run count mismatch: "
            f"expected={expected_count}, recorded={recorded_count}, loaded={len(rows)}"
        )
    case_ids = manifest.get("case_ids")
    treatments = manifest.get("treatments")
    seeds = manifest.get("seeds")
    if (
        not isinstance(case_ids, list)
        or not case_ids
        or any(not isinstance(item, str) or not item for item in case_ids)
        or len(case_ids) != len(set(case_ids))
    ):
        raise AnalysisError("manifest case_ids must be a non-empty unique string list")
    if (
        not isinstance(treatments, list)
        or not treatments
        or any(not isinstance(item, str) or not item for item in treatments)
        or len(treatments) != len(set(treatments))
    ):
        raise AnalysisError("manifest treatments must be a non-empty unique string list")
    if not isinstance(seeds, list) or len(seeds) != repetitions:
        raise AnalysisError("manifest seeds must contain one value per repetition")
    cartesian_count = len(case_ids) * repetitions * len(treatments)
    if expected_count != cartesian_count:
        raise AnalysisError(
            f"manifest expected count {expected_count} does not match design {cartesian_count}"
        )

    experiment_id = manifest.get("experiment_id")
    seen: set[tuple[str, int, str]] = set()
    for row in rows:
        if row.get("experiment_id") != experiment_id:
            raise AnalysisError("raw experiment_id does not match manifest")
        task_id = row.get("task_id")
        repetition = row.get("repetition")
        if task_id not in case_ids:
            raise AnalysisError(f"raw row has undeclared task_id {task_id!r}")
        if isinstance(repetition, bool) or not isinstance(repetition, int):
            raise AnalysisError("raw repetition must be an integer")
        if repetition < 0 or repetition >= repetitions:
            raise AnalysisError(f"raw repetition is outside the manifest: {repetition}")
        if row.get("seed") != seeds[repetition]:
            raise AnalysisError(
                f"raw seed differs from manifest for repetition {repetition}"
            )
        ablation = row.get("ablation")
        treatment = (
            f"full_minus_{ablation}"
            if ablation not in (None, "", "none", "None")
            else str(row.get("qa_mode", "")).lower()
        )
        if treatment not in treatments:
            raise AnalysisError(f"raw row has undeclared treatment {treatment!r}")
        key = (str(task_id), repetition, treatment)
        if key in seen:
            raise AnalysisError(f"duplicate manifest design cell: {key!r}")
        seen.add(key)

    expected_cells = {
        (task_id, repetition, treatment)
        for task_id in case_ids
        for repetition in range(repetitions)
        for treatment in treatments
    }
    if seen != expected_cells:
        missing = sorted(expected_cells - seen)
        raise AnalysisError(
            f"experiment is missing {len(missing)} manifest design cell(s): {missing[:3]!r}"
        )
    digests = manifest.get("input_digests")
    if not isinstance(digests, Mapping) or not digests or any(
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value.lower())
        for value in digests.values()
    ):
        raise AnalysisError("manifest input_digests are missing or invalid")
    software = manifest.get("software")
    if not isinstance(software, Mapping) or not all(
        software.get(name)
        for name in ("artifact_version", "python_version", "package_source_sha256")
    ):
        raise AnalysisError("manifest software provenance is missing")
    package_digest = software["package_source_sha256"]
    if (
        not isinstance(package_digest, str)
        or len(package_digest) != 64
        or any(character not in "0123456789abcdef" for character in package_digest.lower())
    ):
        raise AnalysisError("manifest package source digest is invalid")


def _is_unablated(row: Mapping[str, Any]) -> bool:
    value = row.get("ablation")
    return value in (None, "", "none", "None", "FULL", "full")


def pair_before_after(
    records: Iterable[Mapping[str, Any]],
    *,
    require_complete: bool = True,
) -> list[PairedRows]:
    """Create exact OFF/FULL pairs and reject duplicates or accidental imbalance."""

    indexed: dict[tuple[Any, ...], dict[str, Mapping[str, Any]]] = {}
    for row in records:
        mode = str(row.get("qa_mode", "")).lower()
        if mode not in {"off", "full"} or not _is_unablated(row):
            continue
        missing = [key for key in PAIR_KEYS if row.get(key) is None]
        if missing:
            raise AnalysisError(
                f"Run {row.get('run_id', '<unknown>')} is missing pair key(s): "
                + ", ".join(missing)
            )
        key = tuple(row[key_name] for key_name in PAIR_KEYS)
        bucket = indexed.setdefault(key, {})
        if mode in bucket:
            raise AnalysisError(f"Duplicate {mode} observation for pair key {key!r}")
        bucket[mode] = row

    pairs: list[PairedRows] = []
    incomplete: list[tuple[Any, ...]] = []
    for key in sorted(indexed, key=repr):
        bucket = indexed[key]
        if "off" not in bucket or "full" not in bucket:
            incomplete.append(key)
            continue
        before = bucket["off"]
        after = bucket["full"]
        for field in ("controlled_input_digest", "initial_state_fingerprint"):
            left = before.get(field)
            right = after.get(field)
            if left is not None or right is not None:
                if not left or not right or left != right:
                    raise AnalysisError(
                        f"Paired invariant {field} differs for pair key {key!r}"
                    )
        if (
            str(before.get("provider", "")) == "deterministic_stub"
            and str(after.get("provider", "")) == "deterministic_stub"
        ):
            left = before.get("proposed_action_digest")
            right = after.get("proposed_action_digest")
            if left is not None or right is not None:
                if not left or not right or left != right:
                    raise AnalysisError(
                        "Deterministic paired proposal digest differs for pair key "
                        f"{key!r}"
                    )
        errors = [
            str(row.get("error"))
            for row in (before, after)
            if row.get("error") not in (None, "")
            and row.get("analysis_error_permitted") is not True
        ]
        if errors:
            raise AnalysisError(
                f"Paired observations contain recorded error(s) for {key!r}: "
                + "; ".join(errors)
            )
        pairs.append(PairedRows(key=key, before=before, after=after))
    if require_complete and incomplete:
        examples = ", ".join(repr(item) for item in incomplete[:3])
        raise AnalysisError(
            f"Unpaired OFF/FULL observations for {len(incomplete)} key(s): {examples}"
        )
    if not pairs:
        raise AnalysisError("No complete unablated QA-OFF / QA-FULL pairs were found")
    return pairs


def _binary(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)) and value in (0, 1):
        return int(value)
    if isinstance(value, str) and value.lower() in {"true", "false", "0", "1"}:
        return int(value.lower() in {"true", "1"})
    raise AnalysisError(f"Expected binary value, received {value!r}")


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return float(value)
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise AnalysisError(f"Expected numeric value, received {value!r}") from exc
    if not math.isfinite(result):
        raise AnalysisError(f"Expected finite numeric value, received {value!r}")
    return result


def _bootstrap_mean_ci(
    values: Sequence[float],
    *,
    confidence: float,
    samples: int,
    seed: int,
) -> tuple[float, float] | None:
    if not values:
        return None
    array = np.asarray(values, dtype=float)
    if len(array) == 1 or np.all(array == array[0]):
        exact = float(np.mean(array))
        return (exact, exact)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(array), size=(samples, len(array)))
    means = array[indices].mean(axis=1)
    alpha = (1.0 - confidence) / 2.0
    low, high = np.quantile(means, [alpha, 1.0 - alpha])
    return (float(low), float(high))


def _relative_change(before: float, delta: float) -> float | None:
    return None if math.isclose(before, 0.0, abs_tol=1e-15) else delta / abs(before)


def analyze_binary_metric(
    pairs: Sequence[PairedRows],
    metric: str,
    *,
    confidence: float = 0.95,
    bootstrap_samples: int = 10_000,
    seed: int = 2027,
) -> dict[str, Any] | None:
    """Analyze a paired binary outcome with exact discordant-pair inference."""

    observations: list[tuple[int, int]] = []
    for pair in pairs:
        before = _binary(pair.before.get(metric))
        after = _binary(pair.after.get(metric))
        if before is not None and after is not None:
            observations.append((before, after))
    if not observations:
        return None

    before_values = np.asarray([item[0] for item in observations], dtype=float)
    after_values = np.asarray([item[1] for item in observations], dtype=float)
    differences = after_values - before_values
    before_mean = float(before_values.mean())
    after_mean = float(after_values.mean())
    delta = float(differences.mean())
    before_only = sum(before == 1 and after == 0 for before, after in observations)
    after_only = sum(before == 0 and after == 1 for before, after in observations)
    discordant = before_only + after_only
    if discordant:
        test_result = stats.binomtest(
            min(before_only, after_only), discordant, p=0.5, alternative="two-sided"
        )
        p_value: float | None = float(test_result.pvalue)
        statistic: float | None = float(min(before_only, after_only))
        test = "exact McNemar (two-sided binomial on discordant pairs)"
    else:
        p_value = 1.0
        statistic = 0.0
        test = "exact McNemar (no discordant pairs)"

    # Outcome-occurrence odds after versus before. Apply the Haldane correction
    # only when a discordant cell is zero; no-discordance odds are undefined.
    if discordant == 0:
        matched_odds_ratio: float | None = None
        correction = "undefined: no discordant pairs"
    elif before_only == 0 or after_only == 0:
        matched_odds_ratio = (after_only + 0.5) / (before_only + 0.5)
        correction = "Haldane 0.5 correction for zero discordant cell"
    else:
        matched_odds_ratio = after_only / before_only
        correction = "none"
    ci = _bootstrap_mean_ci(
        differences.tolist(),
        confidence=confidence,
        samples=bootstrap_samples,
        seed=seed,
    )
    return {
        "metric": metric,
        "kind": "binary",
        "n_pairs": len(observations),
        "before": before_mean,
        "after": after_mean,
        "absolute_difference": delta,
        "relative_difference": _relative_change(before_mean, delta),
        "confidence_level": confidence,
        "ci_low": ci[0] if ci else None,
        "ci_high": ci[1] if ci else None,
        "effect_size_name": "matched odds ratio (after/before; Haldane 0.5)",
        "effect_size": matched_odds_ratio,
        "effect_size_correction": correction,
        "test": test,
        "statistic": statistic,
        "p_value": p_value,
        "discordant_before_only": before_only,
        "discordant_after_only": after_only,
    }


def analyze_continuous_metric(
    pairs: Sequence[PairedRows],
    metric: str,
    *,
    confidence: float = 0.95,
    bootstrap_samples: int = 10_000,
    seed: int = 2027,
) -> dict[str, Any] | None:
    """Analyze a continuous/count outcome using within-pair differences."""

    observations: list[tuple[float, float]] = []
    for pair in pairs:
        before = _number(pair.before.get(metric))
        after = _number(pair.after.get(metric))
        if before is not None and after is not None:
            observations.append((before, after))
    if not observations:
        return None
    before_values = np.asarray([item[0] for item in observations], dtype=float)
    after_values = np.asarray([item[1] for item in observations], dtype=float)
    differences = after_values - before_values
    before_mean = float(before_values.mean())
    after_mean = float(after_values.mean())
    delta = float(differences.mean())
    ci = _bootstrap_mean_ci(
        differences.tolist(),
        confidence=confidence,
        samples=bootstrap_samples,
        seed=seed,
    )

    if len(differences) > 1 and float(np.std(differences, ddof=1)) > 0.0:
        effect_size: float | None = delta / float(np.std(differences, ddof=1))
    else:
        effect_size = None

    if np.allclose(differences, 0.0):
        test = "Wilcoxon signed-rank (all paired differences zero)"
        statistic: float | None = 0.0
        p_value: float | None = 1.0
    elif len(differences) < 2:
        test = "Wilcoxon signed-rank (insufficient pairs)"
        statistic = None
        p_value = None
    else:
        result = stats.wilcoxon(
            differences, zero_method="wilcox", correction=False, alternative="two-sided"
        )
        test = "Wilcoxon signed-rank (two-sided)"
        statistic = float(result.statistic)
        p_value = float(result.pvalue)

    return {
        "metric": metric,
        "kind": "continuous",
        "n_pairs": len(observations),
        "before": before_mean,
        "after": after_mean,
        "absolute_difference": delta,
        "relative_difference": _relative_change(before_mean, delta),
        "confidence_level": confidence,
        "ci_low": ci[0] if ci else None,
        "ci_high": ci[1] if ci else None,
        "effect_size_name": "paired standardized mean difference dz",
        "effect_size": effect_size,
        "test": test,
        "statistic": statistic,
        "p_value": p_value,
    }


def analyze_before_after(
    records: Iterable[Mapping[str, Any]],
    *,
    confidence: float = 0.95,
    bootstrap_samples: int = 10_000,
    seed: int = 2027,
) -> dict[str, Any]:
    """Produce complete paired OFF/FULL analysis for every measured metric."""

    if not 0.0 < confidence < 1.0:
        raise AnalysisError("confidence must be strictly between zero and one")
    if isinstance(bootstrap_samples, bool) or bootstrap_samples <= 0:
        raise AnalysisError("bootstrap_samples must be a positive integer")
    rows = list(records)
    pairs = pair_before_after(rows)
    deterministic_fixture_only = all(
        str(pair.before.get("provider", "")) == "deterministic_stub"
        and str(pair.after.get("provider", "")) == "deterministic_stub"
        for pair in pairs
    )
    observed_fields = {key for row in rows for key in row}
    metrics: list[dict[str, Any]] = []
    for index, metric in enumerate(BINARY_METRICS):
        if metric not in observed_fields:
            continue
        result = analyze_binary_metric(
            pairs,
            metric,
            confidence=confidence,
            bootstrap_samples=bootstrap_samples,
            seed=seed + index,
        )
        if result:
            if deterministic_fixture_only:
                _suppress_fixture_inference(result, pairs, metric)
            else:
                _apply_task_cluster_inference(
                    result,
                    pairs,
                    metric,
                    confidence=confidence,
                    bootstrap_samples=bootstrap_samples,
                    seed=seed + index,
                )
            metrics.append(result)
    for index, metric in enumerate(CONTINUOUS_METRICS):
        if metric not in observed_fields:
            continue
        result = analyze_continuous_metric(
            pairs,
            metric,
            confidence=confidence,
            bootstrap_samples=bootstrap_samples,
            seed=seed + 100 + index,
        )
        if result:
            if deterministic_fixture_only:
                _suppress_fixture_inference(result, pairs, metric)
            else:
                _apply_task_cluster_inference(
                    result,
                    pairs,
                    metric,
                    confidence=confidence,
                    bootstrap_samples=bootstrap_samples,
                    seed=seed + 100 + index,
                )
            metrics.append(result)
    if not metrics:
        raise AnalysisError("Paired rows contain none of the registered experiment metrics")
    return {
        "design": "paired QA-OFF versus unablated QA-FULL",
        "pair_keys": list(PAIR_KEYS),
        "n_pairs": len(pairs),
        "confidence_level": confidence,
        "bootstrap_samples": bootstrap_samples,
        "bootstrap_seed": seed,
        "inferential_statistics_eligible": not deterministic_fixture_only,
        "inference_note": (
            "Deterministic-stub repetitions validate the artifact but are not "
            "independent samples of model behavior; confidence intervals and "
            "hypothesis-test outputs are suppressed."
            if deterministic_fixture_only
            else (
                "Inference uses task-cluster means, task-cluster bootstrap intervals, "
                "and task-level sign-flip randomization. The estimand is the mean "
                "effect across this fixed benchmark suite, not unseen-task generalization."
            )
        ),
        "inference_method": (
            "suppressed deterministic fixture"
            if deterministic_fixture_only
            else "task-cluster bootstrap and sign-flip randomization"
        ),
        "metrics": metrics,
        "aggregate_rates": aggregate_rate_summary(rows),
    }


def _apply_task_cluster_inference(
    result: dict[str, Any],
    pairs: Sequence[PairedRows],
    metric: str,
    *,
    confidence: float,
    bootstrap_samples: int,
    seed: int,
) -> None:
    """Treat repeated runs as observations nested within benchmark tasks."""

    clusters: dict[Any, list[tuple[float, float]]] = {}
    for pair in pairs:
        if result["kind"] == "binary":
            before_raw = _binary(pair.before.get(metric))
            after_raw = _binary(pair.after.get(metric))
            before = float(before_raw) if before_raw is not None else None
            after = float(after_raw) if after_raw is not None else None
        else:
            before = _number(pair.before.get(metric))
            after = _number(pair.after.get(metric))
        if before is not None and after is not None:
            clusters.setdefault(pair.key[0], []).append((before, after))

    task_observations = [
        (
            float(np.mean([item[0] for item in observations])),
            float(np.mean([item[1] for item in observations])),
        )
        for _, observations in sorted(clusters.items(), key=lambda item: repr(item[0]))
    ]
    task_differences = [after - before for before, after in task_observations]
    n_tasks = len(task_observations)
    result["n_independent_tasks"] = n_tasks
    result["inference_eligible"] = n_tasks >= 2
    if not task_observations:
        result.update(
            ci_low=None,
            ci_high=None,
            effect_size=None,
            statistic=None,
            p_value=None,
            test="not estimated: no applicable task clusters",
        )
        return

    before_mean = float(np.mean([item[0] for item in task_observations]))
    after_mean = float(np.mean([item[1] for item in task_observations]))
    delta = after_mean - before_mean
    result["before"] = before_mean
    result["after"] = after_mean
    result["absolute_difference"] = delta
    result["relative_difference"] = _relative_change(before_mean, delta)
    if result["kind"] == "binary":
        result["effect_size_name"] = "task-cluster mean risk difference"
        result["effect_size"] = delta
    else:
        result["effect_size_name"] = "task-cluster standardized mean difference dz"
        result["effect_size"] = (
            delta / float(np.std(task_differences, ddof=1))
            if n_tasks > 1 and float(np.std(task_differences, ddof=1)) > 0.0
            else None
        )

    if n_tasks < 2:
        result.update(
            ci_low=None,
            ci_high=None,
            statistic=None,
            p_value=None,
            test="not estimated: fewer than two applicable task clusters",
        )
        return
    ci = _bootstrap_mean_ci(
        task_differences,
        confidence=confidence,
        samples=bootstrap_samples,
        seed=seed,
    )
    result["ci_low"] = ci[0] if ci else None
    result["ci_high"] = ci[1] if ci else None
    result["statistic"] = abs(delta)
    result["p_value"] = _task_sign_flip_p_value(
        task_differences, samples=bootstrap_samples, seed=seed
    )
    result["test"] = "task-cluster sign-flip randomization (two-sided)"


def _task_sign_flip_p_value(
    differences: Sequence[float], *, samples: int, seed: int
) -> float:
    observed = abs(float(np.mean(differences)))
    if math.isclose(observed, 0.0, abs_tol=1e-15):
        return 1.0
    values = np.asarray(differences, dtype=float)
    if len(values) <= 16:
        total = 1 << len(values)
        extreme = 0
        for mask in range(total):
            signed = [
                value if mask & (1 << index) else -value
                for index, value in enumerate(values)
            ]
            if abs(float(np.mean(signed))) >= observed - 1e-15:
                extreme += 1
        return extreme / total
    rng = np.random.default_rng(seed)
    signs = rng.choice(np.asarray([-1.0, 1.0]), size=(samples, len(values)))
    simulated = np.abs((signs * values).mean(axis=1))
    return float((np.count_nonzero(simulated >= observed - 1e-15) + 1) / (samples + 1))


def _suppress_fixture_inference(
    result: dict[str, Any], pairs: Sequence[PairedRows], metric: str
) -> None:
    """Prevent deterministic fixture repetitions from implying statistical power."""

    result["ci_low"] = None
    result["ci_high"] = None
    result["statistic"] = None
    result["p_value"] = None
    result["test"] = "not estimated for deterministic fixture repetitions"
    result["effect_size_name"] = "not estimated for deterministic fixture repetitions"
    result["effect_size"] = None
    applicable = [
        pair
        for pair in pairs
        if pair.before.get(metric) not in (None, "")
        and pair.after.get(metric) not in (None, "")
    ]
    result["n_independent_tasks"] = len({pair.key[0] for pair in applicable})
    result["inference_eligible"] = False
