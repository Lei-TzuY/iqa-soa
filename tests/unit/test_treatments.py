from __future__ import annotations

from pathlib import Path

import pytest

from iqa_soa.experiment.treatments import (
    ABLATION_NAMES,
    load_ablation_treatments,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_ablation_design_is_loaded_from_complete_strict_yaml() -> None:
    treatments = load_ablation_treatments(PROJECT_ROOT / "configs" / "ablations.yaml")
    assert treatments[0].name == "full"
    assert treatments[0].ablation is None
    assert all(treatments[0].enabled_guards.values())
    assert {item.ablation for item in treatments[1:]} == set(ABLATION_NAMES)
    for treatment in treatments[1:]:
        assert {
            guard
            for guard, enabled in treatment.enabled_guards.items()
            if not enabled
        } == {treatment.ablation}


def test_ablation_design_rejects_implicit_or_multi_guard_removal(
    tmp_path: Path,
) -> None:
    invalid = tmp_path / "ablations.yaml"
    invalid.write_text(
        "schema_version: 1\ntreatments:\n"
        "  - name: full\n"
        "    qa_mode: full\n"
        "    ablation: null\n"
        "    guards: {injection: true}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="configure every guard"):
        load_ablation_treatments(invalid)
