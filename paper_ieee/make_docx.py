"""Build the Word version of the IEEE paper on the official IEEE conference template.

    uv run --with lxml python paper_ieee/make_docx.py TEMPLATE.docx [--out paper_ieee/leaklens_ieee.docx]

TEMPLATE.docx is IEEE's "conference-template-letter.docx" (not redistributed here). The text, tables, listing and
references come from paper_ieee/leaklens_ieee.tex (itself generated from paper/leaklens_paper.tex) and from the
bibliography that BibTeX produced for it, so the Word and LaTeX versions say the same thing. Every paragraph uses
a style defined by the template (paper title, Author, Abstract, Keywords, Heading 1/2/5, Body Text, table head,
table col head, table copy, figure caption, references); the template's guidance text is removed. Fig. 1 is the
LaTeX figure rendered to PNG. The template is Strict OOXML, so the XML is written in the Strict namespaces.

Needs: tectonic (path in $TECTONIC) to render Fig. 1 and to produce the bibliography, and pypdfium2 + pillow.
"""

from __future__ import annotations

import argparse
import copy
import io
import os
import re
import subprocess
import tempfile
import unicodedata
import zipfile
from pathlib import Path

from lxml import etree

HERE = Path(__file__).resolve().parent
WNS = "http://purl.oclc.org/ooxml/wordprocessingml/main"
RNS = "http://purl.oclc.org/ooxml/officeDocument/relationships"
WPNS = "http://purl.oclc.org/ooxml/drawingml/wordprocessingDrawing"
ANS = "http://purl.oclc.org/ooxml/drawingml/main"
PICNS = "http://purl.oclc.org/ooxml/drawingml/picture"
W = "{%s}" % WNS
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

COL_TW = 5033      # one text column in the template's two-column section (251.65 pt), twips
FULL_TW = 10426    # full text width (521.3 pt), twips
ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


# --------------------------------------------------------------------------- XML helpers
def el(tag, attrs=None, *children, text=None):
    ns, _, name = tag.partition(":")
    uri = {"w": WNS, "r": RNS, "wp": WPNS, "a": ANS, "pic": PICNS}[ns]
    e = etree.Element("{%s}%s" % (uri, name))
    for k, v in (attrs or {}).items():
        kns, _, kname = k.partition(":")
        if kname:
            kuri = {"w": WNS, "r": RNS}[kns]
            e.set("{%s}%s" % (kuri, kname), str(v))
        else:
            e.set(k, str(v))
    for c in children:
        if c is not None:
            e.append(c)
    if text is not None:
        e.text = text
    return e


def run(text, fmt=frozenset(), size=None, font=None):
    rpr = el("w:rPr")
    if font or "mono" in fmt:
        f = font or "Courier New"
        rpr.append(el("w:rFonts", {"w:ascii": f, "w:hAnsi": f, "w:cs": f}))
    if "b" in fmt:
        rpr.append(el("w:b"))
    if "i" in fmt:
        rpr.append(el("w:i"))
    sz = size or (None if "mono" not in fmt else None)
    if sz:
        rpr.append(el("w:sz", {"w:val": sz}))
        rpr.append(el("w:szCs", {"w:val": sz}))
    if "sup" in fmt:
        rpr.append(el("w:vertAlign", {"w:val": "superscript"}))
    r = el("w:r")
    if len(rpr):
        r.append(rpr)
    parts = text.split("\t")
    for k, part in enumerate(parts):
        if k:
            r.append(el("w:tab"))
        if part:
            t = el("w:t", text=part)
            t.set(XML_SPACE, "preserve")
            r.append(t)
    return r


def para(style=None, runs=(), ppr_extra=(), jc=None, sect=None):
    ppr = el("w:pPr")
    if style:
        ppr.append(el("w:pStyle", {"w:val": style}))
    for x in ppr_extra:
        ppr.append(x)
    if jc:
        ppr.append(el("w:jc", {"w:val": jc}))
    if sect is not None:
        ppr.append(sect)
    p = el("w:p", None, ppr)
    for r in runs:
        p.append(r)
    return p


# --------------------------------------------------------------------------- LaTeX inline -> runs
ACCENT = {'"': "\u0308", "'": "\u0301", "v": "\u030c", "`": "\u0300", "^": "\u0302", "~": "\u0303", "c": "\u0327"}
IGNORE = {"newblock", "BIBentryALTinterwordspacing", "BIBentrySTDinterwordspacing", "raggedright", "footnotesize",
          "scriptsize", "small", "centering", "arraybackslash", "noindent", "relax"}
SYMBOL = {"%": "%", "&": "&", "_": "_", "#": "#", "$": "$", ",": "\u202f", " ": " ", "{": "{", "}": "}", "\n": " ",
          "@": ""}


def group(s, i):
    """s[i] == '{'; return (content, index after the closing brace)."""
    assert s[i] == "{", s[i:i + 30]
    depth, j = 0, i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    raise ValueError("unbalanced: " + s[i:i + 60])


def strip_comments(s):
    return re.sub(r"(?<!\\)%.*", "", s)


class Ctx:
    def __init__(self, cites, labels):
        self.cites, self.labels, self.footnotes = cites, labels, []

    def cite(self, keys):
        nums = sorted(self.cites[k.strip()] for k in keys.split(","))
        out, k = [], 0
        while k < len(nums):
            j = k
            while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
                j += 1
            if j - k >= 2:
                out.append(f"[{nums[k]}]\u2013[{nums[j]}]")
            else:
                out += [f"[{n}]" for n in nums[k:j + 1]]
            k = j + 1
        return ", ".join(out)


def math_runs(s, fmt):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c in "^_":
            i += 1
            if s[i] == "{":
                inner, i = group(s, i)
            else:
                inner, i = s[i], i + 1
            for t, f in math_runs(inner, fmt):
                out.append((t, f | {"sup"}))
            continue
        if c == "\\":
            m = re.match(r"\\([a-zA-Z]+|.)", s[i:])
            name = m[1]
            i += len(m[0])
            out.append(({"dagger": "\u2020", "cdot": "\u00b7", "Delta": "\u0394", "ast": "*", "leq": "\u2264", "geq": "\u2265", ",": "\u202f",
                         "times": "\u00d7"}[name], fmt))
            continue
        if c.isalpha():
            out.append((c, fmt | {"i"}))
        elif c == "-":
            out.append(("\u2212", fmt))
        elif c == " ":
            pass
        else:
            out.append((c, fmt))
        i += 1
    return out


def inline(s, ctx, fmt=frozenset()):
    """Return a list of (text, fmt) and ('\x00footnote', runs) items."""
    out, i, buf = [], 0, []

    def flush():
        if buf:
            out.append(("".join(buf), fmt))
            buf.clear()

    while i < len(s):
        c = s[i]
        if c == "\\":
            m = re.match(r"\\([a-zA-Z]+)\s*|\\([\s\S])", s[i:])
            name = m[1] or m[2]
            i += len(m[0])
            if name in ACCENT and m[2] is not None or name == "v":
                if s[i] == "{":
                    base, i = group(s, i)
                else:
                    base, i = s[i], i + 1
                buf.append(unicodedata.normalize("NFC", base + ACCENT[name]))
                continue
            if m[2] is not None:
                if name == "\\":
                    buf.append(" ")
                else:
                    buf.append(SYMBOL[name])
                continue
            if name in IGNORE:
                continue
            if name == "tool":
                if s[i:i + 2] == "{}":
                    i += 2
                buf.append("LeakLens")
                continue
            arg, i = group(s, i)
            if name in ("textbf", "emph", "textit", "code", "texttt", "url"):
                flush()
                add = {"textbf": {"b"}, "emph": {"i"}, "textit": {"i"}, "code": {"mono"}, "texttt": {"mono"},
                       "url": set()}[name]
                if name == "url":
                    out.append((arg, fmt))
                else:
                    out += inline(arg, ctx, fmt | add)
            elif name == "cite":
                buf.append(ctx.cite(arg))
            elif name == "ref":
                buf.append(ctx.labels[arg])
            elif name == "footnote":
                flush()
                out.append(("\x00footnote", inline(arg, ctx)))
            elif name == "textsuperscript":
                flush()
                out += inline(arg, ctx, fmt | {"sup"})
            else:
                raise ValueError(f"unhandled command \\{name} in: {s[:80]}")
            continue
        if c == "{":
            flush()
            inner, i = group(s, i)
            out += inline(inner, ctx, fmt)
            continue
        if c == "$":
            flush()
            j = s.index("$", i + 1)
            out += math_runs(s[i + 1:j], fmt)
            i = j + 1
            continue
        if s.startswith("---", i):
            buf.append("\u2014")
            i += 3
            continue
        if s.startswith("--", i):
            buf.append("\u2013")
            i += 2
            continue
        if s.startswith("``", i):
            buf.append("\u201c")
            i += 2
            continue
        if s.startswith("''", i):
            buf.append("\u201d")
            i += 2
            continue
        if c == "`":
            buf.append("\u2018")
        elif c == "'":
            buf.append("\u2019")
        elif c == "~":
            buf.append("\u00a0")
        elif c in " \n\t":
            if not buf or buf[-1] != " ":
                buf.append(" ")
        else:
            buf.append(c)
        i += 1
    flush()
    return out


def to_runs(items, ctx, size=None, extra=frozenset(), footnote_runs=None):
    runs = []
    for t, f in items:
        if t == "\x00footnote":
            ctx.footnotes.append(f)
            fid = len(ctx.footnotes)
            r = el("w:r", None, el("w:rPr", None, el("w:vertAlign", {"w:val": "superscript"})),
                   el("w:footnoteReference", {"w:id": fid}))
            runs.append(r)
            continue
        runs.append(run(t, frozenset(f) | extra, size=size))
    return runs


def norm_space(items):
    """Collapse leading/trailing spaces of a paragraph."""
    items = [x for x in items if x[0] != ""]
    if items and items[0][0] != "\x00footnote":
        items[0] = (items[0][0].lstrip(), items[0][1])
    if items and items[-1][0] != "\x00footnote":
        items[-1] = (items[-1][0].rstrip(), items[-1][1])
    return items


# --------------------------------------------------------------------------- tables
def parse_colspec(spec):
    cols, i = [], 0
    while i < len(spec):
        c = spec[i]
        if c in "@><!":
            _, i = group(spec, i + 1)
            continue
        if c in "lrc":
            cols.append({"align": {"l": "start", "r": "end", "c": "center"}[c], "w": None})
        elif c in "pmb":
            arg, i = group(spec, i + 1)
            cols.append({"align": "start", "w": float(re.match(r"[\d.]+", arg)[0])})
            continue
        elif c == "X":
            cols.append({"align": "start", "w": "X"})
        i += 1
    return cols


def split_top(s, sep):
    parts, depth, cur, i = [], 0, [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and s.startswith(sep, i) and sep == "\\\\" and depth == 0:
            parts.append("".join(cur))
            cur = []
            i += 2
            continue
        if c == "\\":
            cur.append(s[i:i + 2])
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        if sep == "&" and c == "&" and depth == 0:
            parts.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    parts.append("".join(cur))
    return parts


def parse_tabular(src):
    m = re.search(r"\\begin\{(tabularx?)\}", src)
    env = m[1]
    i = m.end()
    if env == "tabularx":
        _, i = group(src, i)
    spec, i = group(src, i)
    body = src[i:src.index(r"\end{%s}" % env)]
    after = src[src.index(r"\end{%s}" % env) + len(r"\end{%s}" % env):]
    cols = parse_colspec(spec)
    rows, rule_before, header_end = [], set(), None
    for raw in split_top(body, "\\\\"):
        chunk = raw
        while True:
            chunk = chunk.strip()
            mm = re.match(r"\\(toprule|midrule|bottomrule|cmidrule(\([^)]*\))?\{[^}]*\})", chunk)
            if not mm:
                break
            if mm[1] == "midrule":
                if header_end is None:
                    header_end = len(rows)
                else:
                    rule_before.add(len(rows))
            chunk = chunk[mm.end():]
        if not chunk.strip():
            continue
        cells = []
        for cell in split_top(chunk, "&"):
            cell = cell.strip()
            mc = re.match(r"\\multicolumn\{(\d+)\}\{([^}]*)\}", cell)
            if mc:
                content, _ = group(cell, mc.end())
                cells.append({"text": content, "span": int(mc[1]),
                              "align": {"l": "start", "r": "end", "c": "center"}[mc[2].strip("|")[0]]})
            else:
                cells.append({"text": cell, "span": 1, "align": None})
        rows.append(cells)
    return cols, rows, header_end or 0, rule_before, after


def plain_len(text):
    t = re.sub(r"\\[a-zA-Z]+\*?|[{}$\\^]", "", text)
    return len(t.strip())


def build_table(src, ctx, total_tw, font_sz=16):
    cols, rows, header_end, rule_before, after = parse_tabular(src)
    n = len(cols)
    # widths
    fixed = [c["w"] for c in cols]
    if any(w is not None for w in fixed):
        frac = sum(w for w in fixed if isinstance(w, float))
        nx = sum(1 for w in fixed if w == "X")
        widths = [int(total_tw * (w if isinstance(w, float) else (1 - frac) / max(nx, 1))) if w is not None
                  else 0 for w in fixed]
    else:
        # natural width in points: ~3.7 pt per character at 8 pt Times (bold headers ~8% wider), plus cell
        # margins; spare width is shared equally, a shortfall is taken proportionally
        est = [12.0] * n
        for ri, r in enumerate(rows):
            k = 0
            for c in r:
                if c["span"] == 1:
                    bold = 1.08 if ri < header_end else 1.0
                    est[k] = max(est[k], plain_len(c["text"]) * 3.7 * bold + 4.0)
                k += c["span"]
        avail = total_tw / 20
        spare = avail - sum(est)
        est = [e + spare / n for e in est] if spare > 0 else [e * avail / sum(est) for e in est]
        widths = [int(e * 20) for e in est]
    widths[-1] += total_tw - sum(widths)

    def border(side, sz):
        return el(f"w:{side}", {"w:val": "single", "w:sz": sz, "w:space": 0, "w:color": "000000"})

    tbl = el("w:tbl")
    tblpr = el("w:tblPr", None,
               el("w:tblW", {"w:w": total_tw, "w:type": "dxa"}),
               el("w:jc", {"w:val": "center"}),
               el("w:tblBorders", None, border("top", 8), border("bottom", 8)),
               el("w:tblLayout", {"w:type": "fixed"}),
               el("w:tblCellMar", None, el("w:top", {"w:w": 0, "w:type": "dxa"}),
                  el("w:start", {"w:w": 30, "w:type": "dxa"}), el("w:bottom", {"w:w": 0, "w:type": "dxa"}),
                  el("w:end", {"w:w": 30, "w:type": "dxa"})),
               el("w:tblLook", {"w:firstRow": "1", "w:lastRow": "0", "w:firstColumn": "1", "w:lastColumn": "0",
                                "w:noHBand": "0", "w:noVBand": "1"}))
    tbl.append(tblpr)
    grid = el("w:tblGrid")
    for w_ in widths:
        grid.append(el("w:gridCol", {"w:w": w_}))
    tbl.append(grid)
    for ri, r in enumerate(rows):
        tr = el("w:tr")
        trpr = el("w:trPr", None, el("w:cantSplit"))
        if ri < header_end:
            trpr.append(el("w:tblHeader"))
        tr.append(trpr)
        k = 0
        for c in r:
            w_ = sum(widths[k:k + c["span"]])
            tcpr = el("w:tcPr", None, el("w:tcW", {"w:w": w_, "w:type": "dxa"}))
            if c["span"] > 1:
                tcpr.append(el("w:gridSpan", {"w:val": c["span"]}))
            sides = []
            if ri == header_end - 1:
                sides.append(border("bottom", 4))
            elif ri < header_end - 1 and c["span"] > 1:
                sides.append(border("bottom", 4))  # \cmidrule under a spanning header
            if ri in rule_before:
                sides.insert(0, border("top", 4))
            if sides:
                tcpr.append(el("w:tcBorders", None, *sides))
            tcpr.append(el("w:vAlign", {"w:val": "top"}))
            align = c["align"] or cols[k]["align"]
            style = "tablecolhead" if ri < header_end else "tablecopy"
            items = norm_space(inline(c["text"], ctx))
            keep = [el("w:keepNext")] if ri < len(rows) - 1 else []
            p = para(style, to_runs(items, ctx, size=font_sz), jc=align,
                     ppr_extra=keep + [el("w:spacing", {"w:before": 0, "w:after": 0, "w:line": 240,
                                                         "w:lineRule": "auto"})])
            tc = el("w:tc", None, tcpr, p)
            tr.append(tc)
            k += c["span"]
        tbl.append(tr)
    notes = []
    note_src = re.sub(r"\\vspace\{[^}]*\}", "", after).strip()
    if note_src:
        items = norm_space(inline(note_src, ctx))
        notes.append(para("tablefootnote", to_runs(items, ctx, size=14),
                          ppr_extra=[el("w:numPr", None, el("w:ilvl", {"w:val": 0}), el("w:numId", {"w:val": 0})),
                                     el("w:ind", {"w:start": 0, "w:hanging": 0})], jc="both"))
    return tbl, notes


# --------------------------------------------------------------------------- figure
def render_figure(tex_body, workdir):
    tikz = re.search(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", tex_body, re.S)[0]
    doc = (r"\documentclass[border=1pt]{standalone}" "\n" r"\usepackage[T1]{fontenc}\usepackage{mathptmx}"
           r"\usepackage{xcolor}\usepackage{tikz}\usetikzlibrary{arrows.meta,positioning}"
           r"\definecolor{navy}{HTML}{1F4E79}\newcommand{\code}[1]{\texttt{#1}}" "\n"
           r"\begin{document}\scriptsize" "\n" + tikz + "\n" r"\end{document}" "\n")
    (workdir / "fig1.tex").write_text(doc)
    subprocess.run([os.environ.get("TECTONIC", "tectonic"), "-X", "compile", "fig1.tex"], cwd=workdir,
                   check=True, capture_output=True)
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(workdir / "fig1.pdf"))
    w_pt, h_pt = pdf[0].get_size()
    img = pdf[0].render(scale=600 / 72).to_pil()
    buf = io.BytesIO()
    img.save(buf, format="PNG", dpi=(600, 600))
    return buf.getvalue(), w_pt, h_pt


def drawing(rid, w_pt, h_pt, name, descr):
    cx, cy = int(w_pt * 12700), int(h_pt * 12700)
    pic = el("pic:pic", None,
             el("pic:nvPicPr", None, el("pic:cNvPr", {"id": 0, "name": name}), el("pic:cNvPicPr")),
             el("pic:blipFill", None, el("a:blip", {"r:embed": rid}), el("a:stretch", None, el("a:fillRect"))),
             el("pic:spPr", None, el("a:xfrm", None, el("a:off", {"x": 0, "y": 0}), el("a:ext", {"cx": cx, "cy": cy})),
                el("a:prstGeom", {"prst": "rect"}, el("a:avLst"))))
    inline_ = el("wp:inline", {"distT": 0, "distB": 0, "distL": 0, "distR": 0},
                 el("wp:extent", {"cx": cx, "cy": cy}),
                 el("wp:docPr", {"id": 1, "name": name, "descr": descr}),
                 el("wp:cNvGraphicFramePr", None, el("a:graphicFrameLocks", {"noChangeAspect": 1})),
                 el("a:graphic", None, el("a:graphicData", {"uri": PICNS}, pic)))
    return el("w:r", None, el("w:drawing", None, inline_))


# --------------------------------------------------------------------------- bibliography
def parse_bbl(bbl):
    entries = re.split(r"\\bibitem\{([^}]+)\}", bbl)
    keys, texts = entries[1::2], entries[2::2]
    out = []
    for k, t in zip(keys, texts):
        t = t.split(r"\end{thebibliography}")[0].strip()
        t = re.sub(r"\\hskip\s*[^\\]*\\relax\s*", " ", t)  # IEEEtran's inter-field glue
        out.append((k, t))
    return out


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template")
    ap.add_argument("--tex", default=str(HERE / "leaklens_ieee.tex"))
    ap.add_argument("--out", default=str(HERE / "leaklens_ieee.docx"))
    a = ap.parse_args()
    tex = Path(a.tex).read_text()
    tectonic = os.environ.get("TECTONIC", "tectonic")
    work = Path(tempfile.mkdtemp(prefix="leaklens-docx-"))
    subprocess.run([tectonic, "-X", "compile", "--keep-intermediates", "--outdir", str(work), a.tex],
                   cwd=HERE, check=True, capture_output=True)
    bib = parse_bbl((work / (Path(a.tex).stem + ".bbl")).read_text())
    cites = {k: n for n, (k, _) in enumerate(bib, start=1)}

    title = re.search(r"\\title\{(.*?)\}\n", tex, re.S)[1]
    abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, re.S)[1].strip()
    keywords = re.search(r"\\begin\{IEEEkeywords\}(.*?)\\end\{IEEEkeywords\}", tex, re.S)[1].strip()
    names = re.search(r"\\IEEEauthorblockN\{(.*?)\}\n", tex, re.S)[1].replace("\\\\", "").split(", ")
    names = [x for n in names for x in n.split(" and ")]
    body = strip_comments(tex[tex.index("\\section{Introduction}"):tex.index("\\bibliographystyle")])

    # labels: tables in order of appearance, figures, listings
    labels, nt = {}, 0
    for m in re.finditer(r"\\begin\{table\*?\}.*?\\label\{([^}]+)\}", body, re.S):
        nt += 1
        labels[m[1]] = ROMAN[nt]
    for k, m in enumerate(re.finditer(r"\\begin\{figure\}.*?\\label\{([^}]+)\}", body, re.S), start=1):
        labels[m[1]] = str(k)
    for k, m in enumerate(re.finditer(r"label=\{([^}]+)\}", body), start=1):
        labels[m[1]] = str(k)
    sec, sub = 0, 0  # section labels: IEEE numbering (VII, IV-A)
    for m in re.finditer(r"\\(section|subsection)(\*?)\{[^}]*\}\s*(\\label\{([^}]+)\})?", body):
        if m[2]:
            continue
        if m[1] == "section":
            sec, sub = sec + 1, 0
            if m[4]:
                labels[m[4]] = ROMAN[sec]
        else:
            sub += 1
            if m[4]:
                labels[m[4]] = f"{ROMAN[sec]}-{chr(64 + sub)}"
    ctx = Ctx(cites, labels)

    # ---- template parts
    zin = zipfile.ZipFile(a.template)
    parts = {n: zin.read(n) for n in zin.namelist()}
    doc = etree.fromstring(parts["word/document.xml"])
    tbody = doc.find(W + "body")
    old = list(tbody)
    title_ppr = copy.deepcopy(old[0].find(W + "pPr"))
    sect_first = copy.deepcopy(old[2].find(f"{W}pPr/{W}sectPr"))
    sect_two = copy.deepcopy(old[98].find(f"{W}pPr/{W}sectPr"))
    sect_final = copy.deepcopy(old[-1])
    assert sect_two.find(W + "cols").get(W + "num") == "2"
    sect_one = copy.deepcopy(sect_two)
    sect_one.find(W + "cols").attrib.pop(W + "num")
    for x in old:
        tbody.remove(x)
    B = []

    # ---- title and authors (one block: all authors share one affiliation)
    p = el("w:p", None, title_ppr)
    for r in to_runs(norm_space(inline(title, ctx)), ctx):
        p.append(r)
    B.append(p)
    B.append(para("Author", [run(", ".join(names[:-1]) + " and " + names[-1])],
                  ppr_extra=[el("w:spacing", {"w:before": 240, "w:after": 40})]))
    aff = ("Department of Information Technology, Guru Nanak Institute of Technology, Kolkata, India")
    B.append(para("Author", [run(aff, {"i"}, size=20)], ppr_extra=[el("w:spacing", {"w:before": 0, "w:after": 240})],
                  sect=sect_first))

    # ---- abstract and keywords
    B.append(para("Abstract", [run("Abstract", {"i"}), run("\u2014")] +
                  to_runs(norm_space(inline(abstract, ctx)), ctx)))
    B.append(para("Keywords", [run("Keywords\u2014")] + to_runs(norm_space(inline(keywords, ctx)), ctx)))

    # ---- body
    img_rels = []
    i = 0
    lines = body
    pbuf: list[str] = []

    def flush_para():
        text = " ".join(pbuf).strip()
        pbuf.clear()
        if text:
            B.append(para("BodyText", to_runs(norm_space(inline(text, ctx)), ctx)))

    while i < len(lines):
        if lines.startswith("\n\n", i) or (lines[i] == "\n" and lines[i + 1:i + 2] == "\n"):
            flush_para()
            i += 1
            continue
        m = re.match(r"\\(section|subsection)(\*?)\{", lines[i:])
        if m:
            flush_para()
            head, j = group(lines, i + m.end() - 1)
            i = j
            if m[2]:
                B.append(para("Heading5", to_runs(norm_space(inline(head, ctx)), ctx)))
            else:
                B.append(para("Heading1" if m[1] == "section" else "Heading2",
                              to_runs(norm_space(inline(head, ctx)), ctx)))
            continue
        ml = re.match(r"\\label\{[^}]*\}\s*", lines[i:])
        if ml:
            i += ml.end()
            continue
        m = re.match(r"\\begin\{([a-zA-Z*]+)\}", lines[i:])
        if m:
            flush_para()
            env = m[1]
            end = lines.index("\\end{%s}" % env, i)
            content = lines[i + m.end():end]
            i = end + len("\\end{%s}" % env)
            if env == "enumerate":
                for k, item in enumerate(re.split(r"\\item\s+", content)[1:], start=1):
                    items = norm_space(inline(item, ctx))
                    B.append(para("BodyText", [run(f"{k})\t")] + to_runs(items, ctx),
                                  ppr_extra=[el("w:ind", {"w:start": 288, "w:hanging": 288})]))
            elif env in ("table", "table*"):
                cap, _ = group(content, content.index("\\caption{") + len("\\caption"))
                inp = re.search(r"\\input\{([^}]+)\}", content)
                tsrc = content
                if inp:
                    tsrc = content.replace(inp[0], (HERE / (inp[1] + ".tex")).read_text())
                tsrc = strip_comments(tsrc)
                wide = env == "table*"
                tbl, notes = build_table(tsrc[tsrc.index("\\begin{tabular"):], ctx, FULL_TW if wide else COL_TW)
                tlab = re.search(r"\\label\{([^}]+)\}", content)[1]
                cap_p = para("tablehead", [run(f"Table {labels[tlab]}. ")] +
                             to_runs(norm_space(inline(cap, ctx)), ctx),
                             ppr_extra=[el("w:keepNext"), el("w:numPr", None, el("w:ilvl", {"w:val": 0}), el("w:numId", {"w:val": 0}))])
                if wide:   # end the two-column section, set the table across the page, resume two columns
                    B.append(para(None, [], sect=copy.deepcopy(sect_two)))
                    B += [cap_p, tbl] + notes
                    B.append(para(None, [], ppr_extra=[el("w:spacing", {"w:before": 0, "w:after": 0})],
                                  sect=copy.deepcopy(sect_one)))
                else:
                    B += [cap_p, tbl] + notes
                    B.append(para(None, [], ppr_extra=[el("w:spacing", {"w:before": 0, "w:after": 60,
                                                                        "w:line": 120, "w:lineRule": "exact"})]))
            elif env == "figure":
                cap, _ = group(content, content.index("\\caption{") + len("\\caption"))
                png, w_pt, h_pt = render_figure(content, work)
                rid = "rIdLeakLensFig1"
                img_rels.append((rid, "media/leaklens_fig1.png", png))
                B.append(para(None, [drawing(rid, w_pt, h_pt, "Figure 1", "Stages of LeakLens")], jc="center",
                              ppr_extra=[el("w:keepNext"), el("w:spacing", {"w:before": 120, "w:after": 0})]))
                flab = re.search(r"\\label\{([^}]+)\}", content)[1]
                B.append(para("figurecaption", [run(f"Fig. {labels[flab]}. ")] +
                              to_runs(norm_space(inline(cap, ctx)), ctx), ppr_extra=[el("w:numPr", None, el("w:ilvl", {"w:val": 0}), el("w:numId", {"w:val": 0}))]))
            elif env == "lstlisting":
                opts_end = content.index("]")
                # options may contain ']' inside braces: find the matching ']' at depth 0
                depth = 0
                for j, ch in enumerate(content):
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                    elif ch == "]" and depth == 0:
                        opts_end = j
                        break
                opts, code = content[1:opts_end], content[opts_end + 1:].strip("\n")
                cap, _ = group(opts, opts.index("caption=") + len("caption="))
                shd = el("w:shd", {"w:val": "clear", "w:color": "auto", "w:fill": "F5F6F8"})
                for line in code.split("\n"):
                    B.append(para(None, [run(line if line else " ", size=13, font="Courier New")],
                                  ppr_extra=[el("w:keepNext"), el("w:keepLines"), copy.deepcopy(shd),
                                             el("w:spacing", {"w:before": 0, "w:after": 0, "w:line": 180,
                                                              "w:lineRule": "exact"})], jc="start"))
                B.append(para("figurecaption", [run(f"Listing {labels['lst:example']}. ")] +
                              to_runs(norm_space(inline(cap, ctx)), ctx),
                              ppr_extra=[el("w:numPr", None, el("w:ilvl", {"w:val": 0}), el("w:numId", {"w:val": 0}))]))
            else:
                raise ValueError("unhandled environment " + env)
            continue
        # ordinary text: accumulate the line
        j = lines.find("\n", i)
        j = len(lines) if j < 0 else j
        line = lines[i:j]
        if line.strip():
            pbuf.append(line)
        else:
            flush_para()
        i = j + 1
    flush_para()

    # ---- references
    B.append(para("Heading5", [run("References")]))
    for num, (_k, t) in enumerate(bib, start=1):
        items = norm_space(inline(t, ctx))
        B.append(para("references", [run(f"[{num}]\t")] + to_runs(items, ctx),
                      ppr_extra=[el("w:numPr", None, el("w:ilvl", {"w:val": 0}), el("w:numId", {"w:val": 0})), el("w:tabs", None, el("w:tab", {"w:val": "start", "w:pos": 360})),
                                 el("w:ind", {"w:start": 360, "w:hanging": 360})]))
    B.append(para(None, [], sect=copy.deepcopy(sect_two)))
    for x in B:
        tbody.append(x)
    tbody.append(sect_final)
    parts["word/document.xml"] = etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)

    # ---- footnotes
    fn = etree.fromstring(parts["word/footnotes.xml"])
    for fid, items in enumerate(ctx.footnotes, start=1):
        p = para(None, [el("w:r", None, el("w:rPr", None, el("w:sz", {"w:val": 16}), el("w:szCs", {"w:val": 16}),
                                         el("w:vertAlign", {"w:val": "superscript"})), el("w:footnoteRef")),
                        run(" ", size=16)] + to_runs(norm_space(items), ctx, size=16), jc="both",
                 ppr_extra=[el("w:spacing", {"w:before": 0, "w:after": 0})])
        fn.append(el("w:footnote", {"w:id": fid}, p))
    parts["word/footnotes.xml"] = etree.tostring(fn, xml_declaration=True, encoding="UTF-8", standalone=True)

    # ---- relationships, content types, media, properties
    rels = etree.fromstring(parts["word/_rels/document.xml.rels"])
    RELNS = "http://schemas.openxmlformats.org/package/2006/relationships"
    for rid, target, data in img_rels:
        rels.append(etree.Element("{%s}Relationship" % RELNS, Id=rid, Target=target,
                                  Type="http://purl.oclc.org/ooxml/officeDocument/relationships/image"))
        parts["word/" + target] = data
    parts["word/_rels/document.xml.rels"] = etree.tostring(rels, xml_declaration=True, encoding="UTF-8",
                                                           standalone=True)
    ct = etree.fromstring(parts["[Content_Types].xml"])
    CTNS = "http://schemas.openxmlformats.org/package/2006/content-types"
    if not any(d.get("Extension") == "png" for d in ct):
        ct.insert(0, etree.Element("{%s}Default" % CTNS, Extension="png", ContentType="image/png"))
    parts["[Content_Types].xml"] = etree.tostring(ct, xml_declaration=True, encoding="UTF-8", standalone=True)
    core = parts["docProps/core.xml"].decode()
    plain_title = "".join(t for t, _ in inline(title, ctx))
    core = re.sub(r"<dc:title>.*?</dc:title>", f"<dc:title>{plain_title}</dc:title>", core)
    core = re.sub(r"<dc:creator>.*?</dc:creator>", f"<dc:creator>{names[0]}</dc:creator>", core)
    core = re.sub(r"<cp:lastModifiedBy>.*?</cp:lastModifiedBy>", f"<cp:lastModifiedBy>{names[0]}</cp:lastModifiedBy>",
                  core)
    parts["docProps/core.xml"] = core.encode()

    out = Path(a.out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", parts.pop("[Content_Types].xml"))
        for n, d in parts.items():
            if n.endswith("/"):
                continue
            z.writestr(n, d)
    print("wrote", out, f"({len(B)} body blocks, {len(bib)} references, {len(ctx.footnotes)} footnote)")


if __name__ == "__main__":
    main()
