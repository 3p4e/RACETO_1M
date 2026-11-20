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

## Clean-room check
```bash
scripts/check_clean.sh
```
