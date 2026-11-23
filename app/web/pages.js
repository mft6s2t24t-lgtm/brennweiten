"use strict";
/* Übersicht, Objektive, Kameras, Fototage, Objektiv prüfen, Vergleich und Info-Hilfen */

/* ---------- Info-Texte ---------- */
const INFO = {
  tiles: "Deine wichtigsten Zahlen zum aktuellen Filter. Über „Kennzahlen anpassen“ legst du fest, welche erscheinen.",
  tiles_edit: "Wähle bis zu acht Kennzahlen und bringe sie mit den Pfeilen in deine Reihenfolge. Die Auswahl bleibt gespeichert.",
  tile_rule: "Zählt den Anteil deiner Fotos, die alle eingetragenen Bedingungen erfüllen, zum Beispiel 28–35 mm ab ISO 1600.",
  classes: "Wie sich deine Fotos auf Brennweitenbereiche verteilen, umgerechnet auf Kleinbild. Ein Klick auf einen Balken zeigt die Fotos.",
  hist: "Dieselben Daten millimetergenau. Spitzen zeigen Festbrennweiten und die Enden von Zooms. Die Achse ist logarithmisch, damit kurze Brennweiten lesbar bleiben.",
  top_lenses: "Deine Objektive nach Anzahl der Fotos. Mehr dazu auf der Seite Objektive.",
  years: "Wie sich deine Brennweiten von Jahr zu Jahr verschieben und welche Kameras im Einsatz waren.",
  pick_lens: "Wähle ein Objektiv für die Detailanalyse. „Alle Objektive“ zeigt die Rangliste und den Vergleich aller Objektive.",
  pick_camera: "Wähle eine Kamera für die Detailanalyse. „Alle Kameras“ zeigt die Rangliste.",
  lens_rank: "Alle Objektive im aktuellen Filter. Spalten lassen sich per Klick sortieren.",
  camera_rank: "Alle ausgewerteten Kameras im aktuellen Filter. Spalten lassen sich per Klick sortieren.",
  detail: "Zählt Fotos bei einer bestimmten Brennweite und Blende. Trage Werte ein oder klicke sie in den Listen an, beides lässt sich kombinieren.",
  d_fl: "Zum Beispiel 28. Leer bedeutet: alle Brennweiten.",
  d_fnum: "Zum Beispiel 2,8. Leer bedeutet: alle Blenden.",
  d_basis: "KB-Äquivalent rechnet Crop-Kameras auf Kleinbild um. „Am Objektiv“ zeigt den Wert, der auf dem Objektiv steht.",
  zoom: "Wie oft du die kürzeste oder längste Brennweite eines Zooms genutzt hast. Viele Fotos am Rand können heißen, dass dir dort Reichweite fehlt.",
  lowlight: "Fotos bei ganz offener Blende und zugleich über ISO 3200. Dort war das Objektiv am Limit, mehr Lichtstärke hätte geholfen.",
  uww: "Fotos unter 24 und unter 20 mm Kleinbild, also im Ultraweitwinkel.",
  around: "Fotos um 50 mm (45–55) und um 85 mm (80–90), egal mit welchem Objektiv sie entstanden sind.",
  keepers: "Anteil der Fotos mit mindestens 3 Sternen. Das ist nur aussagekräftig, wenn du deine Fotos regelmäßig bewertest.",
  p_classes: "Verteilung dieser Auswahl auf die Brennweitenbereiche in Kleinbild.",
  p_fnum: "Welche Blenden du hier am häufigsten verwendet hast.",
  p_iso: "Wie hoch die ISO-Werte lagen. Viele Fotos rechts bedeuten häufig wenig Licht.",
  p_time: "Welche Belichtungszeiten du verwendet hast.",
  p_years: "Wie viele Fotos pro Jahr entstanden sind.",
  p_hours: "Zu welcher Uhrzeit die Fotos entstanden sind, laut Kamerauhr.",
  p_other: "Mit welchen Kameras oder Objektiven diese Fotos entstanden sind.",
  day_list: "Jeder Tag mit Fotos, neueste zuerst. Ein Klick zeigt die komplette Auswertung des Tages.",
  trips: "Mindestens zwei Fototage direkt hintereinander. Ein Klick wertet den ganzen Zeitraum aus.",
  day_lenses: "Wie viele verschiedene Objektive du pro Tag verwendet hast und welche an den meisten Tagen dabei waren.",
  day_cameras: "An wie vielen Tagen jede Kamera im Einsatz war. „Allein“ bedeutet: an dem Tag nur mit dieser Kamera.",
  day_wide: "Bis zu dieser Brennweite zählt ein Foto für „Weitwinkel und Tele am selben Tag“ als Weitwinkel.",
  day_tele: "Ab dieser Brennweite zählt ein Foto für „Weitwinkel und Tele am selben Tag“ als Tele.",
  check: "Trage Brennweite und Lichtstärke eines Objektivs ein. Die App spielt es gegen deine bisherigen Fotos durch.",
  check_limit: "Deshalb ist „Am Anschlag“ ein wichtiger Hinweis: Dort wolltest du vielleicht weiter, als dein Objektiv konnte.",
  c_min: "Kürzeste Brennweite des Objektivs, wie sie auf dem Objektiv steht.",
  c_max: "Längste Brennweite. Bei einer Festbrennweite leer lassen.",
  c_ap: "Größte Blende, zum Beispiel 2,8. Bei Zooms mit variabler Blende den Wert am kurzen Ende.",
  c_crop: "Sensor, an dem du das Objektiv nutzen würdest. Die Brennweite wird damit auf Kleinbild umgerechnet.",
  q_range: "Anteil deiner Fotos, die in diesem Brennweitenbereich lagen. Festbrennweiten zählen mit ±6 %.",
  q_replace: "Mit diesen deiner Objektive sind die Fotos in diesem Bereich bisher entstanden.",
  q_light: "Fotos bei Offenblende über ISO 3200, die mit dieser Lichtstärke mehr Licht bekommen hätten. Gerechnet mit gleicher Belichtungszeit.",
  q_new: "Teile des Bereichs, die deine bisherigen Objektive nicht abdecken, und wie oft du bisher genau dort am Anschlag warst.",
  compare: "Stellt zwei Objektive, Kameras oder Zeiträume nebeneinander. Die Spalte „B gegenüber A“ zeigt den Unterschied in Prozentpunkten.",
  cams: "Alle Kameras aus den EXIF-Daten deiner Fotos. Smartphones und Scanner sind zunächst aus.",
  c_on: "Nur Kameras mit Haken fließen in die Auswertung ein.",
  c_name: "Anzeigename in der App. Deine Fotos bleiben unverändert.",
  crop: "Faktor für die Umrechnung auf Kleinbild: Vollformat 1,0, APS-C meist 1,5 oder 1,6, MFT 2,0. Steht „bitte prüfen“ dabei, trage den Wert deiner Kamera ein.",
  sugg: "Fotos ohne sauberen Objektivnamen, erkannt über Brennweite und Blende. Passe den Namen an und bestätige ihn.",
  lenses: "Hier vereinheitlichst du Objektivnamen. Gleicher Name bedeutet: wird zusammengezählt.",
  l_name: "Gib zwei Einträgen denselben Namen, um unterschiedliche EXIF-Schreibweisen zusammenzufassen.",
  l_range: "Kürzeste und längste Brennweite. Wird für „Zoom am Anschlag“ gebraucht.",
  l_ap: "Offenblende am kurzen und langen Ende. Wird für die Auswertung der Offenblende gebraucht.",
  quality: "Zeigt, wo Angaben in den Fotos fehlen oder nicht zusammenpassen. Ein Klick auf eine Zahl öffnet die betroffenen Fotos.",
  quality_other: "Prüft die Crop-Faktoren und zeigt, ob deine Fotoordner erreichbar sind.",
  folders: "Diese Ordner werden ausgewertet, auch externe Laufwerke und NAS. Fotos werden nur gelesen.",
  scan: "Beim ersten Mal werden alle Bilder gelesen, danach nur neue oder geänderte.",
  auto: "Liest neue Fotos beim Start und sobald ein Laufwerk verbunden wird.",
  f_cams: "Begrenzt die Auswertung auf bestimmte Kameras.",
  f_lenses: "Begrenzt die Auswertung auf bestimmte Objektive.",
  f_range: "Begrenzt die Auswertung auf einen Zeitraum.",
  f_good: "Zählt nur Fotos mit mindestens 3 Sternen.",
  f_views: "Speichert Filter, Sortierung und Spalten unter einem Namen, damit du sie später wieder aufrufen kannst.",
  f_export: "Kopiert eine Zusammenfassung oder sichert den aktuellen Filter als PDF oder CSV für Excel.",
  table: "Klick auf eine Überschrift sortiert, ⇧-Klick sortiert zusätzlich nach einer weiteren Spalte. Das ▾ öffnet Wertefilter wie in Excel.",
  t_cols: "Lege fest, welche Spalten die Tabelle und der CSV-Export enthalten.",
  col_file: "Dateiname. Ein Klick öffnet Vorschau und Details.", col_folder: "Ordner, in dem die Datei liegt.", col_path: "Vollständiger Speicherort.",
  col_camera: "Kamera laut EXIF.", col_serial: "Seriennummer der Kamera, falls gespeichert.", col_lens: "Vereinheitlichter Objektivname.",
  col_lens_raw: "Objektivname genau so, wie er in der Datei steht.", col_fl: "Brennweite am Objektiv.", col_kb: "Auf Kleinbild umgerechnete Brennweite.",
  col_kb_src: "Ob der KB-Wert aus der Datei stammt oder berechnet wurde.", col_dx: "Foto im DX-Ausschnitt einer Vollformatkamera.", col_crop: "Crop-Faktor der Kamera.",
  col_fnum: "Verwendete Blende.", col_wo: "Ob das Foto bei ganz offener Blende entstand.", col_exptime: "Belichtungszeit in Sekunden.", col_iso: "ISO-Empfindlichkeit.",
  col_dt: "Aufnahmedatum und Uhrzeit.", col_year: "Aufnahmejahr.", col_month: "Aufnahmemonat.", col_weekday: "Wochentag der Aufnahme.", col_hour: "Stunde der Aufnahme.",
  col_rating: "Sterne aus EXIF, XMP oder Sidecar.", col_ext: "Dateiformat.",
};
const TILE_INFO = {
  photos: "Anzahl der Fotos im Filter, Duplikate wie RAW+JPEG zählen einmal.", median: "Die Hälfte deiner Fotos liegt unter, die Hälfte über diesem Wert.",
  top_lens: "Das Objektiv mit den meisten Fotos.", top_class: "Der Brennweitenbereich mit den meisten Fotos.", days: "Anzahl der Tage mit mindestens einem Foto.",
  per_day: "Durchschnittliche Fotos pro Fototag.", wide_open: "Anteil der Fotos bei ganz offener Blende.", median_iso: "Typischer ISO-Wert deiner Fotos.", median_fnum: "Typische Blende deiner Fotos.",
  high_iso: "Anteil der Fotos über ISO 3200.", u24: "Anteil unter 24 mm Kleinbild.", u20: "Anteil unter 20 mm Kleinbild.", m35: "Anteil zwischen 32 und 38 mm.", m50: "Anteil zwischen 45 und 55 mm.",
  m85: "Anteil zwischen 80 und 90 mm.", o200: "Anteil über 200 mm.", rated: "Anteil der Fotos mit einer Bewertung.", good: "Anteil der Fotos mit mindestens 3 Sternen.",
  n_lenses: "Wie viele verschiedene Objektive im Filter vorkommen.", n_cameras: "Wie viele verschiedene Kameras im Filter vorkommen.",
};
function ib(key, text) {
  const t = text || INFO[key];
  return t ? `<button type="button" class="info" data-tip="${esc(esc(t))}" aria-label="${esc(t)}">i</button>` : "";
}
function hi(label, key) { return label + ib(key); }
function addInfos(root) {
  root.querySelectorAll("[data-i]").forEach((el) => {
    if (el.dataset.iDone) return;
    el.dataset.iDone = "1";
    const html = ib(el.dataset.i);
    if (el.tagName === "DETAILS") el.insertAdjacentHTML("afterend", html);
    else if (el.tagName === "LABEL") {
      const kid = el.querySelector("input,select,.unit"), first = el.firstChild;
      if (kid && kid.type !== "checkbox" && first && first.nodeType === 3 && first.textContent.trim()) {
        const head = document.createElement("span"); head.className = "lab";
        head.textContent = first.textContent.trim(); head.insertAdjacentHTML("beforeend", html); el.replaceChild(head, first);
      } else if (kid && kid.type !== "checkbox") kid.insertAdjacentHTML("beforebegin", html);
      else el.insertAdjacentHTML("beforeend", html);
    } else {
      const small = el.querySelector(":scope > small");
      if (small) small.insertAdjacentHTML("beforebegin", html); else el.insertAdjacentHTML("beforeend", html);
    }
  });
}
function showInfo(b) {
  const tip = $("#tip"); tip.innerHTML = b.getAttribute("data-tip"); tip.hidden = false;
  const r = b.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
  tip.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left)) + "px";
  tip.style.top = (r.top - h - 6 < 8 ? r.bottom + 6 : r.top - h - 6) + "px";
}
document.addEventListener("click", (e) => { const b = e.target.closest(".info"); if (!b) return; e.preventDefault(); e.stopPropagation(); b.focus(); showInfo(b); }, true);
document.addEventListener("focusin", (e) => { if (e.target.classList && e.target.classList.contains("info")) showInfo(e.target); });
document.addEventListener("focusout", (e) => { if (e.target.classList && e.target.classList.contains("info")) $("#tip").hidden = true; });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") $("#tip").hidden = true; });
let infoQueued = false;
new MutationObserver(() => { if (infoQueued) return; infoQueued = true; requestAnimationFrame(() => { infoQueued = false; addInfos(document.body); }); })
  .observe(document.body, { childList: true, subtree: true });
addInfos(document.body);

/* ---------- Kennzahlen ---------- */
let tileData = null;
const tileValue = (t) => {
  if (t.value == null) return "–";
  return ({ pct: () => p(t.value), mm: () => n(t.value) + " mm", iso: () => "ISO " + n(t.value), fnum: () => "f/" + fnumText(t.value), n: () => n(t.value) }[t.fmt] || (() => String(t.value)))();
};
function tileHtml(t) {
  const spec = t.spec ? ` data-photos="${jsonAttr(Object.assign({ title: t.label }, t.spec))}"` : "";
  const help = t.custom ? "Eigene Kennzahl: " + t.sub : TILE_INFO[t.id];
  return `<div class="tile${t.spec ? " click" : ""}"${spec}><div class="v${t.fmt === "text" ? " text" : ""}">${esc(tileValue(t))}</div><div class="l">${esc(t.label)}${ib("", help)}</div><div class="s">${esc(t.sub || "")}</div></div>`;
}
async function loadTiles() {
  tileData = await api("/api/tiles?" + qs());
  $("#tiles").innerHTML = tileData.values.map(tileHtml).join("");
  if ($("#tiles-dlg").open) renderTileDialog();
}
function renderTileDialog() {
  const c = tileData.chosen, names = Object.fromEntries(tileData.library.map((x) => [x.id, x.label]));
  $("#td-count").textContent = `${c.length} von ${tileData.max}`;
  $("#td-chosen").innerHTML = c.map((t, i) => `<div class="td-row"><span>${esc(t.label || names[t.id])}</span>
    <button data-up="${i}" ${i ? "" : "disabled"} aria-label="Nach oben">↑</button><button data-down="${i}" ${i < c.length - 1 ? "" : "disabled"} aria-label="Nach unten">↓</button><button data-rm="${i}" aria-label="Entfernen">✕</button></div>`).join("") || '<p class="muted">Keine Kennzahl gewählt.</p>';
  const used = new Set(c.map((t) => t.id));
  $("#td-lib").innerHTML = tileData.library.filter((x) => !used.has(x.id)).map((x) => `<div class="td-row"><span>${esc(x.label)}${ib("", TILE_INFO[x.id])}</span><button data-add="${x.id}" ${c.length >= tileData.max ? "disabled" : ""}>Hinzufügen</button></div>`).join("");
}
async function saveTiles(list) { await api("/api/tiles", { tiles: list }); await loadTiles(); renderTileDialog(); }
$("#tiles-edit").onclick = () => { renderTileDialog(); $("#tiles-dlg").showModal(); };
$("#td-close").onclick = () => $("#tiles-dlg").close();
$("#tiles-dlg").addEventListener("click", (e) => {
  if (e.target === $("#tiles-dlg")) return $("#tiles-dlg").close();
  const b = e.target.closest("button"); if (!b) return;
  const c = tileData.chosen.slice();
  if (b.dataset.up) { const i = +b.dataset.up; [c[i - 1], c[i]] = [c[i], c[i - 1]]; saveTiles(c); }
  else if (b.dataset.down) { const i = +b.dataset.down; [c[i + 1], c[i]] = [c[i], c[i + 1]]; saveTiles(c); }
  else if (b.dataset.rm) { c.splice(+b.dataset.rm, 1); saveTiles(c); }
  else if (b.dataset.add) { c.push({ id: b.dataset.add }); saveTiles(c); }
});
$("#td-default").onclick = () => saveTiles(tileData.default.map((id) => ({ id })));
$("#r-add").onclick = () => {
  const t = { id: "rule-" + Date.now(), label: $("#r-label").value.trim(), kb_min: $("#r-min").value, kb_max: $("#r-max").value, iso_min: $("#r-iso").value, f_max: $("#r-f").value };
  if (!(t.kb_min || t.kb_max || t.iso_min || t.f_max)) return toast("Bitte mindestens eine Bedingung eintragen");
  if (tileData.chosen.length >= tileData.max) return toast("Es sind höchstens " + tileData.max + " Kennzahlen möglich");
  if (!t.label) t.label = [t.kb_min || t.kb_max ? `${t.kb_min || "…"}–${t.kb_max || "…"} mm` : "", t.iso_min ? "ISO " + t.iso_min : "", t.f_max ? "f/" + t.f_max : ""].filter(Boolean).join(", ");
  saveTiles(tileData.chosen.concat([t]));
  ["#r-label", "#r-min", "#r-max", "#r-iso", "#r-f"].forEach((id) => ($(id).value = ""));
};
async function loadOverview() { await Promise.all([loadAnalysis(), loadTiles()]); }

/* ---------- Detailprofil ---------- */
function profileHtml(r, title, sub, otherLabel, otherKey, specBase) {
  const period = r.from ? (r.from === r.to ? dateDE(r.from) : dateDE(r.from) + " bis " + dateDE(r.to)) : "";
  const tile = (v, l, s, info) => `<div class="tile"><div class="v">${v}</div><div class="l">${l}${ib("", info)}</div><div class="s">${s || ""}</div></div>`;
  const others = r[otherKey] || [];
  return `<div class="detail-head"><h2>${esc(title)}</h2><span class="muted">${esc(sub || period)}</span></div>
  <div class="tiles">${tile(n(r.n), "Fotos", n(r.days) + " Fototage", "Fotos in dieser Auswahl.")}
    ${tile(r.median != null ? n(r.median) + " mm" : "–", "Median-Brennweite", r.min != null ? n(r.min) + "–" + n(r.max) + " mm KB" : "", "Die Hälfte der Fotos liegt unter, die Hälfte über diesem Wert.")}
    ${tile(r.median_fnum ? "f/" + fnumText(r.median_fnum) : "–", "Median-Blende", r.n_known ? p(r.wo_pct) + " bei Offenblende" : "", "Typische Blende und Anteil bei ganz offener Blende.")}
    ${tile(r.median_iso ? n(r.median_iso) : "–", "Median-ISO", p(r.high_iso_pct) + " über ISO 3200", "Typischer ISO-Wert und Anteil bei wenig Licht.")}
    ${tile(p(r.good_pct), "ab 3 Sternen", n(r.good) + " von " + n(r.n) + (r.rated < 30 ? " · wenig bewertet" : ""), "Anteil der Fotos mit mindestens 3 Sternen.")}</div>
  <div class="chart-grid">
    <article class="card"><h2>Brennweiten <small>KB</small>${ib("p_classes")}</h2><div class="chart" data-c="classes"></div></article>
    <article class="card"><h2>Blenden${ib("p_fnum")}</h2><div class="chart" data-c="fnums"></div></article>
    <article class="card"><h2>ISO${ib("p_iso")}</h2><div class="chart" data-c="iso"></div></article>
    <article class="card"><h2>Belichtungszeit${ib("p_time")}</h2><div class="chart" data-c="times"></div></article>
    <article class="card"><h2>${r.from && r.from === r.to ? "Uhrzeit" : "Fotos pro Jahr"}${ib(r.from === r.to ? "p_hours" : "p_years")}</h2><div class="chart" data-c="when"></div></article>
    <article class="card"><h2>${otherLabel}${ib("p_other")}</h2>${table([[otherLabel === "Kameras" ? "Kamera" : "Objektiv"], ["Fotos", "num"], ["Anteil", "num"], [""]],
      others.map((x) => `<tr><td>${esc(x.name)}</td><td class="num">${pl(n(x.n), Object.assign({ title: title + ", " + x.name }, specBase || {}, otherKey === "cameras" ? { camera: x.name } : { lens: x.name }))}</td><td class="num">${p(x.pct)}</td><td>${inbar(x.pct)}</td></tr>`))}</article>
  </div>`;
}
function drawProfile(box, r, title, specBase) {
  const c = (k) => box.querySelector(`[data-c="${k}"]`);
  const opt = { w: 560, h: 220, values: false };
  const bars = (rows, unit) => rows.map((x) => ({ label: x.label, v: x.n, tip: `<b>${esc(x.label)}${unit || ""}</b><br>${n(x.n)} Fotos · ${p(x.pct)}` }));
  barChart(c("classes"), r.classes.map((x) => ({ label: x.label, v: x.n, tip: `<b>${esc(x.label)} mm</b><br>${n(x.n)} Fotos · ${p(x.pct)}`,
    photos: x.n ? Object.assign({ title: title + ", " + x.label + " mm", kb_min: x.lo, kb_max: x.hi }, specBase || {}) : null })), Object.assign({ label: "Brennweiten" }, opt));
  barChart(c("fnums"), r.fnums.map((x) => ({ label: fnumText(x.v), v: x.n, tip: `<b>f/${fnumText(x.v)}</b><br>${n(x.n)} Fotos · ${p(x.pct)}`,
    photos: Object.assign({ title: title + ", f/" + fnumText(x.v), fnum: x.v }, specBase || {}) })), Object.assign({ label: "Blenden" }, opt));
  barChart(c("iso"), bars(r.iso), Object.assign({ label: "ISO" }, opt));
  barChart(c("times"), bars(r.times).map((x) => Object.assign(x, { label: x.label.replace("kürzer ", "<").replace(/–.*/, "") })), Object.assign({ label: "Belichtungszeit" }, opt));
  if (r.from && r.from === r.to) barChart(c("when"), r.hours.map((v, h) => ({ label: h % 3 ? "" : String(h), v, tip: `<b>${h}–${h + 1} Uhr</b><br>${n(v)} Fotos` })), Object.assign({ label: "Uhrzeit" }, opt));
  else barChart(c("when"), r.years.map((x) => ({ label: String(x.year), v: x.n, tip: `<b>${x.year}</b><br>${n(x.n)} Fotos`, photos: Object.assign({ title: title + ", " + x.year, year: x.year }, specBase || {}) })), Object.assign({ label: "Fotos pro Jahr" }, opt));
}

/* ---------- Objektive ---------- */
const rankHead = [["Name"], ["Fotos", "num"], ["Anteil", "num"], ["Fototage", "num"], ["Median", "num"], ["Offenblende", "num"], ["Median-ISO", "num"], ["ab 3 Sternen", "num"], ["Zeitraum", "num"], [""]];
const rankRow = (x, attr) => `<tr><td><button class="link" ${attr}="${esc(x.key)}">${esc(x.name)}</button></td><td class="num">${n(x.n)}</td><td class="num">${p(x.pct)}</td><td class="num">${n(x.days)}</td><td class="num">${x.median != null ? n(x.median) + " mm" : "–"}</td><td class="num">${p(x.wo_pct)}</td><td class="num">${n(x.median_iso)}</td><td class="num">${p(x.good_pct)}</td><td class="num">${x.from ? x.from.slice(0, 4) + (x.to.slice(0, 4) !== x.from.slice(0, 4) ? "–" + x.to.slice(0, 4) : "") : "–"}</td><td>${inbar(x.pct)}</td></tr>`;
async function loadLensPage() {
  const saved = PICK.lens; PICK.lens = "";
  const list = await api("/api/entities?kind=lens&" + qs());
  PICK.lens = list.rows.some((x) => x.key === saved) ? saved : "";
  const sel = $("#ol-select");
  sel.innerHTML = '<option value="">Alle Objektive</option>' + list.rows.map((x) => `<option value="${esc(x.key)}">${esc(x.name)} (${n(x.n)})</option>`).join("");
  sel.value = PICK.lens;
  const has = !!PICK.lens;
  $("#ol-empty").hidden = !!list.rows.length; $("#ol-body").hidden = !list.rows.length;
  $("#ol-back").hidden = !has; $("#ol-rank-card").hidden = has; $("#ol-detail").hidden = !has;
  $("#detail-card").hidden = !has; $("#sec-uww").hidden = has; $("#sec-around").hidden = has; $("#sec-keep").hidden = has;
  if (!list.rows.length) return;
  if (!has) {
    $("#ol-rank").innerHTML = table(rankHead, list.rows.map((x) => rankRow(x, "data-ol")));
    await Promise.all([loadAnalysis(), loadKeep()]);
    return;
  }
  const r = await api("/api/profile", { qs: qs() });
  const box = $("#ol-detail");
  box.innerHTML = profileHtml(r, PICK.lens, "", "Kameras", "cameras", { lens: PICK.lens });
  drawProfile(box, r, PICK.lens, { lens: PICK.lens });
  await loadAnalysis();
}
function pickLens(v) { PICK.lens = v; D.fl = ""; D.fnum = ""; window.scrollTo(0, 0); loadLensPage(); }
$("#ol-select").onchange = (e) => pickLens(e.target.value);
$("#ol-back").onclick = () => pickLens("");
$("#ol-rank").addEventListener("click", (e) => { const b = e.target.closest("[data-ol]"); if (b) pickLens(b.dataset.ol); });

/* ---------- Kameras ---------- */
async function loadCameraPage() {
  const saved = PICK.camera; PICK.camera = "";
  const list = await api("/api/entities?kind=camera&" + qs());
  PICK.camera = list.rows.some((x) => x.key === saved) ? saved : "";
  const sel = $("#cl-select");
  sel.innerHTML = '<option value="">Alle Kameras</option>' + list.rows.map((x) => `<option value="${esc(x.key)}">${esc(x.name)} (${n(x.n)})</option>`).join("");
  sel.value = PICK.camera;
  const has = !!PICK.camera;
  $("#cl-empty").hidden = !!list.rows.length; $("#cl-back").hidden = !has;
  $("#cl-rank-card").hidden = has || !list.rows.length; $("#cl-detail").hidden = !has;
  if (!has) { $("#cl-rank").innerHTML = table(rankHead, list.rows.map((x) => rankRow(x, "data-cl"))); return; }
  const r = await api("/api/profile", { qs: qs() });
  const name = list.rows.find((x) => x.key === PICK.camera).name;
  const box = $("#cl-detail");
  box.innerHTML = profileHtml(r, name, "", "Objektive", "lenses", {});
  drawProfile(box, r, name, {});
}
function pickCamera(v) { PICK.camera = v; window.scrollTo(0, 0); loadCameraPage(); }
$("#cl-select").onchange = (e) => pickCamera(e.target.value);
$("#cl-back").onclick = () => pickCamera("");
$("#cl-rank").addEventListener("click", (e) => { const b = e.target.closest("[data-cl]"); if (b) pickCamera(b.dataset.cl); });

/* ---------- Fototage ---------- */
const DAY = { rows: [], shown: 40, from: "", to: "" };
function renderDayRows() {
  $("#dy-list").innerHTML = table([["Datum"], ["Fotos", "num"], ["Kameras", "num"], ["Objektive", "num"], ["Bereich KB", "num"], ["Meistgenutzt"]],
    DAY.rows.slice(0, DAY.shown).map((d) => `<tr><td><button class="link" data-day="${d.date}">${dateDE(d.date)}</button></td><td class="num">${n(d.n)}</td><td class="num">${d.cameras}</td><td class="num">${d.lenses}</td><td class="num">${d.min != null ? n(d.min) + "–" + n(d.max) + " mm" : "–"}</td><td class="muted">${esc(d.top.join(", "))}</td></tr>`));
  $("#dy-more").hidden = DAY.shown >= DAY.rows.length;
  $("#dy-count").textContent = `${n(Math.min(DAY.shown, DAY.rows.length))} von ${n(DAY.rows.length)} Fototagen`;
}
async function openDays(from, to) {
  DAY.from = from; DAY.to = to;
  const r = await api("/api/profile", { qs: qs(), from, to });
  const box = $("#dy-detail"); box.hidden = false;
  const title = from === to ? dateDE(from) : dateDE(from) + " bis " + dateDE(to);
  const spec = { from, to };
  box.innerHTML = `<div class="actions" style="margin:0 0 10px"><button class="ghost" id="dy-close">Zurück zu allen Fototagen</button>${pl("Alle Fotos zeigen", Object.assign({ title }, spec))}</div>` +
    profileHtml(r, title, n(r.days) + (r.days === 1 ? " Tag" : " Tage"), "Objektive", "lenses", spec) +
    `<article class="card"><h2>Kameras an ${from === to ? "diesem Tag" : "diesen Tagen"}${ib("p_other")}</h2>${table([["Kamera"], ["Fotos", "num"], ["Anteil", "num"], [""]], r.cameras.map((x) => `<tr><td>${esc(x.name)}</td><td class="num">${pl(n(x.n), Object.assign({ title: title + ", " + x.name, camera: x.name }, spec))}</td><td class="num">${p(x.pct)}</td><td>${inbar(x.pct)}</td></tr>`))}</article>`;
  drawProfile(box, r, title, spec);
  $("#dy-close").onclick = () => { DAY.from = DAY.to = ""; box.hidden = true; box.innerHTML = ""; window.scrollTo(0, 0); };
  window.scrollTo(0, 0);
}
async function loadDays() {
  const u = new URLSearchParams(qs()); u.set("wide", $("#dy-wide").value || 28); u.set("tele", $("#dy-tele").value || 100);
  const r = await api("/api/days?" + u.toString());
  const one = r.dist[0] || { days: 0, pct: 0 };
  $("#d-tiles").innerHTML = [[n(r.days), "Fototage", n(r.per_day) + " Fotos pro Tag", "Tage mit mindestens einem Foto."], [p(one.pct), "mit nur einem Objektiv", n(one.days) + " Tage", "An diesen Tagen hast du das Objektiv nicht gewechselt."],
    [p(r.both_pct), "Weitwinkel und Tele am selben Tag", `bis ${r.wide} und ab ${r.tele} mm · ${n(r.both)} Tage`, "Die Grenzen stellst du weiter unten ein."], [n(r.n_trips), "Reisen und Serien", "ab 2 Tagen in Folge", "Mindestens zwei Fototage direkt hintereinander."]]
    .map((t) => `<div class="tile"><div class="v">${t[0]}</div><div class="l">${t[1]}${ib("", t[3])}</div><div class="s">${t[2]}</div></div>`).join("");
  DAY.rows = r.day_rows; renderDayRows();
  $("#dy-dist").innerHTML = table([["Objektive"], ["Tage", "num"], ["Anteil", "num"], [""]], r.dist.map((x) => `<tr><td>${x.label}</td><td class="num">${n(x.days)}</td><td class="num">${p(x.pct)}</td><td>${inbar(x.pct)}</td></tr>`));
  $("#dy-lens").innerHTML = table([["Objektiv"], ["Fototage", "num"], ["Anteil", "num"], ["allein", "num"], [""]], r.per_lens.map((x) => `<tr><td>${esc(x.lens)}</td><td class="num">${n(x.days)}</td><td class="num">${p(x.days_pct)}</td><td class="num">${n(x.alone)}</td><td>${inbar(x.days_pct)}</td></tr>`));
  $("#dy-cam").innerHTML = table([["Kamera"], ["Fototage", "num"], ["Anteil", "num"], ["allein", "num"], ["Fotos", "num"], [""]], r.per_camera.map((x) => `<tr><td>${esc(x.camera)}</td><td class="num">${n(x.days)}</td><td class="num">${p(x.days_pct)}</td><td class="num">${n(x.alone)}</td><td class="num">${n(x.n)}</td><td>${inbar(x.days_pct)}</td></tr>`));
  $("#dy-trips").innerHTML = table([["Zeitraum"], ["Tage", "num"], ["Fotos", "num"], ["Objektive", "num"], ["Bereich KB", "num"], ["Weit + Tele"], ["Meistgenutzt"]],
    r.trips.map((t) => `<tr><td><button class="link" data-trip="${t.from}|${t.to}">${dateDE(t.from)} – ${dateDE(t.to)}</button></td><td class="num">${t.days}</td><td class="num">${n(t.n)}</td><td class="num">${t.lenses}</td><td class="num">${t.min != null ? n(t.min) + "–" + n(t.max) + " mm" : "–"}</td><td>${t.both ? "ja" : "nein"}</td><td class="muted">${esc(t.top.join(", "))}</td></tr>`)) +
    (r.n_trips > r.trips.length ? `<p class="muted">Die neuesten ${r.trips.length} von ${n(r.n_trips)}.</p>` : "");
  if (DAY.from) await openDays(DAY.from, DAY.to);
}
["#dy-wide", "#dy-tele"].forEach((id) => ($(id).onchange = loadDays));
$("#dy-more").onclick = () => { DAY.shown += 60; renderDayRows(); };
$("#tab-fototage").addEventListener("click", (e) => {
  const d = e.target.closest("[data-day]"); if (d) return openDays(d.dataset.day, d.dataset.day);
  const t = e.target.closest("[data-trip]"); if (t) { const [a, b] = t.dataset.trip.split("|"); openDays(a, b); }
});

/* ---------- Objektiv prüfen ---------- */
const CANDS = [{ min: "70", max: "200", ap: "2.8", crop: "1" }, { min: "", max: "", ap: "", crop: "1" }, { min: "", max: "", ap: "", crop: "1" }];
try { const c = JSON.parse(localStorage.getItem("cands") || "null"); if (Array.isArray(c) && c.length === 3) CANDS.splice(0, 3, ...c); } catch (e) {}
let checkMeta = null;
function renderCands() {
  const presets = checkMeta.presets, crops = checkMeta.crops;
  $("#p-cands").innerHTML = CANDS.map((c, i) => `<div class="cand"><b>Objektiv ${i + 1}</b>
    <label>Schnellwahl <select data-c="${i}" data-k="preset" aria-label="Schnellwahl"><option value="">Eigene Werte</option>${presets.map((x) => `<option value="${x.id}" ${+c.min === x.min && +(c.max || c.min) === x.max && +c.ap === x.ap ? "selected" : ""}>${esc(x.name)}</option>`).join("")}</select></label>
    <div class="row"><label><span class="lab">von mm${ib("c_min")}</span><input type="number" data-c="${i}" data-k="min" value="${esc(c.min)}"></label><label><span class="lab">bis mm${ib("c_max")}</span><input type="number" data-c="${i}" data-k="max" value="${esc(c.max)}"></label></div>
    <div class="row"><label><span class="lab">Blende f/${ib("c_ap")}</span><input type="number" step="0.1" data-c="${i}" data-k="ap" value="${esc(c.ap)}"></label>
    <label><span class="lab">Sensor${ib("c_crop")}</span><select data-c="${i}" data-k="crop">${crops.map((x) => `<option value="${x}" ${+c.crop === x ? "selected" : ""}>${x === 1 ? "Vollformat" : "Crop " + nf.format(x)}</option>`).join("")}</select></label></div>
    ${c.min ? `<button class="ghost small" data-clear="${i}">Leeren</button>` : ""}</div>`).join("");
}
function answerHtml(x) {
  const reps = x.replaces.slice(0, 4).map((l) => `<div class="muted">${esc(l.name)}: ${n(l.n)} (${p(l.pct)})</div>`).join("") || '<span class="muted">keine Fotos in diesem Bereich</span>';
  const li = x.light;
  const light = !x.ap ? '<span class="muted">Trage eine Blende ein.</span>' : !li.n ? "Keine Fotos, die davon profitiert hätten." :
    `<b>${pl(n(li.n), { title: x.name + ": mehr Licht", light: { min: x.lo < x.hi ? (x.min_kb ?? x.lo) : x.lo, max: x.hi, ap: x.ap } })} Fotos</b> mit im Median rund ${nf.format(li.stops)} ${nf.format(li.stops) === "1" ? "Blendenstufe" : "Blendenstufen"} mehr Licht, ISO ${n(li.iso_old)} → ${n(li.iso_new)}.`;
  const segs = x.new_segments.length ? "Neu abgedeckt: " + x.new_segments.map((s) => `${s[0]}–${s[1]} mm`).join(", ") : "Deine Objektive decken diesen Bereich bereits ab.";
  const q = (t, key, body) => `<div class="q"><b class="t">${t}${ib(key)}</b>${body}</div>`;
  return `<div class="answer"><h3>${esc(x.name)}</h3><div class="muted">${n(x.lo)}–${n(x.hi)} mm KB</div>
    <div class="q"><b class="t">Wie oft lag ich in diesem Bereich?${ib("q_range")}</b><div class="big-n">${p(x.pct)}</div>${pl(n(x.n) + " von " + n(x.total) + " Fotos", { title: x.name, range: [x.lo, x.hi] })}${inbar(x.pct)}</div>
    ${q("Was würde es ersetzen?", "q_replace", reps)}
    ${q("Was bringt die Lichtstärke?", "q_light", light)}
    ${q("Was kommt wirklich neu dazu?", "q_new", `${esc(segs)}<div class="muted">Am Anschlag deiner Zooms: ${n(x.wider)} Fotos wollten vielleicht weiter, ${n(x.longer)} länger.</div>`)}</div>`;
}
async function runCheck(redraw) {
  const r = await api("/api/check", { qs: qs(), candidates: CANDS.filter((c) => c.min) });
  checkMeta = r;
  if (redraw) renderCands();
  $("#p-result").innerHTML = r.results.length ? `<div class="answers">${r.results.map(answerHtml).join("")}</div>` : '<div class="empty">Trage oben ein Objektiv ein.</div>';
}
const loadCheck = () => runCheck(true);
$("#p-cands").addEventListener("change", (e) => {
  const i = e.target.dataset.c; if (i == null) return;
  const c = CANDS[i], k = e.target.dataset.k;
  if (k === "preset") { const x = checkMeta.presets.find((y) => y.id === e.target.value); if (x) Object.assign(c, { min: String(x.min), max: x.max === x.min ? "" : String(x.max), ap: String(x.ap) }); }
  else c[k] = e.target.value;
  try { localStorage.setItem("cands", JSON.stringify(CANDS)); } catch (err) {}
  runCheck(true);
});
$("#p-cands").addEventListener("click", (e) => {
  const b = e.target.closest("[data-clear]"); if (!b) return;
  Object.assign(CANDS[b.dataset.clear], { min: "", max: "", ap: "" });
  try { localStorage.setItem("cands", JSON.stringify(CANDS)); } catch (err) {}
  runCheck(true);
});

/* ---------- Vergleich ---------- */
let cmpReady = false, cmpMode = "lens";
try { cmpMode = localStorage.getItem("cmpMode") || "lens"; } catch (e) {}
async function prepareCompare() {
  const saved = PICK.lens; PICK.lens = "";
  const [cams, lenses, years] = await Promise.all([api("/api/cameras"), api("/api/entities?kind=lens&" + qs()), api("/api/facet?col=year")]);
  PICK.lens = saved;
  const camOpts = '<option value="">alle Kameras</option>' + cams.cameras.filter((c) => c.enabled).map((c) => `<option value="${esc(c.key)}">${esc(c.name)}</option>`).join("");
  const lensOpts = lenses.rows.map((x) => `<option value="${esc(x.key)}">${esc(x.name)} (${n(x.n)})</option>`).join("");
  ["a", "b"].forEach((s, i) => {
    const cur = { c: $(`#c-${s}-cam`).value, l: $(`#c-${s}-lens`).value };
    $(`#c-${s}-cam`).innerHTML = camOpts; $(`#c-${s}-lens`).innerHTML = lensOpts;
    $(`#c-${s}-cam`).value = cur.c;
    $(`#c-${s}-lens`).value = lenses.rows.some((x) => x.key === cur.l) ? cur.l : (lenses.rows[i] || lenses.rows[0] || { key: "" }).key;
    ["cam", "lens", "from", "to"].forEach((k) => ($(`#c-${s}-${k}`).onchange = loadCompare));
  });
  const camList = cams.cameras.filter((c) => c.enabled);
  if (!$("#c-a-cam").value && camList[0]) $("#c-a-cam").value = camList[0].key;
  if (!$("#c-b-cam").value && camList[1]) $("#c-b-cam").value = camList[1].key;
  cmpYears = years.values.map((x) => x.v).filter((v) => v != null).sort();
  cmpReady = true;
}
let cmpYears = [];
function setCompareMode(mode) {
  cmpMode = mode;
  try { localStorage.setItem("cmpMode", mode); } catch (e) {}
  $$("#c-mode button").forEach((b) => b.classList.toggle("on", b.dataset.mode === mode));
  $(".cmp-form").dataset.mode = mode;
  if (mode === "time") {
    const b = cmpYears[cmpYears.length - 1], a = cmpYears[cmpYears.length - 3] || cmpYears[0];
    if (a && !$("#c-a-from").value && !$("#c-b-from").value) { $("#c-a-from").value = a + "-01-01"; $("#c-a-to").value = a + "-12-31"; $("#c-b-from").value = b + "-01-01"; $("#c-b-to").value = b + "-12-31"; }
  }
}
$("#c-mode").addEventListener("click", (e) => { const b = e.target.closest("[data-mode]"); if (b) { setCompareMode(b.dataset.mode); loadCompare(); } });
async function loadCompare() {
  if (!cmpReady) await prepareCompare();
  setCompareMode(cmpMode);
  const side = (s) => {
    const c = cmpMode === "lens" ? "" : $(`#c-${s}-cam`).value, l = cmpMode === "lens" ? $(`#c-${s}-lens`).value : "";
    return { cameras: c ? [c] : [], lenses: l ? [l] : [], from: $(`#c-${s}-from`).value, to: $(`#c-${s}-to`).value };
  };
  const r = await api("/api/compare", { qs: qs(), a: side("a"), b: side("b") });
  const label = (s) => cmpMode === "lens" ? ($(`#c-${s}-lens`).selectedOptions[0] || {}).textContent?.replace(/ \([\d.]+\)$/, "") || s.toUpperCase() :
    cmpMode === "camera" ? ($(`#c-${s}-cam`).selectedOptions[0] || {}).textContent || s.toUpperCase() : `${$(`#c-${s}-from`).value ? dateDE($(`#c-${s}-from`).value) : "Anfang"} – ${$(`#c-${s}-to`).value ? dateDE($(`#c-${s}-to`).value) : "heute"}`;
  const A = label("a"), B = label("b");
  const dcell = (d) => `<td class="num ${d > 0 ? "pos" : d < 0 ? "neg" : ""}">${pp(d)}</td>`;
  const two = (x, mx) => `<td><div class="inbar" style="margin-bottom:2px"><span style="width:${100 * x.a / mx}%"></span></div><div class="inbar b"><span style="width:${100 * x.b / mx}%"></span></div></td>`;
  const other = cmpMode === "lens" ? r.cameras : r.lens;
  const mxC = Math.max(1, ...r.classes.flatMap((c) => [c.a, c.b])), mxL = Math.max(1, ...other.flatMap((c) => [c.a, c.b]));
  const fact = (l, f) => `<tr><td>${l}</td><td class="num">${f(r.a)}</td><td class="num">${f(r.b)}</td></tr>`;
  $("#c-result").innerHTML = `<div class="legend"><span><i class="sw s-wide"></i>A: ${esc(A)}</span><span><i class="sw s-tele"></i>B: ${esc(B)}</span></div>
    <div class="cols"><div><h3>Eckdaten</h3>${table([["Kennzahl"], ["A", "num"], ["B", "num"]], [fact("Fotos", (x) => n(x.n)), fact("Fototage", (x) => n(x.days)), fact("Median-Brennweite", (x) => x.median != null ? n(x.median) + " mm" : "–"),
      fact("Median-Blende", (x) => x.median_fnum ? "f/" + fnumText(x.median_fnum) : "–"), fact("Median-ISO", (x) => n(x.median_iso)), fact("ab 3 Sternen", (x) => p(x.good))])}</div>
    <div><h3>Anteile</h3>${table([["Kennzahl"], ["A", "num"], ["B", "num"], ["B gegenüber A", "num"]], r.metrics.map((x) => `<tr><td>${x.label}</td><td class="num">${p(x.a)}</td><td class="num">${p(x.b)}</td>${dcell(x.diff)}</tr>`))}</div></div>
    <div class="cols"><div><h3>Brennweitenklassen</h3>${table([["mm"], ["A", "num"], ["B", "num"], ["Diff.", "num"], [""]], r.classes.map((x) => `<tr><td>${x.label}</td><td class="num">${p(x.a)}</td><td class="num">${p(x.b)}</td>${dcell(x.diff)}${two(x, mxC)}</tr>`))}</div>
    <div><h3>${cmpMode === "lens" ? "Kameras" : "Objektive"}</h3>${table([[cmpMode === "lens" ? "Kamera" : "Objektiv"], ["A", "num"], ["B", "num"], ["Diff.", "num"], [""]], other.map((x) => `<tr><td>${esc(x.lens)}</td><td class="num">${p(x.a)}</td><td class="num">${p(x.b)}</td>${dcell(x.diff)}${two(x, mxL)}</tr>`))}</div></div>`;
}

boot();
