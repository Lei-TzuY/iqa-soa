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
) -> None:
    """Execute an immutable historical test blob in its matching repository."""

    observed_blob = _git("rev-parse", f"{commit}:{module_path}")
    assert observed_blob.returncode == 0, (
        "historical commit/blob is unavailable; CI must fetch full history:\n"
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
