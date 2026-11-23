"""Sprache der Exporte und Meldungen. Deutsch ist der Quelltext, web/en.json enthält die englischen Texte."""
import json
import os
import re
import threading

_STATE = threading.local()
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "en.json")
_SPLIT = (" · ", "; ", ", ", ": ")
_ONE = {"photos": "photo", "days": "day", "lenses": "lens", "cameras": "camera", "images": "image", "files": "file",
        "errors": "error", "values": "value"}
_GROUP = {"N": r"([\d.,]+)", "D": r"([\d.\-]+)", "X": r"(.+)"}


def _load():
    with open(PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    exact, templates = {}, []
    for key, target in data.items():
        parts = re.split(r"(\{[NDX]\})", key)
        if len(parts) == 1:
            exact[key] = target
            continue
        kinds = [x[1] for x in parts[1::2]]
        rx = "".join(_GROUP[x[1]] if i % 2 else re.escape(x) for i, x in enumerate(parts))
        templates.append((sum(len(x) for x in parts[0::2]), re.compile("^" + rx + "$", re.S), kinds, target))
    templates.sort(key=lambda t: -t[0])
    return exact, templates


EXACT, TEMPLATES = _load()


def use(language):
    _STATE.lang = "en" if language == "en" else "de"


def lang():
    return getattr(_STATE, "lang", "de")


def csv_delimiter():
    return "," if lang() == "en" else ";"


def number(v):
    """Ganzzahl mit Tausendertrennung in der aktuellen Sprache."""
    s = "{:,}".format(int(v))
    return s if lang() == "en" else s.replace(",", ".")


def decimal(s):
    """Dezimaltrennung eines bereits gerundeten Werts."""
    return s if lang() == "en" else s.replace(".", ",")


def percent(s):
    return "%s%%" % s if lang() == "en" else "%s %%" % s


def _one(s):
    if s in EXACT:
        return EXACT[s]
    if not re.search(r"[A-Za-zÄÖÜäöüß]", s):
        return s
    if s.startswith("·"):
        rest = s[1:].lstrip()
        return s[:len(s) - len(rest)] + _en(rest) if rest else s

    def fill(m, kinds, target):
        return re.sub(r"\$(\d)", lambda g: _en(m.group(int(g.group(1)))) if kinds[int(g.group(1)) - 1] == "X"
                      else m.group(int(g.group(1))), target)

    def split(sep):
        parts = s.split(sep)
        out = [_en(x) for x in parts]
        return sep.join(out) if out != parts else s

    for _, rx, kinds, target in TEMPLATES:
        if "X" not in kinds:
            m = rx.match(s)
            if m:
                return fill(m, kinds, target)
    if " · " in s:
        return split(" · ")
    for _, rx, kinds, target in TEMPLATES:
        if "X" in kinds:
            m = rx.match(s)
            if m:
                return fill(m, kinds, target)
    for sep in _SPLIT[1:]:
        if sep in s:
            return split(sep)
    return s


def _en(s):
    if "\n" in s:
        return "\n".join(_en(x) for x in s.split("\n"))
    m = re.match(r"^(\s*)(.*?)(\s*)$", s, re.S)
    if not m.group(2):
        return s
    out = _one(m.group(2))
    out = re.sub(r"(^|[^\d.,])1 (photos|days|lenses|cameras|images|files|errors|values)\b",
                 lambda g: g.group(1) + "1 " + _ONE[g.group(2)], out)
    return m.group(1) + out + m.group(3)


def t(s):
    """Übersetzt einen Text in die aktuelle Sprache."""
    return _en(s) if lang() == "en" else s
