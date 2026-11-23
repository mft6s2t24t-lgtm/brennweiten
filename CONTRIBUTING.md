# Mitmachen

Danke, dass du Brennweiten verbessern möchtest. Fehlerberichte, Ideen, Code-Reviews und Pull Requests sind willkommen, auf Deutsch oder Englisch.

## Fehler melden

Eröffne ein [Issue](../../issues) und nenne macOS-Version, Mac-Typ, App-Version, Kamera und Objektiv.

**Lade bitte keine privaten Fotos, Datenbanken oder vollständigen Dateipfade hoch.** EXIF-Daten können Seriennummern, Namen und GPS-Positionen enthalten. Für Erkennungsfehler reicht meist diese Ausgabe:

```bash
exiftool -Make -Model -LensModel -LensID -FocalLength -FocalLengthIn35mmFormat -ScaleFactor35efl -FNumber -MaxApertureValue DATEI
```

## Grundsätze

- Fotos werden nur gelesen und niemals verändert.
- Die App arbeitet lokal und sendet keine Daten ins Internet.
- Sie gibt Fakten aus den eigenen Fotos wieder, aber keine Kaufempfehlung.
- Der Python-Teil nutzt nur die Standardbibliothek und bleibt zu Python 3.9 kompatibel.
- Die Oberfläche kommt ohne Frameworks und externe Dateien aus.

## Lokal entwickeln

```bash
brew install exiftool
```

```bash
cd app && BRENNWEITEN_DATA=/tmp/brennweiten-dev BRENNWEITEN_PORT=8792 python3 server.py
```

Danach läuft die Oberfläche unter <http://127.0.0.1:8792>. Vor einem Pull Request bitte den Selbsttest ausführen:

```bash
bash test/make_testfotos.sh && python3 test/check.py
```

Mit einem Beitrag stimmst du zu, dass er unter der [MIT-Lizenz](LICENSE) des Projekts veröffentlicht wird.
