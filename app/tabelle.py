"""Excel-artige Tabelle: Spalten, Filter je Spalte, Sortierung, Werte-Listen."""
import statistics

import i18n

# (Schlüssel, Überschrift, Typ)
COLUMNS = [
    ("file", "Datei", "text"), ("folder", "Ordner", "text"), ("path", "Pfad", "text"),
    ("camera", "Kamera", "text"), ("serial", "Seriennummer", "text"),
    ("lens", "Objektiv", "text"), ("lens_raw", "Objektiv (EXIF)", "text"),
    ("fl", "Brennweite mm", "num"), ("kb", "KB-Brennweite mm", "num"), ("kb_src", "KB-Quelle", "text"),
    ("dx", "DX-Crop", "bool"), ("crop", "Crop", "num"),
    ("fnum", "Blende", "num"), ("wo", "Offenblende", "bool"),
    ("exptime", "Belichtungszeit s", "num"), ("iso", "ISO", "num"),
    ("dt", "Aufnahme", "date"), ("year", "Jahr", "num"), ("month", "Monat", "text"),
    ("weekday", "Wochentag", "text"), ("hour", "Stunde", "num"),
    ("rating", "Bewertung", "num"), ("ext", "Format", "text"),
]
TYPES = {c[0]: c[2] for c in COLUMNS}
WEEK = {"Mo": 0, "Di": 1, "Mi": 2, "Do": 3, "Fr": 4, "Sa": 5, "So": 6}


def pick(cols):
    if not cols:
        return COLUMNS
    wanted = set(cols)
    return [c for c in COLUMNS if c[0] in wanted] or COLUMNS


def value(key, row):
    """Vergleichswert einer Zelle; Datum tageweise."""
    v = row.get(key)
    if v == "":
        v = None
    if v is not None and TYPES.get(key) == "date":
        return v[:10]
    return v


def _pred(key, spec):
    typ = TYPES.get(key)
    if typ is None or not isinstance(spec, dict):
        return None
    tests = []
    if isinstance(spec.get("values"), list):
        allowed = set(spec["values"])
        tests.append(lambda v: v in allowed)
    text = str(spec.get("text") or "").casefold()
    if text:
        op = spec.get("op") or "contains"
        fn = {"contains": lambda s: text in s, "not": lambda s: text not in s,
              "starts": lambda s: s.startswith(text), "ends": lambda s: s.endswith(text),
              "equals": lambda s: s == text}.get(op, lambda s: text in s)
        tests.append(lambda v: fn("" if v is None else str(v).casefold()))
    lo, hi = spec.get("min"), spec.get("max")
    if typ == "num":
        lo = _num(lo)
        hi = _num(hi)
    if lo not in (None, ""):
        tests.append(lambda v: v is not None and v >= lo)
    if hi not in (None, ""):
        tests.append(lambda v: v is not None and v <= hi)
    if not tests:
        return None
    return lambda row: all(t(value(key, row)) for t in tests)


def _num(v):
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def apply(rows, cf, skip=None):
    preds = [p for p in (_pred(k, s) for k, s in (cf or {}).items() if k != skip) if p]
    if not preds:
        return rows
    return [r for r in rows if all(p(r) for p in preds)]


def sort_key(key):
    typ = TYPES.get(key)
    if key == "weekday":
        return lambda v: WEEK.get(v, 9)
    if typ == "text":
        return lambda v: str(v).casefold()
    return lambda v: v


def sort_rows(rows, sort):
    """Mehrstufig; leere Zellen stehen immer unten (wie in Excel)."""
    out = list(rows)
    for key, direction in reversed([s for s in (sort or []) if s and s[0] in TYPES]):
        conv = sort_key(key)
        full = [r for r in out if value(key, r) is not None]
        empty = [r for r in out if value(key, r) is None]
        full.sort(key=lambda r: conv(value(key, r)), reverse=direction == "desc")
        out = full + empty
    return out


def facet(rows, key, search="", limit=500):
    counts = {}
    for r in rows:
        v = value(key, r)
        counts[v] = counts.get(v, 0) + 1
    items = list(counts.items())
    s = (search or "").casefold()
    if s:
        items = [x for x in items if x[0] is not None and s in str(x[0]).casefold()]
    conv = sort_key(key)
    filled = sorted((x for x in items if x[0] is not None), key=lambda x: conv(x[0]))
    blanks = [x for x in items if x[0] is None]
    truncated = len(filled) > limit
    if truncated:  # die häufigsten Werte zeigen
        filled = sorted(sorted(filled, key=lambda x: -x[1])[:limit], key=lambda x: conv(x[0]))
    return {"values": [{"v": k, "n": n} for k, n in blanks + filled], "distinct": len(items),
            "truncated": truncated, "type": TYPES.get(key)}


def stats(rows):
    kb = [r["kb"] for r in rows if r["kb"]]
    iso = [r["iso"] for r in rows if r["iso"]]
    dates = sorted(r["date"] for r in rows if r["date"])
    return {"n": len(rows), "median_kb": round(statistics.median(kb), 1) if kb else None,
            "median_iso": round(statistics.median(iso)) if iso else None,
            "from": dates[0] if dates else None, "to": dates[-1] if dates else None,
            "lenses": len({r["lens"] for r in rows})}


def export_value(col, row, fmt):
    key, _, typ = col
    v = row.get(key)
    if v is None:
        return ""
    if typ == "bool":
        return i18n.t("ja" if v else "nein")
    if key == "exptime":
        return fmt(float(v), 6)
    if key == "iso":
        return fmt(float(v), 0)
    if isinstance(v, float):
        return fmt(v)
    if key in ("lens", "weekday", "kb_src"):
        return i18n.t(v)
    return v


def public(row, keys):
    return {k: row.get(k) for k in keys}
