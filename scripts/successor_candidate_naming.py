#!/usr/bin/env python3
"""The deterministic naming policy for the ONE post-Phase-P successor candidate.

**NO MODEL INFERENCE. NO PROVIDER. NO NETWORK. NO SEED. NO RANDOMNESS.**

WHY A POLICY MODULE AND NOT A LITERAL
=====================================

``docs/post_phaseP_successor_candidate_freeze_setup_authorization.md`` section 8
records that **no frozen upstream record uniquely determines a successor
identifier**, expressly declines to assign one, and instead binds the later
materialisation session to six constraints:

    1. exactly one prospective identifier may be assigned;
    2. the naming policy must be stated before the name is used;
    3. selection must be deterministic and reproducible from the stated policy;
    4. ``rc5`` must not be chosen merely because ``rc4`` existed;
    5. the identifier must be distinct from ``pilot-v7-rc4`` and every historical
       Phase-P namespace;
    6. the identifier must not imply qualification PASS, confirmatory success,
       provider eligibility or scientific superiority.

A hand-picked string cannot satisfy (3): "reproducible" means a second reader,
given only the policy and the committed repository, must arrive at the same
identifier without consulting this session. So the identifier here is COMPUTED
from four committed, frozen constants, and :func:`candidate_identifier` is the
only place it exists. Constraint (4) is honoured structurally rather than by
promise: no component of the policy is an ordinal successor of anything, and
:func:`check_identifier_neutrality` refuses any ``rc<digit>`` token outright.

THE POLICY
==========

``identifier = lineage "-" instrument "-" measurement "-" benchmark`` where

``lineage``
    the fixed neutral noun ``prospective-candidate``. It states the candidate's
    scientific status -- specified before any inference under it exists -- and
    nothing else. It is not an ordinal, not a release number, and asserts no
    property of this candidate or of its predecessor.

    The obvious alternative, ``successor-candidate``, is the governing records'
    own phrase but is REJECTED here on the strict reading of constraint (6):
    ``successor`` literally contains ``success``, and
    :func:`check_identifier_neutrality` matches forbidden tokens as plain
    substrings. Relaxing that matcher to word boundaries to admit one convenient
    noun would weaken the only mechanical guard the constraint has, so the noun
    moved instead of the guard. The lineage relation to ``pilot-v7-rc4`` is not
    lost: it is carried explicitly by the candidate manifest's ``predecessor``
    binding and by the shared benchmark token below, neither of which is an
    ordinal.
``instrument``
    ``"i"`` + :data:`~iqa_soa.instrument.INSTRUMENT_VERSION`. The candidate is
    bound to instrument 5 by the freeze authorization section 10, and rows
    written under instrument 4 may never be pooled with it, so the instrument
    generation is part of the candidate's identity.
``measurement``
    ``"m"`` + the trailing ordinal of
    :data:`successor_scoring_vocabulary.SUCCESSOR_VOCABULARY_VERSION`. What
    actually distinguishes this candidate from its predecessor is the successor
    SCORING PROFILE (C1 and C2); naming it after the measurement revision names
    the real difference.
``benchmark``
    ``"b"`` + the first eight hex characters of the frozen 17-task case-byte
    digest. The task bytes are unchanged, so this token pins WHICH selection the
    candidate is bound to and would move if any task byte ever moved.

Every input is a committed constant. None is an outcome, a provider, a model, a
seed, a rate, a date, a hostname or a human preference, so the identifier is
outcome-independent and provider/model-independent by construction.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Any, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:  # pragma: no cover - import shim
        sys.path.insert(0, str(_root))

from iqa_soa.instrument import INSTRUMENT_VERSION  # noqa: E402

import successor_scoring_vocabulary as sv  # noqa: E402
import validate_successor_scope as scope  # noqa: E402

NAMING_POLICY_VERSION = "successor-candidate-naming-policy-1"

#: The fixed, neutral lineage noun.  Not an ordinal and not a release number.
#: Deliberately NOT ``successor-candidate``: see the module docstring.
LINEAGE_TOKEN = "prospective-candidate"

#: Namespaces the identifier must never collide with or extend by numeral.
HISTORICAL_NAMESPACES: tuple[str, ...] = (
    "pilot-v7-rc4",
    "pilot-v7-rc3",
    "pilot-v7-rc2",
    "pilot-v7-rc1",
    "pilot-v6.1",
    "pilot-v6",
)

#: Tokens whose presence would make the identifier assert an outcome, a
#: qualification, a provider fact or a comparative judgement.  Checked as
#: substrings of the case-folded identifier.
FORBIDDEN_IDENTIFIER_TOKENS: tuple[str, ...] = (
    "pass",
    "fail",
    "qualified",
    "qualification",
    "confirmatory",
    "confirmed",
    "success",
    "superior",
    "better",
    "improved",
    "improvement",
    "best",
    "final",
    "approved",
    "validated",
    "verified",
    "winner",
    "gold",
    "official",
    "eligible",
    "eligibility",
    "ready",
    "release-candidate",
    "phase",
)

#: ``rc<digit>`` is a PATTERN rather than a token so constraint (4) cannot be
#: satisfied by spelling, and a bare ``v<major>.<minor>`` is refused for the same
#: reason: neither may be inherited from the predecessor.
FORBIDDEN_IDENTIFIER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"rc\d"),
    re.compile(r"v\d+\.\d+"),
)


def _trailing_ordinal(version: str) -> str:
    """The trailing integer of a versioned identity string, or refuse.

    ``"successor-scoring-vocabulary-1"`` -> ``"1"``.  Refusing rather than
    defaulting keeps the policy total: an unversioned constant must stop the
    freeze, not silently name the candidate ``m0``.
    """

    match = re.search(r"(\d+)$", version)
    if match is None:
        raise ValueError(
            f"{version!r} carries no trailing ordinal, so the naming policy cannot "
            "derive a measurement token from it"
        )
    return match.group(1)


def naming_components() -> dict[str, str]:
    """The four policy inputs, each read from a committed frozen constant."""

    return {
        "lineage": LINEAGE_TOKEN,
        "instrument": f"i{INSTRUMENT_VERSION}",
        "measurement": f"m{_trailing_ordinal(sv.SUCCESSOR_VOCABULARY_VERSION)}",
        "benchmark": f"b{scope.BENCHMARK_CASE_BYTES_DIGEST[:8]}",
    }


#: The order the four components are joined in.  Named once so the policy text,
#: the identifier and the determinism check cannot disagree about it.
COMPONENT_ORDER: tuple[str, ...] = ("lineage", "instrument", "measurement", "benchmark")


def candidate_identifier() -> str:
    """THE identifier.  Computed, never written twice, never stored as a literal."""

    parts = naming_components()
    return "-".join(parts[key] for key in COMPONENT_ORDER)


def candidate_namespace() -> str:
    """The repository-relative candidate-owned namespace, as POSIX text."""

    return f"candidates/{candidate_identifier()}"


def check_identifier_neutrality(identifier: str) -> list[str]:
    """Constraints (4), (5) and (6) of the freeze authorization section 8."""

    failures: list[str] = []
    lowered = identifier.casefold()
    for token in FORBIDDEN_IDENTIFIER_TOKENS:
        if token in lowered:
            failures.append(
                f"NAMING: the identifier {identifier!r} contains {token!r}, which "
                "asserts an outcome, a qualification, a provider fact or a "
                "comparative judgement the freeze may not make"
            )
    for pattern in FORBIDDEN_IDENTIFIER_PATTERNS:
        if pattern.search(lowered):
            failures.append(
                f"NAMING: the identifier {identifier!r} matches "
                f"{pattern.pattern!r}; successorship of a numeral is not a naming "
                "rule and a release-candidate ordinal may not be inherited"
            )
    for namespace in HISTORICAL_NAMESPACES:
        if namespace.casefold() in lowered:
            failures.append(
                f"NAMING: the identifier {identifier!r} collides with the historical "
                f"namespace {namespace!r}"
            )
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier):
        failures.append(
            f"NAMING: the identifier {identifier!r} is not a lowercase, "
            "hyphen-separated, path-safe token"
        )
    return failures


def check_policy_determinism() -> list[str]:
    """The policy must reproduce the same identifier from the same constants."""

    failures: list[str] = []
    first = candidate_identifier()
    second = candidate_identifier()
    if first != second:
        failures.append(
            f"NAMING: the policy is not deterministic ({first!r} != {second!r})"
        )
    parts = naming_components()
    if parts["lineage"] != LINEAGE_TOKEN:
        failures.append("NAMING: the lineage token is not the fixed neutral noun")
    if parts["instrument"] != f"i{INSTRUMENT_VERSION}":
        failures.append(
            "NAMING: the instrument token is not derived from INSTRUMENT_VERSION"
        )
    if parts["measurement"] != f"m{_trailing_ordinal(sv.SUCCESSOR_VOCABULARY_VERSION)}":
        failures.append(
            "NAMING: the measurement token is not derived from "
            "SUCCESSOR_VOCABULARY_VERSION"
        )
    if parts["benchmark"] != f"b{scope.BENCHMARK_CASE_BYTES_DIGEST[:8]}":
        failures.append(
            "NAMING: the benchmark token is not derived from the frozen case-byte "
            "digest, so the identifier would not move if a task byte moved"
        )
    if first != "-".join(parts[key] for key in COMPONENT_ORDER):
        failures.append(
            "NAMING: the identifier is not the stated join of its components"
        )
    return failures


def policy() -> dict[str, Any]:
    """The machine-readable statement of the policy, for the freeze record."""

    identifier = candidate_identifier()
    return {
        "policy_id": NAMING_POLICY_VERSION,
        "policy_is_stated_before_the_name_is_used": True,
        "identifiers_assigned": 1,
        "identifier_families_reserved": 0,
        "phases_named": 0,
        "rule": (
            "identifier = lineage + '-' + instrument + '-' + measurement + '-' + "
            f"benchmark, where lineage is the fixed neutral noun '{LINEAGE_TOKEN}', "
            "instrument is 'i' + INSTRUMENT_VERSION, measurement is 'm' + the "
            "trailing ordinal of SUCCESSOR_VOCABULARY_VERSION, and benchmark is "
            "'b' + the first eight hex characters of the frozen 17-task benchmark "
            "case-byte digest"
        ),
        "components": naming_components(),
        "component_order": list(COMPONENT_ORDER),
        "component_sources": {
            "lineage": "scripts/successor_candidate_naming.py::LINEAGE_TOKEN",
            "instrument": "src/iqa_soa/instrument.py::INSTRUMENT_VERSION",
            "measurement": (
                "scripts/successor_scoring_vocabulary.py::SUCCESSOR_VOCABULARY_VERSION"
            ),
            "benchmark": (
                "scripts/validate_successor_scope.py::BENCHMARK_CASE_BYTES_DIGEST"
            ),
        },
        "identifier": identifier,
        "namespace": candidate_namespace(),
        "properties": {
            "reproducible_from_committed_constants": True,
            "outcome_independent": True,
            "provider_independent": True,
            "model_independent": True,
            "seed_independent": True,
            "wall_clock_independent": True,
            "host_independent": True,
            "implies_pass": False,
            "implies_qualification": False,
            "implies_confirmatory_success": False,
            "implies_provider_eligibility": False,
            "implies_superiority": False,
            "is_an_ordinal_successor_of_the_predecessor": False,
            "distinct_from_historical_namespaces": True,
        },
        "ordinal_succession_rejected_because": (
            "Successorship of a numeral is not a naming rule. Freeze authorization "
            "section 8 constraint 4 forbids inheriting the predecessor's ordinal "
            "merely because the predecessor carried one, and no frozen record "
            "assigns a release-candidate number to this candidate."
        ),
        "neutrality_failures": check_identifier_neutrality(identifier),
        "determinism_failures": check_policy_determinism(),
    }


def run_all() -> list[str]:
    identifier = candidate_identifier()
    return check_identifier_neutrality(identifier) + check_policy_determinism()


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="State the candidate naming policy.")
    parser.parse_args(argv)
    failures = run_all()
    print(json.dumps(policy(), indent=2, sort_keys=True))
    for failure in failures:
        print(failure)
    print(
        f"candidate naming policy: {'PASS' if not failures else 'FAIL'} "
        f"({len(failures)} failure(s)); NO MODEL INFERENCE; NO PROVIDER CONTACT"
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "COMPONENT_ORDER",
    "FORBIDDEN_IDENTIFIER_PATTERNS",
    "FORBIDDEN_IDENTIFIER_TOKENS",
    "HISTORICAL_NAMESPACES",
    "LINEAGE_TOKEN",
    "NAMING_POLICY_VERSION",
    "PROJECT_ROOT",
    "candidate_identifier",
    "candidate_namespace",
    "check_identifier_neutrality",
    "check_policy_determinism",
    "naming_components",
    "policy",
    "run_all",
]
