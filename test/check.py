"""Selbsttest: bash test/make_testfotos.sh && python3 test/check.py (nutzt eine eigene Test-Datenbank)."""
import os, sys
os.environ.setdefault("BRENNWEITEN_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.db"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import db, scanner, analyse
S = os.path.dirname(os.path.abspath(__file__))
c = db.connect()
if not c.execute("select 1 from folders").fetchone():
    c.execute("INSERT INTO folders(path,added,status) VALUES(?, 'x','neu')", (S + "/testfotos",)); c.commit()
scanner.scan_all()
print("\n".join(scanner.PROGRESS.messages[-3:]))
# Rollei bestätigen wie ein Nutzer
r = analyse.analyse(c, {})
fails = []
def eq(name, got, exp):
    ok = got == exp
    print(("OK  " if ok else "FEHLER ") + name, got, "" if ok else "erwartet %r" % (exp,))
    if not ok: fails.append(name)
eq("Bilder gesamt", r["n_total"], 12)
eq("DX", r["dx"], 1)
eq("Klassen", [x["n"] for x in r["classes"]], [1,1,0,1,1,2,1,3,1,1,0])
eq("UWW <24/<20", (r["uww"]["u24"], r["uww"]["u20"]), (2, 2))
eq("UWW Objektive", [(x["lens"], x["u24"]) for x in r["uww_lens"]], [("EF-S10-18mm f/4.5-5.6 IS STM", 2)])
eq("UWW Jahre", [(x["year"], x["u24"]) for x in r["uww_year"]], [(2023, 2), (2024, 0)])
z = {x["lens"]: (x["n"], x["wide"], x["tele"], x["wide_to"], x["tele_from"]) for x in r["zooms"]}
eq("Zoom 24-120", z.get("NIKKOR Z 24-120mm f/4 S"), (6, 1, 1, 26, 110))
eq("Zoom 10-18", z.get("EF-S10-18mm f/4.5-5.6 IS STM"), (2, 1, 0, 11, 16))
eq("Zoom 18-150", z.get("RF-S18-150mm F3.5-6.3 IS STM"), (2, 0, 1, 20, 137))
ll = {x["lens"]: (x["n_known"], x["wo"], x["both"]) for x in r["lowlight"]}
eq("Offenblende 24-120", ll.get("NIKKOR Z 24-120mm f/4 S"), (6, 3, 1))
eq("Offenblende Rollei", ll.get("Unbekanntes Objektiv 85 mm f/1.8 (?)"), (2, 1, 1))
eq("Offenblende 10-18", ll.get("EF-S10-18mm f/4.5-5.6 IS STM"), (2, 1, 0))
eq("Offenblende 18-150", ll.get("RF-S18-150mm F3.5-6.3 IS STM"), (2, 1, 1))
eq("um 50/85", (r["around"]["n50"], r["around"]["n85"]), (1, 2))
eq("Jahre", [(y["year"], y["n"], y["median"], [g["n"] for g in y["groups"]]) for y in r["years"]],
   [(2023, 4, 34.4, [2, 1, 0, 1]), (2024, 8, 72.5, [0, 4, 4, 0])])
eq("Bewertet / gut", (r["rated"], r["good_n"]), (3, 2))
g = analyse.analyse(c, {"good": True})
eq("nur gute Bilder", (g["n_total"], g["rating_hint"] is not None), (2, True))
f = analyse.analyse(c, {"cameras": ["Canon|Canon EOS R7"], "from": "2023-12-01"})
eq("Filter R7 ab Dez 2023", f["n_total"], 2)
eq("Kameras", sorted((x["name"], x["enabled"]) for x in c.execute("select name, enabled from cameras")),
   [("Apple iPhone 15 Pro", 0), ("Canon EOS R7", 1), ("Nikon Z 6 III", 1), ("Nikon Z 8", 1)])
s = analyse.summary(c, {}, "alle")
eq("Zusammenfassung <= 25 Zeilen", len(s.splitlines()) <= 25, True)
print(s)
csv = analyse.export_csv(c, {})
eq("CSV Zeilen", len(csv.strip().splitlines()), 13)
for mk, md, nm, kind, crop in [("NIKON CORPORATION", "NIKON Z 6_2", "Nikon Z 6 II", "Kamera", 1.0), ("NIKON CORPORATION", "NIKON D7500", "Nikon D7500", "Kamera", 1.5),
        ("Canon", "Canon EOS 1200D", "Canon EOS 1200D", "Kamera", 1.6), ("Canon", "Canon EOS R6m2", "Canon EOS R6m2", "Kamera", 1.0), ("SONY", "ILCE-6700", "Sony ILCE-6700", "Kamera", 1.5),
        ("SONY", "ILCE-7M4", "Sony ILCE-7M4", "Kamera", 1.0), ("FUJIFILM", "X-T5", "Fujifilm X-T5", "Kamera", 1.5), ("FUJIFILM", "GFX100S", "Fujifilm GFX100S", "Kamera", 0.79),
        ("OM Digital Solutions", "OM-1", "OM System OM-1", "Kamera", 2.0), ("Panasonic", "DC-GH6", "Panasonic DC-GH6", "Kamera", 2.0), ("Panasonic", "DC-S5M2", "Panasonic DC-S5M2", "Kamera", 1.0),
        ("Google", "Pixel 7a", "Google Pixel 7a", "Smartphone", None), ("samsung", "SM-G920F", "Samsung SM-G920F", "Smartphone", None), ("EPSON", "Perfection V600", "Epson Perfection V600", "Scanner", None)]:
    eq("Kamera " + md, (db.camera_name(mk, md), db.camera_kind(mk, md), db.known_crop(mk, md)), (nm, kind, crop))
eq("Crop aus EXIF hat Vorrang", db.detect_crop("Foo", "Bar", [], [1.52, 1.5, 1.5]), (1.5, "exif"))
eq("Crop unbekannt", db.detect_crop("Foo", "Bar", [], []), (1.0, "annahme"))
# Zweisprachigkeit: Deutsch bleibt unverändert, Englisch ohne deutsche Reste
import csv as _csv, io as _io, json as _json, re as _re, i18n, report
de_summary, de_csv = analyse.summary(c, {}, "alle"), analyse.export_csv(c, {})
eq("Deutsch unverändert", de_summary, s)
i18n.use("en")
en_summary = analyse.summary(c, {}, "all")
en_csv = analyse.export_csv(c, {})
GERMAN = _re.compile(r"[äöüÄÖÜß]|\b(und|oder|von|bis|mit|Bilder|Fotos|Objektive?|Kameras?|Klassen|Anteil|Jahr|unter|über|Unbekannt\w*)\b")
eq("EN Zusammenfassung ohne Deutsch", [x for x in en_summary.splitlines() if GERMAN.search(x)], [])
eq("EN Zusammenfassung höchstens 25 Zeilen", len(en_summary.splitlines()) <= 25, True)
rows = list(_csv.reader(_io.StringIO(en_csv.lstrip("\ufeff"))))
eq("EN CSV Kopf", rows[0][:2], ["File", "Folder"])
eq("EN CSV Zeilen", len(rows), 13)
eq("EN CSV gleiche Spaltenzahl", {len(x) for x in rows}, {len(rows[0])})
eq("EN Zahl", (i18n.number(12800), i18n.decimal("2.8"), i18n.percent("12.5")), ("12,800", "2.8", "12.5%"))
eq("EN Einzahl", i18n.t("1 Fotos"), "1 photo")
eq("EN PDF", report.build(c, {}, "all")[:5], b"%PDF-")
i18n.use("de")
eq("DE nach EN unverändert", (analyse.summary(c, {}, "alle"), analyse.export_csv(c, {})), (de_summary, de_csv))
with open(i18n.PATH, encoding="utf-8") as fh:
    words = _json.load(fh)
eq("Platzhalter vollständig", [k for k, v in words.items() if len(_re.findall(r"\{[NDX]\}", k)) != len(set(_re.findall(r"\$\d", v)))], [])
print("\nFEHLER:", fails if fails else "keine")
