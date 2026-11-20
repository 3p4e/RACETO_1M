#!/usr/bin/env python3
"""Reference reviewer: deterministic rules over a synthgmp data set.

It proves every planted defect is detectable from the data alone, and sets the bar an AI reviewer must meet.
Usage: python3 review_rules.py <data_dir> <findings.csv>
Writes findings.csv with columns: batch_id, defect, evidence.
"""
import csv, os, sys
from collections import defaultdict

MICRO = {"TAMC", "TYMC", "Bile-tolerant gram-negative bacteria", "Escherichia coli", "Salmonella"}
OOS_KIND = {"Total THC": "OOS_POTENCY", "Total CBD": "OOS_POTENCY", "Loss on drying": "OOS_LOD"}

def load(d, name):
    return list(csv.DictReader(open(os.path.join(d, name), encoding="utf-8")))

def main(d, out):
    batches = {b["batch_id"]: b for b in load(d, "batches.csv")}
    certs = load(d, "certificates.csv")
    results = load(d, "results.csv")
    found = []
    def flag(bid, kind, ev):
        found.append({"batch_id": bid, "defect": kind, "evidence": ev})

    # 1. results outside their criterion, release and retest alike (EU GMP Part I 6.35: OOS stability results are reported)
    for r in results:
        if r["conforms"] == "no":
            kind = OOS_KIND.get(r["test"]) or ("OOS_MICRO" if r["test"] in MICRO else "OOS_OTHER")
            flag(r["batch_id"], kind, f"{r['test']} = {r['result']} {r['unit']} vs {r['criterion']} ({r['cert_no']})")

    # 2. certificate received incomplete
    for c in certs:
        if int(c["pages_received"]) < int(c["pages_total"]):
            flag(c["batch_id"], "MISSING_PAGE", f"{c['cert_no']}: {c['pages_received']} of {c['pages_total']} pages")

    # 3. two laboratories disagree on potency by more than 10 % (relative)
    thc = defaultdict(list)
    for r in results:
        if r["kind"] == "release" and r["test"] == "Total THC" and r["result"]:
            thc[r["batch_id"]].append((float(r["result"]), r["cert_no"]))
    for bid, vals in thc.items():
        if len({c for _, c in vals}) > 1:
            lo, hi = min(v for v, _ in vals), max(v for v, _ in vals)
            if lo > 0 and hi / lo - 1 > 0.10:
                flag(bid, "LAB_DISAGREEMENT", f"Total THC {lo}-{hi} % across {len(vals)} certificates")

    # 4. certificate filed under a code other than its own lot (another lot's certificate)
    for c in certs:
        if c["filed_under"] != c["batch_id"]:
            flag(c["batch_id"], "SUBLOT_TRAP", f"{c['cert_no']} filed under '{c['filed_under']}', lot is {c['batch_id']} ({batches[c['batch_id']]['cultivation_batch']})")

    # 5. a release certificate issued after the lot was packaged
    for c in certs:
        if c["kind"] == "release" and c["issue_date"] > batches[c["batch_id"]]["packaging_date"]:
            flag(c["batch_id"], "RESULT_AFTER_PACK", f"{c['cert_no']} issued {c['issue_date']}, packaged {batches[c['batch_id']]['packaging_date']}")

    # 6. one certificate number on two different lots: numbers run in production order, so the number belongs to the
    #    lot made first; flag every later lot that carries it
    by_no = defaultdict(list)
    for c in certs:
        by_no[c["cert_no"]].append(c)
    for no, cs in by_no.items():
        if len({c["batch_id"] for c in cs}) > 1:
            cs = sorted(cs, key=lambda c: (batches[c["batch_id"]]["manufacture_date"], c["batch_id"]))
            for c in cs[1:]:
                flag(c["batch_id"], "DUP_CERT_NO", f"{no} also on {cs[0]['batch_id']}")

    # 7. retest shows degradation against release
    rel = {(r["batch_id"], r["test"]): r for r in results if r["kind"] == "release"}
    for r in results:
        if r["kind"] == "retest" and r["test"] == "Total THC" and (r["batch_id"], "Total THC") in rel:
            a, b = float(rel[(r["batch_id"], "Total THC")]["result"]), float(r["result"])
            if b < a * 0.97:
                flag(r["batch_id"], "RETEST_DRIFT", f"Total THC {a} -> {b} % ({r['note']})")

    # one finding per (lot, defect)
    seen, uniq = set(), []
    for f in found:
        k = (f["batch_id"], f["defect"])
        if k not in seen:
            seen.add(k); uniq.append(f)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["batch_id", "defect", "evidence"]); w.writeheader(); w.writerows(uniq)
    print(f"{len(uniq)} findings -> {out}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
