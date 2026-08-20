"""Read-only helpers for inspecting generated JSONL evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_evidence(path: str | Path) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"evidence line {line_number} is not a JSON object")
            records.append(value)
    return tuple(records)


__all__ = ["read_evidence"]
