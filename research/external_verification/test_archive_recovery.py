"""Failure-path checks; synthetic inputs are not empirical observations."""

import json
import unittest

import archive_recovery_audit as audit


class RecoveryFailures(unittest.TestCase):
    def test_duplicate_json_fields_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            json.loads('{"validity":"VALID","validity":"INVALID"}',
                       object_pairs_hook=audit.unique_object)

    def test_duplicate_pair_arm_cannot_silently_replace_an_outcome(self):
        row = {"model": "qwen", "cell_id": "example", "arm": "off"}
        with self.assertRaisesRegex(ValueError, "duplicate pair arm"):
            audit.independent_estimates([row, dict(row)], {}, {})

    def test_missing_pair_arm_is_rejected(self):
        row = {"model": "qwen", "cell_id": "example", "arm": "off"}
        with self.assertRaisesRegex(ValueError, "missing arm"):
            audit.independent_estimates([row], {}, {})

    def test_unequal_seeds_are_rejected_before_computing_a_contrast(self):
        rows = [{"model": "qwen", "cell_id": "example", "arm": arm,
                 "seed": seed, "pair_id": "same"}
                for arm, seed in (("off", 1), ("full", 2))]
        with self.assertRaisesRegex(ValueError, "unpaired seed"):
            audit.independent_estimates(rows, {}, {})

    def test_self_digest_detects_edited_registration(self):
        record = {"eligibility": ["example"]}
        record["record_sha256"] = audit.digest(record)
        record["eligibility"] = []
        with self.assertRaisesRegex(ValueError, "self-digest mismatch"):
            audit.self_digest(record, "record_sha256")


if __name__ == "__main__":
    unittest.main()
