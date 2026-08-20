#!/usr/bin/env python3
"""Phase-D provider runtime preflight.  Collects provenance; makes NO inference call.

This runs before the first Phase-D model call.  It records the runtime identity
Phase B could not establish (Ollama version, model digest, chat-template hash,
capabilities) for every configured Phase-D provider slot, together with the
instrument versions, the git HEAD, and the frozen qualification-plan hash.

Qualification STOPS here (non-zero exit) when the expected local models or
runtime cannot be identified sufficiently for reproducibility, so that no
inference is spent on an unidentifiable environment.

Only Ollama metadata endpoints (/api/version, /api/show, /api/tags) are
contacted; see ``iqa_soa.agent.providers.probe_runtime_provenance``.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from iqa_soa.agent.providers import (  # noqa: E402
    OpenAICompatibleProvider,
    probe_runtime_provenance,
)
from iqa_soa.experiment.runner import load_provider  # noqa: E402
from iqa_soa.instrument import (  # noqa: E402
    INSTRUMENT_VERSION,
    NATIVE_TOOL_ADAPTER_VERSION,
)

# Every field that must be identifiable for the environment to be reproducible
# (plan criterion H4).
REQUIRED_PROVENANCE_FIELDS = (
    "runtime",
    "runtime_version",
    "model_identifier",
    "model_digest",
    "template_sha256",
    "capabilities",
)

ARMS = {
    "A": "mistral_none",
    "B": "mistral_trailing_user",
    "C": "qwen_none",
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models", default=str(PROJECT_ROOT / "configs" / "phaseD-models.yaml")
    )
    parser.add_argument(
        "--plan",
        default=str(PROJECT_ROOT / "docs" / "phaseD_instrument_qualification_plan.md"),
    )
    parser.add_argument(
        "--out",
        default=str(
            PROJECT_ROOT / "results" / "phaseD-qualification" / "preflight.json"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan_path = Path(args.plan)
    frozen_hash_path = plan_path.with_suffix(".sha256")

    plan_sha256 = _sha256_file(plan_path)
    frozen_declared = frozen_hash_path.read_text(encoding="utf-8").split()[0]
    if plan_sha256 != frozen_declared:
        print(
            "STOP: qualification plan does not match its frozen hash "
            f"(computed={plan_sha256}, frozen={frozen_declared})",
            file=sys.stderr,
        )
        return 2

    record: dict[str, object] = {
        "phase": "D",
        "purpose": "engineering instrument qualification (non-scientific)",
        "collected_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "inference_performed": False,
        "git_head": _git("rev-parse", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_status_clean": _git("status", "--porcelain") == "",
        "qualification_plan_path": plan_path.relative_to(PROJECT_ROOT).as_posix(),
        "qualification_plan_sha256": plan_sha256,
        "instrument_version": INSTRUMENT_VERSION,
        "native_tool_adapter_version": NATIVE_TOOL_ADAPTER_VERSION,
        "models_config_sha256": _sha256_file(Path(args.models)),
        "arms": {},
    }

    incomplete: list[str] = []
    arms: dict[str, object] = {}
    for arm, slot in sorted(ARMS.items()):
        provider = load_provider(args.models, provider_name=slot)
        if not isinstance(provider, OpenAICompatibleProvider):
            print(f"STOP: arm {arm} slot {slot} is not an HTTP provider", file=sys.stderr)
            return 2
        provenance = probe_runtime_provenance(provider.endpoint, provider.model)
        missing = [
            field
            for field in REQUIRED_PROVENANCE_FIELDS
            if provenance.get(field) in (None, "", [])
        ]
        if provenance.get("probe_error") is not None:
            missing.append(f"probe_error={provenance['probe_error']}")
        if missing:
            incomplete.append(f"{arm}/{slot}: {missing}")
        arms[arm] = {
            "provider_slot": slot,
            "descriptor": provider.descriptor(),
            "runtime_provenance": provenance,
            "missing_provenance_fields": missing,
        }
    record["arms"] = arms
    record["provenance_complete"] = not incomplete

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True))

    if incomplete:
        print(
            "STOP: runtime provenance is insufficient for reproducibility:\n- "
            + "\n- ".join(incomplete),
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
