#!/usr/bin/env python3
"""Render every synthgmp certificate as a PDF: digital (text layer) or scanned-looking (image only).

Usage: python3 render_certs.py <data_dir> <out_dir> [--scanned-share 0.6] [--seed 7] [--limit N]
A certificate with pages_received < pages_total is rendered without its last page; the results that sit on that
page are the ones the data marks "on missing page". Every page prints "Page i of N", so the gap is visible.
"""
import argparse, csv, io, json, math, os, random, subprocess, tempfile
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from PIL import Image, ImageFilter
import numpy as np

W, H = A4

def rows_by_cert(results):
    out = {}
    for r in results:
        out.setdefault((r["cert_no"], r["batch_id"]), []).append(r)
    return out

def paginate(rows, pages_total):
    missing = [r for r in rows if r.get("note") == "on missing page"]
    present = [r for r in rows if r.get("note") != "on missing page"]
    body_pages = pages_total - 1 if missing else pages_total
    per = max(1, math.ceil(len(present) / max(1, body_pages)))
    pages = [present[i * per:(i + 1) * per] for i in range(body_pages)]
    if missing:
        pages.append(missing)
    while len(pages) < pages_total:
        pages.append([])
    return pages

def draw_cert(path, cert, lab, rows):
    c = canvas.Canvas(path, pagesize=A4)
    pages = paginate(rows, int(cert["pages_total"]))
    for i, page_rows in enumerate(pages, 1):
        if i > int(cert["pages_received"]):
            break
        y = H - 60
        c.setFont("Helvetica-Bold", 13); c.drawString(50, y, lab["name"]); y -= 16
        c.setFont("Helvetica", 9); c.drawString(50, y, lab["accreditation"]); y -= 28
        c.setFont("Helvetica-Bold", 12); c.drawString(50, y, f"CERTIFICATE OF ANALYSIS No. {cert['cert_no']}"); y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(50, y, f"Lot: {cert['filed_under']}"); c.drawString(300, y, f"Issue date: {cert['issue_date']}"); y -= 14
        c.drawString(50, y, f"Type: {cert['kind']}"); y -= 26
        c.setFont("Helvetica-Bold", 10)
        for x, t in ((50, "Test"), (250, "Result"), (360, "Unit"), (420, "Specification")):
            c.drawString(x, y, t)
        y -= 6; c.line(50, y, W - 50, y); y -= 16
        c.setFont("Helvetica", 10)
        for r in page_rows:
            c.drawString(50, y, r["test"]); c.drawString(250, y, r["result"])
            c.drawString(360, y, r["unit"]); c.drawString(420, y, r["criterion"][:28]); y -= 16
        c.setFont("Helvetica", 9)
        c.drawString(50, 40, "All data fictional - synthetic test document."); c.drawRightString(W - 50, 40, f"Page {i} of {cert['pages_total']}")
        c.showPage()
    c.save()

def scan_look(pdf_path, rnd):
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["pdftoppm", "-r", "200", "-gray", "-png", pdf_path, os.path.join(td, "p")], check=True)
        imgs = []
        for f in sorted(os.listdir(td)):
            im = Image.open(os.path.join(td, f)).convert("L")
            im = im.rotate(rnd.uniform(-0.9, 0.9), resample=Image.BICUBIC, expand=False, fillcolor=255)
            a = np.asarray(im, dtype=np.int16)
            a = np.clip(a + np.random.default_rng(rnd.randint(0, 10**9)).normal(0, 9, a.shape), 0, 255).astype(np.uint8)
            im = Image.fromarray(a).filter(ImageFilter.GaussianBlur(0.6))
            buf = io.BytesIO(); im.save(buf, "JPEG", quality=70); buf.seek(0)
            imgs.append(Image.open(buf).convert("L"))
        imgs[0].save(pdf_path, "PDF", resolution=200, save_all=True, append_images=imgs[1:])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("out")
    ap.add_argument("--scanned-share", type=float, default=0.6)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    spec = json.load(open(os.path.join(a.data, "spec.json"), encoding="utf-8"))
    certs = list(csv.DictReader(open(os.path.join(a.data, "certificates.csv"), encoding="utf-8")))
    by = rows_by_cert(list(csv.DictReader(open(os.path.join(a.data, "results.csv"), encoding="utf-8"))))
    if a.limit:
        flagged = [c for c in certs if c["pages_received"] != c["pages_total"] or c["filed_under"] != c["batch_id"] or c["kind"] == "retest"]
        rest = [c for c in certs if c not in flagged]
        certs = flagged + rnd.sample(rest, max(0, a.limit - len(flagged)))
    os.makedirs(a.out, exist_ok=True)
    manifest = []
    for c in certs:
        name = f"{c['batch_id']}__{c['cert_no'].replace('/', '-')}.pdf"
        path = os.path.join(a.out, name)
        draw_cert(path, c, spec["labs"][c["lab"]], by.get((c["cert_no"], c["batch_id"]), []))
        scanned = rnd.random() < a.scanned_share
        if scanned:
            scan_look(path, rnd)
        manifest.append({"file": name, "cert_no": c["cert_no"], "batch_id": c["batch_id"], "scanned": scanned})
    json.dump(manifest, open(os.path.join(a.out, "manifest.json"), "w"), indent=1)
    print(f"{len(manifest)} certificate PDFs -> {a.out} ({sum(m['scanned'] for m in manifest)} scanned-looking)")

if __name__ == "__main__":
    main()
