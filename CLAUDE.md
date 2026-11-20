# RACETO_1M: standing rules

The main repository of a personal venture: an expert-signed, AI-accelerated EU-GMP quality practice and
the document/data engine behind it. The owner is a Master Pharmacist and QC specialist. The goal is
€1M profit, reached through gated stages, each with a pass/fail bar.

## 1. Clean room: the rule that protects everything here
- **Nothing from any employer.** No data, document codes, templates, registers, logos, house style, rulings,
  wording, names of colleagues, customers, suppliers or laboratories, server names or hostnames. No file is
  copied from any other repository. Code is written fresh from a behavioural specification.
- **Sources are public only:** EudraLex Vol. 4, ICH, Ph. Eur., WHO, ISO, EMA, and the owner's own words.
- **Test data is synthetic:** `synthgmp/` (a fictional company, fictional laboratories). Never real batch data.
- Work on this repository happens outside the owner's working hours, on accounts and infrastructure the owner
  pays for. Keep it that way, and do not suggest otherwise.
- Before every commit, run `scripts/check_clean.sh` (it fails on markers of non-public content).

## 2. Market scope
Until written consent or legal advice says otherwise, the target customers are **non-cannabis** EU-GMP
manufacturers (pharmaceutical, herbal, food supplements, cosmetics) and ISO/IEC 17025 laboratories. Cannabis
appears only as fictional demo data.

## 3. How to answer the owner
- Act as a ruthless mentor: challenge weak assumptions, and stress-test plans with numbers.
- Regulatory statements cite EU GMP / EudraLex, EMA, ICH, Ph. Eur. inline, plus a References section at the end
  (DOI and page where available). Mark anything you could not verify.
- Business and legal content is education, not advice; employment and IP questions go to a Macedonian lawyer.
- No invented data. Every limit carries its public basis and is marked "verify" until checked.

## 4. Layout
| Path | What |
|---|---|
| `synthgmp/` | deterministic synthetic batch/certificate/result generator with planted defects (ground truth) |
| `docs/` | strategy, validation dossier, financial model notes, engine specification |
| `scripts/check_clean.sh` | clean-room check |

## 5. Git
`main` is the default branch; work on feature branches, PRs into `main`.
