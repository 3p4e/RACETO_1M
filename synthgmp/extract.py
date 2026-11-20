#!/usr/bin/env python3
"""Double-read extraction of certificate PDFs, scored against the source data.

Read A: the PDF text layer if present, otherwise OCR (Tesseract, page segmentation 6).
Read B: always OCR of a binarised raster with a different segmentation mode (4): an independent method.
A field goes to the human queue when A and B disagree. An *undetected error* is a field where A and B agree and are wrong:
that number must be zero.

Usage: python3 extract.py <data_dir> <pdf_dir> <out_dir> [--workers 4]
"""
import argparse, csv, json, os, re, subprocess, tempfile
from concurrent.futures import ProcessPoolExecutor
os.environ.setdefault("OMP_THREAD_LIMIT", "1")  # one Tesseract thread per worker process
import pdfplumber
from PIL import Image

HEAD = {"cert_no": r"CERTIFICATE OF ANALYSIS No\.?\s*([A-Z]{1,3}-\d+/\d{2})",
        "lot": r"Lot:\s*([A-Z0-9][A-Z0-9-]+(?:/\d)?)",
        "issue_date": r"Issue date:\s*(\d{4}-\d{2}-\d{2})",
        "page": r"P[a-z]{2}e\s+(\d+)\s+[o0][fF]\s+(\d+)"}
RESULT = re.compile(r"^(<\s?[\d.]+(?:e-?\d+)?\s?\(LOQ\)|ND \(all residues in scope\)|Conforms|Absent|Present|\d+\s?x\s?10\^\d+|\d+\.\d+|\d+)")

def norm(s):
    s = s.replace("—", "-").replace("–", "-").replace("’", "'")
    # common OCR variants of the exponent notation "2x10^3"
    s = re.sub(r"(\d)\s*[xX×]\s*1[0Oo]\s*[\^*\"'°]\s*(\d)", r"\1x10^\2", s)
    s = re.sub(r"[ \t]+", " ", s)
    return s

def ocr(img_path, psm):
    out = subprocess.run(["tesseract", img_path, "-", "--psm", str(psm), "-l", "eng"], capture_output=True, text=True)
    return out.stdout

def raster(pdf, td, dpi=200):
    subprocess.run(["pdftoppm", "-r", str(dpi), "-gray", "-png", pdf, os.path.join(td, "p")], check=True)
    return [os.path.join(td, f) for f in sorted(os.listdir(td)) if f.endswith(".png")]

def binarise(path):
    im = Image.open(path).convert("L").point(lambda v: 255 if v > 150 else 0)
    p2 = path.replace(".png", "_b.png"); im.save(p2); return p2

UNIT_FORMAT = {"CFU/g": re.compile(r"^\d+x10\^\d+$"),
               "%": re.compile(r"^(\d+\.\d{2}|<\s?[\d.]+\s?\(LOQ\))$")}

def valid(value, unit):
    """Accept a value only if it has the form its unit requires; otherwise the read is refused (None)."""
    rx = UNIT_FORMAT.get(unit)
    return value if (rx is None or rx.match(value)) else None

def parse(pages_text, tests):
    fields, results, pages = {}, {}, []
    for txt in pages_text:
        txt = norm(txt)
        for k in ("cert_no", "lot", "issue_date"):
            m = re.search(HEAD[k], txt)
            if m and k not in fields:
                fields[k] = m.group(1)
        m = re.search(HEAD["page"], txt)
        if m:
            pages.append((int(m.group(1)), int(m.group(2))))
        for line in txt.splitlines():
            line = line.strip()
            for t in tests:  # longest names first
                if line.startswith(t):
                    rest = line[len(t):].strip()
                    m = RESULT.match(rest)
                    if m and len(rest) > m.end() and not rest[m.end()].isspace():
                        m = None  # a partial token (e.g. "2" of a garbled "2x10^3") is not a value
                    if m:
                        results[t] = re.sub(r"\s", "", m.group(1)) if "x" in m.group(1) and "10^" in m.group(1) else m.group(1).replace("< ", "< ").strip()
                    break
    if pages:
        fields["pages_total"] = str(max(p[1] for p in pages))
    return fields, results

def read_one(args):
    pdf, tests = args
    with tempfile.TemporaryDirectory() as td:
        with pdfplumber.open(pdf) as doc:
            layer = [p.extract_text() or "" for p in doc.pages]
        imgs = raster(pdf, td)
        a_text = layer if any(t.strip() for t in layer) else [ocr(i, 6) for i in imgs]
        b_text = [ocr(binarise(i), 4) for i in imgs]
    fa, fb = parse(a_text, tests), parse(b_text, tests)
    for f in (fa, fb):  # pages received = pages physically in the file: structure, not OCR
        f[0]["pages_received"] = str(len(imgs))
    return fa, fb, bool(any(t.strip() for t in layer))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("pdf"); ap.add_argument("out"); ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    spec = json.load(open(os.path.join(a.data, "spec.json"), encoding="utf-8"))
    tests = sorted({t["name"] for t in spec["tests"]}, key=len, reverse=True)
    units = {t["name"]: t.get("unit", "") for t in spec["tests"]}
    certs = {(c["cert_no"], c["batch_id"]): c for c in csv.DictReader(open(os.path.join(a.data, "certificates.csv"), encoding="utf-8"))}
    truth_r = {}
    for r in csv.DictReader(open(os.path.join(a.data, "results.csv"), encoding="utf-8")):
        if r["result"]:
            truth_r.setdefault((r["cert_no"], r["batch_id"]), {})[r["test"]] = r["result"]
    # identifiers must exist in master data (the lot register), or the read is refused
    register = set()
    for b in csv.DictReader(open(os.path.join(a.data, "batches.csv"), encoding="utf-8")):
        register |= {b["batch_id"], b["cultivation_batch"], b["cultivation_batch"].split("/")[0]}
    canon = lambda v: None if v is None else re.sub(r"\s+", "", v)
    manifest = json.load(open(os.path.join(a.pdf, "manifest.json")))
    jobs = [(os.path.join(a.pdf, m["file"]), tests) for m in manifest]
    with ProcessPoolExecutor(a.workers) as ex:
        reads = list(ex.map(read_one, jobs))
    os.makedirs(a.out, exist_ok=True)
    stats = {"fields": 0, "agree_correct": 0, "queued": 0, "undetected_error": 0, "queued_where_A_correct": 0}
    per_kind = {"digital": dict(stats), "scanned": dict(stats)}
    queue, errors = [], []
    for m, ((fa, ra), (fb, rb), has_layer) in zip(manifest, reads):
        c = certs[(m["cert_no"], m["batch_id"])]
        truth = {"cert_no": c["cert_no"], "lot": c["filed_under"], "issue_date": c["issue_date"],
                 "pages_total": c["pages_total"], "pages_received": c["pages_received"]}
        truth.update({f"result:{t}": v for t, v in truth_r.get((m["cert_no"], m["batch_id"]), {}).items()})
        A = {**fa, **{f"result:{t}": valid(v, units[t]) for t, v in ra.items()}}
        B = {**fb, **{f"result:{t}": valid(v, units[t]) for t, v in rb.items()}}
        for R in (A, B):
            if R.get("lot") not in register:
                R["lot"] = None
        kind = "scanned" if m["scanned"] else "digital"
        for k, tv in truth.items():
            av, bv, tv = canon(A.get(k)), canon(B.get(k)), canon(tv)
            for s in (stats, per_kind[kind]):
                s["fields"] += 1
            if av == bv and av is not None:
                if av == tv:
                    for s in (stats, per_kind[kind]): s["agree_correct"] += 1
                else:
                    for s in (stats, per_kind[kind]): s["undetected_error"] += 1
                    errors.append({"file": m["file"], "field": k, "truth": tv, "read": av})
            else:
                for s in (stats, per_kind[kind]):
                    s["queued"] += 1
                    if av == tv: s["queued_where_A_correct"] += 1
                queue.append({"file": m["file"], "field": k, "read_A": av, "read_B": bv, "truth": tv})
    for name, rows in (("human_queue.csv", queue), ("undetected_errors.csv", errors)):
        with open(os.path.join(a.out, name), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["file"]); w.writeheader(); w.writerows(rows)
    def line(lbl, s):
        n = s["fields"] or 1
        return (f"{lbl:<9} fields {s['fields']:>5} | agreed+correct {s['agree_correct']/n:6.1%} | to human {s['queued']/n:6.1%} "
                f"| undetected errors {s['undetected_error']}")
    print(f"certificates {len(manifest)}")
    print(line("all", stats)); print(line("digital", per_kind["digital"])); print(line("scanned", per_kind["scanned"]))
    final = (stats["agree_correct"] + stats["queued"]) / max(1, stats["fields"])
    print(f"accuracy after human review of the queue: {final:.2%} (target >= 99.5 %, and 0 undetected errors)")
    json.dump({"stats": stats, "per_kind": per_kind}, open(os.path.join(a.out, "summary.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
