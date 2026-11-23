"""Analysen je Objektiv, Kamera und Tag, frei wählbare Kennzahlen und „Objektiv prüfen“.
Nur Zahlen aus den eigenen Fotos, keine Empfehlung."""
import json
import statistics

import analyse
import db
import features
from analyse import CLASSES, GOOD, in_range, pct

ISO_BINS = [("≤200", None, 200), ("400", 201, 400), ("800", 401, 800), ("1.600", 801, 1600), ("3.200", 1601, 3200),
            ("6.400", 3201, 6400), ("12.800", 6401, 12800), (">12.800", 12801, None)]
TIME_BINS = [("kürzer 1/2000", None, 1 / 2001), ("1/2000–1/1000", 1 / 2001, 1 / 1001), ("1/1000–1/500", 1 / 1001, 1 / 501),
             ("1/500–1/250", 1 / 501, 1 / 251), ("1/250–1/125", 1 / 251, 1 / 126), ("1/125–1/60", 1 / 126, 1 / 61),
             ("1/60–1/30", 1 / 61, 1 / 31), ("1/30–1 s", 1 / 31, 1), ("ab 1 s", 1, None)]
MAX_TILES = 8

LIBRARY = [
    ("photos", "Fotos"), ("median", "Median-Brennweite"), ("top_lens", "Meistgenutztes Objektiv"),
    ("top_class", "Häufigster Bereich"), ("days", "Fototage"), ("per_day", "Fotos pro Fototag"),
    ("wide_open", "Bei Offenblende"), ("median_iso", "Median-ISO"), ("median_fnum", "Median-Blende"),
    ("high_iso", "ISO über 3200"), ("u24", "Unter 24 mm"), ("u20", "Unter 20 mm"), ("m35", "Um 35 mm"),
    ("m50", "Um 50 mm"), ("m85", "Um 85 mm"), ("o200", "Über 200 mm"), ("rated", "Bewertet"),
    ("good", "Ab 3 Sternen"), ("n_lenses", "Objektive im Einsatz"), ("n_cameras", "Kameras im Einsatz"),
]
DEFAULT_TILES = ["photos", "median", "top_lens", "top_class", "days", "wide_open"]


def _median(vals, nd=1):
    vals = [v for v in vals if v]
    return round(statistics.median(vals), nd) if vals else None


def _bins(values, bins):
    rows = []
    total = len(values)
    for lab, lo, hi in bins:
        c = sum(1 for v in values if (lo is None or v >= lo) and (hi is None or v <= hi))
        rows.append({"label": lab, "n": c, "pct": pct(c, total)})
    return rows


def _time_bins(values):
    rows = []
    for lab, lo, hi in TIME_BINS:
        c = sum(1 for v in values if (lo is None or v >= lo) and (hi is None or v < hi))
        rows.append({"label": lab, "n": c, "pct": pct(c, len(values))})
    return rows


def _count(imgs, key, limit=None):
    c = {}
    for i in imgs:
        v = i[key]
        if v is not None:
            c[v] = c.get(v, 0) + 1
    rows = sorted(c.items(), key=lambda x: -x[1])
    if limit:
        rows = rows[:limit]
    return [{"name": k, "n": v, "pct": pct(v, len(imgs))} for k, v in rows]


def profile(imgs):
    """Einheitliche Auswertung für ein Objektiv, eine Kamera, einen Tag oder eine Reise."""
    kb = [i for i in imgs if i["kb"]]
    known = [i for i in imgs if i["wo"] is not None]
    iso = [i["iso"] for i in imgs if i["iso"]]
    times = [i["exptime"] for i in imgs if i["exptime"]]
    rated = sum(1 for i in imgs if i["rating"] and i["rating"] > 0)
    good = sum(1 for i in imgs if i["rating"] and i["rating"] >= GOOD)
    dates = sorted(i["date"] for i in imgs if i["date"])
    fn = {}
    for i in imgs:
        if i["fnum"]:
            v = round(i["fnum"], 1)
            fn[v] = fn.get(v, 0) + 1
    top_f = sorted(sorted(fn.items(), key=lambda x: -x[1])[:14])
    total_f = sum(fn.values())
    years = {}
    hours = [0] * 24
    for i in imgs:
        if i["year"]:
            years[i["year"]] = years.get(i["year"], 0) + 1
        if i["hour"] is not None and 0 <= i["hour"] < 24:
            hours[i["hour"]] += 1
    return {
        "n": len(imgs), "n_kb": len(kb), "from": dates[0] if dates else None, "to": dates[-1] if dates else None,
        "days": len(set(dates)), "median": _median([i["kb"] for i in kb]), "min": round(min(i["kb"] for i in kb), 1) if kb else None,
        "max": round(max(i["kb"] for i in kb), 1) if kb else None, "median_iso": _median(iso, 0),
        "median_fnum": _median([i["fnum"] for i in imgs]), "wo_pct": pct(sum(1 for i in known if i["wo"]), len(known)),
        "n_known": len(known), "high_iso_pct": pct(sum(1 for v in iso if v > features.ISO_LIMIT), len(iso)),
        "rated": rated, "good": good, "good_pct": pct(good, len(imgs)), "of_rated": pct(good, rated),
        "classes": [{"label": lab, "lo": lo, "hi": hi, "n": c, "pct": pct(c, len(kb))} for lab, lo, hi in CLASSES
                    for c in [sum(1 for i in kb if in_range(i["kbr"], lo, hi))]],
        "fnums": [{"v": k, "n": v, "pct": pct(v, total_f)} for k, v in top_f],
        "iso": _bins(iso, ISO_BINS), "times": _time_bins(times),
        "years": [{"year": y, "n": years[y]} for y in sorted(years)],
        "hours": hours, "lenses": _count(imgs, "lens", 12), "cameras": _count(imgs, "camera", 12),
    }


def entities(conn, f, kind):
    imgs = analyse.selected(conn, f)
    field = "camera_key" if kind == "camera" else "lens"
    groups = {}
    for i in imgs:
        groups.setdefault(i[field], []).append(i)
    rows = []
    for key, g in groups.items():
        kbs = [i["kb"] for i in g if i["kb"]]
        known = [i for i in g if i["wo"] is not None]
        dates = sorted(i["date"] for i in g if i["date"])
        rows.append({"key": key, "name": g[0]["camera"] if kind == "camera" else key, "n": len(g),
                     "pct": pct(len(g), len(imgs)), "median": _median(kbs), "days": len(set(dates)),
                     "from": dates[0] if dates else None, "to": dates[-1] if dates else None,
                     "wo_pct": pct(sum(1 for i in known if i["wo"]), len(known)),
                     "median_iso": _median([i["iso"] for i in g], 0),
                     "good_pct": pct(sum(1 for i in g if i["rating"] and i["rating"] >= GOOD), len(g))})
    rows.sort(key=lambda x: -x["n"])
    return {"total": len(imgs), "rows": rows}


# ---------------------------------------------------------------- Kennzahlen

def load_tiles(conn):
    try:
        v = json.loads(db.get_setting(conn, "tiles", "") or "null")
    except ValueError:
        v = None
    return clean_tiles(v) if v else [{"id": x} for x in DEFAULT_TILES]


def _float(v):
    try:
        x = float(str(v).replace(",", "."))
        return x if x > 0 else None
    except (TypeError, ValueError):
        return None


def clean_tiles(items):
    known = {k for k, _ in LIBRARY}
    out, seen = [], set()
    for t in items if isinstance(items, list) else []:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id") or "")
        if tid in seen:
            continue
        if tid in known:
            out.append({"id": tid})
        elif tid.startswith("rule-"):
            rule = {k: _float(t.get(k)) for k in ("kb_min", "kb_max", "iso_min", "f_max")}
            if any(rule.values()):
                out.append(dict(rule, id=tid[:40], label=str(t.get("label") or "Eigene Kennzahl").strip()[:40]))
        else:
            continue
        seen.add(tid)
    return out[:MAX_TILES]


def rule_test(t):
    def test(i):
        if (t.get("kb_min") or t.get("kb_max")) and not i["kb"]:
            return False
        if t.get("kb_min") and i["kb"] < t["kb_min"] - 0.5:
            return False
        if t.get("kb_max") and i["kb"] > t["kb_max"] + 0.5:
            return False
        if t.get("iso_min") and not (i["iso"] and i["iso"] >= t["iso_min"]):
            return False
        if t.get("f_max") and not (i["fnum"] and i["fnum"] <= t["f_max"] * 1.02):
            return False
        return True
    return test


def rule_text(t):
    parts = []
    a, b = t.get("kb_min"), t.get("kb_max")
    if a and b:
        parts.append("%g–%g mm" % (a, b))
    elif a:
        parts.append("ab %g mm" % a)
    elif b:
        parts.append("bis %g mm" % b)
    if t.get("iso_min"):
        parts.append("ab ISO %g" % t["iso_min"])
    if t.get("f_max"):
        parts.append("f/%g oder offener" % t["f_max"])
    return " · ".join(parts).replace(".", ",")


def tile_values(conn, f, tiles):
    imgs = analyse.selected(conn, f)
    kb = [i for i in imgs if i["kb"]]
    nk = len(kb)
    dates = {i["date"] for i in imgs if i["date"]}
    names = dict(LIBRARY)

    def share(test, sub, spec=None):
        c = sum(1 for i in kb if test(i["kb"]))
        return {"value": pct(c, nk), "fmt": "pct", "sub": "%s · %s Fotos" % (sub, _de(c)), "spec": spec}

    def tile(tid):
        if tid == "photos":
            d = sorted(dates)
            return {"value": len(imgs), "fmt": "n", "sub": "%s–%s" % (d[0][:4], d[-1][:4]) if d else ""}
        if tid == "median":
            return {"value": _median([i["kb"] for i in kb]), "fmt": "mm", "sub": "KB-Äquivalent"}
        if tid == "top_lens":
            t = _count(imgs, "lens", 1)
            return {"value": t[0]["name"] if t else "–", "fmt": "text", "sub": "%s %% der Fotos" % analyse.fmt(t[0]["pct"]) if t else ""}
        if tid == "top_class":
            rows = [(lab, sum(1 for i in kb if in_range(i["kbr"], lo, hi))) for lab, lo, hi in CLASSES]
            lab, c = max(rows, key=lambda x: x[1]) if rows else ("–", 0)
            return {"value": lab + " mm" if c else "–", "fmt": "text", "sub": "%s %% der Fotos" % analyse.fmt(pct(c, nk))}
        if tid == "days":
            return {"value": len(dates), "fmt": "n", "sub": "Tage mit Fotos"}
        if tid == "per_day":
            return {"value": round(len(imgs) / len(dates), 1) if dates else None, "fmt": "n", "sub": "im Durchschnitt"}
        if tid == "wide_open":
            known = [i for i in imgs if i["wo"] is not None]
            c = sum(1 for i in known if i["wo"])
            return {"value": pct(c, len(known)), "fmt": "pct", "sub": _de(c) + " Fotos", "spec": {"wide_open": True}}
        if tid == "median_iso":
            return {"value": _median([i["iso"] for i in imgs], 0), "fmt": "iso", "sub": "typische Empfindlichkeit"}
        if tid == "median_fnum":
            return {"value": _median([i["fnum"] for i in imgs]), "fmt": "fnum", "sub": "typische Blende"}
        if tid == "high_iso":
            iso = [i for i in imgs if i["iso"]]
            c = sum(1 for i in iso if i["iso"] > features.ISO_LIMIT)
            return {"value": pct(c, len(iso)), "fmt": "pct", "sub": _de(c) + " Fotos", "spec": {"iso_over": features.ISO_LIMIT}}
        if tid == "u24":
            return share(lambda v: v < 24, "unter 24 mm", {"kb_under": 24})
        if tid == "u20":
            return share(lambda v: v < 20, "unter 20 mm", {"kb_under": 20})
        if tid == "m35":
            return share(lambda v: 32 <= v <= 38, "32–38 mm", {"range": [32, 38]})
        if tid == "m50":
            return share(lambda v: 45 <= v <= 55, "45–55 mm", {"range": [45, 55]})
        if tid == "m85":
            return share(lambda v: 80 <= v <= 90, "80–90 mm", {"range": [80, 90]})
        if tid == "o200":
            return share(lambda v: v > 200, "über 200 mm", {"range": [200.01, 100000]})
        if tid == "rated":
            c = sum(1 for i in imgs if i["rating"] and i["rating"] > 0)
            return {"value": pct(c, len(imgs)), "fmt": "pct", "sub": _de(c) + " Fotos"}
        if tid == "good":
            c = sum(1 for i in imgs if i["rating"] and i["rating"] >= GOOD)
            return {"value": pct(c, len(imgs)), "fmt": "pct", "sub": _de(c) + " Fotos", "spec": {"rating_min": GOOD}}
        if tid == "n_lenses":
            return {"value": len({i["lens"] for i in imgs}), "fmt": "n", "sub": "verschiedene Objektive"}
        if tid == "n_cameras":
            return {"value": len({i["camera_key"] for i in imgs}), "fmt": "n", "sub": "verschiedene Kameras"}
        return {"value": None, "fmt": "text", "sub": ""}

    out = []
    for t in tiles:
        if t["id"].startswith("rule-"):
            test = rule_test(t)
            c = sum(1 for i in imgs if test(i))
            out.append({"id": t["id"], "label": t["label"], "value": pct(c, len(imgs)), "fmt": "pct", "custom": True,
                        "sub": "%s · %s Fotos" % (rule_text(t), _de(c)), "spec": {"rule": t}})
        else:
            out.append(dict(tile(t["id"]), id=t["id"], label=names[t["id"]]))
    return out


def _de(v):
    return "{:,}".format(v).replace(",", ".")


def tiles_payload(conn, f):
    chosen = load_tiles(conn)
    return {"library": [{"id": k, "label": v} for k, v in LIBRARY], "chosen": chosen, "max": MAX_TILES,
            "default": DEFAULT_TILES, "values": tile_values(conn, f, chosen)}


# ---------------------------------------------------------------- Objektiv prüfen

def own_ranges(imgs):
    """KB-Bereiche der vorhandenen Objektive, so wie sie an den genutzten Kameras eingesetzt wurden."""
    groups = {}
    for i in imgs:
        if i["kb"]:
            groups.setdefault(i["lens"], []).append(i)
    ranges = []
    for g in groups.values():
        L = g[0]["lens_info"] or {}
        mn, mx = L.get("min_fl"), L.get("max_fl")
        if mn and mx:
            for c in {1.5 if i["dx"] and (i["crop"] or 1) < 1.2 else (i["crop"] or 1) for i in g}:
                ranges.append((mn * c - 0.5, mx * c + 0.5))
        else:
            vals = [i["kb"] for i in g]
            ranges.append((min(vals) - 0.5, max(vals) + 0.5))
    ranges.sort()
    merged = []
    for a, b in ranges:
        if merged and a <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def uncovered(lo, hi, own):
    out, cur = [], lo
    for a, b in own:
        if b < cur:
            continue
        if a > hi:
            break
        if a > cur:
            out.append((cur, min(a, hi)))
        cur = max(cur, b)
    if cur < hi:
        out.append((cur, hi))
    return [(round(a), round(b)) for a, b in out if b - a >= 1]


def check(conn, f, candidates):
    imgs = [i for i in analyse.selected(conn, f) if i["kb"]]
    total = len(imgs)
    own = own_ranges(imgs)
    out = []
    for c in (candidates or [])[:3]:
        mn, mx = _float(c.get("min")), _float(c.get("max"))
        if not mn:
            continue
        mx = mx or mn
        if mx < mn:
            mn, mx = mx, mn
        crop = _float(c.get("crop")) or 1.0
        ap = _float(c.get("ap"))
        k_min, k_max = mn * crop, mx * crop
        lo, hi = features.lens_range({"min": k_min, "max": k_max})
        hit = [i for i in imgs if lo <= i["kb"] <= hi]
        segs = uncovered(lo, hi, own)
        new_n = sum(1 for i in hit if any(a <= i["kb"] <= b for a, b in segs))
        wider = longer = 0
        for i in imgs:
            L = i["lens_info"] or {}
            a, b = L.get("min_fl"), L.get("max_fl")
            if not (a and b and b - a >= 2 and i["fl"]):
                continue
            w, t = analyse.zoom_ends(a, b)
            if i["fl"] <= w + 0.01 and k_min < i["kb"] * 0.97 and k_max >= i["kb"] * 0.8:
                wider += 1
            elif i["fl"] >= t - 0.01 and k_max > i["kb"] * 1.03 and k_min <= i["kb"] * 1.25:
                longer += 1
        name = str(c.get("name") or "").strip() or ("%g mm" % mn if mn == mx else "%g–%g mm" % (mn, mx)) + (" f/%g" % ap if ap else "")
        res = {"name": name, "lo": round(lo, 1), "hi": round(hi, 1), "crop": crop, "ap": ap, "total": total, "n": len(hit),
               "pct": pct(len(hit), total), "replaces": _count(hit, "lens", 6), "new_segments": segs, "new_n": new_n,
               "wider": wider, "longer": longer}
        res["light"] = features.light(conn, f, k_min, k_max, ap)["all"] if ap else None
        out.append(res)
    return {"total": total, "own": [[round(a), round(b)] for a, b in own], "results": out, "presets": features.PRESETS,
            "crops": sorted({round(i["crop"] or 1, 2) for i in imgs} | {1.0})}
