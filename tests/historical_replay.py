"""Replay lifecycle-bound pytest modules at the exact Git state they assert.

These modules test prospective absence, authorization, or freeze conditions
that correctly ceased to hold after the corresponding one-shot transition.
Running their unchanged blobs against today's checkout makes valid historical
evidence look like a regression.  A detached worktree preserves every original
assertion while binding it to the commit whose state the assertion describes.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


_CROSS_RUNTIME_QUALIFICATION_CONTRACT = r'''\
from pathlib import Path
import sys
import tempfile

root = Path.cwd()
sys.path[:0] = [str(root / "src"), str(root / "scripts")]

import run_successor_qualification as driver
import successor_qualification_protocol as protocol

evidence = driver.load_runtime_evidence()
captured = {
    slot: driver.capture_stratum_runtime_snapshot(slot)
    for slot in evidence.identity
}
if all(
    captured[slot].runtime_identity_digest == expected
    for slot, expected in evidence.identity.items()
):
    print("CANONICAL_RUNTIME_MATCH")
    raise SystemExit(0)

assert all(
    captured[slot].runtime_identity_digest != expected
    for slot, expected in evidence.identity.items()
)

def probe(model):
    return driver.RuntimeMetadata(
        runtime_version=protocol.EXPECTED_RUNTIME_VERSION,
        model_present=True,
        model_digest=protocol.EXPECTED_MODEL_DIGEST[model],
    )

failures, observations = driver.environment_preflight(
    evidence=evidence,
    probe=probe,
    capture=driver.capture_stratum_runtime_snapshot,
)
assert len(failures) == len(evidence.identity)
assert all("ENVIRONMENT_HOLD" in item for item in failures)
assert all("RESTORE_FROZEN_RUNTIME" in item for item in failures)
assert observations["environment_hold"] is True
assert all(
    observations["strata"][slot]["fresh_runtime_identity_digest"]
    == captured[slot].runtime_identity_digest
    and observations["strata"][slot]["canonical_runtime_identity_digest"]
    == evidence.identity[slot]
    and "runtime_identity_match" not in observations["strata"][slot]
    for slot in evidence.identity
)

calls = []
with tempfile.TemporaryDirectory(prefix="iqa-soa-cross-runtime-") as raw:
    output = Path(raw) / "out"

    def execute_cell(cell):
        calls.append(cell.key)
        raise AssertionError("environment hold failed to stop before cell execution")

    code = driver.execute_offline_bound_run(
        config_path=root / protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE,
        manifest_path=root / protocol.CANONICAL_MANIFEST_RELATIVE,
        output_root=output,
        env={protocol.CREDENTIAL_ENV: "offline-seam-not-a-real-credential"},
        probe=probe,
        capture=driver.capture_stratum_runtime_snapshot,
        execute_cell=execute_cell,
    )
    assert code == protocol.EXIT_ENVIRONMENT_HOLD
    assert calls == []
    assert not output.exists()

print("NONCANONICAL_RUNTIME_FAIL_CLOSED")
'''


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def replay_historical_pytest(
    *,
    commit: str,
    module_path: str,
    blob_id: str,
    expected_tests: int,
    worktree: Path,
    canonical_runtime_bound: bool = False,
) -> None:
    """Execute an immutable historical test blob in its matching repository."""

    observed_blob = _git("rev-parse", f"{commit}:{module_path}")
    assert observed_blob.returncode == 0, (
        "historical commit/blob is unavailable; CI must fetch full history "
        "and required immutable evidence refs:\n"
        + observed_blob.stderr
    )
    assert observed_blob.stdout.strip() == blob_id

    # Windows' legacy MAX_PATH limit is otherwise exceeded by the retained
    # per-cell evidence paths. Keep the checkout root deliberately short.
    token = hashlib.sha256(
        f"{commit}|{module_path}|{worktree}".encode("utf-8")
    ).hexdigest()[:12]
    worktree_parent = ROOT / ".historical-worktrees"
    worktree = worktree_parent / token
    add = _git("worktree", "add", "--detach", "--quiet", str(worktree), commit)
    assert add.returncode == 0, add.stdout + add.stderr
    try:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        collect = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                module_path,
            ],
            cwd=worktree,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert collect.returncode == 0, collect.stdout + collect.stderr
        match = re.search(r"(\d+) tests? collected", collect.stdout)
        assert match is not None, collect.stdout
        assert int(match.group(1)) == expected_tests, collect.stdout

        if canonical_runtime_bound:
            contract = subprocess.run(
                [sys.executable, "-B", "-c", _CROSS_RUNTIME_QUALIFICATION_CONTRACT],
                cwd=worktree,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            assert contract.returncode == 0, contract.stdout + contract.stderr
            marker = contract.stdout.strip().splitlines()[-1]
            assert marker in {
                "CANONICAL_RUNTIME_MATCH",
                "NONCANONICAL_RUNTIME_FAIL_CLOSED",
            }, contract.stdout
            if marker == "NONCANONICAL_RUNTIME_FAIL_CLOSED":
                return

        run = subprocess.run(
            [sys.executable, "-B", "-m", "pytest", "-q", module_path],
            cwd=worktree,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert run.returncode == 0, run.stdout + run.stderr
        match = re.search(r"(\d+) passed", run.stdout)
        assert match is not None, run.stdout
        assert int(match.group(1)) == expected_tests, run.stdout
    finally:
        remove = _git("worktree", "remove", "--force", str(worktree))
        assert remove.returncode == 0, remove.stdout + remove.stderr
        try:
            worktree_parent.rmdir()
        except OSError:
            pass
