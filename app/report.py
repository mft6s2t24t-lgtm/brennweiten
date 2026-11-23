"""PDF-Bericht ohne Zusatzbibliotheken (A4, Helvetica). Nur Zahlen, keine Empfehlung."""
import datetime

import analyse
import features
from analyse import fmt

W, H = 595.28, 841.89
M = 42
HELV = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278] + [556] * 10 + \
    [278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
     667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556, 556,
     278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334,
     260, 334, 584]
BASE = {"ä": "a", "ö": "o", "ü": "u", "Ä": "A", "Ö": "O", "Ü": "U", "ß": "s", "é": "e"}
BLUE = (0.165, 0.47, 0.84)
INK = (0.05, 0.05, 0.05)
GREY = (0.40, 0.40, 0.38)
LINE = (0.88, 0.87, 0.85)
TRACK = (0.93, 0.92, 0.90)


def clean(s):
    s = str(s)
    for a, b in (("≥", ">="), ("≤", "<="), ("→", "->"), ("½", "1/2"), (" ", " "), (" ", " ")):
        s = s.replace(a, b) if a != "½" else s
    return s.encode("cp1252", "replace").decode("cp1252")


def width(s, size):
    t = 0
    for ch in clean(s):
        ch = BASE.get(ch, ch)
        o = ord(ch)
        t += HELV[o - 32] if 32 <= o < 127 else 556
    return t * size / 1000


def fit(s, size, maxw):
    s = clean(s)
    if width(s, size) <= maxw:
        return s
    while s and width(s + "...", size) > maxw:
        s = s[:-1]
    return s + "..."


def esc(s):
    b = clean(s).encode("cp1252", "replace")
    out = bytearray()
    for c in b:
        if c in (40, 41, 92):
            out += b"\\"
        out.append(c)
    return out.decode("latin-1")


class Pdf:
    def __init__(self):
        self.pages = []
        self.cur = None
        self.y = 0
        self.new_page()

    def new_page(self):
        self.cur = []
        self.pages.append(self.cur)
        self.y = H - M

    def need(self, h):
        if self.y - h < M + 18:
            self.new_page()

    def text(self, x, y, s, size=9, bold=False, color=INK, align="l"):
        s = clean(s)
        if align == "r":
            x -= width(s, size)
        self.cur.append("%.3f %.3f %.3f rg BT /%s %.1f Tf %.2f %.2f Td (%s) Tj ET" % (
            color[0], color[1], color[2], "F2" if bold else "F1", size, x, y, esc(s)))

    def rect(self, x, y, w, h, color):
        self.cur.append("%.3f %.3f %.3f rg %.2f %.2f %.2f %.2f re f" % (color[0], color[1], color[2], x, y, w, h))

    def line(self, x1, y1, x2, y2, color=LINE):
        self.cur.append("%.3f %.3f %.3f RG 0.5 w %.2f %.2f m %.2f %.2f l S" % (color[0], color[1], color[2], x1, y1, x2, y2))

    def h(self, s, sub=""):
        self.need(95)
        self.y -= 14
        self.text(M, self.y, s, 12, True)
        if sub:
            self.text(M + width(s, 12) * 1.08 + 10, self.y, sub, 8.5, False, GREY)
        self.y -= 8
        self.line(M, self.y, W - M, self.y)
        self.y -= 14

    def table(self, cols, rows):
        """cols: (Titel, Breite, Ausrichtung)"""
        self.need(14 + min(len(rows), 3) * 13)

        def head():
            x = M
            for t, w, a in cols:
                self.text(x + w - 3 if a == "r" else x, self.y, t, 8, True, GREY, a)
                x += w
            self.y -= 4
            self.line(M, self.y, W - M, self.y)
            self.y -= 10

        head()
        for r in rows:
            if self.y < M + 26:
                self.new_page()
                head()
            x = M
            for v, (t, w, a) in zip(r, cols):
                if isinstance(v, tuple) and v[0] == "bar":
                    self.rect(x, self.y - 1, w - 6, 7, TRACK)
                    self.rect(x, self.y - 1, max(0.5, (w - 6) * min(100, v[1]) / 100), 7, BLUE)
                else:
                    s = fit(v, 8.5, w - 5)
                    self.text(x + w - 3 if a == "r" else x, self.y, s, 8.5, False, INK, a)
                x += w
            self.y -= 13
        self.y -= 4

    def output(self):
        n = len(self.pages)
        for i, c in enumerate(self.pages):
            c.append("%.3f %.3f %.3f rg BT /F1 8 Tf %.2f %.2f Td (Seite %d von %d) Tj ET" % (
                GREY[0], GREY[1], GREY[2], W - M - 55, 24, i + 1, n))
        objs = {1: b"<< /Type /Catalog /Pages 2 0 R >>",
                3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
                4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"}
        kids = []
        nid = 5
        for c in self.pages:
            stream = "\n".join(c).encode("latin-1", "replace")
            objs[nid] = (("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] /Resources << /Font << /F1 3 0 R "
                          "/F2 4 0 R >> >> /Contents %d 0 R >>") % (W, H, nid + 1)).encode()
            objs[nid + 1] = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
            kids.append("%d 0 R" % nid)
            nid += 2
        objs[2] = ("<< /Type /Pages /Kids [%s] /Count %d >>" % (" ".join(kids), len(kids))).encode()
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offs = {}
        for k in sorted(objs):
            offs[k] = len(out)
            out += b"%d 0 obj\n" % k + objs[k] + b"\nendobj\n"
        x = len(out)
        size = max(objs) + 1
        out += b"xref\n0 %d\n0000000000 65535 f \n" % size
        for k in range(1, size):
            out += b"%010d 00000 n \n" % offs[k]
        out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, x)
        return bytes(out)


def pc(v):
    return fmt(float(v)) + " %"


def num(v):
    return "{:,}".format(int(v)).replace(",", ".")


def build(conn, f, filter_text):
    r = analyse.analyse(conn, f)
    pdf = Pdf()
    pdf.y -= 8
    pdf.text(M, pdf.y, "Brennweiten-Bericht", 20, True)
    pdf.y -= 16
    pdf.text(M, pdf.y, "Erstellt am %s  ·  Alle Brennweiten im Kleinbild-Äquivalent  ·  Nur Fakten aus den eigenen Fotos"
             % datetime.date.today().strftime("%d.%m.%Y"), 8.5, False, GREY)
    pdf.y -= 12
    pdf.text(M, pdf.y, fit("Filter: " + filter_text, 8.5, W - 2 * M), 8.5, False, GREY)
    pdf.y -= 22
    if not r["n_total"]:
        pdf.text(M, pdf.y, "Keine Bilder für diesen Filter.", 11)
        return pdf.output()

    p = r["period"]
    tiles = [(num(r["n_total"]), "Bilder", "%s bis %s" % (p[0], p[1]) if p else ""),
             (fmt(r["median"]) + " mm", "Median-Brennweite", "KB"),
             (pc(r["uww"]["u24_pct"]), "unter 24 mm", "unter 20 mm: " + pc(r["uww"]["u20_pct"])),
             (pc(r["around"]["p85"]), "um 85 mm", "um 50 mm: " + pc(r["around"]["p50"]))]
    tw = (W - 2 * M - 18) / 4
    for k, (v, l, s) in enumerate(tiles):
        x = M + k * (tw + 6)
        pdf.rect(x, pdf.y - 40, tw, 50, (0.965, 0.96, 0.945))
        pdf.text(x + 8, pdf.y - 8, v, 14, True)
        pdf.text(x + 8, pdf.y - 21, l, 8.5, False, GREY)
        pdf.text(x + 8, pdf.y - 33, fit(s, 7.5, tw - 12), 7.5, False, GREY)
    pdf.y -= 56

    pdf.h("Brennweitenklassen", "Anteil aller Fotos")
    mx = max(c["pct"] for c in r["classes"]) or 1
    for c in r["classes"]:
        pdf.need(14)
        pdf.text(M, pdf.y, c["label"] + " mm", 8.5)
        bw = 330
        pdf.rect(M + 62, pdf.y - 1, bw * c["pct"] / mx if c["pct"] else 0.1, 8, BLUE)
        pdf.text(W - M, pdf.y, "%s  ·  %s" % (num(c["n"]), pc(c["pct"])), 8.5, align="r")
        pdf.y -= 13
    pdf.y -= 4

    pdf.h("Objektive", "die 15 meistgenutzten")
    pdf.table([("Objektiv", 270, "l"), ("Bilder", 60, "r"), ("Anteil", 60, "r"), ("", 121, "l")],
              [[x["lens"], num(x["n"]), pc(x["pct"]), ("bar", x["pct"] * 100 / max(1, r["lens_counts"][0]["pct"]))]
               for x in r["lens_counts"][:15]])

    pdf.h("Ultraweitwinkel", "unter 24 und unter 20 mm je Jahr")
    pdf.table([("Jahr", 70, "l"), ("Bilder", 80, "r"), ("< 24 mm", 90, "r"), ("Anteil", 70, "r"), ("< 20 mm", 90, "r"), ("Anteil", 70, "r")],
              [[y["year"], num(y["n"]), num(y["u24"]), pc(y["u24_pct"]), num(y["u20"]), pc(y["u20_pct"])] for y in r["uww_year"]])

    pdf.h("Zoom am Anschlag", "Anteil am kurzen und langen Ende, Brennweite am Objektiv")
    pdf.table([("Objektiv", 250, "l"), ("Bilder", 55, "r"), ("kurzes Ende", 105, "r"), ("langes Ende", 101, "r")],
              [[z["lens"], num(z["n"]), "%g-%g: %s" % (z["min"], z["wide_to"], pc(z["wide_pct"])),
                "%g-%g: %s" % (z["tele_from"], z["max"], pc(z["tele_pct"]))] for z in r["zooms"][:12]])

    pdf.h("Offenblende bei wenig Licht", "ISO über 3200")
    pdf.table([("Objektiv", 250, "l"), ("Bilder", 55, "r"), ("Offenblende", 70, "r"), ("ISO > 3200", 66, "r"), ("beides", 70, "r")],
              [[x["lens"], num(x["n"]), pc(x["wo_pct"]), pc(x["iso_pct"]), "%s · %s" % (num(x["both"]), pc(x["both_pct"]))]
               for x in r["lowlight"][:12] if x["n_known"]])

    pdf.h("Entwicklung pro Jahr")
    labels = r["group_labels"]
    pdf.table([("Jahr", 50, "l"), ("Bilder", 60, "r"), ("Median", 65, "r")] + [(g, 84, "r") for g in labels],
              [[y["year"], num(y["n"]), fmt(y["median"]) + " mm"] + [pc(g["pct"]) for g in y["groups"]] for y in r["years"]])

    sim = features.simulate(conn, f, [])
    pdf.h("Abdeckung typischer Objektive", "Anteil der Fotos im Brennweitenbereich")
    pdf.table([("Objektiv", 190, "l"), ("Bereich (KB)", 95, "r"), ("Fotos", 66, "r"), ("Anteil", 60, "r"), ("", 100, "l")],
              [[x["name"], "%s-%s mm" % (fmt(float(x["lo"])), fmt(float(x["hi"]))), num(x["n"]), pc(x["pct"]), ("bar", x["pct"])]
               for x in sim["single"]])

    d = features.days(conn, f)
    pdf.h("Fototage", "%s Tage, im Schnitt %s Fotos" % (num(d["days"]), fmt(d["per_day"])))
    pdf.table([("Objektive am Tag", 200, "l"), ("Tage", 80, "r"), ("Anteil", 80, "r"), ("", 151, "l")],
              [[x["label"], num(x["days"]), pc(x["pct"]), ("bar", x["pct"])] for x in d["dist"]])
    pdf.need(14)
    pdf.text(M, pdf.y, "Weitwinkel (bis %d mm) und Tele (ab %d mm) am selben Tag: %s Tage (%s)"
             % (d["wide"], d["tele"], num(d["both"]), pc(d["both_pct"])), 8.5)
    pdf.y -= 14
    return pdf.output()
