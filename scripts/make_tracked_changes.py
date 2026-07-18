#!/usr/bin/env python3
"""
Build a cleanly-formatted Word .docx with native tracked changes (revisions)
between the original and revised manuscript, attributed to a given author.

Unlike a flat plain-text diff, this walks pandoc's structured JSON AST so the output
has real Word heading styles, clean paragraphs, correct spacing, and Unicode math.
Inserted text is wrapped in <w:ins> and deleted text in <w:del>, both authored by
AUTHOR, so Microsoft Word shows them as that author's tracked changes.

Usage:
    pandoc -f latex -t json ORIG.tex > orig.json
    pandoc -f latex -t json REV.tex  > rev.json
    python make_tracked_changes.py orig.json rev.json OUT.docx "Author Name"
"""

import json
import re
import sys
import difflib
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

DATE = "2026-06-22T00:00:00Z"

# --- LaTeX math -> readable Unicode -------------------------------------------
_MATH = [
    (r"\chi", "χ"), (r"\times", "×"), (r"\approx", "≈"), (r"\sim", "~"),
    (r"\geq", "≥"), (r"\leq", "≤"), (r"\alpha", "α"), (r"\beta", "β"),
    (r"\%", "%"), (r"\,", ""), (r"\;", " "), (r"\quad", " "), (r"{-}", "-"),
    (r"\boldsymbol", ""), (r"\mathrm", ""),
]


_SUP = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵",
        "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹"}


def _superscript(body):
    return "".join(_SUP.get(c, c) for c in body)


def conv_math(s):
    for k, v in _MATH:
        s = s.replace(k, v)
    # superscripts: ^{1,2,3} and ^2 -> Unicode superscript digits
    s = re.sub(r"\^\{([^}]*)\}", lambda m: _superscript(m.group(1)), s)
    s = re.sub(r"\^(\w)", lambda m: _superscript(m.group(1)), s)
    s = s.replace("{", "").replace("}", "").replace("$", "").replace("\\", "")
    return s


# --- pandoc inline AST -> plain text ------------------------------------------
def itext(ils):
    out = []
    for i in ils:
        t = i["t"]
        if t == "Str":
            out.append(i["c"])
        elif t in ("Space", "SoftBreak", "LineBreak"):
            out.append(" ")
        elif t in ("Strong", "Emph", "Underline", "SmallCaps", "Strikeout"):
            out.append(itext(i["c"]) + " ")          # trailing space prevents label gluing
        elif t in ("Superscript", "Subscript"):
            out.append(itext(i["c"]))
        elif t == "Quoted":
            q = '"' if i["c"][0]["t"] == "DoubleQuote" else "'"
            out.append(q + itext(i["c"][1]) + q)
        elif t == "Math":
            out.append(conv_math(i["c"][1]))
        elif t == "Link":
            out.append(itext(i["c"][1]))
        elif t == "Span":
            out.append(itext(i["c"][1]))
        # Cite, RawInline, Note, Image -> dropped
    return "".join(out)


def norm(s):
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([,.;:!?%)\]])", r"\1", s)   # drop space before closing punctuation
    s = re.sub(r"([(\[])\s+", r"\1", s)          # drop space after opening bracket
    return s


# --- AST blocks -> ordered elements -------------------------------------------
def walk(blocks, elements):
    for b in blocks:
        t = b["t"]
        if t == "Header":
            elements.append({"kind": "heading", "level": b["c"][0],
                             "text": norm(itext(b["c"][2]))})
        elif t in ("Para", "Plain"):
            txt = norm(itext(b["c"]))
            if txt:
                elements.append({"kind": "para", "text": txt})
        elif t == "Div":
            walk(b["c"][1], elements)
        elif t == "BlockQuote":
            walk(b["c"], elements)
        # Figure, Table, CodeBlock, RawBlock -> skipped
    return elements


def load_elements(json_path):
    data = json.load(open(json_path))
    els = walk(data["blocks"], [])
    if els and els[0]["kind"] == "para":
        els[0]["kind"] = "title"          # first paragraph is the manuscript title
    return els


# --- OOXML tracked-change run helpers -----------------------------------------
def make_text_run(text, deleted=False, italic=False):
    r = OxmlElement("w:r")
    if italic:
        rpr = OxmlElement("w:rPr")
        rpr.append(OxmlElement("w:i"))
        r.append(rpr)
    tt = OxmlElement("w:delText" if deleted else "w:t")
    tt.set(qn("xml:space"), "preserve")
    tt.text = text
    r.append(tt)
    return r


class Builder:
    def __init__(self, author):
        self.author = author
        self.rev_id = 1

    def revision(self, tag, text, deleted=False):
        el = OxmlElement(tag)
        el.set(qn("w:id"), str(self.rev_id))
        el.set(qn("w:author"), self.author)
        el.set(qn("w:date"), DATE)
        el.append(make_text_run(text, deleted=deleted))
        self.rev_id += 1
        return el

    def add_segments(self, p, segments):
        """segments: list of (text, status) where status in {eq, ins, del}."""
        first = True
        for text, status in segments:
            if not first:
                text = " " + text
            first = False
            if status == "eq":
                p._p.append(make_text_run(text))
            elif status == "ins":
                p._p.append(self.revision("w:ins", text))
            else:
                p._p.append(self.revision("w:del", text, deleted=True))


def word_segments(old_text, new_text):
    """Word-level diff -> ordered (text, status) segments with grouping."""
    a, b = old_text.split(), new_text.split()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    raw = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            raw += [(w, "eq") for w in b[j1:j2]]
        elif tag == "delete":
            raw += [(w, "del") for w in a[i1:i2]]
        elif tag == "insert":
            raw += [(w, "ins") for w in b[j1:j2]]
        else:
            raw += [(w, "del") for w in a[i1:i2]]
            raw += [(w, "ins") for w in b[j1:j2]]
    # group consecutive same-status words
    segs, i = [], 0
    while i < len(raw):
        st = raw[i][1]
        j = i
        words = []
        while j < len(raw) and raw[j][1] == st:
            words.append(raw[j][0])
            j += 1
        segs.append((" ".join(words), st))
        i = j
    return segs


def style_for(el):
    if el["kind"] == "title":
        return "Title"
    if el["kind"] == "heading":
        return f"Heading {min(el.get('level', 1), 3)}"
    return None


def main():
    orig_json, rev_json, out_path, author = sys.argv[1:5]
    A = load_elements(orig_json)
    B = load_elements(rev_json)

    # align elements by (kind,text); within replaced pairs do word-level diff
    keyA = [f"{e['kind']}|{e.get('level','')}|{e['text']}" for e in A]
    keyB = [f"{e['kind']}|{e.get('level','')}|{e['text']}" for e in B]
    sm = difflib.SequenceMatcher(None, keyA, keyB, autojunk=False)

    doc = Document()
    doc.core_properties.author = author
    builder = Builder(author)

    def emit(el, segments):
        p = doc.add_paragraph()
        st = style_for(el)
        if st:
            try:
                p.style = st
            except KeyError:
                pass
        builder.add_segments(p, segments)

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(j1, j2):
                emit(B[k], [(B[k]["text"], "eq")])
        elif tag == "insert":
            for k in range(j1, j2):
                emit(B[k], [(B[k]["text"], "ins")])
        elif tag == "delete":
            for k in range(i1, i2):
                emit(A[k], [(A[k]["text"], "del")])
        else:  # replace: pair up in order, word-diff matching kinds
            olds, news = list(range(i1, i2)), list(range(j1, j2))
            for n in range(max(len(olds), len(news))):
                oi = olds[n] if n < len(olds) else None
                ni = news[n] if n < len(news) else None
                if oi is not None and ni is not None and A[oi]["kind"] == B[ni]["kind"]:
                    emit(B[ni], word_segments(A[oi]["text"], B[ni]["text"]))
                else:
                    if ni is not None:
                        emit(B[ni], [(B[ni]["text"], "ins")])
                    if oi is not None:
                        emit(A[oi], [(A[oi]["text"], "del")])

    # base font tidy
    try:
        normal = doc.styles["Normal"]
        normal.font.name = "Calibri"
        normal.font.size = Pt(11)
    except KeyError:
        pass

    settings = doc.settings.element
    settings.append(OxmlElement("w:trackChanges"))
    doc.save(out_path)
    print(f"Wrote {out_path} with {builder.rev_id - 1} tracked revision runs by {author!r}.")


if __name__ == "__main__":
    main()
