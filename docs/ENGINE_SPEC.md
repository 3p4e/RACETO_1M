# Engine specification v0.1: certificate review and quality-document engine

A behavioural specification: **what** the engine does and how it is proven, written from public requirements and general GMP
practice. Code is written fresh from this document. Every rule names its public basis.

## 1. Intended use (the sentence everything is validated against)
The engine **assists** a qualified reviewer in checking laboratory certificates of analysis for a lot and in drafting the lot's
quality documents. It proposes findings and drafts. It **never** decides conformance or releases a lot. A named person reviews
and signs every output.

*Risk class (ICH Q9(R1), GAMP 5 2nd ed.):* GxP-relevant, indirect impact on product quality via the reviewer's decision, which
makes it a **critical use with human-in-the-loop** in the sense of draft Annex 22. Validation effort is set accordingly (§8).

## 2. Users and outputs
| User | Gets |
|---|---|
| QC reviewer | findings per lot, each with evidence pointing to a certificate, page and value |
| QA / QP | a review summary per lot; drafted quality documents (certificate of quality/conformance, deviation draft) |
| Auditor / inspector | the audit trail, the validation record, the test-set results |

## 3. Data model (minimum)
- **Lot:** id, product, sub-lot relation (parent/sister), manufacture and packaging dates.
- **Certificate:** issuer laboratory (name, accreditation, scope), certificate number, issue date, pages total and pages received,
  the lot it **states** it covers, and the code it was **filed under**, kept separately.
- **Result:** test, method, value, unit, LOQ, **status** (`reported`, `not detected`, `not tested`, `pending`), and its source (certificate, page).
- **Specification:** versioned, with test, criterion, unit and public basis per row.
- **Finding:** lot, defect code, evidence, source pointers, raised by (rule id or AI model version), and the reviewer's decision.

Status rules: *not detected* is a result; *not tested* is the absence of one. They are never interchangeable. *Pending* is printed
as pending and is never filled from another source.

## 4. Review rules (deterministic layer: runs first, every time)
| # | Rule | Defect code | Public basis |
|---|---|---|---|
| R1 | A result outside its current specification is flagged with its criterion | OOS_* | EU GMP Part I Ch. 6 (6.32–6.35); FDA OOS guidance (2006) as practice reference |
| R2 | A certificate with fewer pages than stated is incomplete; values on missing pages are `pending`, never inferred | MISSING_PAGE | ALCOA+ *complete* (PIC/S PI 041-1 §7); Ch. 4 |
| R3 | Two certificates for the same lot and test that differ beyond a set limit are held for decision; no value is chosen automatically | LAB_DISAGREEMENT | Ch. 6; Annex 16 §1.7 (QP must be satisfied all testing is complete and consistent) |
| R4 | Only the lot's own certificates count; a certificate filed under another code, or for a sister sub-lot, is rejected for that lot | SUBLOT_TRAP | Ch. 4 (traceability of records to the batch); Ch. 5 (no mix-ups) |
| R5 | Release results must predate the release/packaging step they support | RESULT_AFTER_PACK | Ch. 6; Annex 16 (batch certification sequence) |
| R6 | A certificate number identifies one record; reuse across lots is a data-integrity flag | DUP_CERT_NO | ALCOA+ *attributable, original*; PIC/S PI 041-1 |
| R7 | A retest is compared with release; degradation beyond a set limit is reported, and the retest never overwrites the release record | RETEST_DRIFT | ICH Q1A(R2), Q1E; Ch. 4 (records are not overwritten) |
| R8 | A result's provenance (laboratory, certificate, page, date) travels with it into every document that prints it | — | Ch. 4; Annex 11 §8 (printouts) |

The limits in R3 and R7 are configuration with a documented rationale, not code constants.

## 5. AI layer (second, and bounded)
**Allowed:** proposing extracted values from a certificate (with page reference); proposing findings the rules cannot express;
drafting wording of documents and deviations; explaining a finding.
**Forbidden:** deciding conformance; filling a missing, pending or unreadable value; choosing between disagreeing laboratories;
changing a specification; any output without a source pointer.
**Controls:**
- **Two independent reads** of every extracted value (two models or two runs, plus OCR). Disagreement goes to a human.
- Model name and version, prompt version and input hash are stored with every proposal.
- Outputs are proposals until a person accepts them. Acceptance is an audit-trailed event.

Basis: draft Annex 22 (intended use, test data, human review, change control, monitoring); EMA reflection paper on AI (2024); EU AI Act Art. 4 (literacy of users).

## 6. Documents
- Templates are fixed and versioned. The engine fills **values**, never wording, criteria or layout.
- No statement appears that is not in a template or a cited source (no invented claims, signatories, dates).
- Every page is checked after rendering: page count, overflow, fonts embedded, no transparency (print-safe), values against source.
- Bilingual output is a template feature, not a translation step at print time.

## 7. Audit trail, records, security (Annex 11)
- An append-only audit trail of who, what, when and why for every create, change, accept and reject (Annex 11 §9).
- Electronic signature bound to the record, with meaning and time (Annex 11 §14).
- Role-based access; no shared accounts (Annex 11 §12).
- Backups tested by restore (Annex 11 §7.2).
- Change control for code, templates, specifications, rules and model versions (Annex 11 §10).

## 8. Validation (how the intended use is proven)
- **Test set:** `synthgmp` data sets (fixed seeds) with planted defects as ground truth, plus a growing library of edge cases.
- **Acceptance criteria:**
  - **Rules layer:** 100 % of planted defects found and 0 false findings, on every seed (met today: 36/36, 0 false, six seeds).
  - **AI extraction:** ≥ 99.5 % field accuracy on synthetic PDFs, with every miss caught by the double read.
- **Regression:** every change runs the full test set in CI; a drop below the acceptance criteria blocks the release.
- **Monitoring in use:** reviewer override rate and missed-defect reports, reviewed monthly (draft Annex 22: performance monitoring).
- **Records:** a validation plan, traceability (requirement → test), a test report, a release note per version (GAMP 5).

## 9. Milestones
| # | Deliverable | Done when |
|---|---|---|
| M1 | Rules layer + scorer + packets | **done:** 36/36, 0 false, deterministic |
| M2 | Synthetic certificate PDFs (digital and scanned-looking) generated from the data, plus extraction with double read | the extracted data reproduce the source CSV at ≥ 99.5 %; every disagreement routed to a human |
| M3 | Lot review summary + certificate-of-quality draft from a fixed template | values traceable to source on every page; render checks pass |
| M4 | Audit trail, accounts, e-signature | the Annex 11 §§9, 12, 14 tests pass |
| M5 | AI reviewer evaluated against the packets | scored by `score.py`; the result is published in the workshop, whatever it is |

## 10. Non-goals
No LIMS, no planner, no ERP. Batch release by software is excluded. No real customer data in this repository, ever.

## References
1. European Commission. EudraLex Vol. 4, EU GMP Part I: Ch. 4 *Documentation*, Ch. 5 *Production*, Ch. 6 *Quality Control*; Annex 11
   *Computerised Systems* (2011); Annex 16 *Certification by a Qualified Person and Batch Release* (2016); drafts of Ch. 4, Annex 11 and
   Annex 22 (consultation 7 July – 7 October 2025). https://health.ec.europa.eu/medicinal-products/eudralex/eudralex-volume-4_en
2. PIC/S. PI 041-1 *Good Practices for Data Management and Integrity in Regulated GMP/GDP Environments* (2021). https://picscheme.org
3. ICH Q9(R1) (2023); Q1A(R2) (2003); Q1E (2003). https://www.ich.org
4. ISPE. *GAMP 5: A Risk-Based Approach to Compliant GxP Computerized Systems*, 2nd ed. (2022). ISBN 978-1-946964-57-1.
5. US FDA. *Investigating Out-of-Specification (OOS) Test Results for Pharmaceutical Production*, Guidance for Industry (2006; rev. 2022).
6. EMA. *Reflection paper on the use of AI in the medicinal product lifecycle*, EMA/CHMP/CVMP/83833/2023 (2024).
7. Regulation (EU) 2024/1689 (AI Act), Art. 4. OJ L, 12.7.2024.
