#!/usr/bin/env python3
"""Export one review packet per lot, for an AI reviewer (or a human) to work from.

Usage: python3 make_packets.py <data_dir> <out_dir>
Each packet is JSON: the lot, its certificates, its results, the specification, and the instruction.
The reviewer answers with lines 'batch_id,DEFECT_CODE,evidence' collected into a findings.csv for score.py.
"""
import csv, json, os, sys
from collections import defaultdict

INSTRUCTION = (
    "You are a QC reviewer. Review this lot's records before release. Report every problem as one line "
    "'batch_id,DEFECT_CODE,evidence', using only these codes: OOS_POTENCY, OOS_LOD, OOS_MICRO, OOS_OTHER, MISSING_PAGE, "
    "LAB_DISAGREEMENT, SUBLOT_TRAP, RESULT_AFTER_PACK, DUP_CERT_NO, RETEST_DRIFT. Report nothing you cannot point to in the data. "
    "If there is no problem, answer NONE.")

def main(d, out):
    rd = lambda n: list(csv.DictReader(open(os.path.join(d, n), encoding="utf-8")))
    certs, results = defaultdict(list), defaultdict(list)
    all_certs = rd("certificates.csv")
    for c in all_certs:
        certs[c["batch_id"]].append(c)
    for r in results_rows if (results_rows := rd("results.csv")) else []:
        results[r["batch_id"]].append(r)
    # certificate numbers used anywhere, so a duplicate is visible from a single packet
    used = defaultdict(list)
    for c in all_certs:
        used[c["cert_no"]].append(c["batch_id"])
    spec = json.load(open(os.path.join(d, "spec.json"), encoding="utf-8"))
    os.makedirs(out, exist_ok=True)
    n = 0
    for b in rd("batches.csv"):
        bid = b["batch_id"]
        packet = {"instruction": INSTRUCTION, "lot": b, "certificates": certs[bid],
                  "certificate_numbers_also_used_by": {c["cert_no"]: [x for x in used[c["cert_no"]] if x != bid] for c in certs[bid]},
                  "results": results[bid], "specification_tests": spec["tests"]}
        json.dump(packet, open(os.path.join(out, f"{bid}.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        n += 1
    print(f"{n} packets -> {out}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
