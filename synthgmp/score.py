#!/usr/bin/env python3
"""Score any reviewer's findings against the planted-defect ground truth.

Usage: python3 score.py <data_dir> <findings.csv>
findings.csv needs columns batch_id and defect (defect codes as in defects_ground_truth.csv).
A sister sub-lot (batch id ending in 'S') counts for its lot's SUBLOT_TRAP.
PASS means: every planted defect found, and no finding that was not planted.
"""
import csv, os, sys
from collections import Counter

def norm(bid, defect):
    return (bid[:-1] if defect == "SUBLOT_TRAP" and bid.endswith("S") else bid, defect)

def main(d, findings):
    truth = {(r["batch_id"], r["defect"]) for r in csv.DictReader(open(os.path.join(d, "defects_ground_truth.csv"), encoding="utf-8"))}
    got = {norm(r["batch_id"].strip(), r["defect"].strip().upper()) for r in csv.DictReader(open(findings, encoding="utf-8"))}
    tp, fn, fp = truth & got, truth - got, got - truth
    kinds = sorted({k for _, k in truth | got})
    t, p, n = Counter(k for _, k in tp), Counter(k for _, k in fp), Counter(k for _, k in fn)
    print(f"{'defect':<20}{'found':>7}{'missed':>8}{'false':>7}")
    for k in kinds:
        print(f"{k:<20}{t[k]:>7}{n[k]:>8}{p[k]:>7}")
    recall = len(tp) / len(truth) if truth else 1.0
    precision = len(tp) / len(got) if got else 0.0
    print(f"\nplanted {len(truth)} · found {len(tp)} · missed {len(fn)} · false {len(fp)}")
    print(f"recall {recall:.1%} · precision {precision:.1%}")
    verdict = "PASS" if not fn and not fp else "FAIL"
    print(f"verdict: {verdict}")
    for label, s in (("missed", fn), ("false", fp)):
        for b, k in sorted(s)[:20]:
            print(f"  {label}: {b} {k}")
    return 0 if verdict == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
