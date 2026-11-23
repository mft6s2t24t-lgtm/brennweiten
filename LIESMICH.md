# Brennweiten-Tool

Wertet aus den EXIF-Daten deiner Fotos aus, welche Brennweiten du wirklich nutzt – als Grundlage
für Objektiv-Entscheidungen. Läuft komplett lokal, ohne Internet. **Fotos werden nur gelesen,
nie verändert, verschoben oder umbenannt.**

## Installieren

1. `Brennweiten.dmg` öffnen und **Brennweiten** auf **Programme** ziehen.
2. Brennweiten aus dem Ordner Programme starten. Es muss nichts zusätzlich installiert werden.
   Die App läuft auf Apple-Silicon- und Intel-Macs ab macOS 12.3.
3. Solange die App nicht von Apple beglaubigt ist, blockiert macOS den ersten Start. Dann unter
   **Systemeinstellungen → Datenschutz & Sicherheit** auf **Dennoch öffnen** klicken und beim
   Start einmal **Freigeben** wählen.

Beim ersten Zugriff auf externe Laufwerke oder ein NAS fragt macOS eventuell nach einer Erlaubnis.
Beenden wie jede Mac-App mit ⌘Q.

## Erste Einrichtung

1. **Fotoordner wählen** (mehrere mit ⌘-Klick). Das Einlesen startet danach von selbst. Beim ersten
   Mal dauert es, später werden nur neue oder geänderte Dateien gelesen.
2. **Kameras** prüfen: Alle Modelle kommen aus den EXIF-Daten deiner Fotos. Smartphones und Scanner
   sind zunächst aus und lassen sich per Haken einschalten. Steht beim Crop-Faktor „bitte prüfen“,
   trage den Wert deiner Kamera ein.
3. **Objektive** prüfen: Oben stehen Vorschläge für Bilder ohne Objektivnamen. Name anpassen und
   **Bestätigen**. **Gleicher Name = wird zusammengezählt.**

## Auswertung

Filter: Kameras, Objektive, Zeitraum, „ab 3 Sternen“. Alle Brennweiten im
Kleinbild-Äquivalent (KB).

Die App ist in drei Bereiche gegliedert:

- **Analyse:** Übersicht, Objektive, Kameras, Fototage, Tabelle
- **Entscheiden:** Objektiv prüfen, Vergleich
- **Verwaltung:** Kameras & Objektive, Datenqualität, Ordner & Einlesen

Die **Übersicht** zeigt deine Kennzahlen, die Verteilung in Klassen (<17 … >400 mm), das feine
Histogramm (je mm), die meistgenutzten Objektive und die Entwicklung pro Jahr.

Auf der Seite **Objektive** findest du Zoom am Anschlag (z. B. 24-120: 24–26 und 110–120 mm, gemessen
am Objektiv), Offenblende bei wenig Licht (Offenblende **und** ISO über 3200), Ultraweitwinkel,
die Nutzung um 50 und 85 mm und die Trefferquote. Wähle ein Objektiv und gib eine Brennweite
(z. B. 28) und/oder Blende (z. B. 2,8) ein, um genau diese Fotos zu zählen.

Unter **Exportieren** sicherst du die gefilterten Bilder als CSV für Excel oder einen PDF-Bericht.
**Zusammenfassung kopieren** legt höchstens 25 Zeilen Zahlen und Fakten in die Zwischenablage.

## So rechnet das Tool

- **KB-Brennweite:** Der EXIF-Wert „FocalLengthIn35mmFormat“ wird genommen, wenn er zum Crop-Faktor
  der Kamera passt, sonst Brennweite × Crop-Faktor. Bilder im **DX-Modus** werden erkannt.
- **Crop-Faktor:** zuerst aus den Bilddaten, dann aus der bekannten Sensorgröße gängiger Baureihen.
  Ist beides nicht möglich, gilt 1,0 und die App bittet dich um Prüfung. Eigene Werte bleiben erhalten.
- **Duplikate** zählen einmal: Bilder derselben Kamera mit gleicher Aufnahmezeit (inkl.
  Sekundenbruchteilen) und Seriennummer gehören zusammen – RAW+JPEG, Exporte (DxO, Lightroom …)
  und Sicherungskopien. Gezählt wird bevorzugt das RAW (NEF/NRW/CR2/CR3), dann DNG, TIFF, HEIF, JPG.
  Serienbilder derselben Sekunde ohne Sekundenbruchteile bleiben getrennt, wenn es unterschiedliche
  Dateien sind.
- **Bewertung:** aus dem Bild (EXIF/XMP) oder dem `.xmp`-Sidecar (`Bild.NEF.xmp` oder `Bild.xmp`);
  der Sidecar hat Vorrang. Bei Duplikaten zählt die höchste Bewertung der Gruppe.
- **Offenblende:** Blende ≤ größtmögliche Blende bei dieser Brennweite (aus EXIF „MaxApertureValue“,
  sonst aus Objektivname/Einstellungen).
- **Fehlendes Laufwerk:** Ist ein Ordner nicht erreichbar, wird er als „nicht erreichbar“ markiert;
  seine Daten bleiben in der Auswertung. Gelöschte Dateien werden nur entfernt, wenn ein Ordner
  vollständig gelesen werden konnte.

## Deine Daten

Datenbank, Vorschaubilder und Protokoll liegen unter `~/Library/Application Support/Brennweiten`
(Menü **Hilfe → Datenordner im Finder zeigen**).

**Deinstallieren:** App beenden, Brennweiten aus Programme und diesen Datenordner in den Papierkorb
legen. Deine Fotos sind davon nicht betroffen.

## Weitere Funktionen

- **Kennzahlen:** Auf der Übersicht legst du über „Kennzahlen anpassen“ bis zu acht Kacheln und ihre Reihenfolge fest, auch eigene Regeln wie „28–35 mm“, „ISO ab 6400“ oder „f/2.8 und offener“.
- **Objektive und Kameras:** Rangliste aller Objektive oder Kameras. Ein Klick öffnet die Detailanalyse mit Brennweiten, Blenden, ISO, Belichtungszeiten und Nutzung pro Jahr. Bei Objektiven kommen Zoom am Anschlag und Offenblende bei wenig Licht dazu.
- **Fototage:** Jeder Tag und jede Reise lässt sich einzeln nach Kameras, Objektiven, Brennweiten, Blenden, ISO und Uhrzeit auswerten.
- **Tabelle:** alle gezählten Fotos wie in Excel. Klick auf eine Überschrift sortiert, ⇧-Klick sortiert zusätzlich nach einer weiteren Spalte. Das ▾ öffnet Werteliste, Textfilter und Von-bis-Filter. Spaltenfilter gelten auch für die Auswertungen, CSV und PDF.
- **Objektiv prüfen:** Trage bis zu drei Objektive ein. Die App zeigt, wie oft du in diesem Bereich lagst, welche eigenen Objektive du dort genutzt hast, was die Lichtstärke gebracht hätte und was neu dazukäme. Sie gibt keine Kaufempfehlung. Fotos zeigen nur, was mit deiner bisherigen Ausrüstung möglich war. Festbrennweiten zählen mit ±6 %. Der Lichtgewinn rechnet mit gleicher Belichtungszeit und nur mit Fotos bei Offenblende über ISO 3200.
- **Vergleich:** zwei Objektive, Kameras oder Zeiträume nebeneinander, Unterschiede in Prozentpunkten.
- **Info-Buttons:** Das ⓘ neben Bereichen, Filtern und Feldern erklärt per Mauszeiger, Klick oder Tastatur, was du dort siehst und einstellen kannst.
- **Datenqualität:** fehlende Angaben, unbestätigte Objektive und mögliche Duplikate.
- **Beispielbilder:** blaue Zahlen öffnen die passenden Fotos. Vorschauen werden nur aus den Fotos gelesen und im eigenen Datenordner unter `vorschau` gespeichert.
- **Ansichten und PDF:** Filter, Sortierung und Spalten lassen sich unter einem Namen speichern. Unter „Exportieren“ erstellt „PDF-Bericht“ einen Bericht zum aktuellen Filter.
- **Automatisch aktualisieren:** liest beim Start und beim Verbinden eines Laufwerks neue Fotos ein. Abschaltbar unter „Ordner & Einlesen“.
- **Telekonverter:** Objektive mit TC oder Extender werden mit ihrem echten Brennweitenbereich und ihrer echten Offenblende gerechnet.

## Wenn etwas nicht klappt

- *macOS blockiert den Start:* Systemeinstellungen → Datenschutz & Sicherheit → **Dennoch öffnen**.
- *Meldung „In Programme verschieben“:* App aus dem DMG in den Ordner Programme ziehen und dort starten.
- *NAS-Ordner fehlt:* NAS im Finder verbinden. Die App liest ihn dann automatisch ein.
- *Nicht lesbare Dateien* stehen unter „Ordner & Einlesen“ und werden beim nächsten Lauf erneut versucht.

## Für Entwickler

Build, Selbsttest und Aufbau stehen in der `README.md`. Mit `SIGN_ID`, `BUNDLE_ID` und `NOTARY_PROFILE` signiert und beglaubigt `build/baue_app.sh` die App für die Weitergabe.
