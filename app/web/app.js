"use strict";
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const nf = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 1 });
const n = (v) => (v == null ? "–" : nf.format(v));
const p = (v) => (v == null ? "–" : nf.format(v) + " %");
const SEP = "\x1f";

async function api(path, body) {
  const opt = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const r = await fetch(path, opt);
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}
const NATIVE = !!(window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.native);
if (NATIVE) document.body.classList.add("native");
const nativeCall = (msg) => window.webkit.messageHandlers.native.postMessage(msg);
async function chooseFolders() {
  if (!NATIVE) return (await api("/api/folders/choose", {})).messages;
  const paths = await nativeCall({ cmd: "chooseFolders" });
  const msgs = [];
  for (const path of paths) msgs.push(...(await api("/api/folders/add", { path })).messages);
  return msgs;
}
const copyText = (text) => (NATIVE ? nativeCall({ cmd: "copy", text }) : navigator.clipboard.writeText(text));
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), 2600);
}

/* ---------------- Tooltip ---------------- */
document.addEventListener("mousemove", (e) => {
  const el = e.target.closest("[data-tip]");
  const tip = $("#tip");
  if (!el) { if (!(document.activeElement && document.activeElement.classList.contains("info"))) tip.hidden = true; return; }
  tip.innerHTML = el.getAttribute("data-tip");
  tip.hidden = false;
  const w = tip.offsetWidth, h = tip.offsetHeight;
  let x = e.clientX + 14, y = e.clientY - h - 10;
  if (x + w > innerWidth - 8) x = e.clientX - w - 14;
  if (y < 8) y = e.clientY + 18;
  tip.style.left = x + "px"; tip.style.top = y + "px";
});

/* ---------------- Tabs ---------------- */
function showTab(name) {
  name = ({ kaufhilfe: "pruefen", kameras: "stamm", objektive: "stamm" })[name] || name;
  $$(".tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  $$(".tab").forEach((t) => t.classList.toggle("active", t.id === "tab-" + name));
  try { localStorage.setItem("tab", name); } catch (e) {}
  const shared = ["auswertung", "objektiv", "kamera", "tabelle", "pruefen", "fototage", "vergleich"].includes(name);
  $("#filterbar").hidden = !shared;
  [["#f-lenses", name === "objektiv" || name === "vergleich"], ["#f-cams", name === "kamera"]].forEach(([id, off]) => {
    const el = $(id); el.hidden = off;
    if (el.nextElementSibling && el.nextElementSibling.classList.contains("info")) el.nextElementSibling.hidden = off;
  });
  window.scrollTo(0, 0);
  renderChips();
  document.body.classList.toggle("wide", name === "tabelle");
  TABS[name]();
}
$$(".tabs button").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));

/* ---------------- Filter ---------------- */
const PICK = { lens: "", camera: "" };
const F = { cameras: [], lenses: [], from: "", to: "", good: false, cf: {} };
try { Object.assign(F, JSON.parse(localStorage.getItem("filter") || "{}")); } catch (e) {}
function qs() {
  const u = new URLSearchParams();
  const tab = (document.querySelector(".tabs .active") || { dataset: {} }).dataset.tab;
  const cams = tab === "kamera" ? (PICK.camera ? [PICK.camera] : []) : F.cameras;
  const lenses = tab === "objektiv" ? (PICK.lens ? [PICK.lens] : []) : tab === "vergleich" ? [] : F.lenses;
  if (cams.length) u.set("cameras", cams.join(SEP));
  if (lenses.length) u.set("lenses", lenses.join(SEP));
  if (F.from) u.set("from", F.from);
  if (F.to) u.set("to", F.to);
  if (F.good) u.set("good", "1");
  if (F.cf && Object.keys(F.cf).length) u.set("cf", JSON.stringify(F.cf));
  return u.toString();
}
function saveFilter() { try { localStorage.setItem("filter", JSON.stringify(F)); } catch (e) {} }
function multi(id, label, items, selected, onChange) {
  const box = $(id);
  const sum = box.querySelector("summary");
  sum.textContent = label + ": " + (selected.length ? selected.length + " gewählt" : "alle");
  box.querySelector(".list").innerHTML =
    `<label><input type="checkbox" data-all ${selected.length ? "" : "checked"}> <b>alle</b></label>` +
    items.map((it) => `<label><input type="checkbox" value="${esc(it.value)}" ${selected.includes(it.value) ? "checked" : ""}> ${esc(it.label)}<span class="n">${it.n != null ? n(it.n) : ""}</span></label>`).join("");
  box.querySelector(".list").onchange = (e) => {
    if (e.target.hasAttribute("data-all")) onChange([]);
    else onChange([...box.querySelectorAll("input[value]:checked")].map((x) => x.value));
  };
}
$("#f-from").value = F.from; $("#f-to").value = F.to; $("#f-good").checked = F.good;
$("#f-from").onchange = (e) => { F.from = e.target.value; saveFilter(); refresh(); };
$("#f-to").onchange = (e) => { F.to = e.target.value; saveFilter(); refresh(); };
$("#f-good").onchange = (e) => { F.good = e.target.checked; saveFilter(); refresh(); };
$("#f-reset").onclick = () => { Object.assign(F, { cameras: [], lenses: [], from: "", to: "", good: false, cf: {} });
  $("#f-from").value = ""; $("#f-to").value = ""; $("#f-good").checked = false; saveFilter(); refresh(); };
document.addEventListener("click", (e) => { $$("details.multi[open]").forEach((d) => { if (!d.contains(e.target)) d.open = false; }); });

$("#csv").onclick = () => { location.href = "/api/export.csv?" + exportQuery(); };
$("#pdf").onclick = () => { location.href = "/api/report.pdf?" + qs(); };
$("#copy").onclick = async () => {
  try {
    const r = await api("/api/summary?" + qs());
    await copyText(r.text);
    toast("Zusammenfassung kopiert (" + r.text.split("\n").length + " Zeilen)");
  } catch (e) { toast("Kopieren fehlgeschlagen: " + e.message); }
};

/* ---------------- Diagramme (SVG) ---------------- */
function barChart(el, data, opt = {}) {
  const W = opt.w || 900, H = opt.h || 240, L = 40, R = 8, T = 22, B = 34;
  const max = Math.max(1, ...data.map((d) => d.v));
  const step = niceStep(max);
  const top = Math.ceil(max / step) * step;
  const bw = (W - L - R) / data.length;
  const y = (v) => T + (H - T - B) * (1 - v / top);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(opt.label || "")}">`;
  for (let g = 0; g <= top; g += step) s += `<line class="gridl" x1="${L}" x2="${W - R}" y1="${y(g)}" y2="${y(g)}"/><text x="${L - 6}" y="${y(g) + 4}" text-anchor="end">${opt.pct ? g + " %" : n(g)}</text>`;
  data.forEach((d, i) => {
    const x = L + i * bw, w = Math.max(2, bw - Math.max(4, bw * 0.28)), h = y(0) - y(d.v);
    const bx = x + (bw - w) / 2;
    if (d.v > 0) s += `<path class="bar" d="M${bx},${y(0)} v${-(h - Math.min(4, h))} q0,-${Math.min(4, h)} ${Math.min(4, w / 2)},-${Math.min(4, h)} h${w - 2 * Math.min(4, w / 2)} q${Math.min(4, w / 2)},0 ${Math.min(4, w / 2)},${Math.min(4, h)} v${h - Math.min(4, h)} z"/>`;
    if (opt.values && d.v > 0) s += `<text class="val" x="${x + bw / 2}" y="${y(d.v) - 6}" text-anchor="middle">${esc(d.valLabel)}</text>`;
    s += `<text x="${x + bw / 2}" y="${H - B + 16}" text-anchor="middle">${esc(d.label)}</text>`;
    s += `<rect class="hit" x="${x}" y="${T}" width="${bw}" height="${H - T - B}" data-tip="${esc(d.tip)}"${d.photos ? ` data-photos="${esc(JSON.stringify(d.photos))}"` : ""}/>`;
  });
  s += `<line class="axis" x1="${L}" x2="${W - R}" y1="${y(0)}" y2="${y(0)}"/></svg>`;
  el.innerHTML = s;
}
function niceStep(max) {
  const raw = max / 4, mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const f = raw / mag;
  return Math.max(1, (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * mag);
}
function histChart(el, hist) {
  if (!hist.length) { el.innerHTML = ""; return; }
  const W = 900, H = 200, L = 40, R = 10, T = 12, B = 30;
  const mmMin = Math.min(10, ...hist.map((h) => h.mm)), mmMax = Math.max(600, ...hist.map((h) => h.mm));
  const lx = (mm) => L + (W - L - R) * (Math.log(mm) - Math.log(mmMin)) / (Math.log(mmMax) - Math.log(mmMin));
  const max = Math.max(...hist.map((h) => h.n));
  const step = niceStep(max), top = Math.ceil(max / step) * step;
  const y = (v) => T + (H - T - B) * (1 - v / top);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Histogramm">`;
  for (let g = 0; g <= top; g += step) s += `<line class="gridl" x1="${L}" x2="${W - R}" y1="${y(g)}" y2="${y(g)}"/><text x="${L - 6}" y="${y(g) + 4}" text-anchor="end">${n(g)}</text>`;
  [12, 16, 20, 24, 28, 35, 50, 70, 85, 105, 135, 200, 300, 400, 600].filter((t) => t >= mmMin && t <= mmMax)
    .forEach((t) => { s += `<line class="gridl" x1="${lx(t)}" x2="${lx(t)}" y1="${y(0)}" y2="${y(0) + 4}"/><text x="${lx(t)}" y="${H - B + 16}" text-anchor="middle">${t}</text>`; });
  hist.forEach((h) => {
    const x = lx(h.mm), w = Math.max(2, (lx(h.mm + 0.5) - lx(h.mm - 0.5)) - 1);
    s += `<rect class="bar" x="${x - w / 2}" y="${y(h.n)}" width="${w}" height="${y(0) - y(h.n)}" rx="1"/>`;
    s += `<rect class="hit" x="${x - Math.max(4, w) / 2}" y="${T}" width="${Math.max(4, w)}" height="${H - T - B}" data-tip="${h.mm} mm: ${n(h.n)} Bilder"/>`;
  });
  s += `<line class="axis" x1="${L}" x2="${W - R}" y1="${y(0)}" y2="${y(0)}"/><text x="${W - R}" y="${H - 2}" text-anchor="end">mm (KB)</text></svg>`;
  el.innerHTML = s;
}
function inbar(pctv) { return `<div class="inbar"><span style="width:${Math.min(100, pctv)}%"></span></div>`; }
function table(head, rows) {
  return `<div class="overflow"><table><thead><tr>${head.map((h) => `<th class="${h[1] || ""}">${h[0]}</th>`).join("")}</tr></thead><tbody>${rows.join("") || `<tr><td colspan="${head.length}" class="muted">keine Daten</td></tr>`}</tbody></table></div>`;
}

/* ---------------- Auswertung ---------------- */
let lastAnalysis = null;
async function loadAnalysis() {
  const [cams, r] = await Promise.all([api("/api/cameras"), api("/api/analysis?" + qs())]);
  lastAnalysis = r;
  const enabled = cams.cameras.filter((c) => c.enabled);
  F.cameras = F.cameras.filter((k) => enabled.some((c) => c.key === k));
  multi("#f-cams", "Kameras", enabled.map((c) => ({ value: c.key, label: c.name, n: c.n_images })), F.cameras, (v) => { F.cameras = v; saveFilter(); refresh(); });
  const lensList = (F.lenses.length || F.cameras.length || F.from || F.to || F.good || Object.keys(F.cf || {}).length) ? null : r.lens_counts;
  const allLenses = lensList || (lastLensList || r.lens_counts);
  if (lensList) lastLensList = lensList;
  multi("#f-lenses", "Objektive", allLenses.map((l) => ({ value: l.lens, label: l.lens, n: l.n })), F.lenses, (v) => { F.lenses = v; saveFilter(); refresh(); });

  const hint = $("#hint");
  hint.hidden = !r.rating_hint; hint.textContent = r.rating_hint || "";
  const empty = $("#empty");
  if (!r.n_total) {
    $("#results").hidden = true; empty.hidden = false;
    empty.innerHTML = cams.cameras.length ? 'Keine Bilder für diesen Filter. <button class="link" onclick="$(\'#f-reset\').click()">Filter zurücksetzen</button>' :
      'Noch keine Fotos gefunden. Prüfe unter <a href="#" onclick="showTab(\'ordner\');return false">Ordner &amp; Einlesen</a> deine Fotoordner.';
    return;
  }
  $("#results").hidden = false; empty.hidden = true;

  barChart($("#chart-classes"), r.classes.map((c) => ({ label: c.label, v: c.pct, valLabel: p(c.pct),
    photos: c.n ? { title: c.label + " mm", kb_min: c.lo, kb_max: c.hi } : null,
    tip: `<b>${esc(c.label)} mm</b><br>${n(c.n)} Bilder · ${p(c.pct)}<br>Klick zeigt die Fotos` })), { pct: true, values: true, label: "Brennweitenklassen" });
  histChart($("#chart-hist"), r.hist);

  $("#uww-lens").innerHTML = table([["Objektiv"], ["< 24 mm", "num"], ["< 20 mm", "num"], ["Anteil am Objektiv", "num"], [""]],
    r.uww_lens.map((x) => `<tr><td>${esc(x.lens)}</td><td class="num">${pl(n(x.u24), { title: x.lens + ", unter 24 mm", lens: x.lens, kb_under: 24 })}</td><td class="num">${pl(n(x.u20), { title: x.lens + ", unter 20 mm", lens: x.lens, kb_under: 20 })}</td><td class="num">${p(x.u24_pct)}</td><td>${inbar(x.u24_pct)}</td></tr>`));
  $("#uww-year").innerHTML = table([["Jahr"], ["Bilder", "num"], ["< 24 mm", "num"], ["< 20 mm", "num"], [""]],
    r.uww_year.map((x) => `<tr><td>${x.year}</td><td class="num">${n(x.n)}</td><td class="num">${pl(n(x.u24), { title: x.year + ", unter 24 mm", year: x.year, kb_under: 24 })} · ${p(x.u24_pct)}</td><td class="num">${pl(n(x.u20), { title: x.year + ", unter 20 mm", year: x.year, kb_under: 20 })} · ${p(x.u20_pct)}</td><td>${inbar(x.u24_pct)}</td></tr>`));

  $("#zooms").innerHTML = table([["Objektiv"], ["Bilder", "num"], ["kurzes Ende", "num"], ["langes Ende", "num"], ["Verteilung"]],
    r.zooms.map((z) => `<tr><td>${esc(z.lens)}${z.crops.some((c) => c !== 1) ? ' <span class="badge">an Crop-Kamera</span>' : ""}</td><td class="num">${n(z.n)}</td>
      <td class="num">${n(z.min)}–${n(z.wide_to)} mm: <b>${p(z.wide_pct)}</b></td><td class="num">${n(z.tele_from)}–${n(z.max)} mm: <b>${p(z.tele_pct)}</b></td>
      <td><div class="stack" data-tip="${esc(z.lens)}<br>kurz ${p(z.wide_pct)} · dazwischen ${p(z.mid_pct)} · lang ${p(z.tele_pct)}"><span class="s-wide" style="width:${z.wide_pct}%"></span><span class="s-mid" style="width:${z.mid_pct}%"></span><span class="s-tele" style="width:${z.tele_pct}%"></span></div></td></tr>`));

  $("#lowlight").innerHTML = table([["Objektiv"], ["Offenblende", "num"], ["Bilder", "num"], ["bei Offenblende", "num"], ["ISO > 3200", "num"], ["Offenblende <b>und</b> ISO > 3200", "num"], [""]],
    r.lowlight.map((x) => `<tr${x.n_known ? "" : ' class="off"'}><td>${esc(x.lens)}</td><td class="num">${x.ap ? "f/" + n(x.ap) + (x.ap_tele && x.ap_tele !== x.ap ? "–" + n(x.ap_tele) : "") : "?"}</td><td class="num">${n(x.n)}</td>
      <td class="num">${x.n_known ? p(x.wo_pct) : "keine Blendendaten"}</td><td class="num">${n(x.iso)} · ${p(x.iso_pct)}</td>
      <td class="num"><b>${pl(n(x.both), { title: x.lens + ", Offenblende und ISO über 3200", lens: x.lens, iso_over: 3200, wide_open: true })} · ${p(x.both_pct)}</b></td><td>${inbar(x.both_pct)}</td></tr>`));

  $("#around-lens").innerHTML = table([["Objektiv"], [r.win50.join("–") + " mm", "num"], [r.win85.join("–") + " mm", "num"]],
    r.around_lens.map((x) => `<tr><td>${esc(x.lens)}</td><td class="num">${n(x.n50)}</td><td class="num">${n(x.n85)}</td></tr>`));
  $("#around-year").innerHTML = table([["Jahr"], ["Bilder", "num"], ["um 50 mm", "num"], ["um 85 mm", "num"]],
    r.around_year.map((x) => `<tr><td>${x.year}</td><td class="num">${n(x.n)}</td><td class="num">${n(x.n50)} · ${p(x.p50)}</td><td class="num">${n(x.n85)} · ${p(x.p85)}</td></tr>`));

  const oc = ["var(--o1)", "var(--o2)", "var(--o3)", "var(--o4)"];
  $("#year-legend").innerHTML = r.group_labels.map((g, i) => `<span><i class="sw" style="background:${oc[i]}"></i>${esc(g)} mm</span>`).join("");
  $("#chart-years").innerHTML = table([["Jahr"], ["Anteile der Brennweitenbereiche"]],
    r.years.map((y) => `<tr><td style="width:60px">${y.year}</td><td><div class="stack" style="height:18px">${y.groups.map((g, i) => g.pct ? `<span style="width:${g.pct}%;background:${oc[i]}" data-tip="<b>${y.year}</b> · ${esc(g.label)} mm<br>${n(g.n)} Bilder · ${p(g.pct)}"></span>` : "").join("")}</div></td></tr>`));
  $("#years-table").innerHTML = table([["Jahr"], ["Bilder", "num"], ["Median", "num"]].concat(r.group_labels.map((g) => [esc(g), "num"])).concat([["Kameras"]]),
    r.years.map((y) => `<tr><td>${y.year}</td><td class="num">${n(y.n)}</td><td class="num">${n(y.median)} mm</td>${y.groups.map((g) => `<td class="num">${p(g.pct)}</td>`).join("")}<td class="muted">${esc(y.cameras.join(", "))}</td></tr>`));

  $("#lens-counts").innerHTML = table([["Objektiv"], ["Bilder", "num"], ["Anteil", "num"], [""]],
    r.lens_counts.map((x) => `<tr><td>${esc(x.lens)}</td><td class="num">${pl(n(x.n), { title: x.lens, lens: x.lens })}</td><td class="num">${p(x.pct)}</td><td>${inbar(x.pct)}</td></tr>`));
  await loadDetail(r.lens_counts);
}
let lastLensList = null;

/* ---------------- Objektiv im Detail ---------------- */
const D = { lens: "", fl: "", fnum: "", basis: "kb" };
try { Object.assign(D, JSON.parse(localStorage.getItem("detail") || "{}"), { lens: "" }); } catch (e) {}
let detailToken = 0;
const fnumText = (v) => v.toLocaleString("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const parseNum = (s) => { const v = parseFloat(String(s).replace(",", ".")); return Number.isFinite(v) && v > 0 ? v : null; };

function detailRows(items, kind, selected, label) {
  const max = Math.max(1, ...items.map((x) => x.n));
  return table([[kind === "fl" ? "Brennweite" : "Blende"], ["Fotos", "num"], ["Anteil", "num"], [""]],
    items.map((x) => `<tr class="${x.v === selected ? "sel" : ""}"><td><button class="rowbtn" data-kind="${kind}" data-v="${x.v}" aria-pressed="${x.v === selected}">${label(x.v)}</button></td>
      <td class="num">${n(x.n)}</td><td class="num">${p(x.pct)}</td><td>${inbar(100 * x.n / max)}</td></tr>`));
}
async function loadDetail(lenses) {
  const sel = $("#d-lens");
  if (lenses) {
    sel.innerHTML = '<option value="">Alle Objektive</option>' + lenses.map((l) => `<option value="${esc(l.lens)}">${esc(l.lens)} (${n(l.n)})</option>`).join("");
  }
  sel.value = D.lens; $("#d-basis").value = D.basis;
  if (document.activeElement !== $("#d-fl")) $("#d-fl").value = D.fl;
  if (document.activeElement !== $("#d-fnum")) $("#d-fnum").value = D.fnum;
  try { localStorage.setItem("detail", JSON.stringify(D)); } catch (e) {}
  const fl = parseNum(D.fl), fnum = parseNum(D.fnum);
  const u = new URLSearchParams(qs());
  if (D.lens) u.set("lens", D.lens);
  if (fl != null) u.set("fl", Math.round(fl));
  if (fnum != null) u.set("fnum", fnum);
  u.set("basis", D.basis);
  const token = ++detailToken;
  const r = await api("/api/detail?" + u.toString());
  if (token !== detailToken) return;
  const selFl = fl != null ? Math.round(fl) : null, selF = fnum != null ? Math.round(fnum * 10) / 10 : null;
  const what = [selFl != null ? selFl + " mm" + (D.basis === "kb" ? " KB" : " am Objektiv") : "", selF != null ? "f/" + fnumText(selF) : ""].filter(Boolean).join(" und ");
  $("#d-result").innerHTML = `<b>${n(r.n)} ${r.n === 1 ? "Foto" : "Fotos"}</b> ${what ? "bei " + esc(what) : "insgesamt"} · ${esc(PICK.lens || "alle Objektive")}` +
    (what ? ` <span class="muted">(${p(r.pct)} von ${n(r.total)})</span>` : "") +
    (r.n ? " " + pl("Fotos zeigen", Object.assign({ title: (PICK.lens || "Alle Objektive") + (what ? ", " + what : "") },
      selFl != null ? (D.basis === "kb" ? { kb_min: selFl, kb_max: selFl } : { fl: selFl }) : {}, selF != null ? { fnum: selF } : {})) : "");
  $("#d-fls").innerHTML = detailRows(r.by_fl, "fl", selFl, (v) => v + " mm") + (r.no_fl ? `<p class="muted">${n(r.no_fl)} Fotos ohne Brennweite</p>` : "");
  $("#d-fnums").innerHTML = detailRows(r.by_fnum, "fnum", selF, (v) => "f/" + fnumText(v)) + (r.no_fnum ? `<p class="muted">${n(r.no_fnum)} Fotos ohne Blendenwert</p>` : "");
  $("#d-fl-list").innerHTML = r.by_fl.map((x) => `<option value="${x.v}">`).join("");
  $("#d-fnum-list").innerHTML = r.by_fnum.map((x) => `<option value="${fnumText(x.v)}">`).join("");
}
$("#d-lens").onchange = (e) => { D.lens = e.target.value; loadDetail(); };
$("#d-basis").onchange = (e) => { D.basis = e.target.value; D.fl = ""; loadDetail(); };
$("#d-fl").oninput = (e) => { D.fl = e.target.value.trim(); loadDetail(); };
$("#d-fnum").oninput = (e) => { D.fnum = e.target.value.trim(); loadDetail(); };
$("#d-clear").onclick = () => { D.fl = ""; D.fnum = ""; $("#d-fl").value = ""; $("#d-fnum").value = ""; loadDetail(); };
$("#detail-card").addEventListener("click", (e) => {
  const b = e.target.closest(".rowbtn"); if (!b) return;
  const key = b.dataset.kind, v = Number(b.dataset.v);
  const cur = parseNum(D[key]);
  const same = cur != null && (key === "fl" ? Math.round(cur) === v : Math.round(cur * 10) / 10 === v);
  D[key] = same ? "" : (key === "fl" ? String(v) : fnumText(v));
  $("#d-" + key).value = D[key];
  loadDetail();
});

/* ---------------- Kameras ---------------- */
let camsData = [];
const cropBadge = (c) => ({ exif: '<span class="badge">Crop aus EXIF</span>', modell: '<span class="badge">Crop vom Modell</span>', manuell: '<span class="badge">Crop von dir</span>', annahme: '<span class="badge warn">Crop bitte prüfen</span>' }[c.crop_src] || "");
async function loadCameras() {
  const r = await api("/api/cameras");
  camsData = r.cameras;
  const rows = camsData.map((c, i) => `<tr class="${c.enabled ? "" : "off"}">
    <td><input type="checkbox" data-i="${i}" data-k="enabled" ${c.enabled ? "checked" : ""}></td>
    <td><input type="text" data-i="${i}" data-k="name" value="${esc(c.name)}"></td>
    <td class="raws">${esc(c.make || "")}<br>${esc(c.model || "")}</td>
    <td><input type="number" step="0.1" min="0.5" max="10" data-i="${i}" data-k="crop" value="${c.crop}"></td>
    <td><span class="badge">${esc(c.status || "")}</span> ${cropBadge(c)}</td>
    <td class="num">${n(c.n_images)}${c.dups ? `<br><span class="muted">+${n(c.dups)} Duplikate</span>` : ""}</td>
    <td class="num">${c.first ? c.first.slice(0, 10) : "–"}<br>${c.last ? c.last.slice(0, 10) : ""}</td>
    <td class="raws">${esc((c.serials || "").split(",").join(", "))}</td></tr>`);
  $("#cams").innerHTML = table([[hi("aus&shy;gewertet", "c_on")], [hi("Name", "c_name")], ["EXIF Hersteller / Modell"], [hi("Crop", "crop")], ["Status"], ["Bilder", "num"], ["Zeitraum", "num"], ["Seriennummer"]], rows) +
    (r.no_camera ? `<p class="muted">${n(r.no_camera)} Dateien ohne Kameraangabe werden nicht ausgewertet.</p>` : "");
}
$("#cams").addEventListener("change", (e) => {
  const i = e.target.dataset.i, k = e.target.dataset.k;
  if (i == null) return;
  camsData[i][k] = k === "enabled" ? e.target.checked : k === "crop" ? parseFloat(e.target.value.replace(",", ".")) : e.target.value;
});
$("#cams-save").onclick = async () => {
  await api("/api/cameras", { cameras: camsData.map((c) => ({ key: c.key, name: c.name, crop: c.crop || 1, enabled: !!c.enabled })) });
  toast("Kameras gespeichert"); lastLensList = null; cmpReady = false; loadCameras();
};

/* ---------------- Objektive ---------------- */
let lensData = [];
async function loadLenses() {
  lensData = await api("/api/lenses");
  const sugg = lensData.map((l, i) => [l, i]).filter(([l]) => !l.confirmed);
  $("#sugg-card").hidden = !sugg.length;
  $("#sugg").innerHTML = table([["Vorschlag (änderbar)"], ["erkannt über"], ["Bilder", "num"], ["Kameras"], [""]],
    sugg.map(([l, i]) => `<tr><td><input type="text" data-i="${i}" data-k="name" value="${esc(l.name)}"></td>
      <td class="raws">${n(l.min_fl)} mm${l.ap_wide ? ", Offenblende f/" + n(l.ap_wide) : ""}${l.raws ? "<br>EXIF: " + esc(l.raws) : "<br>kein Objektivname in EXIF"}</td>
      <td class="num">${n(l.n)}</td><td class="raws">${esc(l.cams || "")}</td>
      <td><button data-confirm="${i}">Bestätigen</button></td></tr>`));
  const rows = lensData.map((l, i) => `<tr>
    <td><input type="text" data-i="${i}" data-k="name" value="${esc(l.name)}">${l.confirmed ? "" : ' <span class="badge">unbestätigt</span>'}</td>
    <td class="raws">${esc((l.raws || "–").split(",").join(" · "))}</td>
    <td class="num"><input type="number" step="1" data-i="${i}" data-k="min_fl" value="${l.min_fl ?? ""}"> – <input type="number" step="1" data-i="${i}" data-k="max_fl" value="${l.max_fl ?? ""}"></td>
    <td class="num">f/<input type="number" step="0.1" data-i="${i}" data-k="ap_wide" value="${l.ap_wide ?? ""}"> – <input type="number" step="0.1" data-i="${i}" data-k="ap_tele" value="${l.ap_tele ?? ""}"></td>
    <td class="num">${n(l.n)}</td><td class="raws">${esc(l.cams || "")}</td></tr>`);
  $("#lenses").innerHTML = table([[hi("Name", "l_name")], ["EXIF-Schreibweisen"], [hi("Bereich mm", "l_range"), "num"], [hi("Offenblende kurz – lang", "l_ap"), "num"], ["Bilder", "num"], ["Kameras"]], rows);
}
function lensChange(e) {
  const i = e.target.dataset.i, k = e.target.dataset.k;
  if (i == null) return;
  lensData[i][k] = e.target.value;
  if (k !== "name") lensData[i].user_set = 1;
}
$("#lenses").addEventListener("change", lensChange);
$("#sugg").addEventListener("change", lensChange);
$("#sugg").addEventListener("click", async (e) => {
  const i = e.target.dataset.confirm;
  if (i == null) return;
  lensData[i].confirmed = 1;
  await saveLenses([lensData[i]]);
  toast("Objektiv bestätigt");
});
async function saveLenses(list) {
  await api("/api/lenses", { lenses: list.map((l) => ({ key: l.key, name: l.name, min_fl: l.min_fl, max_fl: l.max_fl, ap_wide: l.ap_wide, ap_tele: l.ap_tele, confirmed: !!l.confirmed, user_set: !!l.user_set })) });
  lastLensList = null; loadLenses();
}
$("#lenses-save").onclick = async () => { await saveLenses(lensData); toast("Objektive gespeichert"); };

/* ---------------- Ordner & Einlesen ---------------- */
async function loadFolders() {
  const fs = await api("/api/folders");
  $("#folders").innerHTML = table([["Ordner"], ["Status"], ["Dateien", "num"], ["zuletzt eingelesen"], [""]],
    fs.map((f) => `<tr><td>${esc(f.path)}</td>
      <td>${f.online ? `<span class="status-ok">verbunden</span>` : `<span class="status-off">nicht erreichbar</span>`}<br><span class="muted">${esc(f.message || f.status || "")}</span></td>
      <td class="num">${n(f.files)}</td><td>${esc(f.last_scan || "noch nie")}</td>
      <td><button class="ghost" data-rm="${f.id}" data-path="${esc(f.path)}">Entfernen</button></td></tr>`));
  const failed = await api("/api/failed");
  $("#failed-box").hidden = !failed.length;
  $("#failed").innerHTML = table([["Datei"], ["Problem"]], failed.map((f) => `<tr><td>${esc(f.path)}</td><td>${esc(f.message)}</td></tr>`));
}
function folderMsg(msgs) {
  const m = $("#folder-msg"); m.hidden = !msgs.length; m.textContent = msgs.join(" · ");
}
$("#folder-choose").onclick = async () => { folderMsg(await chooseFolders()); loadFolders(); };
$("#folder-add").onclick = async () => {
  const v = $("#folder-path").value.trim(); if (!v) return;
  const r = await api("/api/folders/add", { path: v }); folderMsg(r.messages);
  if (!r.messages.length) $("#folder-path").value = "";
  loadFolders();
};
$("#folders").addEventListener("click", async (e) => {
  const id = e.target.dataset.rm; if (!id) return;
  if (!confirm("Ordner aus der Liste entfernen?\n" + e.target.dataset.path + "\n\nDie Fotos selbst bleiben unberührt, nur die gespeicherten Daten dieses Ordners werden aus der Auswertung entfernt.")) return;
  try { await api("/api/folders/remove", { id: +id }); } catch (err) { toast(err.message); }
  loadFolders();
});
$("#scan").onclick = async () => { await api("/api/scan", {}); wasRunning = true; pollStatus(true); };
$("#scan-cancel").onclick = () => api("/api/scan/cancel", {});

let wasRunning = false, welcomeScan = false;
async function pollStatus(force) {
  let s;
  try { s = await api("/api/status"); } catch (e) { return; }
  const pill = $("#scanpill");
  const pctv = s.todo ? Math.round(100 * s.done / s.todo) : 0;
  if (s.running) {
    pill.hidden = false;
    pill.textContent = s.phase === "EXIF lesen" ? `Einlesen: ${n(s.done)} / ${n(s.todo)}` : `Einlesen: ${s.phase} (${n(s.found)} Dateien)`;
  } else pill.hidden = true;
  $("#scan").disabled = s.running; $("#scan-cancel").hidden = !s.running;
  $("#progress").hidden = !s.running && !s.finished;
  $("#progress-fill").style.width = (s.running ? (s.phase === "EXIF lesen" ? pctv : 3) : 100) + "%";
  $("#progress-text").textContent = s.running
    ? `${s.phase} – ${n(s.found)} Dateien gefunden, ${n(s.done)} von ${n(s.todo)} gelesen${s.errors ? ", " + n(s.errors) + " Fehler" : ""}` + (s.folder ? ` · ${s.folder}` : "")
    : s.finished ? `${s.phase === "abgebrochen" ? "Abgebrochen" : "Fertig"}: ${n(s.done)} Dateien gelesen, ${n(s.removed)} entfernt, ${n(s.errors)} Fehler.` : "";
  $("#log").textContent = s.messages.join("\n");
  if (document.body.classList.contains("first") && welcomeScan) {
    $("#w-progress").hidden = false;
    $("#w-fill").style.width = (s.phase === "EXIF lesen" ? pctv : 3) + "%";
    $("#w-text").textContent = s.running ? (s.phase === "EXIF lesen" ? `${n(s.done)} von ${n(s.todo)} Fotos gelesen` : `Suche Fotos … ${n(s.found)} gefunden`) : "Fertig";
    if (!s.running && s.finished) { welcomeScan = false; wasRunning = false; leaveWelcome(); return; }
  }
  if (wasRunning && !s.running) {
    lastLensList = null;
    const active = $(".tabs .active").dataset.tab;
    showTab(active);
    toast("Einlesen abgeschlossen");
  }
  wasRunning = s.running;
}
setInterval(pollStatus, 1500);

$("#quit").onclick = async () => {
  if (!confirm("Brennweiten-Tool beenden?")) return;
  try { await api("/api/quit", {}); } catch (e) {}
  document.body.innerHTML = '<div class="empty">Das Tool wurde beendet. Du kannst dieses Fenster schließen.<br>Neu starten: Doppelklick auf „Brennweiten“.</div>';
};

