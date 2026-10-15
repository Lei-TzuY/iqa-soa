"""Read-only audit of the original fse2027 external archive (no acquisition).

Run with the original environment: python -B archive_recovery_audit.py REPO_ROOT.
Only stdout is written. Original files, reports, registrations and gates remain
untouched. This reproduces statistics on recorded outcomes, not their oracles.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import socket
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

STUDY = "fse2027-external-replication-v1"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def lines(path):
    return [json.loads(line, object_pairs_hook=unique_object)
            for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory(root, suffix=None):
    files = {p.relative_to(root).as_posix(): file_digest(p)
             for p in sorted(root.rglob("*"))
             if p.is_file() and "__pycache__" not in p.parts
             and (suffix is None or p.suffix == suffix)}
    return {"files": len(files), "sha256": digest(files)}, files


def self_digest(record, field):
    require(record.get(field) == digest({k: v for k, v in record.items() if k != field}),
            f"self-digest mismatch: {field}")


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def audit_stage(study, stage, schedule, models):
    rows = lines(study / stage / "runs.jsonl")
    require([s["position"] for s in schedule] == list(range(len(schedule))),
            f"{stage}: schedule positions")
    require([r["position"] for r in rows] == list(range(len(schedule))),
            f"{stage}: missing, duplicate or reordered terminal records")
    expected_dirs = set()
    raw_hashes, evidence_hashes, model_counts, request_counts = {}, {}, Counter(), Counter()
    for row, slot in zip(rows, schedule):
        for key in ("stage", "model", "arm", "seed", "position"):
            require(row[key] == slot[key], f"{stage}/{row['position']}: {key}")
        for key in ("cell_id", "kind", "suite", "user_task", "injection_task"):
            require(row[key] == slot["cell"][key], f"{stage}/{row['position']}: {key}")
        if stage == "confirmatory":
            require(row["pair_id"] == slot["pair_id"], "pair identity mismatch")
        require(row["study_id"] == STUDY and row["validity"] == "VALID",
                "this recovery audit requires the reported complete VALID archive")
        require(row["model_tag"] == models[row["model"]]["tag"]
                and row["model_digest"] == models[row["model"]]["digest"],
                "recorded model identity mismatch")
        require(timestamp(row["started_utc"]) <= timestamp(row["finished_utc"]),
                "terminal time precedes start")
        for field in ("native_utility", "native_security", "attack_observed",
                      "cpe_executed", "cpe_proposed"):
            if row.get(field) is not None:
                require(type(row[field]) is bool, f"non-boolean outcome: {field}")
        name = f"{row['position']:05d}-{row['model']}-{row['arm']}"
        expected_dirs.add(name)
        cell = study / stage / "cells" / name
        require({p.name for p in cell.iterdir()} == {"raw.json", "evidence.jsonl"},
                f"{stage}/{name}: missing or unexpected cell file")
        raw = load(cell / "raw.json")
        require(raw["record"] == row, f"{stage}/{name}: raw/terminal record mismatch")
        evidence = lines(cell / "evidence.jsonl")
        proposals, telemetry = raw["proposals"], raw["telemetry"]
        effects = [p for p in proposals if p.get("class") == "EFFECT"]
        # Count rules copied from the hash-verified original cell.py; no labels
        # or outcomes are supplied by the recovery auditor.
        counts = {
            "n_model_requests": len(telemetry), "n_tool_proposals": len(proposals),
            "n_effect_proposals": len(effects),
            "n_effect_executed": sum(bool(p.get("executed")) for p in effects),
            "n_blocked": sum(str(p.get("disposition", "")).startswith("NOT_DISPATCHED")
                             for p in proposals),
            "n_unknown_tool": sum(p.get("disposition") == "UNKNOWN_TOOL" for p in proposals),
            "prompt_tokens_total": sum(t.get("prompt_tokens") or 0 for t in telemetry),
            "completion_tokens_total": sum(t.get("completion_tokens") or 0 for t in telemetry),
        }
        for key, value in counts.items():
            require(row[key] == value, f"{stage}/{name}: count mismatch {key}")
        proposal_ids = [p["evidence_id"] for p in proposals if p.get("evidence_id")]
        evidence_ids = [e["evidence_id"] for e in evidence]
        require(len(evidence_ids) == len(set(evidence_ids)), "duplicate cell evidence id")
        require(proposal_ids == evidence_ids, f"{stage}/{name}: proposal/evidence links")
        raw_hashes[name + "/raw.json"] = file_digest(cell / "raw.json")
        evidence_hashes[name + "/evidence.jsonl"] = file_digest(cell / "evidence.jsonl")
        model_counts[row["model"]] += 1
        request_counts[row["model"]] += len(telemetry)
    require({p.name for p in (study / stage / "cells").iterdir()} == expected_dirs,
            f"{stage}: unexpected/missing cell directory")
    ledger = lines(study / stage / "ledger.jsonl")
    started = [e for e in ledger if e["event"] == "STARTED"]
    terminal = [e for e in ledger if e["event"] == "TERMINAL"]
    complete = [e for e in ledger if e["event"] == "COMPLETE"]
    require([e["position"] for e in started] == list(range(len(rows)))
            and [e["position"] for e in terminal] == list(range(len(rows))),
            f"{stage}: ledger omissions, retries or duplicates")
    require(len(complete) == 1 and complete[0]["terminal"] == len(rows),
            f"{stage}: missing completion marker")
    for row, start, end in zip(rows, started, terminal):
        require(all(start[k] == row[k] for k in ("position", "model", "arm", "cell_id"))
                and end["validity"] == row["validity"], "ledger identity/status mismatch")
        require(timestamp(start["utc"]) <= timestamp(end["utc"]), "ledger chronology")
    return rows, {
        "scheduled": len(schedule), "terminal_records": len(rows),
        "raw_record_bindings": len(rows), "proposal_evidence_bindings": len(rows),
        "all_valid_as_recorded": True, "model_counts": dict(model_counts),
        "retained_model_requests": dict(request_counts),
        "ledger_events": dict(Counter(e["event"] for e in ledger)),
        "raw_files": {"files": len(raw_hashes), "sha256": digest(raw_hashes)},
        "evidence_files": {"files": len(evidence_hashes), "sha256": digest(evidence_hashes)},
    }


def independent_estimates(rows, eligibility, reproduced):
    pairs = defaultdict(dict)
    for row in rows:
        key = row["model"], row["cell_id"]
        require(row["arm"] not in pairs[key], "duplicate pair arm")
        pairs[key][row["arm"]] = row
    for arms in pairs.values():
        require(set(arms) == {"off", "full"}, "missing arm")
        require(arms["off"]["seed"] == arms["full"]["seed"]
                and arms["off"]["pair_id"] == arms["full"]["pair_id"], "unpaired seed")
    out = {}
    endpoints = [("primary_cpe_executed", "security", "cpe_executed", True),
                 ("S1_native_attack_success", "security", "native_security", False),
                 ("S2_benign_utility", "benign", "native_utility", False),
                 ("S3_utility_under_attack", "security", "native_utility", False)]
    for name, kind, field, restricted in endpoints:
        units = defaultdict(lambda: defaultdict(list))
        for (model, _), arms in pairs.items():
            off, full = arms["off"], arms["full"]
            if off["kind"] != kind:
                continue
            unit = f"{off['suite']}/{off['injection_task'] if kind == 'security' else off['user_task']}"
            if restricted and unit not in eligibility[model]:
                continue
            if restricted:
                require(type(off.get(field)) is bool and type(full.get(field)) is bool,
                        "missing eligible primary outcome")
            units[model][unit].append(Fraction(int(bool(full.get(field))) - int(bool(off.get(field)))))
        strata = {}
        for model, values in units.items():
            if kind == "security":
                require(all(len(v) == 4 for v in values.values()), "incomplete four-carrier goal")
            means = [sum(v) / len(v) for v in values.values()]
            strata[model] = {"estimate": str(sum(means) / len(means)), "units": len(means)}
        estimate = sum(Fraction(s["estimate"]) for s in strata.values()) / len(strata)
        ref = reproduced[name] if name == "primary_cpe_executed" else reproduced["secondary"][name]
        require(abs(float(estimate) - ref["estimate"]) < 1e-15, "independent estimate mismatch")
        out[name] = {"estimate_exact": str(estimate), "estimate": float(estimate), "strata": strata}
    return out


def audit(root):
    sys.dont_write_bytecode = True
    root = root.resolve()
    study = root / "results" / STUDY
    started = datetime.now(timezone.utc).isoformat()
    before, before_files = inventory(study)
    manifest = load(study / "freeze-manifest.json")
    self_digest(manifest, "manifest_sha256")
    for section in ("code", "study_documents"):
        for rel, expected in manifest["frozen"][section].items():
            path = (root / rel).resolve()
            require(path.is_relative_to(root), "frozen path escapes root")
            require(file_digest(path) == expected, f"frozen hash drift: {rel}")
    sys.path.insert(0, str(root / "scripts"))
    from fse2027_ext import analysis, constants, freeze, population

    freeze.verify(root, manifest)
    frozen_before = freeze.collect(root)
    require(sys.version.split()[0] == manifest["frozen"]["python"], "Python version drift")
    require(importlib.metadata.version("agentdojo") == manifest["agentdojo"]["package_version"],
            "AgentDojo package version drift")
    pop = load(study / "population.json")
    require(population.build_population() == pop, "installed benchmark population differs")
    qs = load(study / "qualification-schedule.json")
    cs = load(study / "registration/confirmatory-schedule.json")
    require(population.qualification_schedule(pop) == qs, "qualification assignment differs")
    require(population.confirmatory_schedule(pop) == cs, "confirmatory assignment differs")
    qual, qualification_audit = audit_stage(study, "qualification", qs, constants.MODELS)
    conf, confirmatory_audit = audit_stage(study, "confirmatory", cs, constants.MODELS)
    decision = load(study / "qualification-decision.json")
    self_digest(decision, "record_sha256")
    require(decision["runs_sha256"] == file_digest(study / "qualification/runs.jsonl"),
            "qualification decision is not bound to these runs")
    qualification = analysis.analyze_qualification(qual, qs)
    metadata_keys = {"freeze_manifest_sha256", "runs_sha256", "created_at_utc", "record_sha256"}
    require(set(decision) == set(qualification) | metadata_keys, "qualification schema differs")
    require(canonical(qualification) == canonical({k: decision[k] for k in qualification}),
            "saved qualification result differs")
    stages = {name: load(study / f"registration/stage-{name}.json") for name in ("a", "b", "c")}
    for record in stages.values():
        self_digest(record, "record_sha256")
        require(record["freeze_manifest_sha256"] == manifest["manifest_sha256"]
                and record["qualification_decision_sha256"] == decision["record_sha256"],
                "registration input reference mismatch")
    require(decision["freeze_manifest_sha256"] == manifest["manifest_sha256"], "decision freeze ref")
    require(stages["a"]["population_sha256"] == file_digest(study / "population.json"), "population ref")
    require(stages["b"]["stage-a_sha256"] == stages["a"]["record_sha256"]
            and stages["c"]["stage-b_sha256"] == stages["b"]["record_sha256"], "registration chain")
    require(stages["b"]["eligibility"] == qualification["stage_b_eligibility"], "eligibility mismatch")
    require(stages["c"]["confirmatory_schedule_sha256"] == file_digest(study / "registration/confirmatory-schedule.json")
            and stages["c"]["analysis_plan_sha256"] == file_digest(study / "analysis-plan.json"), "stage C input refs")
    require(stages["c"]["K_eligible_units"] == {m: len(v) for m, v in stages["b"]["eligibility"].items()}
            and stages["c"]["n_scheduled_executions"] == len(cs), "stage C counts")
    times = [timestamp(stages[n]["created_at_utc"]) for n in ("a", "b", "c")]
    require(times == sorted(times) and max(timestamp(r["finished_utc"]) for r in qual) <= times[0]
            and times[-1] <= min(timestamp(r["started_utc"]) for r in conf), "recorded phase chronology")
    reproduced = analysis.analyze_confirmatory(conf, stages["b"]["eligibility"])
    saved = load(study / "confirmatory-analysis.json")
    self_digest(saved, "record_sha256")
    require(set(saved) == set(reproduced) | metadata_keys, "confirmatory schema differs")
    require(saved["freeze_manifest_sha256"] == manifest["manifest_sha256"]
            and saved["runs_sha256"] == file_digest(study / "confirmatory/runs.jsonl"),
            "saved confirmatory report input references differ")
    require(canonical(reproduced) == canonical({k: saved[k] for k in reproduced}),
            "saved confirmatory result differs")
    independent = independent_estimates(conf, stages["b"]["eligibility"], reproduced)
    after, after_files = inventory(study)
    freeze.verify(root, manifest)
    require(before_files == after_files and frozen_before == freeze.collect(root),
            "source changed during read-only recovery: stop and re-audit")
    control_hashes = {p: h for p, h in before_files.items() if "/cells/" not in p}
    return {
        "audit": "research-cycle-e-recovery", "status": "PASS", "study_id": STUDY,
        "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "hash-bound archive integrity and numerical reproduction of recorded outcomes",
        "auditor_source_sha256": globals().get("AUDITOR_SOURCE_SHA256") or file_digest(Path(__file__)),
        "python": sys.version.split()[0],
        "packages": {p: importlib.metadata.version(p) for p in ("numpy", "agentdojo")},
        "freeze_manifest_sha256": manifest["manifest_sha256"], "frozen_inputs": frozen_before,
        "archive_before": before, "archive_after": after, "sources_unchanged": True,
        "control_file_sha256": control_hashes,
        "qualification": qualification_audit, "qualification_verdict": qualification["verdict"],
        "eligible_goals": {m: len(v) for m, v in stages["b"]["eligibility"].items()},
        "confirmatory": confirmatory_audit, "complete_pairs": len(conf) // 2,
        "registration_self_digests_and_references": "PASS",
        "recorded_phase_order": "PASS (internal timestamps only)",
        "population_and_schedules_regenerated": "PASS",
        "qualification_reproduction": "EXACT", "confirmatory_reproduction": "EXACT",
        "independent_rational_estimates": independent, "reproduced_analysis": reproduced,
        "limitations": [
            "CPE/native outcome labels are recorded labels; independent environment/oracle replay was not executed.",
            "Self-digests and local timestamps do not establish an externally anchored prospective registration.",
            "Original request payloads cannot be reconstructed from payload hashes alone.",
            "No new provider/GPU calls, retries, replacement records or synthetic empirical records were generated.",
            "Frozen internal FSE HOLD gates and QA/ICST held-out-corpus requirements remain unchanged.",
        ],
    }


def main():
    # Block accidental network acquisition for the whole auditor process.
    def no_network(*args, **kwargs):
        raise RuntimeError("network disabled in archive recovery auditor")

    socket.socket.connect = no_network
    socket.socket.connect_ex = no_network
    try:
        result = audit(Path(sys.argv[1]))
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
