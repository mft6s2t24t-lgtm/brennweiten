"""Einlesen der Fotos mit exiftool (nur lesend!), inkrementell, mit Duplikaterkennung."""
import json
import os
import queue
import shutil
import subprocess
import threading
import time
import unicodedata
from datetime import datetime

import db

EXTS = {".nef", ".nrw", ".cr2", ".cr3", ".jpg", ".jpeg", ".heif", ".heic", ".hif",
        ".tif", ".tiff", ".dng"}
SKIP_DIRS = {"CaptureOne", "Lightroom Previews.lrdata", "$RECYCLE.BIN", "System Volume Information"}

# Nur Lese-Optionen. -fast: kein Lesen bis Dateiende (wichtig fürs NAS), Herstellerdaten
# (Objektiv-ID, Seriennummer, DX-Modus) bleiben erhalten. "#" = Zahlenwert statt Text.
EXIF_ARGS = [
    "-j", "-fast", "-charset", "filename=utf8", "-api", "LargeFileSupport=1",
    "-Make", "-Model", "-SerialNumber", "-InternalSerialNumber",
    "-LensModel", "-LensID", "-Lens", "-LensInfo#",
    "-FocalLength#", "-FocalLengthIn35mmFormat#", "-ScaleFactor35efl#", "-FNumber#", "-MaxApertureValue#",
    "-ExposureTime#", "-ISO#", "-DateTimeOriginal", "-CreateDate", "-SubSecTimeOriginal",
    "-Rating#", "-ImageAreaOption", "-ImageArea", "-Software",
]
FORBIDDEN = ("=", "-tagsfromfile", "-o", "-out", "-overwrite_original", "-delete_original",
             "-restore_original", "-geotag", "-srcfile", "-w", "-textout")

BATCH = 60
TIMEOUT = 180  # Sekunden pro Stapel


def find_exiftool():
    for p in (os.environ.get("BRENNWEITEN_EXIFTOOL"), "/opt/homebrew/bin/exiftool", "/usr/local/bin/exiftool", shutil.which("exiftool")):
        if p and os.path.exists(p):
            return p
    return None


class ExifToolError(Exception):
    pass


class ExifTool:
    """Hält einen exiftool-Prozess offen (-stay_open), das spart den Start pro Datei."""

    def __init__(self):
        path = find_exiftool()
        if not path:
            raise ExifToolError("exiftool wurde nicht gefunden (erwartet unter /opt/homebrew/bin).")
        for a in EXIF_ARGS:
            assert not any(a.lower() == f or a.endswith("=") for f in FORBIDDEN), a
        self.proc = subprocess.Popen(
            [path, "-stay_open", "True", "-@", "-"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.q = queue.Queue()
        t = threading.Thread(target=self._reader, daemon=True)
        t.start()

    def _reader(self):
        for line in self.proc.stdout:
            self.q.put(line)
        self.q.put(None)

    def read(self, files, timeout=TIMEOUT):
        files = [f for f in files if "\n" not in f and "\r" not in f]
        if not files:
            return []
        payload = "\n".join(EXIF_ARGS + files + ["-execute"]) + "\n"
        try:
            self.proc.stdin.write(payload.encode("utf-8"))
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            raise ExifToolError("exiftool abgestürzt: %s" % e)
        out = []
        deadline = time.time() + timeout
        while True:
            remain = deadline - time.time()
            if remain <= 0:
                raise ExifToolError("Zeitüberschreitung beim Lesen")
            try:
                line = self.q.get(timeout=remain)
            except queue.Empty:
                raise ExifToolError("Zeitüberschreitung beim Lesen")
            if line is None:
                raise ExifToolError("exiftool beendet")
            s = line.decode("utf-8", "replace")
            if s.strip() == "{ready}":
                break
            out.append(s)
        text = "".join(out).strip()
        if not text:
            return []
        return json.loads(text)

    def close(self):
        try:
            self.proc.stdin.write(b"-stay_open\nFalse\n")
            self.proc.stdin.flush()
            self.proc.wait(timeout=5)
        except Exception:
            self.kill()

    def kill(self):
        try:
            self.proc.kill()
        except Exception:
            pass


# ------------------------------------------------------------------ Status

class Progress:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        self.running = False
        self.phase = ""
        self.folder = ""
        self.found = 0
        self.todo = 0
        self.done = 0
        self.errors = 0
        self.removed = 0
        self.messages = []
        self.started = None
        self.finished = None
        self.cancel = False

    def log(self, msg):
        with self.lock:
            self.messages.append(time.strftime("%H:%M:%S ") + msg)
            self.messages = self.messages[-40:]

    def as_dict(self):
        return {k: getattr(self, k) for k in (
            "running", "phase", "folder", "found", "todo", "done", "errors", "removed",
            "messages", "started", "finished")}


PROGRESS = Progress()


# ------------------------------------------------------------------ Hilfen

def _nfc(s):
    return unicodedata.normalize("NFC", s) if isinstance(s, str) else s


def _s(v):
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _f(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _i(v):
    f = _f(v)
    return int(round(f)) if f is not None else None


def _dt(v):
    """'2024:05:01 10:00:00' -> '2024-05-01 10:00:00' (ohne Zeitzone)."""
    s = _s(v)
    if not s or s.startswith("0000"):
        return None
    s = s[:19]
    if len(s) < 19:
        return None
    return s[0:4] + "-" + s[5:7] + "-" + s[8:10] + " " + s[11:19]


def pick_lens(meta):
    for k in ("LensModel", "LensID", "Lens"):
        v = _s(meta.get(k))
        if v and not db.is_unknown_lens(v):
            return v
    for k in ("LensModel", "LensID", "Lens"):
        v = _s(meta.get(k))
        if v:
            return v
    return None


def row_from_meta(meta, side_meta):
    make, model = _s(meta.get("Make")), _s(meta.get("Model"))
    fl = _f(meta.get("FocalLength"))
    lens = pick_lens(meta)
    area = " ".join(x for x in (_s(meta.get("ImageAreaOption")), _s(meta.get("ImageArea"))) if x) or None
    sub = _s(meta.get("SubSecTimeOriginal"))
    return dict(
        make=make, model=model,
        serial=_s(meta.get("SerialNumber")) or _s(meta.get("InternalSerialNumber")),
        camera_key=db.camera_key(make, model),
        lens_raw=lens, lens_key=db.lens_key(lens, fl),
        fl=fl, fl35_exif=_f(meta.get("FocalLengthIn35mmFormat")), scale35=_f(meta.get("ScaleFactor35efl")),
        fnum=_f(meta.get("FNumber")), maxap=_f(meta.get("MaxApertureValue")),
        exptime=_f(meta.get("ExposureTime")), iso=_f(meta.get("ISO")),
        dt=_dt(meta.get("DateTimeOriginal")) or _dt(meta.get("CreateDate")),
        subsec=sub,
        rating_file=_i(meta.get("Rating")),
        rating_xmp=_i(side_meta.get("Rating")) if side_meta else None,
        image_area=area, lensinfo=_s(meta.get("LensInfo")), software=_s(meta.get("Software")),
    )


COLS = ["make", "model", "serial", "camera_key", "lens_raw", "lens_key", "fl", "fl35_exif", "scale35", "fnum",
        "maxap", "exptime", "iso", "dt", "subsec", "rating_file", "rating_xmp", "image_area",
        "lensinfo", "software"]


# ------------------------------------------------------------------ Ordner

def walk_folder(root, prog):
    """Sammelt Bilddateien. Gibt (dict pfad->(size, mtime, sidecar, sidecar_mtime), ok) zurück."""
    found = {}
    ok = [True]

    def onerr(e):
        ok[0] = False
        prog.log("Lesefehler: %s" % e)

    for dirpath, dirnames, filenames in os.walk(root, onerror=onerr):
        if prog.cancel:
            ok[0] = False
            break
        dirnames[:] = [d for d in dirnames if not d.startswith((".", "@", "#")) and d not in SKIP_DIRS
                       and not d.endswith((".app", ".lrdata", ".photoslibrary"))]
        xmps = {f.lower(): f for f in filenames if f.lower().endswith(".xmp") and not f.startswith("._")}
        for fn in filenames:
            if fn.startswith("._"):
                continue
            stem, ext = os.path.splitext(fn)
            if ext.lower() not in EXTS:
                continue
            full = os.path.join(dirpath, fn)
            try:
                st = os.stat(full)
            except OSError as e:
                onerr(e)
                continue
            side = None
            side_mt = None
            for cand in (fn + ".xmp", stem + ".xmp"):
                real = xmps.get(cand.lower())
                if real:
                    side = os.path.join(dirpath, real)
                    try:
                        side_mt = os.stat(side).st_mtime
                    except OSError:
                        side = None
                    break
            found[full] = (st.st_size, st.st_mtime, side, side_mt)
            prog.found += 1
    return found, ok[0]


def _changed(old, new):
    size, mt, side, side_mt = new
    if old["size"] != size or abs((old["mtime"] or 0) - mt) > 0.0005:
        return True
    if (old["sidecar"] or None) != side:
        return True
    if side and abs((old["sidecar_mtime"] or 0) - (side_mt or 0)) > 0.0005:
        return True
    return False


def _read_batch(et, batch, found, prog):
    """Liest einen Stapel. Gibt (Ergebnisliste, et) zurück; startet exiftool bei Problemen neu."""
    files = list(batch)
    sides = [found[p][2] for p in batch if found[p][2]]
    try:
        res = et.read(files + sides)
        return res, et, []
    except (ExifToolError, ValueError) as e:
        prog.log("Stapel fehlgeschlagen (%s), lese einzeln weiter …" % e)
        et.kill()
        et = ExifTool()
    res, failed = [], []
    for p in batch:
        if not os.path.exists(p):
            failed.append((p, "Datei nicht erreichbar"))
            continue
        one = [p] + ([found[p][2]] if found[p][2] else [])
        try:
            res.extend(et.read(one, timeout=60))
        except (ExifToolError, ValueError) as e:
            failed.append((p, str(e)))
            et.kill()
            et = ExifTool()
    return res, et, failed


def scan_folder(conn, folder, et, prog):
    fid, root = folder["id"], folder["path"]
    prog.folder = root
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if not os.path.isdir(root):
        conn.execute("UPDATE folders SET status='offline', message=? WHERE id=?",
                     ("Ordner nicht erreichbar – vorhandene Daten bleiben erhalten", fid))
        conn.commit()
        prog.log("Nicht erreichbar, übersprungen: %s" % root)
        return et
    prog.phase = "Dateien suchen"
    prog.log("Suche Dateien in %s" % root)
    found, walk_ok = walk_folder(root, prog)
    if not os.path.isdir(root):
        conn.execute("UPDATE folders SET status='offline', message=? WHERE id=?",
                     ("Laufwerk während des Einlesens getrennt", fid))
        conn.commit()
        prog.log("Laufwerk getrennt: %s" % root)
        return et

    existing = {r["path"]: r for r in conn.execute(
        "SELECT id, path, size, mtime, sidecar, sidecar_mtime FROM images WHERE folder_id=?", (fid,))}
    todo = [p for p, v in found.items() if p not in existing or _changed(existing[p], v)]
    todo.sort()
    prog.todo += len(todo)
    prog.log("%d Dateien gefunden, %d neu oder geändert" % (len(found), len(todo)))

    if walk_ok:
        gone = [r["id"] for p, r in existing.items() if p not in found]
        if gone:
            conn.executemany("DELETE FROM images WHERE id=?", [(i,) for i in gone])
            prog.removed += len(gone)
            prog.log("%d nicht mehr vorhandene Dateien entfernt" % len(gone))
    elif existing:
        prog.log("Ordner nicht vollständig lesbar – es werden keine Einträge gelöscht")

    prog.phase = "EXIF lesen"
    for i in range(0, len(todo), BATCH):
        if prog.cancel:
            break
        if not os.path.isdir(root):
            conn.execute("UPDATE folders SET status='offline', message=? WHERE id=?",
                         ("Laufwerk während des Einlesens getrennt – bisher Gelesenes ist gespeichert", fid))
            conn.commit()
            prog.log("Laufwerk getrennt, Einlesen abgebrochen: %s" % root)
            return et
        batch = todo[i:i + BATCH]
        res, et, failed = _read_batch(et, batch, found, prog)
        by_path = {}
        for m in res:
            by_path[_nfc(m.get("SourceFile"))] = m
        rows = []
        for p in batch:
            meta = by_path.get(_nfc(p))
            if meta is None:
                if not any(f[0] == p for f in failed):
                    failed.append((p, "keine Daten"))
                continue
            size, mt, side, side_mt = found[p]
            r = row_from_meta(meta, by_path.get(_nfc(side)) if side else None)
            ext = os.path.splitext(p)[1].lower().lstrip(".")
            rows.append([p, fid, ext, size, mt, side, side_mt] + [r[c] for c in COLS])
        conn.executemany(
            "INSERT INTO images(path,folder_id,ext,size,mtime,sidecar,sidecar_mtime,%s) "
            "VALUES(%s) ON CONFLICT(path) DO UPDATE SET folder_id=excluded.folder_id, ext=excluded.ext, "
            "size=excluded.size, mtime=excluded.mtime, sidecar=excluded.sidecar, "
            "sidecar_mtime=excluded.sidecar_mtime, %s"
            % (",".join(COLS), ",".join("?" * (7 + len(COLS))),
               ", ".join("%s=excluded.%s" % (c, c) for c in COLS)),
            rows)
        for p, msg in failed:
            conn.execute("INSERT OR REPLACE INTO failed(path,message,at) VALUES(?,?,?)", (p, msg, now))
        conn.executemany("DELETE FROM failed WHERE path=?", [(r[0],) for r in rows])
        conn.commit()
        prog.done += len(batch)
        prog.errors += len(failed)

    status = "ok" if walk_ok and not prog.cancel else "unvollständig"
    conn.execute("UPDATE folders SET status=?, last_scan=?, message=? WHERE id=?",
                 (status, now, "%d Bilddateien" % len(found), fid))
    conn.commit()
    return et


# ------------------------------------------------------------------ Duplikate

RAW_EXT = {"nef", "nrw", "cr2", "cr3"}
EDITORS = ("dxo", "lightroom", "photoshop", "capture one", "darktable", "luminar", "affinity",
           "digikam", "gimp", "pixelmator", "on1", "topaz", "rawtherapee", "silkypix", "acdsee",
           "skylum", "photos", "aperture", "snapseed", "lightzone", "photolab", "pureraw", "exiftool")


def is_derived(r):
    sw = (r["software"] or "").lower()
    return any(e in sw for e in EDITORS)


def fmt_rank(r):
    e = r["ext"]
    base = 0 if e in RAW_EXT else 1 if e == "dng" else 2 if e in ("tif", "tiff") else \
        3 if e in ("heif", "heic", "hif") else 4
    return base + (10 if is_derived(r) else 0)


def _split(rows, attr):
    groups = {}
    missing = []
    for r in rows:
        v = r[attr]
        if v:
            groups.setdefault(v, []).append(r)
        else:
            missing.append(r)
    out = list(groups.values())
    if missing:
        if len(out) == 1:
            out[0].extend(missing)
        elif not out:
            out = [missing]
        else:
            # Mehrdeutig: abgeleitete Kopien zählen nie als eigenes Bild
            out[0].extend(r for r in missing if is_derived(r))
            rest = [r for r in missing if not is_derived(r)]
            if rest:
                out.append(rest)
    return out


def dedupe(conn):
    """RAW+JPEG-Paare, Exporte und Kopien zählen als ein Bild. Bevorzugt zählt das RAW."""
    rows = [dict(r) for r in conn.execute(
        "SELECT id, camera_key, serial, dt, subsec, ext, size, software, rating_file, rating_xmp "
        "FROM images")]
    updates = []
    buckets = {}
    for r in rows:
        if r["camera_key"] and r["dt"]:
            buckets.setdefault((r["camera_key"], r["dt"]), []).append(r)
        else:
            rt = _rating(r)
            updates.append((1, rt, None, r["id"]))
    for bucket in buckets.values():
        clusters = []
        for g in _split(bucket, "serial"):
            clusters.extend(_split(g, "subsec"))
        for cl in clusters:
            rt = max((x for x in (_rating(r) for r in cl) if x is not None), default=None)
            best = min(fmt_rank(r) for r in cl)
            cands = sorted((r for r in cl if fmt_rank(r) == best), key=lambda r: r["id"])
            if best >= 10:
                cands = cands[:1]  # nur Exporte vorhanden: zählt einmal
            canon, seen = [], set()
            for r in cands:
                sig = (r["ext"], r["size"])
                if sig in seen:
                    continue
                seen.add(sig)
                canon.append(r)
            first = canon[0]["id"]
            ids = {r["id"] for r in canon}
            for r in cl:
                if r["id"] in ids:
                    updates.append((1, rt, None, r["id"]))
                else:
                    updates.append((0, rt, first, r["id"]))
    conn.executemany("UPDATE images SET canonical=?, group_rating=?, dup_of=? WHERE id=?", updates)
    conn.commit()


def _rating(r):
    v = r["rating_xmp"] if r["rating_xmp"] is not None else r["rating_file"]
    return v


# ------------------------------------------------------------------ Gesamtlauf

def postprocess(conn):
    db.ensure_cameras(conn)
    db.ensure_lenses(conn)
    dedupe(conn)


def scan_all(folder_ids=None, prog=PROGRESS):
    prog.reset()
    prog.running = True
    prog.started = time.time()
    conn = db.connect()
    et = None
    try:
        et = ExifTool()
        folders = conn.execute("SELECT * FROM folders ORDER BY path").fetchall()
        for f in folders:
            if folder_ids and f["id"] not in folder_ids:
                continue
            if prog.cancel:
                break
            et = scan_folder(conn, f, et, prog)
        prog.phase = "Auswerten"
        postprocess(conn)
        prog.log("Fertig: %d gelesen, %d Fehler." % (prog.done, prog.errors))
    except Exception as e:  # noqa
        prog.log("Fehler: %s" % e)
        try:
            postprocess(conn)
        except Exception:
            pass
    finally:
        if et:
            et.close()
        conn.close()
        prog.phase = "abgebrochen" if prog.cancel else "fertig"
        prog.running = False
        prog.finished = time.time()
