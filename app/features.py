"""Kaufhilfe und Komfort: Simulator, Sets, Lichtgewinn, Fototage, Trefferquote, Vergleich, Datenqualität.
Alles reine Zahlen aus den eigenen Fotos, keine Empfehlung."""
import math
import os
import statistics

import analyse
import db
from analyse import CLASSES, GOOD, in_range, pct

PRIME_TOL = 0.06   # Festbrennweite: ±6 %, z. B. 85 mm deckt 80–90 mm ab
ISO_LIMIT = 3200
SMALL_SAMPLE = 30

PRESETS = [
    {"id": "14-24-28", "name": "14-24 f/2.8", "min": 14, "max": 24, "ap": 2.8},
    {"id": "14-30-4", "name": "14-30 f/4", "min": 14, "max": 30, "ap": 4.0},
    {"id": "24-70-28", "name": "24-70 f/2.8", "min": 24, "max": 70, "ap": 2.8},
    {"id": "24-120-4", "name": "24-120 f/4", "min": 24, "max": 120, "ap": 4.0},
    {"id": "35-18", "name": "35 f/1.8", "min": 35, "max": 35, "ap": 1.8},
    {"id": "50-18", "name": "50 f/1.8", "min": 50, "max": 50, "ap": 1.8},
    {"id": "85-18", "name": "85 f/1.8", "min": 85, "max": 85, "ap": 1.8},
    {"id": "70-200-28", "name": "70-200 f/2.8", "min": 70, "max": 200, "ap": 2.8},
    {"id": "100-400", "name": "100-400 f/4.5-5.6", "min": 100, "max": 400, "ap": 4.5},
    {"id": "180-600", "name": "180-600 f/5.6-6.3", "min": 180, "max": 600, "ap": 5.6},
]


def lens_range(L):
    mn, mx = float(L["min"]), float(L["max"])
    if mx - mn < 1:
        return mn * (1 - PRIME_TOL), mx * (1 + PRIME_TOL)
    return mn - 0.5, mx + 0.5


def covered(lenses, kb):
    return any(lo <= kb <= hi for lo, hi in lenses)


def miss_kind(ranges, kb):
    if kb < min(r[0] for r in ranges):
        return "below"
    if kb > max(r[1] for r in ranges):
        return "above"
    return "gap"


def _top(items, key, limit=8):
    c = {}
    for i in items:
        c[i[key]] = c.get(i[key], 0) + 1
    return [{"name": k, "n": v} for k, v in sorted(c.items(), key=lambda x: -x[1])[:limit]]


def simulate(conn, f, sets):
    imgs = [i for i in analyse.selected(conn, f) if i["kb"]]
    total = len(imgs)
    single = []
    for p in PRESETS:
        r = [lens_range(p)]
        n = sum(1 for i in imgs if covered(r, i["kb"]))
        single.append(dict(p, n=n, pct=pct(n, total), lo=round(r[0][0], 1), hi=round(r[0][1], 1)))
    prepared = []
    for s in (sets or [])[:3]:
        lenses = [L for L in s.get("lenses", []) if L.get("min") and L.get("max")]
        prepared.append((s, lenses, [lens_range(L) for L in lenses]))
    flags = [[bool(rg) and covered(rg, i["kb"]) for _, _, rg in prepared] for i in imgs]
    out = []
    for idx, (s, lenses, rg) in enumerate(prepared):
        hit = sum(1 for fl in flags if fl[idx])
        missed = [i for i, fl in zip(imgs, flags) if not fl[idx]]
        kinds = {"below": 0, "above": 0, "gap": 0}
        if rg:
            for i in missed:
                kinds[miss_kind(rg, i["kb"])] += 1
        only = sum(1 for fl in flags if fl[idx] and sum(fl) == 1)
        per = []
        for L, one in zip(lenses, rg):
            k = sum(1 for i in imgs if one[0] <= i["kb"] <= one[1])
            excl = sum(1 for i in imgs if one[0] <= i["kb"] <= one[1]
                       and not any(o[0] <= i["kb"] <= o[1] for o in rg if o is not one))
            per.append({"name": L.get("name") or "%g-%g" % (L["min"], L["max"]), "n": k, "pct": pct(k, total),
                        "only": excl, "only_pct": pct(excl, total)})
        classes = [{"label": lab, "n": sum(1 for i in missed if in_range(i["kbr"], lo, hi))}
                   for lab, lo, hi in CLASSES]
        out.append({"name": s.get("name") or "Set %d" % (idx + 1), "lenses": per, "n": hit, "pct": pct(hit, total),
                    "missed": len(missed), "missed_pct": pct(len(missed), total), "kinds": kinds,
                    "only_this_set": only, "missed_classes": [c for c in classes if c["n"]],
                    "missed_lenses": _top(missed, "lens"), "def": {"lenses": lenses}})
    return {"total": total, "single": single, "sets": out, "presets": PRESETS, "prime_tol": PRIME_TOL}


def light(conn, f, mn, mx, ap):
    """Fotos mit ISO > 3200 bei Offenblende, die das neue Objektiv lichtstärker machen könnte."""
    rg = lens_range({"min": mn, "max": mx})
    imgs = [i for i in analyse.selected(conn, f) if i["kb"] and rg[0] <= i["kb"] <= rg[1]]
    high = [i for i in imgs if i["iso"] and i["iso"] > ISO_LIMIT]
    wo = [i for i in high if i["wo"] is True and i["fnum"]]
    gain = [i for i in wo if i["fnum"] > ap * 1.04]
    rows = []
    for i in gain:
        stops = 2 * math.log2(i["fnum"] / ap)
        rows.append((i, stops, i["iso"] / (2 ** stops)))

    def block(items):
        if not items:
            return {"n": 0, "stops": None, "iso_old": None, "iso_new": None, "under": 0, "under_pct": 0}
        under = sum(1 for _, _, new in items if new <= ISO_LIMIT)
        return {"n": len(items), "stops": round(statistics.median(s for _, s, _ in items), 2),
                "iso_old": round(statistics.median(i["iso"] for i, _, _ in items)),
                "iso_new": round(statistics.median(new for _, _, new in items)),
                "under": under, "under_pct": pct(under, len(items))}

    groups = {}
    for x in rows:
        groups.setdefault(x[0]["lens"], []).append(x)
    by_lens = sorted([dict(block(g), lens=k) for k, g in groups.items()], key=lambda x: -x["n"])
    buckets = [("unter ½ Blende", 0, .5), ("½ bis 1 Blende", .5, 1), ("1 bis 2 Blenden", 1, 2), ("ab 2 Blenden", 2, 99)]
    dist = [{"label": lab, "n": sum(1 for _, s, _ in rows if lo <= s < hi)} for lab, lo, hi in buckets]
    return {"range": [round(rg[0], 1), round(rg[1], 1)], "ap": ap, "n_range": len(imgs), "n_high": len(high),
            "n_wo": len(wo), "n_not_wo": len(high) - len(wo), "n_already": len(wo) - len(gain),
            "all": block(rows), "by_lens": by_lens, "dist": dist, "iso_limit": ISO_LIMIT}


def days(conn, f, wide=28, tele=100):
    imgs = [i for i in analyse.selected(conn, f) if i["date"]]
    by_day = {}
    for i in imgs:
        by_day.setdefault(i["date"], []).append(i)

    def info(d, g):
        kbs = [i["kb"] for i in g if i["kb"]]
        return {"date": d, "n": len(g), "lenses": len({i["lens"] for i in g}),
                "min": round(min(kbs), 1) if kbs else None, "max": round(max(kbs), 1) if kbs else None,
                "both": bool(kbs) and min(kbs) <= wide and max(kbs) >= tele}

    infos = {d: info(d, g) for d, g in by_day.items()}
    nd = len(infos)
    dist = [{"label": lab, "days": c, "pct": pct(c, nd)} for lab, test in
            [("1 Objektiv", lambda x: x == 1), ("2 Objektive", lambda x: x == 2), ("3 Objektive", lambda x: x == 3),
             ("4 und mehr", lambda x: x >= 4)]
            for c in [sum(1 for x in infos.values() if test(x["lenses"]))]]
    lens_days = {}
    for d, g in by_day.items():
        names = {i["lens"] for i in g}
        for L in names:
            e = lens_days.setdefault(L, {"lens": L, "days": 0, "alone": 0, "n": 0})
            e["days"] += 1
            e["alone"] += 1 if len(names) == 1 else 0
        for i in g:
            lens_days[i["lens"]]["n"] += 1
    per_lens = sorted(lens_days.values(), key=lambda x: -x["days"])
    for e in per_lens:
        e["days_pct"] = pct(e["days"], nd)

    suffices = []
    for p in PRESETS:
        rg = [lens_range(p)]
        full = near = 0
        for g in by_day.values():
            kbs = [i["kb"] for i in g if i["kb"]]
            if not kbs:
                continue
            k = sum(1 for v in kbs if covered(rg, v))
            full += k == len(kbs)
            near += k >= 0.9 * len(kbs)
        suffices.append({"name": p["name"], "full": full, "full_pct": pct(full, nd), "near": near, "near_pct": pct(near, nd)})

    cam_days = {}
    for g in by_day.values():
        names = {i["camera"] for i in g}
        for C in names:
            e = cam_days.setdefault(C, {"camera": C, "days": 0, "alone": 0, "n": 0})
            e["days"] += 1
            e["alone"] += 1 if len(names) == 1 else 0
        for i in g:
            cam_days[i["camera"]]["n"] += 1
    per_camera = sorted(cam_days.values(), key=lambda x: -x["days"])
    for e in per_camera:
        e["days_pct"] = pct(e["days"], nd)
    day_rows = []
    for d in sorted(by_day, reverse=True):
        g = by_day[d]
        day_rows.append(dict(infos[d], cameras=len({i["camera"] for i in g}), top=[e["name"] for e in _top(g, "lens", 2)],
                             top_camera=_top(g, "camera", 1)[0]["name"]))

    # Reisen: mindestens zwei aufeinanderfolgende Fototage
    import datetime as dt
    trips, cur = [], []
    for d in sorted(by_day):
        day = dt.date(int(d[:4]), int(d[5:7]), int(d[8:10]))
        if cur and (day - cur[-1][0]).days != 1:
            trips.append(cur)
            cur = []
        cur.append((day, d))
    if cur:
        trips.append(cur)
    trip_rows = []
    for t in trips:
        if len(t) < 2:
            continue
        g = [i for _, d in t for i in by_day[d]]
        x = info(t[0][1], g)
        trip_rows.append({"from": t[0][1], "to": t[-1][1], "days": len(t), "n": len(g), "lenses": x["lenses"],
                          "min": x["min"], "max": x["max"], "both": x["both"],
                          "top": [e["name"] for e in _top(g, "lens", 3)]})
    trip_rows.sort(key=lambda x: x["from"], reverse=True)
    both = sum(1 for x in infos.values() if x["both"])
    return {"days": nd, "n": len(imgs), "per_day": round(len(imgs) / nd, 1) if nd else 0, "dist": dist,
            "both": both, "both_pct": pct(both, nd), "wide": wide, "tele": tele, "per_lens": per_lens,
            "suffices": suffices, "per_camera": per_camera, "day_rows": day_rows, "trips": trip_rows[:60], "n_trips": len(trip_rows)}


def keepers(conn, f):
    imgs = analyse.load(conn, f)
    rated_all = sum(1 for i in imgs if i["rating"] and i["rating"] > 0)

    def table(key, order=None):
        groups = {}
        for i in imgs:
            v = key(i)
            if v is not None:
                groups.setdefault(v, []).append(i)
        out = []
        for k, g in groups.items():
            rated = sum(1 for i in g if i["rating"] and i["rating"] > 0)
            good = sum(1 for i in g if i["rating"] and i["rating"] >= GOOD)
            out.append({"name": k, "n": len(g), "rated": rated, "good": good, "good_pct": pct(good, len(g)),
                        "of_rated": pct(good, rated), "small": rated < SMALL_SAMPLE})
        if order:
            return sorted(out, key=lambda x: order.index(x["name"]))
        return sorted(out, key=lambda x: (x["small"], -x["good_pct"], -x["n"]))

    labels = [c[0] for c in CLASSES]

    def klass(i):
        for lab, lo, hi in CLASSES:
            if in_range(i["kbr"], lo, hi):
                return lab
        return None

    hint = None
    if rated_all < 0.2 * max(1, len(imgs)):
        hint = ("Nur %s %% der Fotos sind bewertet. Die Quoten zeigen also, wo du bewertet hast, "
                "und sind nur ein grober Anhaltspunkt." % analyse.fmt(pct(rated_all, len(imgs))))
    return {"n": len(imgs), "rated": rated_all, "rated_pct": pct(rated_all, len(imgs)),
            "good": sum(1 for i in imgs if i["rating"] and i["rating"] >= GOOD), "hint": hint,
            "small": SMALL_SAMPLE, "lens": table(lambda i: i["lens"]),
            "classes": table(klass, order=[x for x in labels if any(klass(i) == x for i in imgs)]),
            "camera": table(lambda i: i["camera"])}


def compare(conn, f, a, b):
    def side(ov):
        g = dict(f)
        for k in ("cameras", "lenses"):
            if ov.get(k):
                g[k] = ov[k]
        for k in ("from", "to"):
            if ov.get(k):
                g[k] = ov[k]
        imgs = [i for i in analyse.selected(conn, g)]
        kb = [i for i in imgs if i["kb"]]
        n = len(kb)
        high = [i for i in imgs if i["iso"] and i["iso"] > ISO_LIMIT]
        wo = [i for i in imgs if i["wo"] is True]
        known = [i for i in imgs if i["wo"] is not None]
        lens = {}
        for i in imgs:
            lens[i["lens"]] = lens.get(i["lens"], 0) + 1
        cams = {}
        for i in imgs:
            cams[i["camera"]] = cams.get(i["camera"], 0) + 1
        isos = [i["iso"] for i in imgs if i["iso"]]
        fnums = [i["fnum"] for i in imgs if i["fnum"]]
        return {"n": len(imgs), "n_kb": n, "days": len({i["date"] for i in imgs if i["date"]}),
                "median_iso": round(statistics.median(isos)) if isos else None,
                "median_fnum": round(statistics.median(fnums), 1) if fnums else None,
                "good": pct(sum(1 for i in imgs if i["rating"] and i["rating"] >= GOOD), len(imgs)),
                "cameras": {k: pct(v, len(imgs)) for k, v in cams.items()},
                "median": round(statistics.median(i["kb"] for i in kb), 1) if kb else None,
                "metrics": {"u24": pct(sum(1 for i in kb if i["kb"] < 24), n),
                            "u20": pct(sum(1 for i in kb if i["kb"] < 20), n),
                            "m50": pct(sum(1 for i in kb if 45 <= i["kb"] <= 55), n),
                            "m85": pct(sum(1 for i in kb if 80 <= i["kb"] <= 90), n),
                            "o200": pct(sum(1 for i in kb if i["kb"] > 200), n),
                            "iso": pct(len(high), len(imgs)), "wo": pct(len(wo), len(known))},
                "classes": [{"label": lab, "pct": pct(sum(1 for i in kb if in_range(i["kbr"], lo, hi)), n)}
                            for lab, lo, hi in CLASSES],
                "lens": {k: pct(v, len(imgs)) for k, v in lens.items()}}

    A, B = side(a or {}), side(b or {})
    names = sorted(set(A["lens"]) | set(B["lens"]),
                   key=lambda k: -max(A["lens"].get(k, 0), B["lens"].get(k, 0)))[:15]
    lens = [{"lens": k, "a": A["lens"].get(k, 0), "b": B["lens"].get(k, 0),
             "diff": round(B["lens"].get(k, 0) - A["lens"].get(k, 0), 1)} for k in names]
    cam_names = sorted(set(A["cameras"]) | set(B["cameras"]),
                       key=lambda k: -max(A["cameras"].get(k, 0), B["cameras"].get(k, 0)))[:15]
    cameras = [{"lens": k, "a": A["cameras"].get(k, 0), "b": B["cameras"].get(k, 0),
                "diff": round(B["cameras"].get(k, 0) - A["cameras"].get(k, 0), 1)} for k in cam_names]
    labels = [("u24", "unter 24 mm"), ("u20", "unter 20 mm"), ("m50", "um 50 mm"), ("m85", "um 85 mm"),
              ("o200", "über 200 mm"), ("iso", "ISO über 3200"), ("wo", "bei Offenblende")]
    metrics = [{"key": k, "label": lab, "a": A["metrics"][k], "b": B["metrics"][k],
                "diff": round(B["metrics"][k] - A["metrics"][k], 1)} for k, lab in labels]
    classes = [{"label": x["label"], "a": x["pct"], "b": y["pct"], "diff": round(y["pct"] - x["pct"], 1)}
               for x, y in zip(A["classes"], B["classes"])]
    keys = ("n", "n_kb", "median", "days", "median_iso", "median_fnum", "good")
    return {"a": {k: A[k] for k in keys}, "b": {k: B[k] for k in keys},
            "metrics": metrics, "classes": classes, "lens": lens, "cameras": cameras}


# ---------------------------------------------------------------- Datenqualität

ISSUES = [
    ("no_lens", "Ohne Objektivangabe", lambda i: not i["lens_raw"]),
    ("no_fl", "Ohne Brennweite", lambda i: not i["fl"]),
    ("no_fnum", "Ohne Blende", lambda i: not i["fnum"]),
    ("no_iso", "Ohne ISO", lambda i: not i["iso"]),
    ("no_date", "Ohne Aufnahmedatum", lambda i: not i["dt"]),
    ("unconfirmed", "Objektiv noch nicht bestätigt", lambda i: i["lens"].endswith(" (?)")),
    ("out_of_range", "Brennweite passt nicht zum Objektiv", lambda i: _out_of_range(i)),
]


def _out_of_range(i):
    L = i["lens_info"] or {}
    mn, mx = L.get("min_fl"), L.get("max_fl")
    return bool(i["fl"] and mn and mx and (i["fl"] < mn * 0.93 or i["fl"] > mx * 1.07))


def issue_test(key):
    for k, _, test in ISSUES:
        if k == key:
            return test
    if key == "unsure_dup":
        return None
    return None


def unsure_ids(conn):
    """Gezählte Bilder ohne Sekundenbruchteile, die sich Kamera und Sekunde mit anderen teilen."""
    rows = conn.execute(
        "SELECT id, camera_key, dt, subsec FROM images WHERE canonical=1 AND dt IS NOT NULL AND camera_key<>''").fetchall()
    groups = {}
    for r in rows:
        groups.setdefault((r["camera_key"], r["dt"]), []).append(r)
    ids = set()
    for g in groups.values():
        if len(g) > 1 and any(not r["subsec"] for r in g):
            ids.update(r["id"] for r in g)
    return ids


def quality(conn):
    imgs = analyse.base_rows(conn)
    out = []
    for key, label, test in ISSUES:
        hit = [i for i in imgs if test(i)]
        out.append({"key": key, "label": label, "n": len(hit), "pct": pct(len(hit), len(imgs)),
                    "lenses": _top(hit, "camera", 3)})
    uns = unsure_ids(conn)
    hit = [i for i in imgs if i["id"] in uns]
    out.append({"key": "unsure_dup", "label": "Mögliche Duplikate (gleiche Sekunde, ohne Sekundenbruchteile)",
                "n": len(hit), "pct": pct(len(hit), len(imgs)), "lenses": _top(hit, "camera", 3)})
    cams = []
    for r in conn.execute("SELECT c.name, c.make, c.model, c.crop, c.crop_src, c.enabled, COUNT(i.id) n FROM cameras c "
                          "LEFT JOIN images i ON i.camera_key=c.key AND i.canonical=1 GROUP BY c.key"):
        k = db.known_crop(r["make"], r["model"])
        differs = k is not None and abs((r["crop"] or 1) - k) / k > 0.1
        if differs or r["crop_src"] == "annahme":
            cams.append({"name": r["name"], "crop": r["crop"], "expected": k, "enabled": bool(r["enabled"]), "n": r["n"]})
    disabled = conn.execute("SELECT COUNT(*) FROM images i JOIN cameras c ON c.key=i.camera_key "
                            "WHERE i.canonical=1 AND c.enabled=0").fetchone()[0]
    folders = [{"path": r["path"], "online": os.path.isdir(r["path"]), "last_scan": r["last_scan"],
                "files": conn.execute("SELECT COUNT(*) FROM images WHERE folder_id=?", (r["id"],)).fetchone()[0]}
               for r in conn.execute("SELECT * FROM folders ORDER BY path").fetchall()]
    nocam = conn.execute("SELECT COUNT(*) FROM images WHERE camera_key IS NULL OR camera_key=''").fetchone()[0]
    return {"total": len(imgs), "issues": out, "crop_check": cams, "disabled": disabled, "no_camera": nocam,
            "dups": conn.execute("SELECT COUNT(*) FROM images WHERE canonical=0").fetchone()[0],
            "failed": conn.execute("SELECT COUNT(*) FROM failed").fetchone()[0], "folders": folders}


# ---------------------------------------------------------------- Beispielbilder

def photos(conn, f, spec, offset=0, limit=60):
    """Fotos zu einem angeklickten Wert. Alle Bedingungen in spec gelten zusammen."""
    spec = spec or {}
    imgs = analyse.base_rows(conn) if spec.get("ignoreFilter") else analyse.selected(conn, f)
    tests = []
    if spec.get("lens"):
        tests.append(lambda i: i["lens"] == spec["lens"])
    if spec.get("kb_min") is not None:
        tests.append(lambda i: i["kb"] and i["kbr"] >= spec["kb_min"])
    if spec.get("kb_max") is not None:
        tests.append(lambda i: i["kb"] and i["kbr"] <= spec["kb_max"])
    if spec.get("kb_under") is not None:
        tests.append(lambda i: i["kb"] and i["kb"] < spec["kb_under"])
    if spec.get("fl") is not None:
        tests.append(lambda i: i["fl"] and int(round(i["fl"])) == spec["fl"])
    if spec.get("fnum") is not None:
        tests.append(lambda i: i["fnum"] and round(i["fnum"], 1) == spec["fnum"])
    if spec.get("year") is not None:
        tests.append(lambda i: i["year"] == spec["year"])
    if spec.get("day"):
        tests.append(lambda i: i["date"] == spec["day"])
    if spec.get("from") and spec.get("to"):
        tests.append(lambda i: i["date"] and spec["from"] <= i["date"] <= spec["to"])
    if spec.get("iso_over") is not None:
        tests.append(lambda i: i["iso"] and i["iso"] > spec["iso_over"])
    if spec.get("wide_open"):
        tests.append(lambda i: i["wo"] is True)
    if spec.get("rating_min") is not None:
        tests.append(lambda i: i["rating"] and i["rating"] >= spec["rating_min"])
    if spec.get("camera"):
        tests.append(lambda i: i["camera"] == spec["camera"])
    if spec.get("range"):
        lo, hi = spec["range"]
        tests.append(lambda i: i["kb"] and lo <= i["kb"] <= hi)
    if spec.get("rule"):
        import insights
        tests.append(insights.rule_test(spec["rule"]))
    if spec.get("issue"):
        if spec["issue"] == "unsure_dup":
            ids = unsure_ids(conn)
            tests.append(lambda i: i["id"] in ids)
        else:
            t = issue_test(spec["issue"])
            if t:
                tests.append(t)
    if spec.get("set"):
        rg = [lens_range(L) for L in spec["set"].get("lenses", [])]
        kind = spec.get("kind") or "missed"
        if rg:
            def test_set(i):
                if not i["kb"] or covered(rg, i["kb"]):
                    return False
                return kind == "missed" or miss_kind(rg, i["kb"]) == kind
            tests.append(test_set)
    if spec.get("light"):
        L = spec["light"]
        rg = lens_range(L)
        ap = float(L["ap"])
        tests.append(lambda i: i["kb"] and rg[0] <= i["kb"] <= rg[1] and i["iso"] and i["iso"] > ISO_LIMIT
                     and i["wo"] is True and i["fnum"] and i["fnum"] > ap * 1.04)
    hit = [i for i in imgs if all(t(i) for t in tests)]
    hit.sort(key=lambda i: i["dt"] or "", reverse=True)
    page = hit[offset:offset + limit]
    keys = ("id", "file", "camera", "lens", "kb", "fl", "fnum", "exptime", "iso", "dt", "rating")
    return {"total": len(hit), "offset": offset, "items": [{k: i[k] for k in keys} for i in page]}
