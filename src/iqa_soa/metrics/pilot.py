"""Integrity validation and summaries for real-model pilot experiment bundles."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping, Sequence, cast

from iqa_soa.failure_taxonomy import (
    INFRASTRUCTURE_FAILURE_CLASSES,
    SCIENTIFIC_FAILURE_CLASSES,
    infer_legacy_failure_class,
)
from iqa_soa.instrument import (
    PRE_REPAIR_INSTRUMENT_VERSION,
    PRE_REPAIR_RAW_SCHEMA_VERSION,
    RAW_SCHEMA_VERSION,
)
from iqa_soa.metrics.definitions import PILOT_RAW_FIELDS, PILOT_RAW_FIELDS_V3
from iqa_soa.metrics.statistics import AnalysisError, analyze_before_after, pair_before_after


def load_real_pilot_records(
    sources: Sequence[str | Path],
    *,
    allow_infrastructure_failures: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load one complete per-model run per source and verify pooled integrity."""

    if not sources:
        raise AnalysisError("at least one real-pilot experiment directory is required")
    all_rows: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    source_records: list[dict[str, Any]] = []
    seen_experiments: set[str] = set()
    seen_models: set[tuple[str, str]] = set()
    common_design: tuple[Any, ...] | None = None
    common_instrument: tuple[str, str] | None = None
    for raw_source in sources:
        source = Path(raw_source).resolve()
        if not source.is_dir():
            raise AnalysisError(f"real-pilot source must be an experiment directory: {source}")
        run_path = source / "runs.jsonl"
        manifest_path = source / "manifest.json"
        try:
            manifest_value = json.loads(manifest_path.read_text(encoding="utf-8"))
            rows = [
                json.loads(line)
                for line in run_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except (OSError, json.JSONDecodeError) as exc:
            raise AnalysisError(f"cannot read real-pilot source {source}: {exc}") from exc
        if not isinstance(manifest_value, Mapping):
            raise AnalysisError(f"real-pilot manifest must be an object: {manifest_path}")
        manifest = dict(manifest_value)
        if not rows or any(not isinstance(row, dict) for row in rows):
            raise AnalysisError(f"real-pilot source has no valid object rows: {run_path}")
        _validate_pilot_manifest(manifest, rows)
        experiment_id = str(manifest["experiment_id"])
        if experiment_id in seen_experiments:
            raise AnalysisError(f"duplicate real-pilot experiment source: {experiment_id}")
        seen_experiments.add(experiment_id)
        provider = _mapping(manifest.get("provider"), "manifest provider")
        provider_model = (
            _nonempty(provider.get("provider"), "manifest provider.provider"),
            _nonempty(provider.get("model"), "manifest provider.model"),
        )
        if provider_model[0] == "deterministic_stub":
            raise AnalysisError("deterministic fixture rows cannot enter real-model pilot analysis")
        if provider_model in seen_models:
            raise AnalysisError(
                f"duplicate provider/model pilot source: {provider_model!r}"
            )
        seen_models.add(provider_model)
        # Instrument boundary: pre-repair and post-repair measurements are not
        # the same instrument and must never be pooled.  Frozen manifests
        # predate the field, so they default to the pre-repair version.
        instrument = (
            str(manifest.get("instrument_version", PRE_REPAIR_INSTRUMENT_VERSION)),
            # The native-tool adapter shapes what the model actually sees, so a
            # differing adapter is a differing instrument even at the same
            # instrument_version.
            str(manifest.get("native_tool_adapter_version", "")),
        )
        if common_instrument is None:
            common_instrument = instrument
        elif instrument != common_instrument:
            raise AnalysisError(
                "real-pilot sources were produced by different instrument "
                f"versions ({common_instrument!r} vs {instrument!r}); pre-repair "
                "and post-repair measurements must not be pooled"
            )
        design = (
            manifest.get("benchmark_version"),
            _mapping(manifest.get("input_digests"), "manifest input_digests").get(
                "benchmark_manifest_sha256"
            ),
            tuple(manifest.get("case_ids", [])),
            manifest.get("repetitions"),
            tuple(manifest.get("seeds", [])),
            tuple(manifest.get("treatments", [])),
            _mapping(manifest.get("resource_budget_policy"), "manifest resource_budget_policy").get(
                "policy_id"
            )
            if manifest.get("resource_budget_policy") is not None
            else None,
        )
        if common_design is None:
            common_design = design
        elif design != common_design:
            raise AnalysisError("real-pilot sources do not share one frozen paired design")
        classified_rows = [_classified_failure_row(row) for row in rows]
        for row in classified_rows:
            _validate_failure(row, allow_infrastructure_failures)
        _validate_pilot_pairs(classified_rows)
        all_rows.extend(classified_rows)
        manifests.append(manifest)
        source_records.append(
            {
                "experiment_dir": str(source),
                "experiment_id": experiment_id,
                "provider": provider_model[0],
                "model": provider_model[1],
                "runs_sha256": hashlib.sha256(run_path.read_bytes()).hexdigest(),
                "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            }
        )
    _validate_pooled_pairs(all_rows)
    failures = Counter(
        str(row.get("analysis_failure_class"))
        for row in all_rows
        if row.get("analysis_failure_class") not in (None, "")
    )
    failure_sources = Counter(
        str(row.get("analysis_failure_class_source"))
        for row in all_rows
        if row.get("analysis_failure_class") not in (None, "")
    )
    return all_rows, {
        "sources": source_records,
        "models": len(seen_models),
        "records": len(all_rows),
        "benchmark_version": common_design[0] if common_design else None,
        "benchmark_manifest_sha256": common_design[1] if common_design else None,
        "case_ids": list(common_design[2]) if common_design else [],
        "repetitions": common_design[3] if common_design else None,
        "seeds": list(common_design[4]) if common_design else [],
        "treatments": list(common_design[5]) if common_design else [],
        "failure_counts": dict(sorted(failures.items())),
        "failure_classification_sources": dict(sorted(failure_sources.items())),
        "historical_failure_taxonomy_inferred": "legacy_inferred_from_error" in failure_sources,
        "infrastructure_failures_allowed": allow_infrastructure_failures,
        "instrument_version": common_instrument[0] if common_instrument else None,
        "native_tool_adapter_version": (
            (common_instrument[1] or None) if common_instrument else None
        ),
    }


def analyze_real_pilot(
    sources: Sequence[str | Path],
    *,
    confidence: float = 0.95,
    bootstrap_samples: int = 10_000,
    seed: int = 2027,
    allow_infrastructure_failures: bool = False,
) -> dict[str, Any]:
    rows, validation = load_real_pilot_records(
        sources,
        allow_infrastructure_failures=allow_infrastructure_failures,
    )
    analysis_rows = [_analysis_row(row) for row in rows]
    overall = analyze_before_after(
        analysis_rows,
        confidence=confidence,
        bootstrap_samples=bootstrap_samples,
        seed=seed,
    )
    model_keys = sorted(
        {(str(row["provider"]), str(row["model"])) for row in rows}
    )
    per_model: list[dict[str, Any]] = []
    for index, (provider, model) in enumerate(model_keys):
        selected = [
            row
            for row in analysis_rows
            if row["provider"] == provider and row["model"] == model
        ]
        per_model.append(
            {
                "provider": provider,
                "model": model,
                "summary": _summary_rows(selected),
                "paired_analysis": analyze_before_after(
                    selected,
                    confidence=confidence,
                    bootstrap_samples=bootstrap_samples,
                    seed=seed + 1000 + index,
                ),
            }
        )
    return {
        "result_provenance": "real-model pilot",
        "result_status": (
            "descriptive pilot result; legacy failure taxonomy inferred from immutable raw rows"
            if validation["historical_failure_taxonomy_inferred"]
            else "descriptive pilot result"
        ),
        "validation": validation,
        "summary": _summary_rows(analysis_rows),
        "paired_analysis": overall,
        "per_model": per_model,
        "anomalies": _anomaly_summary(rows),
        "inference_note": (
            "Pilot inference is descriptive and task-clustered over this frozen suite; "
            "it is not final FSE evidence or unseen-task generalization."
        ),
    }


def _validate_pilot_manifest(
    manifest: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]
) -> None:
    required = {
        "schema_version",
        "raw_schema_version",
        "experiment_id",
        "experiment_kind",
        "status",
        "completed_at",
        "provider",
        "benchmark_version",
        "case_ids",
        "treatments",
        "repetitions",
        "seeds",
        "expected_record_count",
        "record_count",
        "input_digests",
        "software",
        "infrastructure_retry_limit",
        "resource_budget_policy",
    }
    missing = required - set(manifest)
    if missing:
        raise AnalysisError(f"real-pilot manifest is missing fields: {sorted(missing)}")
    raw_schema = manifest.get("raw_schema_version")
    if manifest.get("schema_version") != 2 or raw_schema not in {
        PRE_REPAIR_RAW_SCHEMA_VERSION,
        RAW_SCHEMA_VERSION,
    }:
        raise AnalysisError(
            "real-pilot manifest schema_version must be 2 and raw_schema_version "
            f"must be {PRE_REPAIR_RAW_SCHEMA_VERSION} or {RAW_SCHEMA_VERSION}"
        )
    if manifest.get("experiment_kind") != "real_model_pilot":
        raise AnalysisError(
            "pilot analysis accepts only experiment_kind=real_model_pilot; "
            "connectivity smoke and deterministic rows are excluded"
        )
    if manifest.get("status") != "complete":
        raise AnalysisError("real-pilot manifest must be complete")
    if manifest.get("infrastructure_retry_limit") != 0:
        raise AnalysisError("real-pilot manifest must record zero automatic retries")
    if not isinstance(manifest.get("benchmark_version"), str):
        raise AnalysisError("real-pilot benchmark_version is missing")
    case_ids = manifest.get("case_ids")
    treatments = manifest.get("treatments")
    repetitions = manifest.get("repetitions")
    seeds = manifest.get("seeds")
    if not isinstance(case_ids, list) or len(case_ids) < 10:
        raise AnalysisError("real-pilot manifest must contain the frozen pilot task set")
    if treatments != ["off", "full"]:
        raise AnalysisError("real-pilot manifest treatments must be [off, full]")
    if isinstance(repetitions, bool) or not isinstance(repetitions, int) or repetitions < 2:
        raise AnalysisError("real-pilot requires repeated execution")
    if not isinstance(seeds, list) or len(seeds) != repetitions:
        raise AnalysisError("real-pilot seeds/repetitions mismatch")
    expected = len(case_ids) * repetitions * 2
    if (
        manifest.get("expected_record_count") != expected
        or manifest.get("record_count") != expected
        or len(rows) != expected
    ):
        raise AnalysisError("real-pilot manifest/run count is incomplete")
    digests = _mapping(manifest.get("input_digests"), "manifest input_digests")
    for name in (
        "benchmark_manifest_sha256",
        "selected_case_set_sha256",
        "qa_xml_policy_sha256",
        "model_config_sha256",
        "experiment_config_sha256",
        "resource_budget_policy_sha256",
    ):
        if not _is_sha256(digests.get(name)):
            raise AnalysisError(f"real-pilot input digest is missing/invalid: {name}")
    expected_cells = {
        (str(task_id), repetition, mode)
        for task_id in case_ids
        for repetition in range(repetitions)
        for mode in ("off", "full")
    }
    seen: set[tuple[str, int, str]] = set()
    post_repair = manifest.get("raw_schema_version") == RAW_SCHEMA_VERSION
    required_row_fields = (
        set(PILOT_RAW_FIELDS_V3) if post_repair else set(PILOT_RAW_FIELDS)
    )
    manifest_instrument = manifest.get("instrument_version")
    manifest_adapter = manifest.get("native_tool_adapter_version")
    if post_repair:
        # A post-repair manifest must identify its instrument and its native
        # tool adapter, and must agree with the provider descriptor it used.
        if not isinstance(manifest_instrument, str) or not manifest_instrument:
            raise AnalysisError(
                "post-repair real-pilot manifest must record instrument_version"
            )
        if not isinstance(manifest_adapter, str) or not manifest_adapter:
            raise AnalysisError(
                "post-repair real-pilot manifest must record "
                "native_tool_adapter_version"
            )
        provider_block = manifest.get("provider")
        provider_adapter = (
            provider_block.get("native_tool_adapter_version")
            if isinstance(provider_block, Mapping)
            else None
        )
        if provider_adapter is not None and provider_adapter != manifest_adapter:
            raise AnalysisError(
                "real-pilot manifest native_tool_adapter_version disagrees with "
                f"its provider descriptor ({manifest_adapter!r} vs "
                f"{provider_adapter!r})"
            )
    elif manifest_instrument is not None and str(manifest_instrument) != (
        PRE_REPAIR_INSTRUMENT_VERSION
    ):
        raise AnalysisError(
            "raw schema "
            f"{PRE_REPAIR_RAW_SCHEMA_VERSION} cannot declare instrument_version "
            f"{manifest_instrument!r}"
        )
    for row in rows:
        missing_fields = required_row_fields - set(row)
        if missing_fields:
            raise AnalysisError(
                f"real-pilot row lacks schema fields: {sorted(missing_fields)}"
            )
        if row.get("experiment_id") != manifest.get("experiment_id"):
            raise AnalysisError("real-pilot row experiment_id differs from manifest")
        if post_repair:
            if row.get("instrument_version") != manifest_instrument:
                raise AnalysisError(
                    "real-pilot row instrument_version differs from manifest "
                    f"({row.get('instrument_version')!r} vs "
                    f"{manifest_instrument!r})"
                )
            if row.get("native_tool_adapter_version") != manifest_adapter:
                raise AnalysisError(
                    "real-pilot row native_tool_adapter_version differs from "
                    f"manifest ({row.get('native_tool_adapter_version')!r} vs "
                    f"{manifest_adapter!r})"
                )
        if row.get("experiment_kind") != "real_model_pilot":
            raise AnalysisError("real-pilot row has an invalid provenance label")
        if row.get("benchmark_version") != manifest.get("benchmark_version"):
            raise AnalysisError("real-pilot row benchmark_version differs from manifest")
        if row.get("benchmark_manifest_sha256") != digests["benchmark_manifest_sha256"]:
            raise AnalysisError("real-pilot row benchmark manifest digest differs")
        policy = manifest.get("resource_budget_policy")
        expected_policy_id = policy.get("policy_id") if isinstance(policy, Mapping) else None
        if row.get("resource_budget_policy_id") != expected_policy_id:
            raise AnalysisError("real-pilot row resource budget policy differs from manifest")
        repetition = row.get("repetition")
        if isinstance(repetition, bool) or not isinstance(repetition, int):
            raise AnalysisError("real-pilot repetition must be an integer")
        cell = (str(row.get("task_id")), repetition, str(row.get("qa_mode")))
        if cell in seen:
            raise AnalysisError(f"duplicate real-pilot cell: {cell!r}")
        seen.add(cell)
        if row.get("seed") != seeds[repetition]:
            raise AnalysisError("real-pilot row seed differs from manifest")
        if not _is_sha256(row.get("system_prompt_sha256")) or not _is_sha256(
            row.get("user_prompt_sha256")
        ):
            raise AnalysisError("real-pilot prompt hashes are invalid")
        attempts = row.get("provider_attempts")
        if not isinstance(attempts, list) or row.get("provider_attempt_count") != len(attempts):
            raise AnalysisError("real-pilot provider attempt provenance is incomplete")
        if not attempts:
            raise AnalysisError("every real-pilot cell must preserve a provider attempt")
    if seen != expected_cells:
        raise AnalysisError("real-pilot manifest is missing expected cells")


def _validate_failure(
    row: Mapping[str, Any], allow_infrastructure_failures: bool
) -> None:
    failure = row.get("analysis_failure_class")
    error = row.get("error")
    if failure in (None, ""):
        if error not in (None, ""):
            raise AnalysisError("unclassified real-pilot error cannot enter analysis")
        return
    if failure in SCIENTIFIC_FAILURE_CLASSES:
        return
    if failure not in INFRASTRUCTURE_FAILURE_CLASSES:
        raise AnalysisError(f"unknown real-pilot failure class: {failure!r}")
    if not allow_infrastructure_failures:
        raise AnalysisError(
            f"infrastructure failure {failure!r} prevents complete pilot analysis"
        )


def _classified_failure_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Attach an analysis-only class without mutating immutable raw records."""

    classified = dict(row)
    recorded = row.get("failure_class")
    if isinstance(recorded, str) and recorded:
        classified["analysis_failure_class"] = recorded
        classified["analysis_failure_class_source"] = "recorded"
        classified["analysis_error_permitted"] = recorded in SCIENTIFIC_FAILURE_CLASSES
        return classified
    error = row.get("error")
    if isinstance(error, str) and error:
        inferred = infer_legacy_failure_class(error)
        if inferred is not None:
            classified["analysis_failure_class"] = inferred
            classified["analysis_failure_class_source"] = "legacy_inferred_from_error"
            classified["analysis_error_permitted"] = True
            return classified
    classified["analysis_failure_class"] = None
    classified["analysis_failure_class_source"] = None
    classified["analysis_error_permitted"] = False
    return classified


def _validate_pilot_pairs(rows: Sequence[Mapping[str, Any]]) -> None:
    cleaned = [_analysis_row(row) for row in rows]
    pairs = pair_before_after(cleaned)
    for pair in pairs:
        if pair.before.get("pair_id") != pair.after.get("pair_id"):
            raise AnalysisError(f"pair_id mismatch for {pair.key!r}")
        for field in (
            "benchmark_manifest_sha256",
            "system_prompt_sha256",
            "user_prompt_sha256",
            "policy_sha256",
            "resource_budget_policy_id",
            "tool_state_sha256",
            "temperature",
            "top_p",
            "max_output_tokens",
        ):
            if pair.before.get(field) != pair.after.get(field):
                raise AnalysisError(f"paired pilot invariant {field} differs for {pair.key!r}")
        positions = {pair.before.get("treatment_index"), pair.after.get("treatment_index")}
        if positions != {0, 1}:
            raise AnalysisError(f"paired treatment positions are invalid for {pair.key!r}")
    position_counts: dict[tuple[str, str, str], Counter[int]] = {}
    for row in rows:
        key = (str(row["provider"]), str(row["model"]), str(row["qa_mode"]))
        position = row.get("treatment_index")
        if isinstance(position, int) and not isinstance(position, bool):
            position_counts.setdefault(key, Counter())[position] += 1
    for key, counts in position_counts.items():
        if set(counts) != {0, 1} or abs(counts[0] - counts[1]) > len(
            {str(row["task_id"]) for row in rows}
        ):
            raise AnalysisError(f"pilot treatment ordering is materially imbalanced: {key!r}")


def _validate_pooled_pairs(rows: Sequence[Mapping[str, Any]]) -> None:
    pair_before_after([_analysis_row(row) for row in rows])


def _analysis_row(row: Mapping[str, Any]) -> dict[str, Any]:
    # Keep the original error text.  Statistics use recorded metrics; derived
    # output must not hide a scientific model/tool failure from readers.
    return dict(row)


def _summary_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    specifications = (
        ("Safety/Security Violation Rate", "run_rate", "safety_security_violation"),
        ("Resource Budget Violation Rate", "run_rate", "resource_budget_violation"),
        ("Constraint Violation Rate", "run_rate", "constraint_violation"),
        ("Unauthorized Action Rate", "action_rate", ("unsafe_executed_count", "unsafe_proposed_count")),
        ("Attack Success Rate", "run_rate", "attack_success"),
        ("Privacy Leakage Rate", "run_rate", "privacy_leak"),
        ("Task Success Rate", "run_rate", "task_success"),
        ("False Rejection Rate", "action_rate", ("expected_blocked_count", "expected_action_count")),
        ("Median Latency (ms)", "median", "end_to_end_latency_ms"),
        ("Mean Token Usage", "mean", "total_tokens"),
        ("Estimated Cost", "mean", "estimated_cost"),
        ("Evidence Completeness", "mean", "evidence_completeness"),
    )
    summaries: list[dict[str, Any]] = []
    for label, kind, field in specifications:
        values: dict[str, tuple[float | None, int, float | None]] = {}
        for mode in ("off", "full"):
            selected = [row for row in rows if str(row.get("qa_mode")) == mode]
            if kind == "action_rate":
                numerator_field, denominator_field = cast(tuple[str, str], field)
                numerator = sum(_number(row.get(numerator_field)) or 0.0 for row in selected)
                denominator = sum(_number(row.get(denominator_field)) or 0.0 for row in selected)
                value = numerator / denominator if denominator else None
                values[mode] = (value, int(denominator), numerator)
            else:
                observed = [
                    number
                    for row in selected
                    if (number := _number(row.get(cast(str, field)))) is not None
                ]
                if not observed:
                    values[mode] = (None, 0, None)
                elif kind == "median":
                    values[mode] = (float(median(observed)), len(observed), None)
                else:
                    values[mode] = (sum(observed) / len(observed), len(observed), None)
        before, before_n, before_num = values["off"]
        after, after_n, after_num = values["full"]
        delta = after - before if before is not None and after is not None else None
        summaries.append(
            {
                "metric": label,
                "qa_off": before,
                "qa_full": after,
                "delta": delta,
                "relative_delta": (
                    delta / abs(before)
                    if delta is not None and before is not None and before != 0.0
                    else None
                ),
                "qa_off_n": before_n,
                "qa_full_n": after_n,
                "qa_off_numerator": before_num,
                "qa_full_numerator": after_num,
                "summary_kind": kind,
            }
        )
    return summaries


def _anomaly_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    fields = (
        "model_refusal",
        "invalid_action_format",
        "tool_call_parse_failure",
        "no_action",
        "constraint_violation",
        "safety_security_violation",
        "resource_budget_violation",
        "false_rejection",
    )
    result: dict[str, Any] = {}
    for field in fields:
        result[field] = sum(bool(row.get(field)) for row in rows)
    result["failure_class_counts"] = dict(
        sorted(
            Counter(
                str(row["analysis_failure_class"])
                for row in rows
                if row.get("analysis_failure_class") not in (None, "")
            ).items()
        )
    )
    return result


def _number(value: Any) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
        return float(value) if isinstance(value, bool) else None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    raise AnalysisError(f"expected a finite numeric pilot value, got {value!r}")


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AnalysisError(f"{where} must be an object")
    return cast(Mapping[str, Any], value)


def _nonempty(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise AnalysisError(f"{where} must be a non-empty string")
    return value


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value.lower()
    )


__all__ = [
    "INFRASTRUCTURE_FAILURE_CLASSES",
    "SCIENTIFIC_FAILURE_CLASSES",
    "analyze_real_pilot",
    "load_real_pilot_records",
]
