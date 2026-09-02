"""The candidate naming policy: deterministic, reproducible and neutral.

NO MODEL INFERENCE. NO PROVIDER. NO NETWORK. These tests read committed
constants and derive a string from them.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from iqa_soa.instrument import INSTRUMENT_VERSION  # noqa: E402

import successor_candidate_naming as naming  # noqa: E402
import successor_scoring_vocabulary as sv  # noqa: E402
import validate_successor_scope as scope  # noqa: E402


def test_policy_passes_its_own_checks() -> None:
    assert naming.run_all() == []


def test_identifier_is_deterministic_across_repeated_derivations() -> None:
    derived = {naming.candidate_identifier() for _ in range(5)}
    assert len(derived) == 1


def test_identifier_is_the_stated_join_of_its_components() -> None:
    parts = naming.naming_components()
    expected = "-".join(parts[key] for key in naming.COMPONENT_ORDER)
    assert naming.candidate_identifier() == expected


def test_every_component_is_derived_from_a_committed_constant() -> None:
    parts = naming.naming_components()
    assert parts["lineage"] == naming.LINEAGE_TOKEN
    assert parts["instrument"] == f"i{INSTRUMENT_VERSION}"
    assert parts["measurement"] == "m" + sv.SUCCESSOR_VOCABULARY_VERSION.rsplit("-", 1)[1]
    assert parts["benchmark"] == f"b{scope.BENCHMARK_CASE_BYTES_DIGEST[:8]}"


def test_identifier_is_neutral() -> None:
    assert naming.check_identifier_neutrality(naming.candidate_identifier()) == []


@pytest.mark.parametrize(
    "candidate",
    [
        "pilot-v7-rc5",
        "pilot-v7-rc4",
        "rc5-candidate",
        "qualified-successor",
        "candidate-pass-1",
        "confirmatory-candidate",
        "final-candidate",
        "improved-candidate",
        "provider-eligible-candidate",
    ],
)
def test_loaded_or_ordinal_identifiers_are_refused(candidate: str) -> None:
    assert naming.check_identifier_neutrality(candidate) != []


def test_an_ordinal_successor_of_the_predecessor_is_refused() -> None:
    """Constraint 4: rc5 must not be chosen merely because rc4 existed."""

    failures = naming.check_identifier_neutrality("rc5")
    assert any("numeral is not a naming rule" in failure for failure in failures)


def test_identifier_is_distinct_from_every_historical_namespace() -> None:
    identifier = naming.candidate_identifier()
    for namespace in naming.HISTORICAL_NAMESPACES:
        assert namespace not in identifier


def test_identifier_is_path_safe() -> None:
    identifier = naming.candidate_identifier()
    assert identifier == identifier.lower()
    assert "/" not in identifier and "\\" not in identifier and " " not in identifier
    assert naming.candidate_namespace() == f"candidates/{identifier}"


def test_identifier_carries_the_benchmark_binding() -> None:
    """A task-byte move would move the identifier, not just a digest field."""

    assert scope.BENCHMARK_CASE_BYTES_DIGEST[:8] in naming.candidate_identifier()


def test_policy_document_states_the_rule_and_its_properties() -> None:
    policy = naming.policy()
    assert policy["policy_id"] == naming.NAMING_POLICY_VERSION
    assert policy["identifiers_assigned"] == 1
    assert policy["identifier_families_reserved"] == 0
    assert policy["phases_named"] == 0
    assert policy["identifier"] == naming.candidate_identifier()
    assert policy["neutrality_failures"] == []
    assert policy["determinism_failures"] == []
    properties = policy["properties"]
    assert properties["outcome_independent"] is True
    assert properties["provider_independent"] is True
    assert properties["model_independent"] is True
    assert properties["implies_pass"] is False
    assert properties["implies_qualification"] is False
    assert properties["implies_confirmatory_success"] is False
    assert properties["implies_superiority"] is False
    assert properties["is_an_ordinal_successor_of_the_predecessor"] is False


def test_an_unversioned_measurement_constant_stops_the_policy() -> None:
    with pytest.raises(ValueError):
        naming._trailing_ordinal("successor-scoring-vocabulary")
