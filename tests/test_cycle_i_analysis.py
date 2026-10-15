"""Deterministic arithmetic checks; fixtures are not empirical adjudications."""
import importlib.util
import itertools
import pathlib
import random
import unittest
from fractions import Fraction


PATH = pathlib.Path(__file__).parents[1] / "research/external_verification/audit_cycle_i.py"
SPEC = importlib.util.spec_from_file_location("cycle_i_audit", PATH)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def exhaustive(contexts):
    variables = [(i, j) for i, pair in enumerate(contexts) for j, y in enumerate(pair) if y is None]
    states = set()
    for completion in itertools.product((False, True), repeat=len(variables)):
        values = [list(pair) for pair in contexts]
        for (i, j), y in zip(variables, completion):
            values[i][j] = y
        denominator = sum(p for p, _ in values)
        numerator = sum(p and not e for p, e in values)
        states.add((numerator, denominator))
    return states


class CycleIAnalysisTests(unittest.TestCase):
    def test_unknown_is_never_coerced_to_a_favorable_boolean(self):
        self.assertIs(audit.parse_outcome("True"), True)
        self.assertIs(audit.parse_outcome("False"), False)
        self.assertIsNone(audit.parse_outcome("AMBIGUOUS"))
        with self.assertRaises(ValueError):
            audit.parse_outcome("INSUFFICIENT_EVIDENCE")

    def test_count_dynamic_program_matches_independent_binary_enumeration(self):
        rng = random.Random(917)
        for _ in range(20):
            contexts = [tuple(rng.choice((False, True, None)) for _ in range(2)) for _ in range(5)]
            self.assertEqual(audit.completion_counts(contexts), exhaustive(contexts))

    def test_order_and_input_immutability(self):
        contexts = [(True, False), (None, None), (False, False), (True, True), (None, False)]
        original = list(contexts)
        result = audit.completion_rates(contexts)
        self.assertEqual(result, audit.completion_rates(list(reversed(contexts))))
        self.assertEqual(contexts, original)

    def test_ratio_is_not_difference_of_separate_rate_bounds(self):
        result = audit.completion_rates([(True, False), (True, True), (None, None)])
        self.assertEqual(result["proposal_nonexecution_fraction"]["lower"]["fraction"], "1/3")
        self.assertEqual(result["proposal_nonexecution_fraction"]["upper"]["fraction"], "2/3")

    def test_zero_denominator_is_explicit(self):
        result = audit.completion_rates([(None, False)])
        self.assertTrue(result["zero_denominator_possible"])
        self.assertEqual(result["proposal_nonexecution_fraction"]["lower"]["fraction"], "1")
        never = audit.completion_rates([(False, False)])
        self.assertIsNone(never["proposal_nonexecution_fraction"]["lower"])

    def test_one_noneligible_proposal_changes_a_ratio_without_changing_eligibility(self):
        eligible = [(True, False)] * 40 + [(True, True)] * 15 + [(False, False)] * 29
        all_canonical = eligible + [(True, False)] + [(False, False)] * 51
        self.assertEqual(len(eligible), 84)
        self.assertEqual(len(all_canonical), 136)
        self.assertEqual(audit.completion_rates(eligible)["proposal_nonexecution_fraction"]["lower"]["fraction"], "8/11")
        self.assertEqual(audit.completion_rates(all_canonical)["proposal_nonexecution_fraction"]["lower"]["fraction"], "41/56")


if __name__ == "__main__":
    unittest.main()
