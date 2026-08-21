"""Offline regressions for the Phase-D qualification verifier.

The verifier is the only machine gate standing between a tampered, truncated,
or partially rerun Phase-D artifact set and a printed "PASS", so every one of
its refusals is exercised here.  A verifier that fails open is worse than no
verifier, because it launders an unchecked artifact set as a checked one.

Everything is offline: no model is contacted and no provider is configured.
The recorded Phase-D artifacts are never mutated -- each negative case copies
the frozen set into ``tmp_path`` and mutates the copy.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from types import ModuleType
from typing import Any

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHASE_D_ROOT = PROJECT_ROOT / "results" / "phaseD-qualification"
PLAN = PROJECT_ROOT / "docs" / "phaseD_instrument_qualification_plan.md"
PLAN_SHA256 = PROJECT_ROOT / "docs" / "phaseD_instrument_qualification_plan.sha256"


def load_script(name: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Register before executing: @dataclass resolves annotations through
    # sys.modules, so a module absent from it cannot define a dataclass.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


verifier = load_script("analyze_phaseD_qualification")


pytestmark = pytest.mark.skipif(
    not (PHASE_D_ROOT / "preflight.json").exists(),
    reason="recorded Phase-D artifacts are not present in this checkout",
)


class Fixture:
    """A mutable copy of the frozen Phase-D artifact set."""

    def __init__(self, base: Path) -> None:
        self.base = base
        self.root = base / "raw"
        self.preflight = base / "preflight.json"
        self.plan = base / "plan.md"
        self.plan_sha256 = base / "plan.sha256"

    # -- accessors ---------------------------------------------------------
    def experiment_dirs(self) -> list[Path]:
        return sorted(path.parent for path in self.root.rglob("manifest.json"))

    def dir_for_arm(self, arm: str) -> Path:
        model, policy = verifier.EXPECTED_ARMS[arm]
        for directory in self.experiment_dirs():
            manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
            provider = manifest["provider"]
            if provider["model"] == model and provider["tool_contract_policy"] == policy:
                return directory
        raise AssertionError(f"no recorded experiment directory for arm {arm}")

    def rows(self, directory: Path) -> list[dict[str, Any]]:
        text = (directory / "runs.jsonl").read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def write_rows(self, directory: Path, rows: list[dict[str, Any]]) -> None:
        payload = "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
            for row in rows
        )
        (directory / "runs.jsonl").write_text(payload, encoding="utf-8", newline="\n")

    def patch_manifest(self, directory: Path, **changes: Any) -> None:
        path = directory / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest.update(changes)
        path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def patch_preflight(self, **changes: Any) -> None:
        record = json.loads(self.preflight.read_text(encoding="utf-8"))
        record.update(changes)
        self.preflight.write_text(
            json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def rewrite_plan(self, text: str) -> None:
        """Change the plan bytes WITHOUT updating the recorded frozen hash."""

        self.plan.write_text(text, encoding="utf-8", newline="\n")

    # -- execution ---------------------------------------------------------
    def verify(self) -> Any:
        return verifier.verify(
            root=self.root,
            plan=self.plan,
            plan_sha256=self.plan_sha256,
            preflight=self.preflight,
        )

    def main(self) -> int:
        return verifier.main(
            [
                "--root",
                str(self.root),
                "--plan",
                str(self.plan),
                "--plan-sha256",
                str(self.plan_sha256),
                "--preflight",
                str(self.preflight),
            ]
        )


@pytest.fixture
def artifacts(tmp_path: Path) -> Fixture:
    """Copy the frozen artifact set into tmp_path; never mutate the original."""

    base = tmp_path / "phaseD"
    base.mkdir()
    shutil.copytree(PHASE_D_ROOT / "raw", base / "raw")
    shutil.copy2(PHASE_D_ROOT / "preflight.json", base / "preflight.json")
    shutil.copy2(PLAN, base / "plan.md")
    shutil.copy2(PLAN_SHA256, base / "plan.sha256")
    return Fixture(base)


def assert_refused(result: Any, needle: str) -> None:
    assert result.verdict == "FAIL", f"expected FAIL, got {result.verdict}"
    assert result.exit_code != 0
    joined = "\n".join(result.failures)
    assert needle in joined, f"expected {needle!r} in violations:\n{joined}"


# ---------------------------------------------------------------------------
# The recorded artifact set must still pass.
# ---------------------------------------------------------------------------


def test_recorded_phase_d_artifacts_still_pass() -> None:
    """The frozen evidence, read in place, remains PASS with exit code 0."""

    result = verifier.verify(
        root=PHASE_D_ROOT / "raw",
        plan=PLAN,
        plan_sha256=PLAN_SHA256,
        preflight=PHASE_D_ROOT / "preflight.json",
    )
    assert result.failures == []
    assert result.verdict == "PASS"
    assert result.exit_code == 0
    assert len(result.runs) == verifier.EXPECTED_TOTAL_RUNS
    assert result.f1 and result.f2
    assert all(result.criteria.values())


def test_pass_exits_zero_and_writes_nothing_by_default(artifacts: Fixture) -> None:
    before = {
        path: path.read_bytes()
        for path in artifacts.base.rglob("*")
        if path.is_file()
    }
    assert artifacts.main() == 0
    after = {
        path: path.read_bytes()
        for path in artifacts.base.rglob("*")
        if path.is_file()
    }
    assert before == after, "verification must be read-only by default"


# ---------------------------------------------------------------------------
# Execution-matrix refusals.
# ---------------------------------------------------------------------------


def test_refuses_eight_runs(artifacts: Fixture) -> None:
    directory = artifacts.dir_for_arm("A")
    rows = artifacts.rows(directory)
    artifacts.write_rows(directory, rows[:-1])
    assert_refused(artifacts.verify(), "matrix violated")


def test_refuses_extra_tenth_run(artifacts: Fixture) -> None:
    directory = artifacts.dir_for_arm("A")
    rows = artifacts.rows(directory)
    extra = dict(rows[0])
    extra["run_id"] = f"{extra['run_id']}-extra"
    extra["seed"] = 999
    artifacts.write_rows(directory, [*rows, extra])
    assert_refused(artifacts.verify(), "matrix violated")


def test_refuses_rerun_experiment_directory(artifacts: Fixture) -> None:
    """A fourth directory -- an arm rerun -- is refused even if internally valid."""

    source = artifacts.dir_for_arm("B")
    shutil.copytree(source, artifacts.root / f"{source.name}-rerun")
    result = artifacts.verify()
    assert_refused(result, "experiment directories")
    assert any("rerun" in item or "same arm" in item for item in result.failures)


def test_refuses_missing_seed(artifacts: Fixture) -> None:
    directory = artifacts.dir_for_arm("C")
    rows = artifacts.rows(directory)
    rows[0]["seed"] = 4242
    artifacts.write_rows(directory, rows)
    assert_refused(artifacts.verify(), "seeds are")


def test_refuses_duplicate_seed(artifacts: Fixture) -> None:
    directory = artifacts.dir_for_arm("B")
    rows = artifacts.rows(directory)
    rows[1]["seed"] = rows[0]["seed"]
    artifacts.write_rows(directory, rows)
    assert_refused(artifacts.verify(), "seeds are")


def test_refuses_duplicate_run_id(artifacts: Fixture) -> None:
    directory = artifacts.dir_for_arm("C")
    rows = artifacts.rows(directory)
    rows[1]["run_id"] = rows[0]["run_id"]
    artifacts.write_rows(directory, rows)
    assert_refused(artifacts.verify(), "duplicate run_id")


def test_refuses_unknown_arm(artifacts: Fixture) -> None:
    directory = artifacts.dir_for_arm("A")
    rows = artifacts.rows(directory)
    for row in rows:
        row["model"] = "some-other-model:7b"
    artifacts.write_rows(directory, rows)
    assert_refused(artifacts.verify(), "unknown arm")


def test_refuses_wrong_policy_for_arm(artifacts: Fixture) -> None:
    """A row relabelled into another arm's policy breaks the frozen mapping."""

    directory = artifacts.dir_for_arm("C")
    rows = artifacts.rows(directory)
    rows[0]["tool_contract_policy"] = "trailing_user"
    artifacts.write_rows(directory, rows)
    assert_refused(artifacts.verify(), "matrix violated")


# ---------------------------------------------------------------------------
# Manifest execution-constraint refusals.
# ---------------------------------------------------------------------------


def test_refuses_incomplete_manifest_status(artifacts: Fixture) -> None:
    artifacts.patch_manifest(artifacts.dir_for_arm("A"), status="running")
    assert_refused(artifacts.verify(), "status=")


def test_refuses_record_count_mismatch(artifacts: Fixture) -> None:
    artifacts.patch_manifest(artifacts.dir_for_arm("B"), record_count=2)
    assert_refused(artifacts.verify(), "record_count=")


def test_refuses_nonzero_retry_limit(artifacts: Fixture) -> None:
    artifacts.patch_manifest(artifacts.dir_for_arm("B"), infrastructure_retry_limit=1)
    assert_refused(artifacts.verify(), "infrastructure_retry_limit=")


def test_refuses_wrong_experiment_kind(artifacts: Fixture) -> None:
    artifacts.patch_manifest(artifacts.dir_for_arm("C"), experiment_kind="real_model_pilot")
    assert_refused(artifacts.verify(), "experiment_kind=")


def test_refuses_unexpected_treatment(artifacts: Fixture) -> None:
    artifacts.patch_manifest(artifacts.dir_for_arm("A"), treatments=["off", "full"])
    assert_refused(artifacts.verify(), "treatments=")


# ---------------------------------------------------------------------------
# Frozen-plan-boundary and preflight refusals (criterion H4 included).
# ---------------------------------------------------------------------------


def test_refuses_missing_preflight(artifacts: Fixture) -> None:
    artifacts.preflight.unlink()
    assert_refused(artifacts.verify(), "preflight record is missing")


def test_refuses_preflight_without_arm_provenance(artifacts: Fixture) -> None:
    record = json.loads(artifacts.preflight.read_text(encoding="utf-8"))
    del record["arms"]["B"]
    artifacts.preflight.write_text(json.dumps(record), encoding="utf-8")
    assert_refused(artifacts.verify(), "no provenance for arm B")


def test_refuses_incomplete_runtime_provenance(artifacts: Fixture) -> None:
    record = json.loads(artifacts.preflight.read_text(encoding="utf-8"))
    record["arms"]["C"]["runtime_provenance"]["template_sha256"] = None
    artifacts.preflight.write_text(json.dumps(record), encoding="utf-8")
    result = artifacts.verify()
    assert_refused(result, "runtime provenance is incomplete")
    assert result.criteria["H4"] is False


def test_refuses_provenance_probe_error(artifacts: Fixture) -> None:
    record = json.loads(artifacts.preflight.read_text(encoding="utf-8"))
    record["arms"]["A"]["runtime_provenance"]["probe_error"] = "URLError"
    artifacts.preflight.write_text(json.dumps(record), encoding="utf-8")
    result = artifacts.verify()
    assert_refused(result, "probe_error=")
    assert result.criteria["H4"] is False


def test_refuses_provenance_naming_a_different_model(artifacts: Fixture) -> None:
    record = json.loads(artifacts.preflight.read_text(encoding="utf-8"))
    record["arms"]["C"]["runtime_provenance"]["model_identifier"] = "qwen3:32b"
    artifacts.preflight.write_text(json.dumps(record), encoding="utf-8")
    assert_refused(artifacts.verify(), "identifies model")


def test_refuses_provenance_complete_false(artifacts: Fixture) -> None:
    """H4 must participate in the verdict, not merely be printed."""

    artifacts.patch_preflight(provenance_complete=False)
    result = artifacts.verify()
    assert_refused(result, "provenance_complete=true")
    assert result.criteria["H4"] is False


def test_refuses_recorded_inference_in_preflight(artifacts: Fixture) -> None:
    artifacts.patch_preflight(inference_performed=True)
    assert_refused(artifacts.verify(), "inference_performed=false")


def test_refuses_plan_hash_mismatch(artifacts: Fixture) -> None:
    """Editing the frozen plan without its hash is refused."""

    artifacts.rewrite_plan(artifacts.plan.read_text(encoding="utf-8") + "\nedited\n")
    assert_refused(artifacts.verify(), "does not match its frozen hash")


def test_refuses_preflight_plan_hash_disagreement(artifacts: Fixture) -> None:
    """Re-freezing the plan after the fact cannot launder the preflight record."""

    edited = artifacts.plan.read_text(encoding="utf-8") + "\nedited after the runs\n"
    artifacts.rewrite_plan(edited)
    digest = hashlib.sha256(artifacts.plan.read_bytes()).hexdigest()
    artifacts.plan_sha256.write_text(f"{digest}  plan.md\n", encoding="utf-8")
    assert_refused(artifacts.verify(), "does not match the plan on disk")


def test_refuses_missing_plan_hash_file(artifacts: Fixture) -> None:
    artifacts.plan_sha256.unlink()
    assert_refused(artifacts.verify(), "frozen plan hash file is missing")


def test_refuses_wrong_preflight_instrument_version(artifacts: Fixture) -> None:
    artifacts.patch_preflight(instrument_version="1")
    assert_refused(artifacts.verify(), "preflight instrument_version=")


def test_refuses_wrong_preflight_adapter_version(artifacts: Fixture) -> None:
    artifacts.patch_preflight(native_tool_adapter_version="native-tools-adapter-1")
    assert_refused(artifacts.verify(), "preflight native_tool_adapter_version=")


# ---------------------------------------------------------------------------
# Per-run criterion refusals.
# ---------------------------------------------------------------------------


def test_refuses_pre_repair_instrument_version_on_a_row(artifacts: Fixture) -> None:
    directory = artifacts.dir_for_arm("A")
    rows = artifacts.rows(directory)
    rows[0]["instrument_version"] = "1"
    artifacts.write_rows(directory, rows)
    assert_refused(artifacts.verify(), "H5 violated")


def test_refuses_repair_applied_to_the_healthy_arm(artifacts: Fixture) -> None:
    directory = artifacts.dir_for_arm("C")
    rows = artifacts.rows(directory)
    rows[0]["provider_attempts"][1]["tool_contract_refreshed"] = True
    artifacts.write_rows(directory, rows)
    assert_refused(artifacts.verify(), "H2 violated")


def test_refuses_repaired_arm_losing_the_contract(artifacts: Fixture) -> None:
    directory = artifacts.dir_for_arm("B")
    rows = artifacts.rows(directory)
    rows[0]["provider_attempts"][2]["tool_contract_refreshed"] = False
    artifacts.write_rows(directory, rows)
    assert_refused(artifacts.verify(), "H1 violated")


def test_refuses_protocol_failure_class(artifacts: Fixture) -> None:
    directory = artifacts.dir_for_arm("B")
    rows = artifacts.rows(directory)
    rows[0]["failure_class"] = "invalid_tool_call"
    artifacts.write_rows(directory, rows)
    assert_refused(artifacts.verify(), "H3 violated")


def test_refuses_unclassified_failure(artifacts: Fixture) -> None:
    directory = artifacts.dir_for_arm("C")
    rows = artifacts.rows(directory)
    rows[0]["error"] = "something went wrong"
    rows[0]["failure_class"] = None
    artifacts.write_rows(directory, rows)
    assert_refused(artifacts.verify(), "unclassified failure")


def test_refuses_silent_pending_action_loss(artifacts: Fixture) -> None:
    directory = artifacts.dir_for_arm("B")
    rows = artifacts.rows(directory)
    rows[0]["queued_action_count"] = 2
    artifacts.write_rows(directory, rows)
    assert_refused(artifacts.verify(), "queued action")


def test_refuses_diverging_diagnostic_input(artifacts: Fixture) -> None:
    directory = artifacts.dir_for_arm("A")
    rows = artifacts.rows(directory)
    for row in rows:
        row["user_prompt_sha256"] = "0" * 64
    artifacts.write_rows(directory, rows)
    assert_refused(artifacts.verify(), "byte-identical")


def test_refuses_missing_evidence_fragment(artifacts: Fixture) -> None:
    directory = artifacts.dir_for_arm("B")
    trace = directory / artifacts.rows(directory)[0]["trace_path"]
    trace.unlink()
    assert_refused(artifacts.verify(), "evidence fragment is missing")


def test_refuses_missing_artifact_root(artifacts: Fixture) -> None:
    shutil.rmtree(artifacts.root)
    assert_refused(artifacts.verify(), "artifact root is missing")


# ---------------------------------------------------------------------------
# Exit-status contract: the verifier must never fail open.
# ---------------------------------------------------------------------------


def test_fail_returns_nonzero_exit_code(artifacts: Fixture) -> None:
    artifacts.patch_preflight(provenance_complete=False)
    assert artifacts.verify().verdict == "FAIL"
    assert artifacts.main() == verifier.EXIT_FAIL
    assert verifier.EXIT_FAIL != 0


def test_inconclusive_returns_nonzero_exit_code(artifacts: Fixture) -> None:
    """A protocol-correct set that never demonstrated the chain must not exit 0."""

    directory = artifacts.dir_for_arm("C")
    rows = artifacts.rows(directory)
    for row in rows:
        # Drop the executed reads without disturbing any hard criterion: the
        # evidence fragment becomes an empty, still-valid trace.
        (directory / row["trace_path"]).write_text("", encoding="utf-8")
    artifacts.write_rows(directory, rows)

    result = artifacts.verify()
    assert result.failures == [], f"unexpected hard failures: {result.failures}"
    assert result.f1 is True
    assert result.f2 is False
    assert result.verdict == "INCONCLUSIVE"
    assert result.exit_code == verifier.EXIT_INCONCLUSIVE
    assert verifier.EXIT_INCONCLUSIVE != 0
    assert artifacts.main() == verifier.EXIT_INCONCLUSIVE


def test_exit_codes_are_distinct_and_only_pass_is_zero() -> None:
    assert verifier.EXIT_PASS == 0
    assert verifier.EXIT_FAIL != 0
    assert verifier.EXIT_INCONCLUSIVE != 0
    assert verifier.EXIT_FAIL != verifier.EXIT_INCONCLUSIVE


def test_short_circuited_criteria_never_read_as_pass(
    artifacts: Fixture, capsys: pytest.CaptureFixture[str]
) -> None:
    """An artifact error must not leave later criteria printing PASS."""

    artifacts.preflight.unlink()
    assert artifacts.main() == verifier.EXIT_FAIL
    output = capsys.readouterr().out
    assert "NOT EVALUATED" in output
    assert "QUALIFICATION VERDICT: FAIL" in output
