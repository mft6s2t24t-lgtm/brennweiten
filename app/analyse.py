"""Auswertungen. Alle Brennweiten im Kleinbild-Äquivalent (KB), sofern nicht anders angegeben."""
import i18n
import csv
import datetime
import io
import statistics

import tabelle

CLASSES = [("<17", None, 16), ("17–20", 17, 20), ("21–23", 21, 23), ("24", 24, 24),
           ("25–35", 25, 35), ("36–50", 36, 50), ("51–70", 51, 70), ("71–105", 71, 105),
           ("106–200", 106, 200), ("201–400", 201, 400), (">400", 401, None)]
GROUPS = [("unter 24", None, 23), ("24–70", 24, 70), ("71–200", 71, 200), ("über 200", 201, None)]
WIN50 = (45, 55)
WIN85 = (80, 90)
GOOD = 3


def compute_fl35(fl, f35, crop, area):
    """KB-Brennweite: EXIF-Wert, wenn plausibel, sonst Brennweite × Crop-Faktor.
    Gibt (kb, dx, quelle) zurück."""
    crop = crop or 1.0
    dx = bool(area and "DX" in area.upper())
    if fl and fl > 0 and f35 and f35 > 0 and crop < 1.2 and abs(f35 / fl - 1.5) / 1.5 < 0.06:
        dx = True
    eff = 1.5 if (dx and crop < 1.2) else crop
    if fl and fl > 0:
        if f35 and f35 > 0 and abs(f35 / fl - eff) / eff <= 0.12:
            return float(f35), dx, "exif"
        return fl * eff, dx, "berechnet"
    if f35 and f35 > 0:
        return float(f35), dx, "exif"
    return None, dx, None


def in_range(v, lo, hi):
    return v is not None and (lo is None or v >= lo) and (hi is None or v <= hi)


def zoom_ends(mn, mx):
    """Bereiche 'am Anschlag', z. B. 24-120: 24–26 und 110–120 mm."""
    w = mn + max(1, round(mn * 0.085))
    t = mx - max(1, round(mx * 0.085))
    return w, t


_BASE = {"key": None, "rows": []}
WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def base_rows(conn):
    """Alle gezählten Bilder ausgewählter Kameras; zwischengespeichert, bis sich die Datenbank ändert."""
    key = (id(conn), conn.total_changes, conn.execute("PRAGMA data_version").fetchone()[0])
    if _BASE["key"] == key:
        return _BASE["rows"]
    cams = {r["key"]: dict(r) for r in conn.execute("SELECT * FROM cameras")}
    lenses = {r["key"]: dict(r) for r in conn.execute("SELECT * FROM lenses")}
    out = []
    for r in conn.execute("SELECT i.*, fo.path AS folder_path FROM images i "
                          "LEFT JOIN folders fo ON fo.id=i.folder_id WHERE i.canonical=1"):
        cam = cams.get(r["camera_key"])
        if not cam or not cam["enabled"]:
            continue
        lens = lenses.get(r["lens_key"]) or {}
        lname = lens.get("name") or (r["lens_raw"] or "Unbekanntes Objektiv")
        if lens and not lens.get("confirmed"):
            lname += " (?)"
        d = (r["dt"] or "")[:10]
        kb, dx, src = compute_fl35(r["fl"], r["fl35_exif"], cam["crop"], r["image_area"])
        path = r["path"]
        wd = hour = None
        if len(d) == 10:
            try:
                wd = WEEKDAYS[datetime.date(int(d[:4]), int(d[5:7]), int(d[8:])).weekday()]
                hour = int((r["dt"] or "")[11:13])
            except ValueError:
                pass
        img = dict(
            id=r["id"], path=path, file=path.rsplit("/", 1)[-1], folder=path.rsplit("/", 1)[0],
            ext=r["ext"], camera=cam["name"], camera_key=r["camera_key"],
            serial=r["serial"], lens=lname, lens_key=r["lens_key"], lens_raw=r["lens_raw"],
            fl=r["fl"], kb=kb, kbr=int(round(kb)) if kb else None, dx=dx, kb_src=src,
            fnum=r["fnum"], maxap=r["maxap"], exptime=r["exptime"], iso=r["iso"], dt=r["dt"],
            date=d or None, year=int(d[:4]) if d else None, month=d[:7] or None, weekday=wd, hour=hour,
            rating=r["group_rating"], crop=cam["crop"], lens_info=lens)
        img["wo"] = wide_open(img)
        out.append(img)
    _BASE.update(key=key, rows=out)
    return out


def load(conn, f):
    """Gefilterte, gezählte Bilder (Duplikate entfernt, nur ausgewählte Kameras, Spaltenfilter)."""
    sel_cams = set(f.get("cameras") or [])
    sel_lenses = set(f.get("lenses") or [])
    dfrom, dto = f.get("from") or None, f.get("to") or None
    out = []
    for i in base_rows(conn):
        if sel_cams and i["camera_key"] not in sel_cams:
            continue
        if sel_lenses and i["lens"] not in sel_lenses:
            continue
        d = i["date"] or ""
        if dfrom and (not d or d < dfrom):
            continue
        if dto and (not d or d > dto):
            continue
        out.append(i)
    return tabelle.apply(out, f.get("cf"))


def selected(conn, f):
    imgs = load(conn, f)
    return [i for i in imgs if i["rating"] and i["rating"] >= GOOD] if f.get("good") else imgs


def pct(a, b):
    return round(100.0 * a / b, 1) if b else 0.0


def wide_open(img):
    """Offenblende: Blende ≤ größtmögliche Blende bei dieser Brennweite (kleine Toleranz)."""
    f = img["fnum"]
    if not f or f <= 0:
        return None
    ap = img["maxap"]
    L = img["lens_info"] or {}
    if not ap or ap <= 0:
        aw, at, mn, mx = L.get("ap_wide"), L.get("ap_tele"), L.get("min_fl"), L.get("max_fl")
        if not aw:
            return None
        ap = aw
        if at and mn and mx and mx > mn and img["fl"]:
            t = min(1.0, max(0.0, (img["fl"] - mn) / (mx - mn)))
            ap = aw + (at - aw) * t
    return f <= ap * 1.04 + 0.05


def analyse(conn, f):
    allimgs = load(conn, f)
    rated = sum(1 for i in allimgs if i["rating"] and i["rating"] > 0)
    good_n = sum(1 for i in allimgs if i["rating"] and i["rating"] >= GOOD)
    imgs = [i for i in allimgs if i["rating"] and i["rating"] >= GOOD] if f.get("good") else allimgs
    withkb = [i for i in imgs if i["kb"]]
    n = len(withkb)
    by_lens, kb_by_lens, kb_by_year = {}, {}, {}
    for i in imgs:
        by_lens.setdefault(i["lens"], []).append(i)
        if i["kb"]:
            kb_by_lens.setdefault(i["lens"], []).append(i)
            if i["year"]:
                kb_by_year.setdefault(i["year"], []).append(i)

    res = {"n_total": len(imgs), "n_kb": n, "n_no_kb": len(imgs) - n,
           "rated": rated, "rated_pct": pct(rated, len(allimgs)), "good_n": good_n,
           "n_before_good": len(allimgs), "dx": sum(1 for i in imgs if i["dx"])}
    dates = sorted(i["dt"] for i in imgs if i["dt"])
    res["period"] = [dates[0][:10], dates[-1][:10]] if dates else None
    hint = None
    if f.get("good") and (rated < 0.2 * len(allimgs) or good_n < 50):
        hint = (i18n.t("Nur %s %% der Bilder haben eine Bewertung, %d davon mit ≥ 3 Sternen. "
                       "Die Auswertung „nur gute Bilder“ ist daher wenig aussagekräftig.")
                % (fmt(res["rated_pct"]), good_n))
    elif not f.get("good") and rated < 0.2 * max(1, len(allimgs)):
        hint = (i18n.t("Nur %s %% der Bilder sind bewertet – der Filter „ab 3 Sternen“ hätte wenig Daten.")
                % fmt(res["rated_pct"]))
    res["rating_hint"] = hint
    res["median"] = round(statistics.median([i["kb"] for i in withkb]), 1) if withkb else None

    # 1. Klassen + feines Histogramm (je mm)
    res["classes"] = [{"label": lab, "lo": lo, "hi": hi, "n": c, "pct": pct(c, n)} for lab, lo, hi in CLASSES
                      for c in [sum(1 for i in withkb if in_range(i["kbr"], lo, hi))]]
    hist = {}
    for i in withkb:
        hist[i["kbr"]] = hist.get(i["kbr"], 0) + 1
    res["hist"] = [{"mm": k, "n": v} for k, v in sorted(hist.items())]

    # 2. Ultraweitwinkel
    def uww(group):
        g = [i for i in group if i["kb"]]
        a = sum(1 for i in g if i["kb"] < 24)
        b = sum(1 for i in g if i["kb"] < 20)
        return {"n": len(g), "u24": a, "u24_pct": pct(a, len(g)), "u20": b, "u20_pct": pct(b, len(g))}

    res["uww"] = uww(withkb)
    res["uww_lens"] = sorted(
        [dict(uww(g), lens=L) for L, g in kb_by_lens.items()],
        key=lambda x: (-x["u24"], -x["n"]))
    res["uww_lens"] = [x for x in res["uww_lens"] if x["u24"] > 0]
    years = sorted(kb_by_year)
    res["uww_year"] = [dict(uww(kb_by_year[y]), year=y) for y in years]

    # 3. Zoom am Anschlag (echte Brennweite am Objektiv)
    zooms = []
    for key, group in by_lens.items():
        li = [i for i in group if i["fl"]]
        if not li:
            continue
        L = li[0]["lens_info"] or {}
        mn, mx = L.get("min_fl"), L.get("max_fl")
        if not mn or not mx or mx - mn < 2:
            continue
        w, t = zoom_ends(mn, mx)
        a = sum(1 for i in li if i["fl"] <= w + 0.01)
        b = sum(1 for i in li if i["fl"] >= t - 0.01)
        crops = sorted({i["crop"] for i in li})
        zooms.append({"lens": key, "n": len(li), "min": mn, "max": mx, "wide_to": w, "tele_from": t,
                      "wide": a, "wide_pct": pct(a, len(li)), "tele": b, "tele_pct": pct(b, len(li)),
                      "mid_pct": pct(len(li) - a - b, len(li)), "crops": crops})
    res["zooms"] = sorted(zooms, key=lambda z: -z["n"])

    # 4. Offenblende bei wenig Licht (ISO > 3200)
    lowlight = []
    for key, li in by_lens.items():
        flags = [(i, i["wo"]) for i in li]
        known = [(i, w) for i, w in flags if w is not None]
        hi = [i for i in li if i["iso"] and i["iso"] > 3200]
        wo = [i for i, w in known if w]
        both = [i for i, w in known if w and i["iso"] and i["iso"] > 3200]
        L = li[0]["lens_info"] or {}
        lowlight.append({"lens": key, "n": len(li), "n_known": len(known), "ap": L.get("ap_wide"),
                         "ap_tele": L.get("ap_tele"),
                         "wo": len(wo), "wo_pct": pct(len(wo), len(known)),
                         "iso": len(hi), "iso_pct": pct(len(hi), len(li)),
                         "both": len(both), "both_pct": pct(len(both), len(known)),
                         "both_of_iso_pct": pct(len(both), len([i for i in hi if i["wo"] is not None]))})
    res["lowlight"] = sorted(lowlight, key=lambda x: -x["n"])

    # 5. Um 50 mm und um 85 mm
    def around(group):
        g = [i for i in group if i["kb"]]
        a = sum(1 for i in g if WIN50[0] <= i["kb"] <= WIN50[1])
        b = sum(1 for i in g if WIN85[0] <= i["kb"] <= WIN85[1])
        return {"n": len(g), "n50": a, "p50": pct(a, len(g)), "n85": b, "p85": pct(b, len(g))}

    res["win50"], res["win85"] = list(WIN50), list(WIN85)
    res["around"] = around(withkb)
    al = [dict(around(g), lens=L) for L, g in kb_by_lens.items()]
    res["around_lens"] = sorted([x for x in al if x["n50"] or x["n85"]],
                                key=lambda x: -(x["n50"] + x["n85"]))
    res["around_year"] = [dict(around(kb_by_year[y]), year=y) for y in years]

    # 6. Entwicklung pro Jahr
    peryear = []
    for y in years:
        g = kb_by_year[y]
        row = {"year": y, "n": len(g), "median": round(statistics.median([i["kb"] for i in g]), 1),
               "groups": [{"label": lab, "n": c, "pct": pct(c, len(g))} for lab, lo, hi in GROUPS
                          for c in [sum(1 for i in g if in_range(i["kbr"], lo, hi))]],
               "cameras": sorted({i["camera"] for i in g})}
        peryear.append(row)
    res["years"] = peryear
    res["group_labels"] = [g[0] for g in GROUPS]

    # Objektive gesamt
    lc = {}
    for i in imgs:
        lc[i["lens"]] = lc.get(i["lens"], 0) + 1
    res["lens_counts"] = [{"lens": k, "n": v, "pct": pct(v, len(imgs))}
                          for k, v in sorted(lc.items(), key=lambda x: -x[1])]
    cc = {}
    for i in imgs:
        cc[i["camera"]] = cc.get(i["camera"], 0) + 1
    res["camera_counts"] = [{"camera": k, "n": v} for k, v in sorted(cc.items(), key=lambda x: -x[1])]
    return res


def detail(conn, f, lens="", fl=None, fnum=None, basis="kb"):
    """Fotos je Brennweite und je Blende, optional für ein Objektiv und kombinierbar."""
    imgs = selected(conn, f)
    if lens:
        imgs = [i for i in imgs if i["lens"] == lens]

    def mm(i):
        if basis == "objektiv":
            return int(round(i["fl"])) if i["fl"] and i["fl"] > 0 else None
        return i["kbr"]

    def ap(i):
        return round(i["fnum"], 1) if i["fnum"] and i["fnum"] > 0 else None

    def counts(group, key):
        c = {}
        for i in group:
            v = key(i)
            if v is not None:
                c[v] = c.get(v, 0) + 1
        total = sum(c.values())
        return [{"v": k, "n": v, "pct": pct(v, total)} for k, v in sorted(c.items())]

    at_fnum = [i for i in imgs if fnum is None or ap(i) == fnum]
    at_fl = [i for i in imgs if fl is None or mm(i) == fl]
    hit = [i for i in at_fl if fnum is None or ap(i) == fnum]
    return {"total": len(imgs), "n": len(hit), "pct": pct(len(hit), len(imgs)),
            "by_fl": counts(at_fnum, mm), "by_fnum": counts(at_fl, ap),
            "no_fl": sum(1 for i in imgs if mm(i) is None),
            "no_fnum": sum(1 for i in imgs if ap(i) is None)}


# ------------------------------------------------------------------ Export

def fmt(v, nd=1):
    if v is None:
        return ""
    if isinstance(v, float):
        s = ("%." + str(nd) + "f") % v
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return i18n.decimal(s)
    return str(v)


def export_csv(conn, f, sort=None, cols=None):
    """Export der gefilterten Fotos; Reihenfolge und Spalten wie in der Tabelle."""
    imgs = selected(conn, f)
    imgs = tabelle.sort_rows(imgs, sort) if sort else sorted(imgs, key=lambda x: x["dt"] or "")
    columns = tabelle.pick(cols)
    buf = io.StringIO()
    buf.write("\ufeff")
    w = csv.writer(buf, delimiter=i18n.csv_delimiter())
    w.writerow([i18n.t(c[1]) for c in columns])
    for i in imgs:
        w.writerow([tabelle.export_value(c, i, fmt) for c in columns])
    return buf.getvalue()


def summary(conn, f, filter_text):
    r = analyse(conn, f)
    L = []
    _ = i18n.t
    p = r["period"]
    L.append(_("Brennweiten-Auswertung (KB-Äquivalent), Filter: %s") % filter_text)
    L.append(_("Bilder: %d (Duplikate entfernt), mit Brennweite: %d, Zeitraum %s bis %s")
             % (r["n_total"], r["n_kb"], p[0] if p else "-", p[1] if p else "-"))
    L.append(_("Kameras: ") + ", ".join("%s %d" % (c["camera"], c["n"]) for c in r["camera_counts"]))
    L.append(_("Median-Brennweite: %s mm") % fmt(r["median"]))
    cl = r["classes"]
    L.append(_("Klassen (mm): ") + " | ".join("%s: %s%%" % (_(c["label"]), fmt(c["pct"])) for c in cl[:6]))
    L.append(_("Klassen (mm): ") + " | ".join("%s: %s%%" % (_(c["label"]), fmt(c["pct"])) for c in cl[6:]))
    u = r["uww"]
    L.append(_("Unter 24 mm: %d (%s%%), unter 20 mm: %d (%s%%)")
             % (u["u24"], fmt(u["u24_pct"]), u["u20"], fmt(u["u20_pct"])))
    if r["uww_year"]:
        L.append(_("Unter 24 mm je Jahr: ") + ", ".join(
            "%d %s%%" % (y["year"], fmt(y["u24_pct"])) for y in r["uww_year"][-8:]))
    a = r["around"]
    L.append(_("Um 50 mm (45–55): %d (%s%%), um 85 mm (80–90): %d (%s%%)")
             % (a["n50"], fmt(a["p50"]), a["n85"], fmt(a["p85"])))
    L.append(_("Objektive (Anteil): ") + ", ".join(
        "%s %s%%" % (_(x["lens"]), fmt(x["pct"])) for x in r["lens_counts"][:6]))
    for z in r["zooms"][:4]:
        L.append(_("Zoom %s (%d Bilder): %g–%g mm %s%%, %g–%g mm %s%%")
                 % (_(z["lens"]), z["n"], z["min"], z["wide_to"], fmt(z["wide_pct"]),
                    z["tele_from"], z["max"], fmt(z["tele_pct"])))
    for x in [x for x in r["lowlight"] if x["n_known"]][:5]:
        L.append(_("Offenblende + ISO>3200, %s: %d von %d (%s%%); Offenblende gesamt %s%%")
                 % (_(x["lens"]), x["both"], x["n_known"], fmt(x["both_pct"]), fmt(x["wo_pct"])))
    for y in r["years"][-4:]:
        L.append(_("%d: %d Bilder, Median %s mm, ") % (y["year"], y["n"], fmt(y["median"])) + ", ".join(
            "%s %s%%" % (_(g["label"]), fmt(g["pct"])) for g in y["groups"]))
    L.append(_("Bewertet: %s%% der Bilder, davon ≥3 Sterne: %d") % (fmt(r["rated_pct"]), r["good_n"]))
    return "\n".join(L[:25])
