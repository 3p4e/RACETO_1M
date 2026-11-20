#!/usr/bin/env python3
"""synthgmp - deterministic synthetic GMP batch and analysis data.

Generates a fictional company's production batches, external and in-house
laboratory certificates, results, and a ground-truth list of planted defects.
Every name, number and limit is invented or modelled on a public text
(see spec_demo.json). Nothing comes from any real company.

Usage: python3 generate.py [--batches 200] [--seed 42] [--spec spec_demo.json] [--out out]
"""
import argparse, csv, datetime as dt, hashlib, json, math, os, random

DEFECTS = {
    "OOS_POTENCY":      "Total THC outside the grade window",
    "OOS_LOD":          "Loss on drying above the limit",
    "OOS_MICRO":        "TAMC above the limit",
    "MISSING_PAGE":     "Contaminant certificate received without one page; results on it absent",
    "LAB_DISAGREEMENT": "A second laboratory reports potency more than 10 % (rel.) away from the first",
    "SUBLOT_TRAP":      "Sister sub-lots with different results; one certificate filed under the parent code",
    "RESULT_AFTER_PACK":"A release result is dated after the packaging date",
    "DUP_CERT_NO":      "The same certificate number appears on two different batches",
    "RETEST_DRIFT":     "Retest months later: THC down, CBN up (expected degradation, CBN may exceed)",
}

def d(x):
    return x.isoformat()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batches", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--spec", default=os.path.join(os.path.dirname(__file__), "spec_demo.json"))
    ap.add_argument("--out", default="out")
    ap.add_argument("--defect-rate", type=float, default=0.18)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    spec = json.load(open(a.spec, encoding="utf-8"))
    tests = spec["tests"]
    os.makedirs(a.out, exist_ok=True)

    batches, certs, results, defects = [], [], [], []
    cert_seq = {"LAB-A": 1000, "LAB-B": 5000, "LAB-C": 300, "INHOUSE": 1}
    start = dt.date(2025, 1, 6)

    def new_cert(lab, batch_id, issued, pages=None, kind="release"):
        cert_seq[lab] += 1
        prefix = {"LAB-A": "A", "LAB-B": "B", "LAB-C": "C", "INHOUSE": "IQC"}[lab]
        no = f"{prefix}-{cert_seq[lab]}/{issued.year % 100:02d}"
        pages = pages or rnd.choice([2, 3, 4])
        c = {"cert_no": no, "lab": lab, "batch_id": batch_id, "kind": kind,
             "issue_date": d(issued), "pages_total": pages, "pages_received": pages,
             "filed_under": batch_id}
        certs.append(c)
        return c

    def value_for(t, cv, rnd, months=0, force_fail=False, ctx=None):
        ctx = ctx if ctx is not None else {}
        """Return (result string, numeric or None, conforms bool)."""
        ty = t["type"]
        if ty == "pass":
            return "Conforms", None, True
        if ty == "nd":
            return "ND (all residues in scope)", None, True
        if ty == "absent":
            return ("Present" if force_fail else "Absent"), None, not force_fail
        if ty == "assay":
            nominal = cv["thc_nominal"] if t["name"].endswith("THC") else cv["cbd_nominal"]
            decay = math.exp(-0.012 * months) if t["name"].endswith("THC") else 1.0
            if nominal < 1.0:  # low-content cannabinoid: reported against a maximum, not a window
                v = round(rnd.uniform(0.03, 0.4), 2)
                return f"{v:.2f}", v, v <= 1.0
            v = nominal * decay * min(1.08, max(0.92, rnd.gauss(1.0, 0.035)))
            if force_fail:
                v = nominal * (1 + rnd.choice([-1, 1]) * rnd.uniform(0.12, 0.22))
            lo, hi = nominal * (1 - t["window_rel"]), nominal * (1 + t["window_rel"])
            v = round(max(v, 0.01), 2)
            return f"{v:.2f}", v, lo <= v <= hi
        if ty in ("max", "max_cfu"):
            lim = t["limit"]
            if ty == "max_cfu":
                v = 10 ** rnd.uniform(1.0, math.log10(lim) - 0.7)
                if force_fail:
                    v = lim * rnd.uniform(1.5, 8)
                v = int(round(v, -1)) or 10
                return f"{v:.0e}".replace("e+0", "x10^").replace("e+", "x10^"), v, v <= lim
            if t["name"] == "CBN":
                v = rnd.uniform(0.05, 0.25) + 0.035 * months
            elif t["name"] == "Loss on drying":
                v = min(9.6, rnd.gauss(8.0, 0.7))
            elif t["name"].startswith("Total aflatoxins") and ctx.get("b1") is not None:
                v = ctx["b1"] + lim * rnd.uniform(0.0, 0.2)
            else:
                v = lim * rnd.uniform(0.02, 0.45)
            if t["name"] == "Aflatoxin B1":
                ctx["b1"] = round(v, 2)
            if force_fail:
                v = lim * rnd.uniform(1.08, 1.4)
            v = round(max(v, 0.0), 2 if lim >= 1 else 3)
            loq = lim * 0.05
            txt = f"< {loq:.2g} (LOQ)" if v < loq else f"{v}"
            return txt, v, v <= lim
        raise ValueError(ty)

    n_def = int(round(a.batches * a.defect_rate))
    defect_slots = rnd.sample(range(10, a.batches), n_def)  # the first 10 lots stay clean (a duplicate needs an earlier lot)
    kinds = list(DEFECTS)
    planned = {i: kinds[k % len(kinds)] for k, i in enumerate(defect_slots)}

    for i in range(a.batches):
        cv = rnd.choice(spec["cultivars"])
        harvest = start + dt.timedelta(days=int(i * 3.4) + rnd.randint(0, 2))
        manuf = harvest + dt.timedelta(days=rnd.randint(14, 24))
        pack = manuf + dt.timedelta(days=rnd.randint(18, 28))  # release testing completes before packaging
        parent = f"{cv['code']}{harvest:%m%y}{i % 7 + 1:02d}"
        bid = f"DMO-{harvest:%y}-{i + 1:03d}"
        sub = ""
        defect = planned.get(i)
        if defect == "SUBLOT_TRAP":
            sub = "/1"
        batches.append({"batch_id": bid, "cultivation_batch": parent + sub, "product": f"{cv['name']} dried flower (fictional)",
                        "cultivar_code": cv["code"], "harvest_date": d(harvest), "manufacture_date": d(manuf),
                        "packaging_date": d(pack), "batch_size_kg": round(rnd.uniform(4, 40), 1)})

        test_day = manuf + dt.timedelta(days=rnd.randint(1, 3))
        issued = {lab: test_day + dt.timedelta(days=rnd.randint(3, 12)) for lab in ("LAB-A", "LAB-B", "LAB-C")}
        issued["INHOUSE"] = test_day
        if defect == "RESULT_AFTER_PACK":
            issued["LAB-C"] = pack + dt.timedelta(days=rnd.randint(5, 20))
        cmap = {lab: new_cert(lab, bid, iss) for lab, iss in issued.items()}
        if defect == "MISSING_PAGE":
            cmap["LAB-B"]["pages_total"] = max(cmap["LAB-B"]["pages_total"], 3)
            cmap["LAB-B"]["pages_received"] = cmap["LAB-B"]["pages_total"] - 1
        if defect == "DUP_CERT_NO":
            # copy from a lot made clearly earlier (>= 10 lots back), so production order is unambiguous
            earlier = [c for c in certs if c["lab"] == "LAB-A" and c["kind"] == "release"
                       and c["batch_id"][-3:].isdigit() and int(c["batch_id"][-3:]) <= i + 1 - 10]
            if earlier:
                cmap["LAB-A"]["cert_no"] = earlier[-1]["cert_no"]
            else:
                defect = None  # nothing earlier to duplicate: plant nothing, list nothing

        fail_test = {"OOS_POTENCY": "Total THC", "OOS_LOD": "Loss on drying", "OOS_MICRO": "TAMC"}.get(defect)
        missing_names = {"Total aflatoxins (B1+B2+G1+G2)", "Lead (Pb)", "Pesticide residues"} if defect == "MISSING_PAGE" else set()
        ctx = {}
        for t in tests:
            c = cmap[t["lab"]]
            if t["name"] in missing_names:
                results.append({"batch_id": bid, "cert_no": c["cert_no"], "lab": t["lab"], "test_id": t["id"], "test": t["name"],
                                "result": "", "unit": t.get("unit", ""), "criterion": crit(t, cv), "conforms": "",
                                "analysis_date": d(test_day), "kind": "release", "note": "on missing page"})
                continue
            txt, v, ok = value_for(t, cv, rnd, 0, force_fail=(t["name"] == fail_test), ctx=ctx)
            results.append({"batch_id": bid, "cert_no": c["cert_no"], "lab": t["lab"], "test_id": t["id"], "test": t["name"],
                            "result": txt, "unit": t.get("unit", ""), "criterion": crit(t, cv), "conforms": "yes" if ok else "no",
                            "analysis_date": d(test_day), "kind": "release", "note": ""})

        if defect == "LAB_DISAGREEMENT":
            c2 = new_cert("LAB-C", bid, issued["LAB-A"] + dt.timedelta(days=2))
            first = next(r for r in results if r["batch_id"] == bid and r["test"] == "Total THC")
            v2 = round(float(first["result"]) * rnd.choice([0.85, 1.14]), 2)
            results.append({"batch_id": bid, "cert_no": c2["cert_no"], "lab": "LAB-C", "test_id": "3", "test": "Total THC",
                            "result": f"{v2:.2f}", "unit": "%", "criterion": first["criterion"], "conforms": "",
                            "analysis_date": d(test_day), "kind": "release", "note": "second laboratory"})
        if defect == "SUBLOT_TRAP":
            sis = dict(batches[-1]); sis["batch_id"] = bid + "S"; sis["cultivation_batch"] = parent + "/2"
            batches.append(sis)
            c3 = new_cert("LAB-A", sis["batch_id"], issued["LAB-A"])
            c3["filed_under"] = parent
            for t in [t for t in tests if t["lab"] == "LAB-A"]:
                txt, v, ok = value_for(t, cv, rnd)
                results.append({"batch_id": sis["batch_id"], "cert_no": c3["cert_no"], "lab": "LAB-A", "test_id": t["id"], "test": t["name"],
                                "result": txt, "unit": t.get("unit", ""), "criterion": crit(t, cv), "conforms": "yes" if ok else "no",
                                "analysis_date": d(test_day), "kind": "release", "note": "sister sub-lot; filed under parent code"})
        if defect == "RETEST_DRIFT":
            months = rnd.randint(8, 14)
            rday = test_day + dt.timedelta(days=30 * months)
            c4 = new_cert("LAB-A", bid, rday + dt.timedelta(days=5), kind="retest")
            for t in [t for t in tests if t["lab"] == "LAB-A"]:
                txt, v, ok = value_for(t, cv, rnd, months)
                results.append({"batch_id": bid, "cert_no": c4["cert_no"], "lab": "LAB-A", "test_id": t["id"], "test": t["name"],
                                "result": txt, "unit": t.get("unit", ""), "criterion": crit(t, cv), "conforms": "yes" if ok else "no",
                                "analysis_date": d(rday), "kind": "retest", "note": f"retest after {months} months"})
        if defect:
            defects.append({"batch_id": bid, "defect": defect, "description": DEFECTS[defect]})

    def write(name, rows):
        p = os.path.join(a.out, name)
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        return p

    files = [write("batches.csv", batches), write("certificates.csv", certs), write("results.csv", results),
             write("defects_ground_truth.csv", defects)]
    json.dump(spec, open(os.path.join(a.out, "spec.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    files.append(os.path.join(a.out, "spec.json"))
    manifest = {"generator": "synthgmp 0.1", "seed": a.seed, "batches_requested": a.batches,
                "batches_written": len(batches), "certificates": len(certs), "results": len(results),
                "planted_defects": len(defects), "all_fictional": True,
                "sha256": {os.path.basename(p): hashlib.sha256(open(p, "rb").read()).hexdigest() for p in files}}
    json.dump(manifest, open(os.path.join(a.out, "MANIFEST.json"), "w"), indent=2)
    print(json.dumps({k: v for k, v in manifest.items() if k != "sha256"}, indent=2))

def crit(t, cv):
    if t["type"] == "assay":
        nominal = cv["thc_nominal"] if t["name"].endswith("THC") else cv["cbd_nominal"]
        if nominal < 1.0:
            return "<= 1.0 %"
        lo, hi = nominal * (1 - t["window_rel"]), nominal * (1 + t["window_rel"])
        return f"{nominal:.2f} % ({lo:.2f}-{hi:.2f} %)"
    if t["type"] in ("max", "max_cfu"):
        return f"<= {t['limit']:g} {t['unit']}"
    return t.get("criterion", "")

if __name__ == "__main__":
    main()
