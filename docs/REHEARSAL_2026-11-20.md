# Rehearsal 1: Claude as a blind QC reviewer (20.11.2026)

## Set-up
- Data: `synthgmp` seed 42 (as generated on 20.11.2026, before the generator fixes below): 204 lots, 36 planted defects.
- Reviewers: four independent Claude agents with no prior context, 51 lots each. Each saw only its packets plus the shared
  instruction and specification. None saw the answer key, the generator or this repository.
- Method: the agents could read files and write small scripts ("Claude with tools"), not reading by eye alone. State that when presenting.

## Result
| Scoring | Found | Missed | False | Verdict |
|---|---|---|---|---|
| Original answer key | 36/36 | 0 | 8 | FAIL |
| Corrected answer key (justified extras recognised) | **36/36** | **0** | **0** (8 justified extras) | **PASS** |

The 8 "false" findings were all correct. The answer key was incomplete:
- **4× DUP_CERT_NO on the other lot of a pair.** Both lots really carry the same certificate number; each reviewer saw only its
  own lot, so flagging it is right.
- **4× OOS_POTENCY on retest results.** Each retest value is outside the specification window (e.g. 15.17 % against 16.20–19.80 %).
  An OOS stability result must be reported (EU GMP Part I, 6.35). The key had listed these only as drift.

## What the reviewers found that the generator got wrong (now fixed)
1. Cultivation-batch codes were reused across lots with different harvest dates. Codes are now unique per lot.
2. A sister sub-lot carried only 4 of the 19 specified tests. It now carries the full panel; only its potency certificate is misfiled.
3. The reference reviewer did not flag out-of-specification retest results. It does now.

## Lessons for the workshop
- **Test the test first.** The rehearsal failed on the first scoring, and the fault was the answer key, not the AI. Under draft Annex 22, test data
  and acceptance criteria are part of what gets validated.
- **"Justified extra" is a category the acceptance criteria need.** A good reviewer reports true problems the key did not plan.
- **Judgement calls show up as disagreements between reviewers**: one reviewer filed a second-laboratory value only as a
  disagreement, another also as OOS. The procedure, not the model, must decide how such cases are coded.
- **Reviewers flagged two real problems no code covered**: a reused cultivation code, and an incomplete test set. Add codes
  (`IDENTITY_CONFLICT`, `TESTS_MISSING`) in the next version.

## Reference
1. European Commission. EudraLex Vol. 4, EU GMP Part I, Chapter 6 *Quality Control*, 6.35 (on-going stability: out-of-specification
   results). https://health.ec.europa.eu/medicinal-products/eudralex/eudralex-volume-4_en
2. European Commission. Draft Annex 22 *Artificial Intelligence* (consultation 7 July – 7 October 2025): test data, acceptance criteria.
