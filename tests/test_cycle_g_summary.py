"""Audit arithmetic/integrity fixtures, not empirical experiment records."""
import importlib.util
import pathlib
import unittest
from fractions import Fraction

PATH = pathlib.Path(__file__).resolve().parents[1] / "research/external_verification/summarize_cycle_g.py"
SPEC = importlib.util.spec_from_file_location("cycle_g_summary", PATH)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def rows(model, goal, carrier, off, full):
    result = []
    for arm, value in (("off", off), ("full", full)):
        result.append({"stage": "confirmatory", "position": carrier * 2 + (arm == "full"),
            "model": model, "cell_id": goal + "/" + str(carrier), "pair_id": model + goal + str(carrier),
            "arm": arm, "seed": carrier, "suite": "fixture", "injection_task": goal,
            "user_task": str(carrier), "kind": "security", "canonical_population": True,
            "cpe_executed": value})
    return result


class CycleGArithmeticTests(unittest.TestCase):
    def test_goal_and_model_weights_are_not_record_weights(self):
        data = rows("qwen", "g1", 0, False, True)
        for c in range(1, 4):
            data += rows("qwen", "g2", c, False, False)
        data += rows("mistral", "g3", 4, False, False)
        result = audit.unit_differences(audit.paired_metadata(data), None, "cpe_executed")
        self.assertEqual(result["estimate"]["fraction"], "1/4")
        self.assertNotEqual(result["estimate"]["estimate"], 1 / 5)

    def test_unknown_completions_bound_every_assignment(self):
        data = rows("qwen", "g1", 0, False, False) + rows("mistral", "g2", 1, False, False)
        pairs = audit.paired_metadata(data)
        decisions = {audit.key(r): {"executed": "AMBIGUOUS" if r["model"] == "qwen" else False} for r in data}
        lo = audit.unit_differences(pairs, decisions, "cpe_executed", completion="lower")
        hi = audit.unit_differences(pairs, decisions, "cpe_executed", completion="upper")
        self.assertEqual(Fraction(lo["estimate"]["fraction"]), Fraction(-1, 2))
        self.assertEqual(Fraction(hi["estimate"]["fraction"]), Fraction(1, 2))
        for off in (False, True):
            for full in (False, True):
                d = {k: dict(v) for k, v in decisions.items()}
                d[("confirmatory", 0)]["executed"] = off
                d[("confirmatory", 1)]["executed"] = full
                value = audit.unit_differences(pairs, d, "cpe_executed")["estimate"]["estimate"]
                self.assertLessEqual(-0.5, value)
                self.assertLessEqual(value, 0.5)
        with self.assertRaisesRegex(ValueError, "explicit completion"):
            audit.unit_differences(pairs, decisions, "cpe_executed")

    def test_pair_integrity_rejects_duplicate_missing_or_different_seed(self):
        data = rows("qwen", "g1", 0, False, True)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit.paired_metadata(data + [data[0]])
        with self.assertRaisesRegex(ValueError, "missing paired arm"):
            audit.paired_metadata(data[:1])
        data[1]["seed"] = 99
        with self.assertRaisesRegex(ValueError, "seed"):
            audit.paired_metadata(data)


if __name__ == "__main__":
    unittest.main()
