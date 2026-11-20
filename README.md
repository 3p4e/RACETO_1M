# RACETO_1M

A personal venture: an expert-signed, AI-accelerated EU-GMP quality practice, and the engine behind it.
Rules for working here: [`CLAUDE.md`](CLAUDE.md).

## Synthetic test data
```bash
python3 synthgmp/generate.py --batches 200 --seed 42 --out out
```
It writes a fictional company's batches, laboratory certificates and results, plus `defects_ground_truth.csv`, a list of
planted defects (out-of-specification results, a missing certificate page, laboratories that disagree, sub-lot
mix-ups, a result dated after packaging, a duplicated certificate number, retest drift). An engine is scored by whether it
catches every planted defect and nothing else. The same seed always gives byte-identical files. Every limit in
`synthgmp/spec_demo.json` names its public basis (Ph. Eur.) and is marked "verify".

## Scoring a reviewer (human or AI)
```bash
python3 synthgmp/generate.py --out out                     # the fictional data set
python3 synthgmp/make_packets.py out out/packets           # one JSON packet per lot, with the reviewer instruction
python3 synthgmp/review_rules.py out out/findings.csv      # the reference reviewer (deterministic rules)
python3 synthgmp/score.py out out/findings.csv             # found / missed / false per defect, PASS only at 36 of 36 with 0 false
```
The reference reviewer scores 36/36 with 0 false findings on every seed tested. That proves every planted defect can be
found from the data alone. A reviewer that only checks results against limits finds 12 of 36. Any AI reviewer answers the
packets, its lines are collected into a findings CSV, and `score.py` grades it.

## Clean-room check
```bash
scripts/check_clean.sh
```
