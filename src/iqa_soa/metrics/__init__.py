"""Metric collection and paired statistical analysis."""

from iqa_soa.metrics.pilot import analyze_real_pilot, load_real_pilot_records
from iqa_soa.metrics.statistics import (
    analyze_before_after,
    load_run_records,
    raw_source_digests,
)

__all__ = [
    "analyze_before_after",
    "analyze_real_pilot",
    "load_real_pilot_records",
    "load_run_records",
    "raw_source_digests",
]
