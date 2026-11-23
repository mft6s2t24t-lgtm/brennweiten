"""Datenbank (SQLite) und Stammdaten: Kameras, Objektive."""
import os
import re
import sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("BRENNWEITEN_DATA") or os.path.join(BASE, "daten")
DB_PATH = os.environ.get("BRENNWEITEN_DB") or os.path.join(DATA_DIR, "brennweiten.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS folders(
  id INTEGER PRIMARY KEY, path TEXT UNIQUE, added TEXT, last_scan TEXT,
  status TEXT, message TEXT);
CREATE TABLE IF NOT EXISTS images(
  id INTEGER PRIMARY KEY, path TEXT UNIQUE, folder_id INTEGER, ext TEXT,
  size INTEGER, mtime REAL, sidecar TEXT, sidecar_mtime REAL,
  make TEXT, model TEXT, serial TEXT, camera_key TEXT,
  lens_raw TEXT, lens_key TEXT,
  fl REAL, fl35_exif REAL, fnum REAL, maxap REAL, exptime REAL, iso REAL,
  dt TEXT, subsec TEXT, rating_file INTEGER, rating_xmp INTEGER,
  image_area TEXT, lensinfo TEXT, software TEXT,
  canonical INTEGER DEFAULT 1, group_rating INTEGER, dup_of INTEGER);
CREATE INDEX IF NOT EXISTS ix_img_folder ON images(folder_id);
CREATE INDEX IF NOT EXISTS ix_img_cam ON images(camera_key);
CREATE TABLE IF NOT EXISTS cameras(
  key TEXT PRIMARY KEY, make TEXT, model TEXT, name TEXT, crop REAL,
  enabled INTEGER, status TEXT, user_set INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS lenses(
  key TEXT PRIMARY KEY, name TEXT, min_fl REAL, max_fl REAL,
  ap_wide REAL, ap_tele REAL, confirmed INTEGER DEFAULT 1,
  suggestion INTEGER DEFAULT 0, user_set INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS failed(path TEXT PRIMARY KEY, message TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS views(id INTEGER PRIMARY KEY, name TEXT UNIQUE, state TEXT, created TEXT);
"""


def connect(path=None):
    os.makedirs(DATA_DIR, exist_ok=True)
    c = sqlite3.connect(path or DB_PATH, timeout=60, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript(SCHEMA)
    for table, col, typ in (("images", "scale35", "REAL"), ("cameras", "crop_src", "TEXT")):
        if col not in {r["name"] for r in c.execute("PRAGMA table_info(%s)" % table)}:
            c.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, col, typ))
    c.commit()
    return c


# ---------------------------------------------------------------- Kameras

def norm(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


BRANDS = {"NIKON": "Nikon", "CANON": "Canon", "SONY": "Sony", "FUJIFILM": "Fujifilm", "FUJI": "Fujifilm",
          "OLYMPUS": "Olympus", "OM": "OM System", "PANASONIC": "Panasonic", "LEICA": "Leica", "RICOH": "Ricoh",
          "PENTAX": "Pentax", "HASSELBLAD": "Hasselblad", "SIGMA": "Sigma", "APPLE": "Apple", "GOOGLE": "Google",
          "SAMSUNG": "Samsung", "DJI": "DJI", "GOPRO": "GoPro", "XIAOMI": "Xiaomi", "HUAWEI": "Huawei"}
PHONE_MAKES = {"APPLE", "GOOGLE", "SAMSUNG", "HUAWEI", "HONOR", "XIAOMI", "ONEPLUS", "OPPO", "VIVO", "REALME",
               "MOTOROLA", "NOKIA", "HMD", "LG", "LGE", "BQ", "ZTE", "ASUS", "HTC", "FAIRPHONE", "NOTHING"}
PHONE_MODEL = re.compile(r"iphone|ipad|\bpixel\b|^SM-|^GT-|^JSN-|aquaris|galaxy|redmi|oneplus", re.I)
SCANNER = re.compile(r"scan|coolscan|plustek|reflecta|epson|perfection|imagescan|fujitsu", re.I)
ROMAN = {"2": "II", "3": "III", "4": "IV", "5": "V"}
CORP = re.compile(r"\b(corporation|corp\.?|company|imaging|digital solutions|camera|co\.?|ltd\.?|inc\.?|ag|gmbh)\b[,.]*", re.I)
CROP_STEPS = (0.79, 1.0, 1.3, 1.5, 1.6, 2.0, 2.7)


def camera_key(make, model):
    make = (make or "").strip()
    model = (model or "").strip()
    if not make and not model:
        return ""
    return make + "|" + model


def _brand(make):
    words = (make or "").strip().split()
    if not words:
        return ""
    known = BRANDS.get(norm(words[0]))
    if known:
        return known
    clean = " ".join(CORP.sub(" ", make).split()).strip(" ,.")
    clean = clean or make.strip()
    return clean.title() if clean.isupper() and len(clean) > 3 else clean


def camera_name(make, model):
    """Lesbarer Name direkt aus EXIF, z. B. NIKON Z6_3 -> Nikon Z6 III."""
    brand = _brand(make)
    m = (model or "").strip()
    for w in {brand, (make or "").split(" ")[0]} - {""}:
        if m.upper().startswith(w.upper() + " "):
            m = m[len(w):].strip()
    m = re.sub(r"_(\d)$", lambda x: " " + ROMAN.get(x.group(1), x.group(1)), m)
    return (brand + " " + m).strip() or "Unbekannte Kamera"


def camera_kind(make, model):
    word = norm((make or "").split(" ")[0])
    if word in PHONE_MAKES or PHONE_MODEL.search(model or ""):
        # Samsung NX und ähnliche Systemkameras bleiben Kameras
        if not re.search(r"\bNX\s?\d", model or "", re.I):
            return "Smartphone"
    if SCANNER.search((make or "") + " " + (model or "")):
        return "Scanner"
    return "Kamera"


def known_crop(make, model):
    """Sensorgröße bekannter Baureihen, falls die Dateien keine Angabe enthalten."""
    b = norm((make or "").split(" ")[0])
    m = (model or "").upper().strip()
    if b == "CANON":
        if re.search(r"EOS\s*(\d{2,4}D|7D(\s*MARK\s*II)?|R7|R10|R50|R100|M\d*|KISS.*|REBEL.*)$", m):
            return 1.6
        if re.search(r"EOS", m):
            return 1.0
    if b == "NIKON":
        if re.search(r"\bD(3\d{3}|5\d{3}|7\d{3}|40X?|50|60|70S?|80|90|100|200|300S?|500)\b|\bZ\s?(30|50(_2)?|FC)\b", m):
            return 1.5
        if re.search(r"\bZ\s?\d|\bZF\b|\bD\d", m):
            return 1.0
    if b == "SONY":
        if re.search(r"ILCE-(5|6)\d{3}|NEX-|ZV-E10", m):
            return 1.5
        if re.search(r"ILCE-(1|7|9)", m):
            return 1.0
    if b in ("FUJIFILM", "FUJI"):
        if "GFX" in m:
            return 0.79
        if re.match(r"X-?[A-Z]?\d", m) or m.startswith("X-"):
            return 1.5
    if b in ("OLYMPUS", "OM") or (b == "PANASONIC" and re.search(r"-G[0-9HXF]|GH\d|GX\d", m)):
        return 2.0
    if b == "PANASONIC" and re.search(r"-S\d", m):
        return 1.0
    if b == "PENTAX" or b == "RICOH":
        if re.search(r"K-1\b", m):
            return 1.0
        if re.search(r"K-\d|KP", m):
            return 1.5
    return None


def nice_crop(ratio):
    if not ratio:
        return 1.0
    for c in CROP_STEPS:
        if abs(ratio - c) / c < 0.05:
            return c
    return round(ratio, 2)


def detect_crop(make, model, scales, ratios):
    """Crop-Faktor: zuerst aus den EXIF-Daten, dann aus bekannten Baureihen. Gibt (crop, quelle) zurück."""
    # ExifTool meldet 1.0 auch dann, wenn es den Sensor nicht kennt. Deshalb zählt 1.0 dort nicht als Beleg.
    def mid(vals):
        good = sorted(v for v in vals if v and 0.3 < v < 15)
        return good[len(good) // 2] if good else None
    value = mid(ratios) or mid([v for v in scales if abs(v - 1) > 0.02])
    k = known_crop(make, model)
    # Manche Kameras schreiben die echte Brennweite auch ins KB-Feld. Die bekannte Sensorgröße gewinnt dann.
    if value and not (k and k != 1 and abs(value - 1) < 0.03):
        return nice_crop(value), "exif"
    if k:
        return k, "modell"
    return 1.0, "annahme"


def ensure_cameras(conn):
    """Legt alle gefundenen Kameras aus den EXIF-Daten an. Nur Smartphones und Scanner sind zunächst aus."""
    known = {r["key"]: r for r in conn.execute("SELECT key,user_set FROM cameras")}
    groups = {}
    for r in conn.execute("SELECT camera_key k, make, model, fl, fl35_exif f, scale35 s FROM images WHERE camera_key<>''"):
        g = groups.setdefault(r["k"], {"make": r["make"], "model": r["model"], "s": [], "r": []})
        if r["s"]:
            g["s"].append(r["s"])
        if r["fl"] and r["fl"] > 0 and r["f"] and r["f"] > 0:
            g["r"].append(r["f"] / r["fl"])
    for key, g in groups.items():
        crop, src = detect_crop(g["make"], g["model"], g["s"], g["r"])
        old = known.get(key)
        if old is None:
            kind = camera_kind(g["make"], g["model"])
            conn.execute("INSERT INTO cameras(key,make,model,name,crop,enabled,status,crop_src) VALUES(?,?,?,?,?,?,?,?)",
                         (key, g["make"], g["model"], camera_name(g["make"], g["model"]), crop,
                          1 if kind == "Kamera" else 0, kind, src))
        elif not old["user_set"]:
            conn.execute("UPDATE cameras SET crop=?, crop_src=? WHERE key=?", (crop, src, key))
    conn.commit()


# ---------------------------------------------------------------- Objektive

UNKNOWN_LENS = re.compile(r"^(?:|-+|0|none|n/a)$|unknown|^0(?:\.0)?\s*mm", re.I)


def is_unknown_lens(raw):
    raw = (raw or "").strip()
    return bool(UNKNOWN_LENS.search(raw)) or not re.search(r"\d", raw)


def lens_key(raw, fl):
    """Schlüssel, der unterschiedliche EXIF-Schreibweisen desselben Objektivs zusammenfasst."""
    if is_unknown_lens(raw):
        if fl and fl > 0:
            return "?%gmm" % round(fl)
        return "?"
    s = raw.upper()
    s = re.sub(r"^(CANON|NIKON|SONY|FUJIFILM|SIGMA|TAMRON)\s+", "", s)
    s = s.replace("F/", "F")
    return re.sub(r"[^A-Z0-9.]", "", s)


RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*mm", re.I)
PRIME_RE = re.compile(r"(\d+(?:\.\d+)?)\s*mm", re.I)
AP_RE = re.compile(r"f\s*/?\s*(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?", re.I)


TC_RE = re.compile(r"(?:TC|EXTENDER(?:\s+(?:RF|EF))?)[\s-]*(1\.4|1\.7|2(?:\.0)?)\s*X", re.I)


def converter_factor(name):
    """Telekonverter im Objektivnamen, z. B. 'Z TC-1.4x' oder 'EXTENDER RF2x'."""
    m = TC_RE.search(name or "")
    return float(m.group(1)) if m else 1.0


def parse_lens_name(name):
    """Liefert (min_fl, max_fl, ap_wide, ap_tele) aus einem Objektivnamen, soweit erkennbar."""
    mn = mx = aw = at = None
    m = RANGE_RE.search(name or "")
    if m:
        mn, mx = float(m.group(1)), float(m.group(2))
    else:
        m = PRIME_RE.search(name or "")
        if m:
            mn = mx = float(m.group(1))
    tail = (name or "")[m.end():] if m else (name or "")
    a = AP_RE.search(tail)
    if a:
        aw = float(a.group(1))
        at = float(a.group(2)) if a.group(2) else aw
    tc = converter_factor(name)
    if tc > 1:  # EXIF meldet Brennweite und Blende inklusive Konverter
        mn, mx = mn * tc if mn else mn, mx * tc if mx else mx
        aw, at = round(aw * tc, 1) if aw else aw, round(at * tc, 1) if at else at
    return mn, mx, aw, at


def suggest_unknown(fl, ap):
    if ap:
        return "Unbekanntes Objektiv %g mm f/%g" % (fl, ap)
    return "Unbekanntes Objektiv %g mm" % fl if fl else "Unbekanntes Objektiv"


def ensure_lenses(conn):
    """Legt Objektive an bzw. aktualisiert Brennweitenbereich und Offenblende (außer bei Handeingaben)."""
    existing = {r["key"]: r for r in conn.execute("SELECT * FROM lenses")}
    keys = conn.execute(
        "SELECT lens_key, COUNT(*) n, MIN(fl) mnfl, MAX(fl) mxfl, MIN(fnum) mnf "
        "FROM images WHERE lens_key IS NOT NULL AND lens_key<>'' GROUP BY lens_key").fetchall()
    for k in keys:
        key = k["lens_key"]
        raws = conn.execute(
            "SELECT lens_raw, COUNT(*) n FROM images WHERE lens_key=? GROUP BY lens_raw ORDER BY n DESC",
            (key,)).fetchall()
        infos = conn.execute(
            "SELECT lensinfo, COUNT(*) n FROM images WHERE lens_key=? AND lensinfo IS NOT NULL "
            "AND lensinfo<>'' GROUP BY lensinfo ORDER BY n DESC LIMIT 1", (key,)).fetchone()
        # Offenblende an der kürzesten Brennweite aus MaxApertureValue
        mxap = conn.execute(
            "SELECT MIN(maxap) a FROM images WHERE lens_key=? AND maxap>0 AND fl<=?",
            (key, (k["mnfl"] or 0) * 1.05 + 0.5)).fetchone()["a"]
        mxap_t = conn.execute(
            "SELECT MIN(maxap) a FROM images WHERE lens_key=? AND maxap>0 AND fl>=?",
            (key, (k["mxfl"] or 0) * 0.95 - 0.5)).fetchone()["a"]

        if key.startswith("?"):
            fl = k["mnfl"]
            ap = mxap or k["mnf"]
            ap = round(ap, 1) if ap else None
            vals = dict(name=suggest_unknown(fl, ap), min_fl=fl, max_fl=fl, ap_wide=ap, ap_tele=ap,
                        confirmed=0, suggestion=1)
        else:
            raw = raws[0]["lens_raw"] if raws else key
            mn, mx, aw, at = parse_lens_name(raw)
            if infos:
                try:
                    p = [float(x) for x in infos["lensinfo"].split()]
                    tc = converter_factor(raw) > 1  # LensInfo enthält den Konverter bereits
                    if len(p) >= 2 and p[0] > 0:
                        mn, mx = (p[0], p[1]) if tc else (mn or p[0], mx or p[1])
                    if len(p) >= 4 and p[2] > 0:
                        aw, at = (p[2], p[3]) if tc else (aw or p[2], at or p[3])
                except ValueError:
                    pass
            mn = mn or k["mnfl"]
            mx = mx or k["mxfl"]
            aw = aw or (round(mxap, 1) if mxap else None)
            at = at or (round(mxap_t, 1) if mxap_t else aw)
            vals = dict(name=raw.strip(), min_fl=mn, max_fl=mx, ap_wide=aw, ap_tele=at,
                        confirmed=1, suggestion=0)

        old = existing.get(key)
        if old is None:
            conn.execute(
                "INSERT INTO lenses(key,name,min_fl,max_fl,ap_wide,ap_tele,confirmed,suggestion) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (key, vals["name"], vals["min_fl"], vals["max_fl"], vals["ap_wide"], vals["ap_tele"],
                 vals["confirmed"], vals["suggestion"]))
        elif not old["user_set"]:
            # Name und Bestätigung bleiben, technische Werte werden aktualisiert
            conn.execute(
                "UPDATE lenses SET min_fl=?, max_fl=?, ap_wide=?, ap_tele=? WHERE key=?",
                (vals["min_fl"], vals["max_fl"], vals["ap_wide"], vals["ap_tele"], key))
    conn.commit()


def get_setting(conn, key, default=None):
    r = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default


def set_setting(conn, key, value):
    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, str(value)))
    conn.commit()


def migrate(conn):
    """Korrigiert gespeicherte Stammdaten (Handeingaben bleiben)."""
    ensure_cameras(conn)
    for r in conn.execute("SELECT key,name,max_fl,user_set FROM lenses").fetchall():
        tc = converter_factor(r["name"])
        base = parse_lens_name(r["name"])[1]
        if tc > 1 and not r["user_set"] and r["max_fl"] and base and r["max_fl"] < base * 0.9:
            ensure_lenses(conn)
            return True
    return False
