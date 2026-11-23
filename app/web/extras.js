"use strict";
/* Tabelle (Excel-Filter), Datenqualität, Galerie, Ansichten */
const TABS = {
  auswertung: () => loadOverview(), objektiv: () => loadLensPage(), kamera: () => loadCameraPage(), tabelle: loadTable, pruefen: () => loadCheck(),
  fototage: () => loadDays(), vergleich: () => loadCompare(), qualitaet: loadQuality, stamm: () => Promise.all([loadCameras(), loadLenses()]), ordner: loadFolders,
};
const activeTab = () => $(".tabs .active").dataset.tab;
function refresh() { renderChips(); TABS[activeTab()](); }
const jsonAttr = (o) => esc(JSON.stringify(o));
function pl(text, spec) { return `<button class="link" data-photos="${jsonAttr(spec)}">${text}</button>`; }
const pp = (v) => (v > 0 ? "+" : "") + nf.format(v) + " Pkt.";
const dateDE = (d) => (d ? d.slice(8, 10) + "." + d.slice(5, 7) + "." + d.slice(0, 4) : "–");

/* ---------- Alle Tabellen sortierbar ---------- */
function cellValue(td) {
  const inp = td.querySelector("input[type=text],input[type=number]");
  const t = (inp ? inp.value : td.textContent).trim();
  const m = t.match(/^[^\d-]{0,3}(-?\d[\d.]*(?:,\d+)?)/);
  return m ? { num: parseFloat(m[1].replace(/\./g, "").replace(",", ".")), t } : { num: null, t };
}
function markTables() { $$("main table:not(.grid)").forEach((t) => t.classList.add("sortable")); }
new MutationObserver(markTables).observe(document.querySelector("main"), { childList: true, subtree: true });
document.addEventListener("click", (e) => {
  const th = e.target.closest("table.sortable th");
  if (!th || !th.textContent.trim()) return;
  const tr = th.parentElement, table = th.closest("table"), idx = [...tr.children].indexOf(th);
  const body = table.tBodies[0];
  if (!body || body.rows.length < 2) return;
  const dir = th.dataset.dir === "asc" ? "desc" : "asc";
  [...tr.children].forEach((x) => delete x.dataset.dir);
  th.dataset.dir = dir;
  const f = dir === "asc" ? 1 : -1;
  const rows = [...body.rows].map((r) => ({ r, v: r.cells[idx] ? cellValue(r.cells[idx]) : { num: null, t: "" } }));
  rows.sort((a, b) => {
    if (a.v.num != null && b.v.num != null) return f * (a.v.num - b.v.num);
    if (a.v.num != null) return -1;
    if (b.v.num != null) return 1;
    if (!a.v.t) return 1;
    if (!b.v.t) return -1;
    return f * a.v.t.localeCompare(b.v.t, "de", { numeric: true });
  });
  rows.forEach((x) => body.appendChild(x.r));
});

/* ---------- Spaltenfilter-Chips ---------- */
let COLS = [];
const colLabel = (k) => (COLS.find((c) => c.key === k) || { label: k }).label;
function cfText(k, s) {
  const c = COLS.find((x) => x.key === k) || {};
  const parts = [];
  if (s.values) parts.push(s.values.length === 1 ? cellText(c, s.values[0]) || "(leer)" : s.values.length + " Werte");
  if (s.text) parts.push(({ contains: "enthält", not: "enthält nicht", starts: "beginnt mit", ends: "endet mit", equals: "ist" })[s.op || "contains"] + " „" + s.text + "“");
  if (s.min !== undefined && s.min !== "") parts.push("ab " + (c.type === "date" ? dateDE(s.min) : s.min));
  if (s.max !== undefined && s.max !== "") parts.push("bis " + (c.type === "date" ? dateDE(s.max) : s.max));
  return parts.join(", ");
}
function renderChips() {
  const box = $("#chips");
  const keys = Object.keys(F.cf || {});
  const shared = !$("#filterbar").hidden;
  box.hidden = !keys.length || !shared;
  $("#f-reset").hidden = !(F.cameras.length || F.lenses.length || F.from || F.to || F.good || keys.length);
  box.innerHTML = keys.map((k) => `<button class="chip" data-cf="${esc(k)}" title="Filter entfernen"><b>${esc(colLabel(k))}</b> ${esc(cfText(k, F.cf[k]))} ✕</button>`).join("") +
    (keys.length > 1 ? `<button class="chip" data-cf="*">Alle Spaltenfilter löschen</button>` : "");
}
$("#chips").addEventListener("click", (e) => {
  const b = e.target.closest("[data-cf]"); if (!b) return;
  if (b.dataset.cf === "*") F.cf = {}; else delete F.cf[b.dataset.cf];
  saveFilter(); resetTablePos(); refresh();
});

/* ---------- Tabelle ---------- */
const T = { sort: [["dt", "desc"]], cols: ["file", "camera", "lens", "fl", "kb", "fnum", "wo", "exptime", "iso", "dt", "rating", "ext"], rows: [], total: 0, loading: false, token: 0 };
try { Object.assign(T, JSON.parse(localStorage.getItem("table") || "{}"), { rows: [], total: 0, loading: false, token: 0 }); } catch (e) {}
function saveTable() { try { localStorage.setItem("table", JSON.stringify({ sort: T.sort, cols: T.cols })); } catch (e) {} }
function resetTablePos() { T.rows = []; T.total = 0; $("#t-wrap").scrollTop = 0; }
function exportQuery() {
  const u = new URLSearchParams(qs());
  if (activeTab() === "tabelle") { u.set("sort", JSON.stringify(T.sort)); u.set("cols", T.cols.join(",")); }
  return u.toString();
}
function shutter(v) {
  if (v == null) return "";
  if (v >= 0.3) return nf.format(v) + " s";
  return "1/" + Math.round(1 / v) + " s";
}
function cellText(c, v) {
  if (v == null || v === "") return "";
  if (c.type === "bool") return v ? "ja" : "nein";
  if (c.key === "exptime") return shutter(v);
  if (c.key === "fnum") return "f/" + fnumText(v);
  if (c.key === "year" || c.key === "hour") return String(v);
  if (c.key === "dt") return v.length > 10 ? dateDE(v) + " " + v.slice(11, 19) : dateDE(v);
  if (c.type === "num") return nf.format(v);
  return String(v);
}
function renderHead() {
  const cols = COLS.filter((c) => T.cols.includes(c.key));
  $("#t-grid thead").innerHTML = "<tr>" + cols.map((c) => {
    const si = T.sort.findIndex((s) => s[0] === c.key);
    const mark = si < 0 ? "" : (T.sort[si][1] === "asc" ? " ▲" : " ▼") + (T.sort.length > 1 ? (si + 1) : "");
    return `<th class="${F.cf[c.key] ? "on" : ""}" aria-sort="${si < 0 ? "none" : T.sort[si][1] === "asc" ? "ascending" : "descending"}"><div class="h"><button class="lab" data-sort="${c.key}">${esc(c.label)}${mark}</button><button class="fb" data-menu="${c.key}" aria-label="Filter ${esc(c.label)}">▾</button></div></th>`;
  }).join("") + "</tr>";
  $("#t-cols .list").innerHTML = COLS.map((c) => `<label><input type="checkbox" value="${c.key}" ${T.cols.includes(c.key) ? "checked" : ""}> ${esc(c.label)}</label>`).join("");
}
function rowHtml(r, cols) {
  return `<tr data-id="${r.id}">` + cols.map((c) => {
    const t = cellText(c, r[c.key]);
    const num = c.type === "num" ? " class=num" : "";
    if (c.key === "file") return `<td title="${esc(r.path)}"><button class="link" data-row="${r.id}">${esc(t)}</button></td>`;
    return `<td${num} title="${esc(t)}">${esc(t)}</td>`;
  }).join("") + "</tr>";
}
async function loadTable(more) {
  if (!COLS.length) COLS = await api("/api/columns");
  renderChips();
  if (!more) { T.rows = []; renderHead(); }
  const token = ++T.token;
  T.loading = true;
  const u = new URLSearchParams(qs());
  u.set("sort", JSON.stringify(T.sort)); u.set("offset", T.rows.length); u.set("limit", 150);
  const r = await api("/api/table?" + u.toString());
  if (token !== T.token) return;
  T.loading = false;
  T.total = r.stats.n;
  const cols = COLS.filter((c) => T.cols.includes(c.key));
  const html = r.rows.map((x) => rowHtml(x, cols)).join("");
  const body = $("#t-grid tbody");
  if (more) body.insertAdjacentHTML("beforeend", html); else body.innerHTML = html;
  T.rows = T.rows.concat(r.rows);
  const s = r.stats;
  $("#t-stats").innerHTML = `<b>${n(s.n)} Fotos</b> · ${n(s.lenses)} Objektive` + (s.median_kb != null ? ` · Median ${n(s.median_kb)} mm KB` : "") +
    (s.median_iso != null ? ` · Median ISO ${n(s.median_iso)}` : "") + (s.from ? ` · ${dateDE(s.from)} bis ${dateDE(s.to)}` : "");
  $("#t-more").textContent = !s.n ? "Keine Fotos für diesen Filter." : T.rows.length < s.n ? `${n(T.rows.length)} von ${n(s.n)} geladen, weiter scrollen …` : `Alle ${n(s.n)} Fotos angezeigt`;
}
$("#t-wrap").addEventListener("scroll", (e) => {
  const w = e.target;
  if (!T.loading && T.rows.length < T.total && w.scrollTop + w.clientHeight > w.scrollHeight - 500) loadTable(true);
});
$("#t-grid").addEventListener("click", (e) => {
  const rowBtn = e.target.closest("[data-row]");
  if (rowBtn) { const x = T.rows.find((r) => r.id === +rowBtn.dataset.row); if (x) openPhoto(x); return; }
  const m = e.target.closest("[data-menu]");
  if (m) { e.stopPropagation(); openMenu(m.dataset.menu, m); return; }
  const b = e.target.closest("[data-sort]"); if (!b) return;
  const k = b.dataset.sort, i = T.sort.findIndex((s) => s[0] === k);
  if (e.shiftKey) {
    if (i < 0) T.sort.push([k, "asc"]);
    else if (T.sort[i][1] === "asc") T.sort[i][1] = "desc";
    else T.sort.splice(i, 1);
  } else {
    T.sort = [[k, i >= 0 && T.sort[i][1] === "asc" ? "desc" : "asc"]];
  }
  saveTable(); $("#t-wrap").scrollTop = 0; loadTable();
});
$("#t-cols").addEventListener("change", (e) => {
  const v = e.target.value;
  T.cols = e.target.checked ? [...T.cols, v] : T.cols.filter((x) => x !== v);
  if (!T.cols.length) T.cols = ["file"];
  saveTable(); loadTable();
});
$("#t-reset").onclick = () => { T.sort = [["dt", "desc"]]; F.cf = {}; saveTable(); saveFilter(); $("#t-wrap").scrollTop = 0; refresh(); };

/* ---------- Spaltenmenü wie in Excel ---------- */
const menu = $("#colmenu");
async function openMenu(key, anchor) {
  const c = COLS.find((x) => x.key === key);
  const cur = F.cf[key] || {};
  const rect = anchor.getBoundingClientRect();
  menu.hidden = false;
  menu.style.left = Math.max(8, Math.min(innerWidth - 322, rect.right - 300)) + "px";
  menu.style.top = Math.min(innerHeight - 200, rect.bottom + 4) + "px";
  const sortAsc = c.type === "text" ? "A → Z" : c.type === "date" ? "Alt → neu" : "Klein → groß";
  const sortDesc = c.type === "text" ? "Z → A" : c.type === "date" ? "Neu → alt" : "Groß → klein";
  const range = c.type === "num" || c.type === "date";
  const it = c.type === "date" ? "date" : "number";
  menu.innerHTML = `<b>${esc(c.label)}${ib("col_" + c.key)}</b>
    <div class="row"><button class="ghost" data-s="asc">${sortAsc}</button><button class="ghost" data-s="desc">${sortDesc}</button></div>
    ${range ? `<div class="row"><input type="${it}" step="any" id="m-min" placeholder="von" aria-label="von" value="${esc(cur.min ?? "")}"><input type="${it}" step="any" id="m-max" placeholder="bis" aria-label="bis" value="${esc(cur.max ?? "")}"></div>` : ""}
    ${c.type === "text" ? `<div class="row"><select id="m-op" aria-label="Textfilter">${[["contains", "enthält"], ["not", "enthält nicht"], ["starts", "beginnt mit"], ["ends", "endet mit"], ["equals", "ist gleich"]].map(([v, l]) => `<option value="${v}" ${cur.op === v ? "selected" : ""}>${l}</option>`).join("")}</select><input type="text" id="m-text" aria-label="Text" value="${esc(cur.text || "")}"></div>` : ""}
    <input type="text" id="m-search" placeholder="Werte suchen …" aria-label="Werte suchen">
    <div class="row"><button class="ghost" id="m-all">Alle</button><button class="ghost" id="m-none">Keine</button></div>
    <div class="vals" id="m-vals"><span class="muted">lädt …</span></div>
    <div class="row"><button class="ghost" id="m-clear">Filter löschen</button><button id="m-ok">OK</button></div>`;
  let facet = null, checked = null;
  async function loadVals(search) {
    const u = new URLSearchParams(qs()); u.set("col", key); if (search) u.set("search", search);
    facet = await api("/api/facet?" + u.toString());
    if (checked === null) {
      checked = new Set(cur.values ? cur.values.map(String) : (facet.truncated ? [] : facet.values.map((x) => String(x.v))));
    }
    $("#m-vals").innerHTML = (facet.truncated ? `<div class="muted">Die ${n(facet.values.length)} häufigsten von ${n(facet.distinct)} Werten. Suche grenzt ein.</div>` : "") +
      facet.values.map((x) => `<label><input type="checkbox" data-v="${esc(String(x.v))}" ${checked.has(String(x.v)) ? "checked" : ""}><span>${x.v == null ? "(leer)" : esc(cellText(c, x.v))}</span><span class="c">${n(x.n)}</span></label>`).join("");
  }
  await loadVals("");
  $("#m-vals").onchange = (e) => { const v = e.target.dataset.v; if (e.target.checked) checked.add(v); else checked.delete(v); };
  let st;
  $("#m-search").oninput = (e) => { clearTimeout(st); st = setTimeout(() => loadVals(e.target.value.trim()), 150); };
  const setAll = (on) => { facet.values.forEach((x) => { if (on) checked.add(String(x.v)); else checked.delete(String(x.v)); }); $$("#m-vals input").forEach((i) => (i.checked = on)); };
  $("#m-all").onclick = () => setAll(true);
  $("#m-none").onclick = () => setAll(false);
  menu.querySelectorAll("[data-s]").forEach((b) => (b.onclick = () => { T.sort = [[key, b.dataset.s]]; saveTable(); closeMenu(); $("#t-wrap").scrollTop = 0; loadTable(); }));
  $("#m-clear").onclick = () => { delete F.cf[key]; saveFilter(); closeMenu(); resetTablePos(); refresh(); };
  $("#m-ok").onclick = async () => {
    const spec = {};
    if (range) { const a = $("#m-min").value, b = $("#m-max").value; if (a !== "") spec.min = a; if (b !== "") spec.max = b; }
    if (c.type === "text") { const t = $("#m-text").value.trim(); if (t) { spec.text = t; spec.op = $("#m-op").value; } }
    const u = new URLSearchParams(qs()); u.set("col", key);
    const all = await api("/api/facet?" + u.toString());
    const allChecked = !all.truncated && all.values.every((x) => checked.has(String(x.v)));
    if (!allChecked && (checked.size || !all.truncated)) {
      const known = new Map(all.values.map((x) => [String(x.v), x.v]));
      (cur.values || []).forEach((v) => { if (!known.has(String(v))) known.set(String(v), v); });
      spec.values = [...checked].filter((v) => known.has(v)).map((v) => known.get(v));
    }
    if (Object.keys(spec).length) F.cf[key] = spec; else delete F.cf[key];
    saveFilter(); closeMenu(); resetTablePos(); refresh();
  };
}
function closeMenu() { menu.hidden = true; menu.innerHTML = ""; }
document.addEventListener("mousedown", (e) => { if (!menu.hidden && !menu.contains(e.target) && !e.target.closest("[data-menu]")) closeMenu(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !menu.hidden) closeMenu(); });

/* ---------- Galerie ---------- */
const G = { spec: null, items: [], total: 0 };
document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-photos]"); if (!el) return;
  e.preventDefault();
  openGallery(JSON.parse(el.getAttribute("data-photos")));
});
async function openGallery(spec) {
  G.spec = spec; G.items = [];
  $("#gal-title").textContent = spec.title || "Fotos";
  $("#gal-grid").innerHTML = "";
  if (!$("#gal").open) $("#gal").showModal();
  await moreGallery();
}
async function moreGallery() {
  const r = await api("/api/photos", { qs: qs(), spec: G.spec, offset: G.items.length });
  G.total = r.total; const start = G.items.length; G.items = G.items.concat(r.items);
  $("#gal-grid").insertAdjacentHTML("beforeend", r.items.map((x, i) => `<button data-g="${start + i}" title="${esc(x.file)}"><span class="im"><img loading="lazy" src="/thumb/${x.id}" alt="${esc(x.file)}" onerror="this.parentElement.textContent='Keine Vorschau (Laufwerk verbunden?)'"></span><small>${x.kb ? n(x.kb) + " mm" : ""}${x.fnum ? " · f/" + fnumText(x.fnum) : ""}${x.iso ? " · ISO " + n(x.iso) : ""}</small><small>${esc(x.lens)}</small></button>`).join(""));
  $("#gal-more").hidden = G.items.length >= G.total;
  $("#gal-count").textContent = `${n(G.items.length)} von ${n(G.total)} Fotos, neueste zuerst`;
}
$("#gal-more").onclick = moreGallery;
$("#gal-close").onclick = () => $("#gal").close();
$("#gal-grid").addEventListener("click", (e) => { const b = e.target.closest("[data-g]"); if (b) openPhoto(G.items[+b.dataset.g]); });
function openPhoto(x) {
  const img = $("#ph-img"); img.hidden = false; img.onerror = () => { img.hidden = true; }; img.src = "/thumb/" + x.id;
  const rows = [["Datei", x.file], ["Kamera", x.camera], ["Objektiv", x.lens], ["Brennweite", x.fl ? n(x.fl) + " mm" : "–"], ["KB", x.kb ? n(x.kb) + " mm" : "–"],
    ["Blende", x.fnum ? "f/" + fnumText(x.fnum) : "–"], ["Zeit", shutter(x.exptime) || "–"], ["ISO", x.iso ? n(x.iso) : "–"], ["Aufnahme", x.dt ? cellText({ key: "dt" }, x.dt) : "–"], ["Bewertung", x.rating != null ? x.rating + " Sterne" : "–"]];
  $("#ph-meta").innerHTML = `<table>${rows.map(([a, b]) => `<tr><td>${a}</td><td>${esc(b)}</td></tr>`).join("")}</table>
    <div class="actions"><button id="ph-finder">Im Finder zeigen</button><button class="ghost" id="ph-close">Schließen</button></div>`;
  $("#ph-finder").onclick = async () => { try { await api("/api/reveal", { id: x.id }); } catch (e) { toast(e.message); } };
  $("#ph-close").onclick = () => $("#photo").close();
  $("#photo").showModal();
}
["#gal", "#photo"].forEach((id) => $(id).addEventListener("click", (e) => { if (e.target === $(id)) $(id).close(); }));

async function loadKeep() {
  const r = await api("/api/keepers?" + qs());
  const h = $("#k-hint"); h.hidden = !r.hint; h.textContent = r.hint || "";
  const t = (rows, label) => table([[label], ["Fotos", "num"], ["bewertet", "num"], ["≥ 3 Sterne", "num"], ["von allen", "num"], ["von bewerteten", "num"]],
    rows.map((x) => `<tr class="${x.small ? "off" : ""}"><td>${esc(x.name)}${x.small ? ' <span class="badge">wenig Daten</span>' : ""}</td><td class="num">${n(x.n)}</td><td class="num">${n(x.rated)}</td><td class="num">${n(x.good)}</td><td class="num">${p(x.good_pct)}</td><td class="num">${x.rated ? p(x.of_rated) : "–"}</td></tr>`));
  $("#k-keep").innerHTML = `<p class="muted">${n(r.good)} von ${n(r.n)} Fotos haben mindestens 3 Sterne. „Wenig Daten“: weniger als ${r.small} bewertete Fotos.</p>
    <h3>Nach Objektiv</h3>${t(r.lens, "Objektiv")}<div class="cols"><div><h3>Nach Brennweite (KB)</h3>${t(r.classes, "mm")}</div><div><h3>Nach Kamera</h3>${t(r.camera, "Kamera")}</div></div>`;
}

/* ---------- Datenqualität ---------- */
async function loadQuality() {
  const r = await api("/api/quality");
  $("#q-issues").innerHTML = `<p class="muted">Geprüft: ${n(r.total)} gezählte Fotos der ausgewählten Kameras. ${n(r.dups)} Duplikate wurden herausgerechnet, ${n(r.disabled)} Fotos stammen von ausgeschalteten Kameras, ${n(r.no_camera)} Dateien haben keine Kameraangabe und werden nicht gezählt, ${n(r.failed)} Dateien waren nicht lesbar.</p>` +
    table([["Prüfung"], ["Fotos", "num"], ["Anteil", "num"], ["vor allem"]], r.issues.map((x) => `<tr class="${x.n ? "" : "off"}"><td>${esc(x.label)}</td><td class="num">${x.n ? pl(n(x.n), { title: x.label, issue: x.key, ignoreFilter: true }) : "0"}</td><td class="num">${p(x.pct)}</td><td class="muted">${esc(x.lenses.map((l) => l.name + " " + n(l.n)).join(", "))}</td></tr>`));
  $("#q-other").innerHTML = (r.crop_check.length ? `<div class="hint">Crop-Faktor prüfen: ${r.crop_check.map((c) => `${esc(c.name)} steht auf ${n(c.crop)}${c.expected ? `, erwartet wäre ${n(c.expected)}` : ", die Sensorgröße ist nicht bekannt"} (${n(c.n)} Fotos${c.enabled ? "" : ", derzeit ausgeschaltet"})`).join("; ")}. Änderbar unter Kameras.</div>` : "") +
    table([["Ordner"], ["Status"], ["Dateien", "num"], ["zuletzt eingelesen"]], r.folders.map((f) => `<tr><td>${esc(f.path)}</td><td>${f.online ? '<span class="status-ok">verbunden</span>' : '<span class="status-off">nicht erreichbar</span>'}</td><td class="num">${n(f.files)}</td><td>${esc(f.last_scan || "noch nie")}</td></tr>`));
}

/* ---------- Gespeicherte Ansichten ---------- */
let VIEWS = [];
async function loadViews(sel) {
  VIEWS = await api("/api/views");
  $("#view-select").innerHTML = '<option value="">–</option>' + VIEWS.map((v) => `<option value="${v.id}">${esc(v.name)}</option>`).join("");
  $("#view-select").value = sel || "";
  $("#view-del").hidden = !$("#view-select").value;
}
$("#view-save").onclick = async () => {
  const cur = VIEWS.find((v) => String(v.id) === $("#view-select").value);
  const name = prompt("Name der Ansicht:", cur ? cur.name : ""); if (!name || !name.trim()) return;
  await api("/api/views", { name, state: { F: JSON.parse(JSON.stringify(F)), sort: T.sort, cols: T.cols, tab: activeTab() } });
  await loadViews(); const v = VIEWS.find((x) => x.name === name.trim().slice(0, 80)); if (v) { $("#view-select").value = v.id; $("#view-del").hidden = false; }
  toast("Ansicht gespeichert");
};
$("#view-select").onchange = (e) => {
  $("#view-del").hidden = !e.target.value;
  const v = VIEWS.find((x) => String(x.id) === e.target.value); if (!v) return;
  Object.assign(F, { cameras: [], lenses: [], from: "", to: "", good: false, cf: {} }, v.state.F);
  if (v.state.sort) T.sort = v.state.sort;
  if (v.state.cols) T.cols = v.state.cols;
  $("#f-from").value = F.from; $("#f-to").value = F.to; $("#f-good").checked = F.good;
  saveFilter(); saveTable(); resetTablePos(); showTab(v.state.tab || activeTab());
};
$("#view-del").onclick = async () => {
  const v = VIEWS.find((x) => String(x.id) === $("#view-select").value); if (!v) return;
  if (!confirm(`Ansicht „${v.name}“ löschen?`)) return;
  await api("/api/views/delete", { id: v.id }); await loadViews(); toast("Ansicht gelöscht");
};

/* ---------- Automatisch aktualisieren ---------- */
$("#auto-scan").onchange = async (e) => { await api("/api/settings", { auto_scan: e.target.checked }); toast(e.target.checked ? "Automatisches Aktualisieren an" : "Automatisches Aktualisieren aus"); };

/* ---------- Bedienung und erster Start ---------- */
document.addEventListener("click", (e) => {
  const j = e.target.closest("[data-jump]");
  if (j) document.getElementById(j.dataset.jump).scrollIntoView({ behavior: "smooth", block: "start" });
  const item = e.target.closest("details.menu .list button");
  if (item) item.closest("details").open = false;
});
function enterWelcome() {
  Object.assign(F, { cameras: [], lenses: [], from: "", to: "", good: false, cf: {} });
  saveFilter();
  document.body.classList.add("first");
  $("#welcome").hidden = false;
}
function leaveWelcome() {
  document.body.classList.remove("first");
  $("#welcome").hidden = true;
  lastLensList = null; cmpReady = false;
  showTab("auswertung");
  toast("Einlesen abgeschlossen");
}
$("#w-choose").onclick = async () => {
  const msgs = await chooseFolders();
  const m = $("#w-msg"); m.hidden = !msgs.length; m.textContent = msgs.join(" · ");
  if (!(await api("/api/folders")).length) return;
  $("#w-choose").disabled = true;
  welcomeScan = true;
  await api("/api/scan", {});
  pollStatus();
};

/* ---------- Start ---------- */
async function boot() {
  F.cf = F.cf || {};
  COLS = await api("/api/columns");
  markTables();
  let tab = "auswertung";
  try { tab = localStorage.getItem("tab") || tab; } catch (e) {}
  if (!TABS[tab]) tab = "auswertung";
  const fs = await api("/api/folders");
  loadViews();
  api("/api/settings").then((s) => { $("#auto-scan").checked = s.auto_scan; });
  if (!fs.length) enterWelcome(); else showTab(tab);
  pollStatus();
}
