"""Lokaler Webserver (nur 127.0.0.1) für die Oberfläche."""
import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyse  # noqa: E402
import db  # noqa: E402
import features  # noqa: E402
import insights  # noqa: E402
import report  # noqa: E402
import scanner  # noqa: E402
import tabelle  # noqa: E402
import thumbs  # noqa: E402

PORT_SETTING = os.environ.get("BRENNWEITEN_PORT") or "8765"
PORT = 8765 if PORT_SETTING == "auto" else int(PORT_SETTING)
PARENT = int(os.environ.get("BRENNWEITEN_PARENT") or 0)
WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
IDLE_QUIT = 20 * 60  # Sekunden ohne geöffnete Oberfläche -> Programm beendet sich
LAST_SEEN = [time.time()]
CONN_LOCK = threading.Lock()
CONN = None
SERVER = None


def conn():
    global CONN
    if CONN is None:
        CONN = db.connect()
    return CONN


def filters_from(q):
    def lst(k):
        v = q.get(k, [""])[0]
        return [x for x in v.split("\x1f") if x] if v else []
    try:
        cf = json.loads(q.get("cf", ["{}"])[0] or "{}")
    except ValueError:
        cf = {}
    return {"cameras": lst("cameras"), "lenses": lst("lenses"), "from": q.get("from", [""])[0],
            "to": q.get("to", [""])[0], "good": q.get("good", [""])[0] in ("1", "true"), "cf": cf}


def sort_from(q):
    try:
        s = json.loads(q.get("sort", ["[]"])[0] or "[]")
    except ValueError:
        return []
    return [x for x in s if isinstance(x, list) and len(x) == 2]


def cols_from(q):
    v = q.get("cols", [""])[0]
    return v.split(",") if v else None


def filter_text(f):
    parts = []
    c = conn()
    if f["cameras"]:
        names = {r["key"]: r["name"] for r in c.execute("SELECT key,name FROM cameras")}
        parts.append("Kameras " + ", ".join(names.get(k, k) for k in f["cameras"]))
    else:
        parts.append("alle ausgewählten Kameras")
    if f["lenses"]:
        parts.append("Objektive " + ", ".join(f["lenses"]))
    if f["from"] or f["to"]:
        parts.append("Zeitraum %s bis %s" % (f["from"] or "Anfang", f["to"] or "heute"))
    if f["good"]:
        parts.append("nur ≥ 3 Sterne")
    labels = {k: l for k, l, _ in tabelle.COLUMNS}
    active = [labels[k] for k, v in (f.get("cf") or {}).items() if k in labels and v]
    if active:
        parts.append("Spaltenfilter: " + ", ".join(active))
    return "; ".join(parts)


def choose_folders():
    script = [
        "-e", 'activate',
        "-e", 'set fs to choose folder with prompt "Fotoordner auswählen (mehrere mit ⌘-Klick)" '
              'with multiple selections allowed',
        "-e", 'set out to ""',
        "-e", 'repeat with f in fs',
        "-e", 'set out to out & POSIX path of f & linefeed',
        "-e", 'end repeat',
        "-e", 'return out']
    p = subprocess.run(["osascript"] + script, capture_output=True, text=True)
    if p.returncode != 0:
        return []
    return [x.rstrip("/") or "/" for x in p.stdout.splitlines() if x.strip()]


def add_folder(path):
    c = conn()
    path = os.path.abspath(os.path.expanduser(path.strip())).rstrip("/") or "/"
    if not os.path.isdir(path):
        return "Ordner nicht gefunden: %s" % path
    rows = c.execute("SELECT id, path FROM folders").fetchall()
    for r in rows:
        if path == r["path"] or path.startswith(r["path"] + "/"):
            return "Schon enthalten in %s" % r["path"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cur = c.execute("INSERT INTO folders(path, added, status) VALUES(?,?,?)", (path, now, "neu"))
    new_id = cur.lastrowid
    # Unterordner, die schon eingetragen waren, werden zusammengeführt
    for r in rows:
        if r["path"].startswith(path + "/"):
            c.execute("UPDATE images SET folder_id=? WHERE folder_id=?", (new_id, r["id"]))
            c.execute("DELETE FROM folders WHERE id=?", (r["id"],))
    c.commit()
    return None


def folders_info():
    c = conn()
    out = []
    for r in c.execute("SELECT * FROM folders ORDER BY path"):
        n = c.execute("SELECT COUNT(*) FROM images WHERE folder_id=?", (r["id"],)).fetchone()[0]
        d = dict(r)
        d["files"] = n
        d["online"] = os.path.isdir(r["path"])
        out.append(d)
    return out


def cameras_info():
    c = conn()
    rows = c.execute(
        "SELECT c.*, COUNT(i.id) n, MIN(i.dt) first, MAX(i.dt) last, "
        "SUM(CASE WHEN i.canonical=0 THEN 1 ELSE 0 END) dups, "
        "GROUP_CONCAT(DISTINCT i.serial) serials, COUNT(DISTINCT i.lens_key) nlens "
        "FROM cameras c LEFT JOIN images i ON i.camera_key=c.key GROUP BY c.key "
        "ORDER BY c.enabled DESC, n DESC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["n_images"] = (d["n"] or 0) - (d["dups"] or 0)
        out.append(d)
    nocam = c.execute("SELECT COUNT(*) FROM images WHERE camera_key IS NULL OR camera_key=''").fetchone()[0]
    return {"cameras": out, "no_camera": nocam}


def lenses_info():
    c = conn()
    rows = c.execute(
        "SELECT l.*, COUNT(i.id) n, GROUP_CONCAT(DISTINCT i.lens_raw) raws, "
        "GROUP_CONCAT(DISTINCT c.name) cams FROM lenses l "
        "JOIN images i ON i.lens_key=l.key AND i.canonical=1 "
        "JOIN cameras c ON c.key=i.camera_key AND c.enabled=1 "
        "GROUP BY l.key ORDER BY l.confirmed, n DESC").fetchall()
    return [dict(r) for r in rows]


def start_scan(ids=None):
    if scanner.PROGRESS.running:
        return False
    threading.Thread(target=scanner.scan_all, args=(ids,), daemon=True).start()
    return True


def auto_enabled():
    with CONN_LOCK:
        return db.get_setting(conn(), "auto_scan", "1") == "1"


def auto_update():
    """Beim Start neue Fotos einlesen und sobald ein Laufwerk wieder verbunden ist."""
    if os.environ.get("BRENNWEITEN_NOAUTO"):
        return
    time.sleep(2)
    seen = {}
    first = True
    while True:
        try:
            with CONN_LOCK:
                rows = [(r["id"], r["path"]) for r in conn().execute("SELECT id, path FROM folders")]
            online = {i: os.path.isdir(x) for i, x in rows}
            todo = [i for i, up in online.items() if up and (first or not seen.get(i))]
            seen = online
            first = False
            if todo and auto_enabled() and not scanner.PROGRESS.running:
                start_scan(todo)
        except Exception:  # noqa
            pass
        time.sleep(30)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, (dict, list)) or body is None:
            body = json.dumps(body, ensure_ascii=False)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def check_origin(self):
        # Schutz gegen fremde Webseiten, die den lokalen Server ansprechen
        o = self.headers.get("Origin")
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            return False
        return not o or o in ("http://127.0.0.1:%d" % PORT, "http://localhost:%d" % PORT)

    def do_GET(self):
        LAST_SEEN[0] = time.time()
        if not self.check_origin():
            return self.send(403, {"error": "forbidden"})
        u = urlparse(self.path)
        q = parse_qs(u.query)
        p = u.path
        try:
            if p in ("/", "/index.html"):
                return self.static("index.html")
            if p.startswith("/web/"):
                return self.static(p[5:])
            if p == "/api/ping":
                return self.send(200, {"app": "brennweiten", "code": os.path.dirname(os.path.abspath(__file__))})
            if p == "/api/status":
                return self.send(200, scanner.PROGRESS.as_dict())
            if p == "/api/folders":
                return self.send(200, folders_info())
            if p == "/api/cameras":
                with CONN_LOCK:
                    return self.send(200, cameras_info())
            if p == "/api/lenses":
                with CONN_LOCK:
                    return self.send(200, lenses_info())
            if p == "/api/failed":
                return self.send(200, [dict(r) for r in conn().execute(
                    "SELECT * FROM failed ORDER BY at DESC LIMIT 200")])
            if p == "/api/analysis":
                with CONN_LOCK:
                    return self.send(200, analyse.analyse(conn(), filters_from(q)))
            if p == "/api/detail":
                def number(k):
                    try:
                        return float(q.get(k, [""])[0].replace(",", "."))
                    except ValueError:
                        return None
                mm = number("fl")
                ap = number("fnum")
                basis = "objektiv" if q.get("basis", [""])[0] == "objektiv" else "kb"
                with CONN_LOCK:
                    return self.send(200, analyse.detail(
                        conn(), filters_from(q), q.get("lens", [""])[0],
                        int(round(mm)) if mm is not None else None,
                        round(ap, 1) if ap is not None else None, basis))
            if p == "/api/columns":
                return self.send(200, [{"key": k, "label": l, "type": t} for k, l, t in tabelle.COLUMNS])
            if p == "/api/table":
                f = filters_from(q)
                offset = max(0, int(q.get("offset", ["0"])[0] or 0))
                limit = min(500, max(1, int(q.get("limit", ["100"])[0] or 100)))
                with CONN_LOCK:
                    rows = tabelle.sort_rows(analyse.selected(conn(), f), sort_from(q))
                keys = ["id"] + [c[0] for c in tabelle.COLUMNS]
                return self.send(200, {"stats": tabelle.stats(rows), "offset": offset,
                                       "rows": [tabelle.public(r, keys) for r in rows[offset:offset + limit]]})
            if p == "/api/facet":
                f = filters_from(q)
                col = q.get("col", [""])[0]
                if col not in tabelle.TYPES:
                    return self.send(400, {"error": "unbekannte Spalte"})
                f["cf"] = {k: v for k, v in f["cf"].items() if k != col}
                with CONN_LOCK:
                    rows = analyse.selected(conn(), f)
                return self.send(200, tabelle.facet(rows, col, q.get("search", [""])[0]))
            if p == "/api/days":
                def intval(k, d):
                    try:
                        return int(q.get(k, [d])[0])
                    except ValueError:
                        return d
                with CONN_LOCK:
                    return self.send(200, features.days(conn(), filters_from(q), intval("wide", 28), intval("tele", 100)))
            if p == "/api/keepers":
                with CONN_LOCK:
                    return self.send(200, features.keepers(conn(), filters_from(q)))
            if p == "/api/entities":
                kind = "camera" if q.get("kind", [""])[0] == "camera" else "lens"
                with CONN_LOCK:
                    return self.send(200, insights.entities(conn(), filters_from(q), kind))
            if p == "/api/tiles":
                with CONN_LOCK:
                    return self.send(200, insights.tiles_payload(conn(), filters_from(q)))
            if p == "/api/quality":
                with CONN_LOCK:
                    return self.send(200, features.quality(conn()))
            if p == "/api/views":
                with CONN_LOCK:
                    return self.send(200, [{"id": r["id"], "name": r["name"], "state": json.loads(r["state"])}
                                           for r in conn().execute("SELECT * FROM views ORDER BY name")])
            if p == "/api/settings":
                return self.send(200, {"auto_scan": auto_enabled()})
            if p.startswith("/thumb/"):
                with CONN_LOCK:
                    r = conn().execute("SELECT path,size,mtime,ext FROM images WHERE id=?", (int(p[7:]),)).fetchone()
                if not r:
                    return self.send(404, {"error": "not found"})
                t = thumbs.get(r["path"], r["size"], r["mtime"], r["ext"])
                if not t:
                    return self.send(404, {"error": "keine Vorschau"})
                with open(t, "rb") as fh:
                    return self.send(200, fh.read(), "image/jpeg")
            if p == "/api/report.pdf":
                f = filters_from(q)
                with CONN_LOCK:
                    data = report.build(conn(), f, filter_text(f))
                name = "brennweiten_bericht_%s.pdf" % datetime.now().strftime("%Y-%m-%d")
                return self.send(200, data, "application/pdf",
                                 {"Content-Disposition": 'attachment; filename="%s"' % name})
            if p == "/api/summary":
                f = filters_from(q)
                with CONN_LOCK:
                    return self.send(200, {"text": analyse.summary(conn(), f, filter_text(f))})
            if p == "/api/export.csv":
                with CONN_LOCK:
                    data = analyse.export_csv(conn(), filters_from(q), sort_from(q), cols_from(q))
                name = "brennweiten_%s.csv" % datetime.now().strftime("%Y-%m-%d")
                return self.send(200, data, "text/csv; charset=utf-8",
                                 {"Content-Disposition": 'attachment; filename="%s"' % name})
            return self.send(404, {"error": "not found"})
        except Exception as e:  # noqa
            return self.send(500, {"error": str(e)})

    def do_POST(self):
        LAST_SEEN[0] = time.time()
        if not self.check_origin():
            return self.send(403, {"error": "forbidden"})
        p = urlparse(self.path).path
        try:
            b = self.body()
            c = conn()
            if p == "/api/folders/choose":
                msgs = [m for m in (add_folder(x) for x in choose_folders()) if m]
                return self.send(200, {"messages": msgs})
            if p == "/api/folders/add":
                m = add_folder(b.get("path", ""))
                return self.send(200, {"messages": [m] if m else []})
            if p == "/api/folders/remove":
                with CONN_LOCK:
                    if scanner.PROGRESS.running:
                        return self.send(409, {"error": "Bitte warten, bis das Einlesen fertig ist."})
                    c.execute("DELETE FROM images WHERE folder_id=?", (b["id"],))
                    c.execute("DELETE FROM folders WHERE id=?", (b["id"],))
                    c.commit()
                    scanner.postprocess(c)
                return self.send(200, {"ok": True})
            if p == "/api/scan":
                ok = start_scan(b.get("ids"))
                return self.send(200, {"started": ok})
            if p == "/api/scan/cancel":
                scanner.PROGRESS.cancel = True
                return self.send(200, {"ok": True})
            if p == "/api/cameras":
                with CONN_LOCK:
                    for k in b.get("cameras", []):
                        old = c.execute("SELECT crop, crop_src, user_set FROM cameras WHERE key=?", (k["key"],)).fetchone()
                        if not old:
                            continue
                        crop = float(k["crop"])
                        changed = abs(crop - (old["crop"] or 0)) > 0.001
                        c.execute("UPDATE cameras SET name=?, crop=?, enabled=?, user_set=?, crop_src=? WHERE key=?",
                                  (k["name"], crop, 1 if k["enabled"] else 0, 1 if changed or old["user_set"] else 0,
                                   "manuell" if changed else old["crop_src"], k["key"]))
                    c.commit()
                return self.send(200, {"ok": True})
            if p == "/api/lenses":
                with CONN_LOCK:
                    for k in b.get("lenses", []):
                        def num(v):
                            try:
                                return float(str(v).replace(",", "."))
                            except (TypeError, ValueError):
                                return None
                        c.execute(
                            "UPDATE lenses SET name=?, min_fl=?, max_fl=?, ap_wide=?, ap_tele=?, "
                            "confirmed=?, user_set=? WHERE key=?",
                            (k["name"].strip(), num(k["min_fl"]), num(k["max_fl"]), num(k["ap_wide"]),
                             num(k["ap_tele"]), 1 if k.get("confirmed") else 0,
                             1 if k.get("user_set") else 0, k["key"]))
                    c.commit()
                return self.send(200, {"ok": True})
            if p == "/api/tiles":
                with CONN_LOCK:
                    db.set_setting(c, "tiles", json.dumps(insights.clean_tiles(b.get("tiles")), ensure_ascii=False))
                return self.send(200, {"ok": True})
            if p in ("/api/simulate", "/api/light", "/api/compare", "/api/photos", "/api/profile", "/api/check"):
                f = filters_from(parse_qs(b.get("qs") or ""))
                with CONN_LOCK:
                    if p == "/api/profile":
                        if b.get("from"):
                            f["from"] = b["from"]
                        if b.get("to"):
                            f["to"] = b["to"]
                        return self.send(200, insights.profile(analyse.selected(c, f)))
                    if p == "/api/check":
                        return self.send(200, insights.check(c, f, b.get("candidates")))
                    if p == "/api/simulate":
                        return self.send(200, features.simulate(c, f, b.get("sets")))
                    if p == "/api/light":
                        return self.send(200, features.light(c, f, float(b["min"]), float(b["max"]), float(b["ap"])))
                    if p == "/api/compare":
                        return self.send(200, features.compare(c, f, b.get("a"), b.get("b")))
                    return self.send(200, features.photos(c, f, b.get("spec"), int(b.get("offset") or 0)))
            if p == "/api/reveal":
                with CONN_LOCK:
                    r = c.execute("SELECT path FROM images WHERE id=?", (int(b["id"]),)).fetchone()
                if not r or not os.path.exists(r["path"]):
                    return self.send(404, {"error": "Datei nicht erreichbar (Laufwerk verbunden?)"})
                subprocess.run(["/usr/bin/open", "-R", r["path"]], check=False)
                return self.send(200, {"ok": True})
            if p == "/api/views":
                with CONN_LOCK:
                    c.execute("INSERT OR REPLACE INTO views(name,state,created) VALUES(?,?,?)",
                              (b["name"].strip()[:80], json.dumps(b["state"], ensure_ascii=False),
                               datetime.now().strftime("%Y-%m-%d %H:%M")))
                    c.commit()
                return self.send(200, {"ok": True})
            if p == "/api/views/delete":
                with CONN_LOCK:
                    c.execute("DELETE FROM views WHERE id=?", (int(b["id"]),))
                    c.commit()
                return self.send(200, {"ok": True})
            if p == "/api/settings":
                with CONN_LOCK:
                    db.set_setting(c, "auto_scan", "1" if b.get("auto_scan") else "0")
                return self.send(200, {"ok": True})
            if p == "/api/quit":
                self.send(200, {"ok": True})
                threading.Thread(target=shutdown, daemon=True).start()
                return
            return self.send(404, {"error": "not found"})
        except Exception as e:  # noqa
            return self.send(500, {"error": str(e)})

    def static(self, name):
        path = os.path.normpath(os.path.join(WEB, name))
        if not path.startswith(WEB) or not os.path.isfile(path):
            return self.send(404, {"error": "not found"})
        ctype = {"html": "text/html", "js": "text/javascript", "css": "text/css",
                 "svg": "image/svg+xml", "png": "image/png"}.get(path.rsplit(".", 1)[-1], "text/plain")
        with open(path, "rb") as fh:
            return self.send(200, fh.read(), ctype + "; charset=utf-8")


def shutdown():
    time.sleep(0.3)
    scanner.PROGRESS.cancel = True
    SERVER.shutdown()


def watchdog():
    while True:
        time.sleep(2 if PARENT else 30)
        if PARENT:
            if os.getppid() != PARENT:   # App wurde beendet oder ist abgestürzt
                shutdown()
                return
        elif time.time() - LAST_SEEN[0] > IDLE_QUIT and not scanner.PROGRESS.running:
            shutdown()
            return


def bind():
    """Fester Port, damit Filter erhalten bleiben. Ist er belegt, nimmt die App einen freien."""
    global PORT
    ports = list(range(8765, 8785)) + [0] if PORT_SETTING == "auto" else [PORT]
    for i, port in enumerate(ports):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port), H)
            PORT = srv.server_address[1]
            return srv
        except OSError:
            if i == len(ports) - 1:
                raise


def main():
    global SERVER
    SERVER = bind()
    SERVER.daemon_threads = True
    url = "http://127.0.0.1:%d/" % PORT
    signal.signal(signal.SIGTERM, lambda *_: threading.Thread(target=shutdown, daemon=True).start())
    db.migrate(conn())
    threading.Thread(target=watchdog, daemon=True).start()
    threading.Thread(target=auto_update, daemon=True).start()
    if "--open" in sys.argv:
        subprocess.Popen(["open", url])
    print("PORT=%d" % PORT, flush=True)
    print("Brennweiten-Tool läuft auf %s" % url, flush=True)
    SERVER.serve_forever()


if __name__ == "__main__":
    main()
