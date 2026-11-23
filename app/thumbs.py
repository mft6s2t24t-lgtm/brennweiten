"""Vorschaubilder: werden nur aus den Fotos gelesen und im eigenen Datenordner gespeichert."""
import base64
import hashlib
import json
import os
import subprocess
import tempfile
import threading

import db
import scanner

SIZE = 420
MAX_FILES = 12000
SLOTS = threading.Semaphore(3)
_made = [0]
DIRECT = {"jpg", "jpeg", "heic", "heif", "hif", "tif", "tiff"}
ROTATE = {3: "180", 6: "90", 8: "270"}


def cache_dir():
    d = os.path.join(db.DATA_DIR, "vorschau")
    os.makedirs(d, exist_ok=True)
    return d


def cache_path(path, size, mtime):
    h = hashlib.sha1(("%s|%s|%s" % (path, size, mtime)).encode("utf-8", "surrogateescape")).hexdigest()
    return os.path.join(cache_dir(), h + ".jpg")


def _sips(src, out, rotate=None):
    cmd = ["/usr/bin/sips", "-s", "format", "jpeg", "-s", "formatOptions", "72", "-Z", str(SIZE)]
    if rotate:
        cmd += ["-r", rotate]
    cmd += [src, "--out", out]
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=40)
    return r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0


def _embedded(path):
    """Größte eingebettete Vorschau + Drehung über exiftool (nur lesend)."""
    tool = scanner.find_exiftool()
    if not tool:
        return None, None
    for tags in (["-PreviewImage", "-OtherImage"], ["-JpgFromRaw"], ["-ThumbnailImage"]):
        p = subprocess.run([tool, "-j", "-b", "-n", "-Orientation"] + tags + ["--", path],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=40)
        if p.returncode != 0 or not p.stdout:
            continue
        try:
            meta = json.loads(p.stdout.decode("utf-8", "replace"))[0]
        except (ValueError, IndexError):
            continue
        best = b""
        for t in ("PreviewImage", "OtherImage", "JpgFromRaw", "ThumbnailImage"):
            v = meta.get(t)
            if isinstance(v, str) and v.startswith("base64:"):
                data = base64.b64decode(v[7:])
                if data[:2] == b"\xff\xd8" and len(data) > len(best):
                    best = data
        if best:
            return best, meta.get("Orientation")
    return None, None


def _prune():
    d = cache_dir()
    files = [os.path.join(d, x) for x in os.listdir(d) if x.endswith(".jpg")]
    if len(files) <= MAX_FILES:
        return
    files.sort(key=lambda x: os.path.getatime(x))
    for x in files[:len(files) - MAX_FILES]:
        try:
            os.remove(x)
        except OSError:
            pass


def get(path, size, mtime, ext):
    """Pfad des Vorschaubilds oder None (z. B. wenn das Laufwerk nicht verbunden ist)."""
    out = cache_path(path, size, mtime)
    if os.path.exists(out):
        return out
    if not os.path.isfile(path):
        return None
    with SLOTS:
        if os.path.exists(out):
            return out
        fd, tmp_out = tempfile.mkstemp(suffix=".jpg", dir=cache_dir())
        os.close(fd)
        os.remove(tmp_out)
        tmp_src = None
        try:
            ok = False
            if (ext or "").lower() in DIRECT:
                ok = _sips(path, tmp_out)
            if not ok:
                data, orient = _embedded(path)
                if data:
                    fd, tmp_src = tempfile.mkstemp(suffix=".jpg", dir=cache_dir())
                    with os.fdopen(fd, "wb") as fh:
                        fh.write(data)
                    ok = _sips(tmp_src, tmp_out, ROTATE.get(orient))
            if not ok:
                ok = _sips(path, tmp_out)
            if not ok:
                return None
            os.replace(tmp_out, out)
            _made[0] += 1
            if _made[0] % 200 == 0:
                _prune()
            return out
        except (subprocess.SubprocessError, OSError):
            return None
        finally:
            for x in (tmp_out, tmp_src):
                if x and os.path.exists(x):
                    try:
                        os.remove(x)
                    except OSError:
                        pass
