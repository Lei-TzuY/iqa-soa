"""Evaluator entry point kept at the benchmark boundary."""

from iqa_soa.metrics.collector import collect_run_metrics, load_evidence_events

__all__ = ["collect_run_metrics", "load_evidence_events"]
