"""Data-driven IQA-SOA treatment definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml  # type: ignore[import-untyped]

from iqa_soa.types import QAMode


GUARD_NAMES: tuple[str, ...] = (
    "injection",
    "permission",
    "privacy",
    "budget",
    "output_validation",
    "evidence",
)
ABLATION_NAMES: tuple[str, ...] = GUARD_NAMES
PARTIAL_GUARDS = frozenset({"permission", "budget"})


@dataclass(frozen=True, slots=True)
class Treatment:
    name: str
    qa_mode: QAMode
    enabled_guards: Mapping[str, bool]
    ablation: str | None = None

    def __post_init__(self) -> None:
        unknown = set(self.enabled_guards) - set(GUARD_NAMES)
        if unknown:
            raise ValueError(f"unknown guards in treatment {self.name}: {sorted(unknown)}")
        if self.qa_mode is QAMode.ABLATION and self.ablation not in ABLATION_NAMES:
            raise ValueError("ablation treatment must name exactly one implemented guard")
        if self.qa_mode is not QAMode.ABLATION and self.ablation is not None:
            raise ValueError("ordinary treatments cannot carry an ablation label")

    @property
    def detailed_evidence(self) -> bool:
        return bool(self.enabled_guards.get("evidence", False)) and self.qa_mode not in {
            QAMode.OFF
        }


def treatment_for(name: str) -> Treatment:
    normalized = name.strip().lower().replace("-", "_")
    if normalized in {"off", "g0", "before"}:
        return Treatment("off", QAMode.OFF, {guard: False for guard in GUARD_NAMES})
    if normalized in {"partial", "g1"}:
        return Treatment(
            "partial",
            QAMode.PARTIAL,
            {guard: guard in PARTIAL_GUARDS for guard in GUARD_NAMES},
        )
    if normalized in {"full", "g2", "after"}:
        return Treatment("full", QAMode.FULL, {guard: True for guard in GUARD_NAMES})
    prefix = "full_minus_"
    if normalized.startswith(prefix):
        ablation = normalized[len(prefix) :]
    elif normalized.startswith("ablation_"):
        ablation = normalized[len("ablation_") :]
    else:
        raise ValueError(f"unknown treatment: {name!r}")
    aliases = {"prompt_injection": "injection", "output": "output_validation"}
    ablation = aliases.get(ablation, ablation)
    if ablation not in ABLATION_NAMES:
        raise ValueError(f"unknown ablation guard: {ablation!r}")
    enabled = {guard: guard != ablation for guard in GUARD_NAMES}
    return Treatment(f"full_minus_{ablation}", QAMode.ABLATION, enabled, ablation)


def load_ablation_treatments(path: str | Path) -> tuple[Treatment, ...]:
    """Load the complete FULL/full-minus-one design from strict YAML data."""

    source = Path(path)
    try:
        data = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot read ablation configuration {source}: {exc}") from exc
    if not isinstance(data, Mapping) or set(data) != {"schema_version", "treatments"}:
        raise ValueError("ablation configuration must contain schema_version and treatments")
    if data["schema_version"] != 1 or not isinstance(data["treatments"], list):
        raise ValueError("ablation schema_version must be 1 and treatments must be a list")

    treatments: list[Treatment] = []
    for index, raw in enumerate(data["treatments"]):
        if not isinstance(raw, Mapping) or set(raw) != {
            "name",
            "qa_mode",
            "ablation",
            "guards",
        }:
            raise ValueError(f"ablation treatment {index} has an invalid field set")
        name = raw["name"]
        mode = raw["qa_mode"]
        ablation = raw["ablation"]
        guards = raw["guards"]
        if not isinstance(name, str) or not name:
            raise ValueError(f"ablation treatment {index} name must be non-empty")
        if not isinstance(guards, Mapping) or set(guards) != set(GUARD_NAMES):
            raise ValueError(f"ablation treatment {name!r} must configure every guard")
        if any(not isinstance(value, bool) for value in guards.values()):
            raise ValueError(f"ablation treatment {name!r} guard values must be boolean")
        if mode == "full" and ablation is None:
            qa_mode = QAMode.FULL
        elif mode == "ablation" and isinstance(ablation, str):
            qa_mode = QAMode.ABLATION
        else:
            raise ValueError(f"ablation treatment {name!r} has invalid mode/label")
        treatments.append(
            Treatment(
                name=name,
                qa_mode=qa_mode,
                enabled_guards={str(key): bool(value) for key, value in guards.items()},
                ablation=ablation,
            )
        )

    expected_names = {"full", *(f"full_minus_{guard}" for guard in ABLATION_NAMES)}
    observed_names = {item.name for item in treatments}
    if len(treatments) != len(observed_names) or observed_names != expected_names:
        raise ValueError("ablation configuration must define FULL and each guard removal once")
    for treatment in treatments:
        disabled = {
            guard for guard, enabled in treatment.enabled_guards.items() if not enabled
        }
        expected_disabled = {treatment.ablation} if treatment.ablation else set()
        if disabled != expected_disabled:
            raise ValueError(
                f"ablation treatment {treatment.name!r} must disable exactly "
                f"{sorted(expected_disabled)}"
            )
        expected_name = (
            "full" if treatment.ablation is None else f"full_minus_{treatment.ablation}"
        )
        if treatment.name != expected_name:
            raise ValueError(
                f"ablation treatment {treatment.name!r} must be named {expected_name!r}"
            )
    return tuple(treatments)


__all__ = [
    "ABLATION_NAMES",
    "GUARD_NAMES",
    "PARTIAL_GUARDS",
    "Treatment",
    "load_ablation_treatments",
    "treatment_for",
]
