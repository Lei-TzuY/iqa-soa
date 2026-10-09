"""Synthetic checker regressions only. No synthetic observations are paper evidence."""
from __future__ import annotations

import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from records_audit import EvidenceError, FIELDS, MODELS, audit_bundle, infer, macro_mean, parse_json, sha, units_for_endpoint
from upstream_audit import ROOT, collect_tasks, source_audit
from prepare_bundle import prepare


class AuditTests(unittest.TestCase):
    def test_pinned_source_inventory_includes_combinations_and_updates(self):
        audit = source_audit()
        self.assertEqual(audit["totals"]["combined_user_tasks"], 11)
        self.assertEqual(audit["totals"]["user_tasks"], 97)
        self.assertEqual(audit["totals"]["cartesian_user_goal_pairs"], 949)
        trace = [r for r in audit["goals"] if r["boundary"] == "proposed_call_trace"]
        text = [r for r in audit["goals"] if r["boundary"] == "model_text"]
        self.assertEqual([(r["suite"], r["goal"]) for r in trace], [("slack", "injection_task_5")])
        self.assertEqual([(r["suite"], r["goal"]) for r in text], [("travel", "injection_task_6")])

    def test_version_update_wins_and_combination_adds_one_unit(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            old = base / "v1/banking"
            new = base / "v1_2_2/banking"
            old.mkdir(parents=True)
            new.mkdir(parents=True)
            (old / "user_tasks.py").write_text(
                "@task_suite.register_user_task\nclass UserTask0(Base):\n pass\n"
                "@task_suite.register_user_task\nclass UserTask1(Base):\n pass\n"
                "combinator.create_combined_task('UserTask2', a, b)\n")
            (new / "user_tasks.py").write_text(
                "@task_suite.update_user_task((1,2,2))\nclass UserTask0(Base):\n value=7\n")
            tasks = collect_tasks(base)
            self.assertEqual(len(tasks), 3)
            self.assertEqual(tasks[("banking", "UserTask", 0)]["version"], (1, 2, 2))
            self.assertTrue(tasks[("banking", "UserTask", 2)]["combined"])
            node = tasks[("banking", "UserTask", 0)]["node"]
            self.assertIsInstance(node, ast.ClassDef)

    @staticmethod
    def paired_rows():
        rows = []
        for model in MODELS:
            for goal in ("a", "b"):
                for carrier in range(4):
                    for arm in ("OFF", "FULL"):
                        rows.append({"phase": "confirm", "model": model, "kind": "attack",
                                     "suite": "banking", "goal": goal, "user_task": f"user{carrier}",
                                     "seed": 11, "arm": arm,
                                     "protected_effect_executed": arm == "OFF" and goal == "a"})
        eligible = {model: [["banking", "a"], ["banking", "b"]] for model in MODELS}
        return rows, eligible

    def test_carriers_are_nested_in_goals_and_macro_mean_weights_strata(self):
        rows, eligible = self.paired_rows()
        strata = units_for_endpoint(rows, eligible, "protected_effect_executed", "eligible")
        self.assertEqual({k: len(v) for k, v in strata.items()}, {m: 2 for m in MODELS})
        self.assertEqual(macro_mean(strata), -.5)
        self.assertEqual(macro_mean({"one": [1.0], "two": [0.0] * 9}), .5)

    def test_duplicate_missing_and_mismatched_seed_pairs_fail(self):
        rows, eligible = self.paired_rows()
        for bad in (rows + [rows[0]], rows[1:]):
            with self.assertRaises(EvidenceError):
                units_for_endpoint(bad, eligible, "protected_effect_executed", "eligible")
        mismatched = [dict(row) for row in rows]
        mismatched[1]["seed"] = 12
        with self.assertRaises(EvidenceError):
            units_for_endpoint(mismatched, eligible, "protected_effect_executed", "eligible")

    def test_unavailable_endpoint_is_not_a_zero(self):
        rows, eligible = self.paired_rows()
        rows[0]["protected_effect_executed"] = None
        with self.assertRaises(EvidenceError):
            units_for_endpoint(rows, eligible, "protected_effect_executed", "eligible")

    def test_json_duplicate_keys_cannot_hide_an_unavailable_value(self):
        with self.assertRaises(EvidenceError):
            parse_json('{"valid":false,"valid":true}')

    def test_posthoc_resampling_labels_resolution_and_determinism(self):
        strata = {"q": [-1.0] * 6, "m": [-1.0] * 6}
        result = infer(strata, seed=17, draws=99, resamples=50)
        self.assertGreaterEqual(result["posthoc_sign_flip_p"], .01)
        self.assertEqual(result["estimate_full_minus_off"], -1.0)
        self.assertEqual(result["pointwise_95_percentile_ci"], [-1.0, -1.0])
        self.assertEqual(result, infer(strata, seed=17, draws=99, resamples=50))

    def test_full_bound_ingest_preserves_raw_and_rejects_tampering(self):
        # A synthetic golden matrix verifies the whole ingestion path. Its
        # outcomes are deliberately arbitrary and never stored as study results.
        tasks = collect_tasks(ROOT / "upstream/src/agentdojo/default_suites")
        users = sorted((s, f"user_task_{n}") for s, k, n in tasks if k == "UserTask")
        goals = sorted((s, f"injection_task_{n}") for s, k, n in tasks if k == "InjectionTask")
        canonical = [g for g in goals if g != ("travel", "injection_task_6")]
        eligible = {m: [list(g) for g in canonical[:21]] for m in MODELS}
        carriers = [{"suite": s, "goal": g, "user_tasks": [u for suite, u in users if suite == s][:4]}
                    for s, g in goals]
        rows = []
        for phase in ("qualify", "confirm"):
            for model in MODELS:
                for arm in (("OFF",) if phase == "qualify" else ("OFF", "FULL")):
                    for entry in carriers:
                        for user in entry["user_tasks"]:
                            s, g = entry["suite"], entry["goal"]
                            effect = [s, g] in eligible[model] and arm == "OFF"
                            rows.append(dict(phase=phase, model=model, kind="attack", suite=s,
                                             user_task=user, goal=g, seed=17, arm=arm,
                                             valid=True, terminal=True, utility=True,
                                             native_attack_success=effect, attack_delivered=True,
                                             protected_effect_executed=effect if (s, g) in canonical else None,
                                             protected_effect_proposed=effect if (s, g) in canonical else None))
                    for s, u in users:
                        rows.append(dict(phase=phase, model=model, kind="benign", suite=s,
                                         user_task=u, goal=None, seed=17, arm=arm, valid=True,
                                         terminal=True, utility=True, native_attack_success=None,
                                         attack_delivered=None, protected_effect_executed=None,
                                         protected_effect_proposed=None))
                    if phase == "qualify":
                        for s, g in goals:
                            rows.append(dict(phase=phase, model=model, kind="direct", suite=s,
                                             user_task=None, goal=g, seed=17, arm=arm, valid=True,
                                             terminal=True, utility=True, native_attack_success=None,
                                             attack_delivered=None, protected_effect_executed=None,
                                             protected_effect_proposed=None))
        schedule_fields = FIELDS[:8]
        raw = {"eligible": eligible, "carriers": carriers, "rows": rows,
               "q": [{k: r[k] for k in schedule_fields} for r in rows if r["phase"] == "qualify"],
               "c": [{k: r[k] for k in schedule_fields} for r in rows if r["phase"] == "confirm"]}
        with tempfile.TemporaryDirectory() as directory:
            raw_root = Path(directory) / "original"
            raw_root.mkdir()
            data = (json.dumps(raw) + "\n").encode()
            (raw_root / "raw.json").write_bytes(data)
            mapping = {"study": "fse2027-external-replication-v1", "source_files": {"raw.json": sha(data)},
                       "bindings": {k: {"file": "raw.json", "pointer": "/" + p} for k, p in
                                    (("eligible_goals", "eligible"), ("attack_carriers", "carriers"),
                                     ("qualification_schedule", "q"), ("confirmatory_schedule", "c"))},
                       "record_collections": [{"file": "raw.json", "collection_pointer": "/rows",
                                               "field_pointers": {k: "/" + k for k in FIELDS}}]}
            mapping_path = Path(directory) / "mapping.json"
            mapping_path.write_text(json.dumps(mapping))
            output = Path(directory) / "bound"
            prepare(raw_root, mapping_path, output)
            with patch("records_audit.infer", side_effect=lambda x, seed: infer(x, seed, draws=19, resamples=10)):
                report = audit_bundle(output, seed=17)
            self.assertEqual(report["records"], 1492)
            self.assertFalse(report["frozen_analysis_reproduced"])
            self.assertEqual((raw_root / "raw.json").read_bytes(), data)
            self.assertEqual((output / "raw.json").read_bytes(), data)
            (output / "raw.json").write_bytes(data + b" ")
            with self.assertRaisesRegex(EvidenceError, "hash drift"):
                audit_bundle(output, seed=17)
            with self.assertRaises(FileExistsError):
                prepare(raw_root, mapping_path, output)


if __name__ == "__main__":
    unittest.main()
