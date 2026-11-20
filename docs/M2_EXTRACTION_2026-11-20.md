# M2: certificate extraction with a double read (20.11.2026)

## What was tested
- `render_certs.py` turns synthgmp certificates into PDFs: digital (text layer) or scanned-looking (image only, rotated ±0.9°,
  noise, blur, JPEG). A certificate missing a page is rendered without it; every page prints "Page i of N".
- `extract.py` reads every PDF twice by independent methods. Read A: the text layer, or OCR (Tesseract psm 6). Read B: OCR of a
  binarised raster (psm 4). Every field is compared with the source data.
- **Pass criteria (ENGINE_SPEC §8):** ≥ 99.5 % of fields correct after the human queue, and **0 undetected errors** (both reads
  agree and are wrong).

## Results
| Run | Certificates | Fields | Agreed and correct | To a human | Undetected errors | Verdict |
|---|---|---|---|---|---|---|
| First version (40) | 40 | 384 | 91.1 % | 6.8 % | **8** | FAIL |
| Final (sample used for tuning, seed 42) | 120 | 1,177 | 92.4 % | 7.6 % | **0** | PASS |
| Final (**unseen data**, seed 2026, new scans) | 100 | 962 | 90.6 % | 9.4 % | **0** | PASS |

## What failed first, and the control that fixed it
| Failure | Why the double read did not catch it | Control added |
|---|---|---|
| Microbial counts "2x10^3" read as "2" by **both** reads: a 1,000-fold error | the two reads shared one parser, so they failed the same way | a partial token is never a value; the unit decides the allowed form (CFU/g must be in exponent form, % must have decimals); a field neither read can parse goes to a human |
| Lot "CAL0825068" read as "CALO825068" by both | O/0 confusion is common to both OCR modes | **identifiers are checked against master data** (lot register); an unknown identifier is refused |
| Pages-received count disagreed on 11 of 40 certificates | the footer was read by OCR | pages received is taken from the file structure, not from OCR |
| "< 1 (LOQ)" vs "<1(LOQ)" | spacing only | values compared in canonical form |

**Lesson for the engine and for the workshop:** two reads are independent only where they fail differently. Shared parsing,
shared character confusions and shared assumptions make them fail together. The controls that reached zero undetected
errors were type rules, master-data checks and structural facts, not "more AI".

## Open
- **The human queue is 7.6–9.4 %** (about 10 % on scanned certificates). That is the cost driver of the desk offer (line C). Next:
  a third read only on queued fields, before any human; better scan preprocessing (deskew).
- Real laboratory layouts vary far more than this one template. The next test set needs several layouts per laboratory.

## References
1. European Commission. EudraLex Vol. 4, EU GMP Part I, Chapter 4 *Documentation* (traceability; records complete and accurate); Annex 11
   *Computerised Systems* (2011), §5 (data: built-in checks for correct and secure entry), §6 (accuracy checks).
   https://health.ec.europa.eu/medicinal-products/eudralex/eudralex-volume-4_en
2. PIC/S. PI 041-1 *Good Practices for Data Management and Integrity in Regulated GMP/GDP Environments* (2021). https://picscheme.org
