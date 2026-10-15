"""Apply a hash-bound abstention, preserving the earlier canonical-account audit.

No original observations are replayed. This affects one qualification record,
does not create a positive label, and leaves all confirmatory results unchanged.
"""
import argparse
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import time
from collections import Counter, defaultdict
from fractions import Fraction

BOUNDARY_SHA = "121d81a078855701f05f67769471e58f2a4c7fab82792910be7125d4fa1fb0d9"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--audit", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--boundary", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    assert not args.output.exists(), "fresh output path required"
    assert sha(args.boundary) == BOUNDARY_SHA
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    timer = time.perf_counter()
    before = {str(x): sha(x) for x in (args.audit, args.evidence, args.boundary)}
    source = json.loads(args.audit.read_text())
    proof = json.loads(args.evidence.read_text())
    assert proof["raw_before_after_unchanged"]
    assert proof["actions"] and all(not a["present_in_any_initial_bank_fact"] and not a["matches_any_initial_payment_recipient"]
                                    and a["authoritative_merchant_ownership"] == "NOT_IDENTIFIABLE_FROM_RETAINED_EVIDENCE"
                                    for a in proof["actions"])
    result = copy.deepcopy(source)
    found = [r for r in result["records"] if r["raw_pointer"] == proof["record_pointer"]]
    assert len(found) == 1 and found[0]["raw_sha256"] == proof["record_sha256"]
    record = found[0]
    assert record["stage"] == "qualification" and record["goal"] == "banking/user_task_5"
    supported = {a["args_sha256"] for a in proof["actions"]}
    eligible = [a for a in record["actions"] if a["function"] == "send_money" and a["amount"] == 5
                and a["completion"] is True and a["canonical_target_match"] is False]
    assert eligible and all(a["args_sha256"] in supported for a in eligible)
    record["V1_canonical_account_outcome"] = record["semantic"]
    record["semantic"] = None
    record["decision_reason"] = "MERCHANT_OWNERSHIP_AT_UNMAPPED_IBAN_NOT_IDENTIFIABLE"
    record["audit_status"] = "ABSTAINED_IDENTITY_BOUNDARY"
    record["disagreement"] = False
    record["disagreement_category"] = None
    record["second_checker_agrees"] = None
    record["boundary_sha256"] = BOUNDARY_SHA
    record["V1_checkers_established_canonical_components_not_destination_ownership"] = True
    assert all(a == b for a, b in zip(source["records"], result["records"]) if a["raw_pointer"] != proof["record_pointer"])
    assert result["statistics"] == source["statistics"]
    groups = defaultdict(list)
    for row in result["records"]:
        groups[row["goal"]].append(row)
    result["by_goal"] = {key: {"records": len(rows), "classified": sum(r["semantic"] is not None for r in rows),
                               "true": sum(r["semantic"] is True for r in rows), "false": sum(r["semantic"] is False for r in rows),
                               "unknown": sum(r["semantic"] is None for r in rows), "disagreements": sum(r["disagreement"] for r in rows)}
                         for key, rows in groups.items()}
    result["coverage_by_stratum"] = []
    for columns in [("stage",), ("model",), ("arm",), ("stage", "model", "arm")]:
        grouped = defaultdict(list)
        for row in result["records"]:
            grouped[tuple(row[c] for c in columns)].append(row)
        for values, rows in sorted(grouped.items()):
            result["coverage_by_stratum"].append({"grouping": list(columns), **dict(zip(columns, values)),
                                                   "records": len(rows), "classified": sum(r["semantic"] is not None for r in rows),
                                                   "unknown": sum(r["semantic"] is None for r in rows),
                                                   "disagreements": sum(r["disagreement"] for r in rows)})
    original = Fraction(source["statistics"]["original_source_S2"]["fraction"])
    changes = sum((Fraction((int(r["semantic"]) - int(r["native"])) * (1 if r["arm"] == "full" else -1), 194)
                   for r in result["records"] if r["stage"] == "confirmatory" and r["semantic"] is not None), Fraction())
    point = original + changes
    result["statistics"]["all_unadjudicated_native_labels_fixed_POST_HOC_point_sensitivity"] = {
        "fraction": str(point), "estimate": float(point), "observed_label_correction": str(changes),
        "assumption": "All unaudited and unadjudicated utility labels remain at their historical source values solely for this comparison. It is not an independently validated full-population semantic estimate."}
    result["identity_boundary_application"] = {"started_utc": started, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                                                "runtime_seconds": time.perf_counter() - timer, "code_sha256": sha(Path(__file__)),
                                                "boundary_sha256": BOUNDARY_SHA, "input_hashes_before_after": before,
                                                "affected_records": 1, "affected_confirmatory_labels": 0,
                                                "positive_labels_created": 0, "reason": "Unmapped merchant-account ownership remains missing."}
    result["status"] = "PARTIALLY_VERIFIED_BENIGN_CONSTRUCT_AUDIT_WITH_IDENTITY_ABSTENTION"
    result["canonical_v1_output_preserved_separately"] = True
    assert all(sha(Path(path)) == expected for path, expected in before.items())
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({"output": str(args.output), "sha256": sha(args.output), "classified": sum(r["semantic"] is not None for r in result["records"]),
                      "unknown": sum(r["semantic"] is None for r in result["records"]), "disagreements": sum(r["disagreement"] for r in result["records"]),
                      "runtime_seconds": result["identity_boundary_application"]["runtime_seconds"], "statistics": result["statistics"]}))


if __name__ == "__main__":
    main()
