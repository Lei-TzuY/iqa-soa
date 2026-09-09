"""Execute lifecycle-bound test modules at the Git states they describe."""
from __future__ import annotations

from pathlib import Path

import pytest

from historical_replay import replay_historical_pytest


HISTORICAL_MODULES = (
    (
        "candidate-freeze",
        "d5b5537a84cc8b57bca2195c3b3bb4cfdb857e5c",
        "tests/integration/test_successor_candidate_freeze.py",
        "6232e4fd65a24a272421a32faceb39da04dd83c1",
        77,
    ),
    (
        "qualification-execution",
        "966c8d089f07c9a531da65453db54912dcab68cf",
        "tests/integration/test_successor_qualification_execution.py",
        "2ef40f2f4f5f11f307481378b6c6846a83a812bd",
        146,
    ),
    (
        "pilot-v7-rc3",
        "beafa5d170659997790e1c3e79086ea05548c094",
        "tests/benchmark/test_pilot_v7_rc3_construct.py",
        "cca3c938b16347e52b2d702a11032ba986862b27",
        158,
    ),
    (
        "pilot-v7-rc4",
        "f65ee4980813b465431c5f7d75a0d00db87785b6",
        "tests/benchmark/test_pilot_v7_rc4_construct.py",
        "1466ede775c856d96566c0808198052a14e84575",
        31,
    ),
    (
        "phase-m-instrument",
        "f65ee4980813b465431c5f7d75a0d00db87785b6",
        "tests/integration/test_phaseM_fault_provenance_instrument.py",
        "5ec6518f6b0fe7769faf56a3f46a3aac7f6f91a2",
        63,
    ),
    (
        "phase-o-redesign",
        "469b0c5916ae74f098da8ab2a45955297a04120b",
        "tests/integration/test_phaseO_rc4_redesign.py",
        "5dc3fade073aaa5411d6a17e2966938b0a4debc6",
        194,
    ),
    (
        "phase-p-execution",
        "b46b2c1b0ce26c1f7be75d942e6eb7f4f49f1b46",
        "tests/integration/test_phaseP_execution_protocol.py",
        "14987e0a16dfd2e17dc580a290105d72f4fb93d4",
        296,
    ),
    (
        "seed-supersession",
        "883c425daf2e6462877f0626f5fce0664ac85ca9",
        "tests/integration/test_post_phaseP_seed_provenance_supersession.py",
        "247566404fc69ddc4355bb39646af6046d995404",
        25,
    ),
    (
        "successor-capability",
        "469b0c5916ae74f098da8ab2a45955297a04120b",
        "tests/integration/test_post_phaseP_successor_implementation.py",
        "9256f6f341e620a54095bfd0ce77f8fd0f9f233d",
        54,
    ),
)


@pytest.mark.parametrize(
    ("label", "commit", "module_path", "blob_id", "expected_tests"),
    HISTORICAL_MODULES,
    ids=[case[0] for case in HISTORICAL_MODULES],
)
def test_lifecycle_bound_module_replays_unchanged(
    label: str,
    commit: str,
    module_path: str,
    blob_id: str,
    expected_tests: int,
    tmp_path: Path,
) -> None:
    del label
    replay_historical_pytest(
        commit=commit,
        module_path=module_path,
        blob_id=blob_id,
        expected_tests=expected_tests,
        worktree=tmp_path,
    )
