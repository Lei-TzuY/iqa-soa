#!/usr/bin/env python3
"""The successor real-model qualification DRIVER.

**THIS DRIVER CANNOT CURRENTLY EXECUTE ANYTHING.**

``docs/post_phaseP_successor_provider_and_qualification_protocol_authorization.md``
authorizes the successor provider configuration, the successor
``ExperimentConfig``, the qualification protocol, the frozen execution-input
bindings and the offline eligibility preflight.  It explicitly withholds provider
contact, endpoint probes, model inference, qualification execution and
confirmatory execution.  Its section 5A additionally resolves the runtime-version
disagreement as ``RESTORE_FROZEN_RUNTIME`` -- restore the environment to the
pinned runtime; do not repin the protocol to the environment.

The driver exists now so that the execution boundary is a reviewed, tested
artifact BEFORE anyone is in a position to cross it -- not so that it can be
crossed.

THE ORDER OF THE LOCKS IS THE POINT
===================================

``--preflight`` is offline and always available.  ``--execute-real-model`` is
refused, and refused in a specific order:

1. :func:`~successor_qualification_protocol.require_execution_authorization`
   first.  While ``QUALIFICATION_EXECUTION_AUTHORIZED`` is ``False`` a caller who
   supplies BOTH the flag and the environment gate still gets a refusal, and
   gets it before either is read.  A human record is the authorization; the
   gates are only how an already-granted authorization is exercised.
2. Only then the two gates, then the offline preflight, then -- under a future
   authorization -- the runtime preflight and the schedule.

Written the other way round, a green environment would look like consent.  It is
not consent, and this driver never lets it read as consent.

The results namespace is NEVER created by any path in this file.  Nothing is
written, no provider object is constructed, and no credential is read.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
SRC_ROOT = PROJECT_ROOT / "src"
for _root in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import successor_eligibility_preflight as eligibility  # noqa: E402
import successor_qualification_protocol as protocol  # noqa: E402


def offline_preflight_failures() -> list[str]:
    """Every offline failure the driver can see, protocol first."""

    return protocol.offline_preflight() + eligibility.check_argument_integrity()


def offline_preflight_report() -> dict[str, Any]:
    """Everything the driver can establish with no provider contact."""

    protocol_failures = protocol.offline_preflight()
    eligibility_failures = eligibility.check_argument_integrity()
    return {
        "candidate_identifier": protocol.CANDIDATE_IDENTIFIER,
        "candidate_status_at_entry": protocol.CANDIDATE_STATUS_AT_ENTRY,
        "proposed_strata": [list(item) for item in protocol.PROPOSED_STRATA],
        "protocol_preflight_failures": protocol_failures,
        "eligibility_argument_failures": eligibility_failures,
        "stage_a_status": eligibility.stage_a_status(),
        "runtime_snapshot_capture_required_next": (
            eligibility.runtime_snapshot_capture_required_next()
        ),
        "models_config": protocol.CANONICAL_MODELS_RELATIVE,
        "experiment_config": protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE,
        "seeds": list(protocol.SEEDS),
        "seed_selection_status": protocol.SEED_SELECTION_STATUS,
        "seed_derivation_record": protocol.SEED_DERIVATION_RECORD_RELATIVE,
        "planned_cells": protocol.PLANNED_CELLS,
        "expected_runtime_version": protocol.EXPECTED_RUNTIME_VERSION,
        "runtime_version_resolution": protocol.RUNTIME_VERSION_RESOLUTION,
        "runtime_repin_authorized": protocol.RUNTIME_REPIN_AUTHORIZED,
        "runtime_restore_required": protocol.RUNTIME_RESTORE_REQUIRED,
        "results_namespace": protocol.RESULTS_NAMESPACE,
        "results_namespace_created": (
            PROJECT_ROOT / protocol.RESULTS_NAMESPACE
        ).exists(),
        "qualification_execution_authorized": protocol.QUALIFICATION_EXECUTION_AUTHORIZED,
        "provider_contact_authorized": protocol.PROVIDER_CONTACT_AUTHORIZED,
        "model_inference_authorized": protocol.MODEL_INFERENCE_AUTHORIZED,
        "provider_contacted": False,
        "model_inference_performed": False,
        "rows_written": 0,
    }


def _refuse_execution() -> int:
    """The execution path, in full.  It ends in a refusal, by construction."""

    try:
        protocol.require_execution_authorization()
    except protocol.QualificationExecutionNotAuthorized as exc:
        print(str(exc))
        return protocol.EXIT_GATE_CLOSED

    # Unreachable while the authorization constant is False.  It is written out
    # rather than omitted so that the day a human record does authorize
    # execution, the remaining gates are already here, already reviewed, and
    # nobody has to invent them under time pressure.
    gate_value = os.environ.get(protocol.HUMAN_GATE_ENV)  # pragma: no cover
    if gate_value != protocol.HUMAN_GATE_VALUE:  # pragma: no cover
        print(
            f"GATE_CLOSED: {protocol.HUMAN_GATE_ENV} must be "
            f"{protocol.HUMAN_GATE_VALUE!r}"
        )
        return protocol.EXIT_GATE_CLOSED
    failures = protocol.offline_preflight()  # pragma: no cover
    if failures:  # pragma: no cover
        for failure in failures:
            print(failure)
        return protocol.EXIT_PREFLIGHT_STOP
    print(  # pragma: no cover
        "PREFLIGHT_STOP: a runtime preflight capturing one RuntimeSnapshotV1 per "
        "proposed stratum, and verifying every model/runtime pin, must precede any "
        "cell. It is not implemented here because capturing it requires provider "
        "contact, which no record has yet authorized."
    )
    return protocol.EXIT_PREFLIGHT_STOP  # pragma: no cover


def main(argv: Sequence[str] | None = None) -> int:
    import argparse  # noqa: PLC0415 - CLI only

    parser = argparse.ArgumentParser(
        description="Successor real-model qualification driver"
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="run every offline check and report; contacts nothing",
    )
    parser.add_argument(
        protocol.HUMAN_GATE_FLAG,
        dest="execute_real_model",
        action="store_true",
        help=(
            "request real-model execution; currently refused because no human "
            "record authorizes qualification execution"
        ),
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.execute_real_model:
        return _refuse_execution()

    report = offline_preflight_report()
    failures = offline_preflight_failures()
    print(json.dumps(report, indent=2, sort_keys=True))
    print(
        f"Successor qualification driver: OFFLINE_PREFLIGHT "
        f"{'PASS' if not failures else 'FAIL'} ({len(failures)} failure(s)); "
        "QUALIFICATION_EXECUTION: NOT_AUTHORIZED; NO PROVIDER CONTACT"
    )
    return protocol.EXIT_OK if not failures else protocol.EXIT_PREFLIGHT_STOP


if __name__ == "__main__":
    raise SystemExit(main())
