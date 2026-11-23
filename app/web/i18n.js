"use strict";
/* Sprache der Oberfläche. Deutsch ist der Quelltext, en.json enthält die englischen Texte.
   Angezeigte Texte werden übersetzt, gespeicherte Daten und Filterwerte bleiben unverändert. */
const LANG = (() => {
  const ok = (v) => (v === "de" || v === "en" ? v : "");
  return ok(window.BW_SAVED_LANG) || ok(window.BW_NATIVE_LANG) || (String(navigator.language || "").toLowerCase().startsWith("de") ? "de" : "en");
})();
const LOCALE = LANG === "en" ? "en-US" : "de-DE";
const PCT = LANG === "en" ? "%" : " %";
document.documentElement.lang = LANG;

const tr = (() => {
  if (LANG !== "en") return (s) => s;
  const GROUP = { N: "([\\d.,]+)", D: "([\\d.\\-]+)", X: "([\\s\\S]+)" };
  const quote = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const ONE = { photos: "photo", days: "day", lenses: "lens", cameras: "camera", images: "image", files: "file", errors: "error", values: "value" };
  const exact = new Map(), templates = [], cache = new Map();
  Object.entries(window.BW_EN || {}).forEach(([key, to]) => {
    const parts = key.split(/(\{[NDX]\})/);
    if (parts.length === 1) { exact.set(key, to); return; }
    const kinds = parts.filter((_, i) => i % 2).map((x) => x[1]);
    const rx = parts.map((x, i) => (i % 2 ? GROUP[x[1]] : quote(x))).join("");
    templates.push({ size: parts.filter((_, i) => !(i % 2)).join("").length, re: new RegExp("^" + rx + "$"), kinds, to });
  });
  templates.sort((a, b) => b.size - a.size);
  function one(s) {
    if (exact.has(s)) return exact.get(s);
    if (!/[A-Za-zÄÖÜäöüß]/.test(s)) return s;
    const lead = /^(·\s*)([\s\S]+)$/.exec(s);
    if (lead) return lead[1] + en(lead[2]);
    const fill = (t, m) => t.to.replace(/\$(\d)/g, (_, i) => (t.kinds[i - 1] === "X" ? en(m[i]) : m[i]));
    for (const t of templates) {
      if (t.kinds.includes("X")) continue;
      const m = t.re.exec(s);
      if (m) return fill(t, m);
    }
    const split = (sep) => {
      const parts = s.split(sep), out = parts.map(en);
      return out.some((x, i) => x !== parts[i]) ? out.join(sep) : s;
    };
    if (s.includes(" · ")) return split(" · ");
    for (const t of templates) {
      if (!t.kinds.includes("X")) continue;
      const m = t.re.exec(s);
      if (m) return fill(t, m);
    }
    for (const sep of ["; ", ", ", ": "]) if (s.includes(sep)) return split(sep);
    return s;
  }
  function en(s) {
    if (s.includes("\n")) return s.split("\n").map(en).join("\n");
    const m = /^(\s*)([\s\S]*?)(\s*)$/.exec(s);
    if (!m[2]) return s;
    const out = one(m[2]).replace(/(^|[^\d.,])1 (photos|days|lenses|cameras|images|files|errors|values)\b/g, (_, a, w) => a + "1 " + ONE[w]);
    return m[1] + out + m[3];
  }
  return (s) => {
    if (s == null || s === "") return s;
    s = String(s);
    if (cache.has(s)) return cache.get(s);
    const out = en(s);
    if (cache.size > 20000) cache.clear();
    cache.set(s, out);
    return out;
  };
})();

if (LANG === "en") {
  const ATTRS = ["placeholder", "title", "aria-label", "data-tip"];
  const cell = (s) => (/^(Mo|Di|Mi|Do|Fr|Sa|So|ja|nein|berechnet)$/.test(s.trim()) || s.startsWith("Unbekannt") ? tr(s) : s);
  const trAttr = (el, a, grid) => {
    const v = el.getAttribute(a);
    if (!v) return;
    const out = grid && a === "title" ? cell(v) : a === "data-tip" ? v.split(/(<[^>]+>)/).map((x, i) => (i % 2 ? x : tr(x))).join("") : tr(v);
    if (out !== v) el.setAttribute(a, out);
  };
  const trText = (node, grid) => {
    const p = node.parentElement;
    if (!p || p.tagName === "SCRIPT" || p.tagName === "STYLE" || p.tagName === "TITLE" || p.closest(".side > h1")) return;
    const out = grid ? cell(node.nodeValue) : tr(node.nodeValue);
    if (out !== node.nodeValue) node.nodeValue = out;
  };
  const apply = (root) => {
    if (root.nodeType === 3) { trText(root, !!(root.parentElement && root.parentElement.closest("#t-grid tbody"))); return; }
    if (root.nodeType !== 1) return;
    const grid = !!root.closest("#t-grid tbody");
    ATTRS.forEach((a) => trAttr(root, a, grid));
    root.querySelectorAll("[placeholder],[title],[aria-label],[data-tip]").forEach((el) => ATTRS.forEach((a) => trAttr(el, a, grid)));
    const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walk.nextNode()) trText(walk.currentNode, grid);
  };
  apply(document.documentElement);
  new MutationObserver((list) => list.forEach((m) => {
    if (m.type === "attributes") trAttr(m.target, m.attributeName, !!m.target.closest("#t-grid tbody"));
    else if (m.type === "characterData") apply(m.target);
    else m.addedNodes.forEach(apply);
  })).observe(document.documentElement, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS });
  const ask = window.confirm.bind(window), input = window.prompt.bind(window);
  window.confirm = (m) => ask(tr(m));
  window.prompt = (m, d) => input(tr(m), d);
}
