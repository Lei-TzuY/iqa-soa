"""Current-checkout pytest collection policy.

The listed modules assert lifecycle states that were true only at their bound
historical commits (for example, that an exactly-once result namespace was not
yet present). Their unchanged blobs are executed by
``tests/test_historical_lifecycle_replays.py`` in detached worktrees.
"""

collect_ignore = [
    "tests/benchmark/test_pilot_v7_rc3_construct.py",
    "tests/benchmark/test_pilot_v7_rc4_construct.py",
    "tests/integration/test_phaseM_fault_provenance_instrument.py",
    "tests/integration/test_phaseO_rc4_redesign.py",
    "tests/integration/test_phaseP_execution_protocol.py",
    "tests/integration/test_post_phaseP_seed_provenance_supersession.py",
    "tests/integration/test_post_phaseP_successor_implementation.py",
    "tests/integration/test_successor_candidate_freeze.py",
    "tests/integration/test_successor_qualification_execution.py",
]
