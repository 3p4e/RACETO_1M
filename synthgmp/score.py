#!/usr/bin/env python3
"""Score any reviewer's findings against the planted-defect ground truth.

Usage: python3 score.py <data_dir> <findings.csv>
findings.csv needs columns batch_id and defect (defect codes as in defects_ground_truth.csv).
A sister sub-lot (batch id ending in 'S') counts for its lot's SUBLOT_TRAP.
PASS means: every planted defect found, and no finding that is neither planted nor justified.

Justified extras are true findings the answer key does not require (counted separately, never as false):
- DUP_CERT_NO on the other lot of a pair that shares a certificate number (both lots really carry it);
- OOS_* on a retest result that is itself outside specification (EU GMP Part I 6.35: report OOS stability results).
"""
import csv, os, sys
from collections import Counter

def norm(bid, defect):
    return (bid[:-1] if defect == "SUBLOT_TRAP" and bid.endswith("S") else bid, defect)

def main(d, findings):
    truth = {(r["batch_id"], r["defect"]) for r in csv.DictReader(open(os.path.join(d, "defects_ground_truth.csv"), encoding="utf-8"))}
    got = {norm(r["batch_id"].strip(), r["defect"].strip().upper()) for r in csv.DictReader(open(findings, encoding="utf-8"))}
    certs = list(csv.DictReader(open(os.path.join(d, "certificates.csv"), encoding="utf-8")))
    results = list(csv.DictReader(open(os.path.join(d, "results.csv"), encoding="utf-8")))
    owners = {}
    for c in certs:
        owners.setdefault(c["cert_no"], set()).add(c["batch_id"])
    justified = set()
    for lots in owners.values():
        if len(lots) > 1:
            justified |= {(b, "DUP_CERT_NO") for b in lots}
    oos_codes = {"Total THC": "OOS_POTENCY", "Total CBD": "OOS_POTENCY", "Loss on drying": "OOS_LOD"}
    for r in results:
        if r["kind"] == "retest" and r["conforms"] == "no":
            justified.add((r["batch_id"], oos_codes.get(r["test"], "OOS_OTHER")))
    tp, fn = truth & got, truth - got
    extra = (got - truth) & justified
    fp = got - truth - justified
    kinds = sorted({k for _, k in truth | got})
    t, p, n = Counter(k for _, k in tp), Counter(k for _, k in fp), Counter(k for _, k in fn)
    print(f"{'defect':<20}{'found':>7}{'missed':>8}{'false':>7}")
    for k in kinds:
        print(f"{k:<20}{t[k]:>7}{n[k]:>8}{p[k]:>7}")
    recall = len(tp) / len(truth) if truth else 1.0
    precision = (len(tp) + len(extra)) / len(got) if got else 0.0
    print(f"\nplanted {len(truth)} · found {len(tp)} · missed {len(fn)} · false {len(fp)} · justified extras {len(extra)}")
    print(f"recall {recall:.1%} · precision {precision:.1%}")
    verdict = "PASS" if not fn and not fp else "FAIL"
    print(f"verdict: {verdict}")
    for label, s in (("missed", fn), ("false", fp), ("justified", extra)):
        for b, k in sorted(s)[:20]:
            print(f"  {label}: {b} {k}")
    return 0 if verdict == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
