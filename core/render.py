"""Render a markdown resume as a professionally-styled PDF or LaTeX source.

Parses the LLM's markdown output (headings, entry lines with dates, bullets)
into a simple structure and renders it in a clean single-column layout:
large centered name, one contact line, section headings with a horizontal
rule, bold role - company rows with right-aligned italic dates.
"""
import re

# ---------------- parsing ----------------

_HEADING_RE = re.compile(r"^\s*#{1,6}\s*(.+?)\s*#*\s*$")
_BULLET_RE = re.compile(r"^\s*(?:[-*\u2022\u2023\u25aa])\s+(.*)$")
_MD_CHARS_RE = re.compile(r"[*_`]+")


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", _MD_CHARS_RE.sub("", s or "")).strip()


# "June 2022 – June 2025", "03/2020 - Present", "2021", "May 2024 to Aug 2025"...
_DATE_RE = re.compile(
    r"^(?:[a-z]{3,10}\.?\s+)?(?:\d{1,2}/)?(?:19|20)\d{2}"
    r"(?:\s*(?:[-\u2013\u2014]|to|until)\s*"
    r"(?:[a-z]{3,10}\.?\s+)?(?:\d{1,2}/)?(?:(?:19|20)\d{2}|present|current|now)"
    r"|present|current|now)?$",
    re.I)


def _looks_like_dates(s: str) -> bool:
    return bool(s) and len(s) <= 45 and bool(_DATE_RE.fullmatch(s.strip(" .,()[]")))


def _split_entry(line: str):
    """Split 'Title — Company | June 2022 – June 2025' into (left, right)."""
    sep_tail = " \t|(\u00b7*_,"

    def tidy(s):
        return s.rstrip(sep_tail)

    m = re.search(r"[|(·]\s*([^|()]*?)\)?\s*$", line)
    if m and _looks_like_dates(m.group(1)):
        return tidy(line[:m.start()]), m.group(1).strip()
    m = re.search(r"(?<!\*)\*([^*]+)\*(?!\*)\s*$", line)
    if m and _looks_like_dates(m.group(1)):
        return tidy(line[:m.start()]), m.group(1).strip()
    m = re.search(r"[(]\s*([^()]*?)\s*[)]\s*$", line)
    if m and _looks_like_dates(m.group(1)):
        return tidy(line[:m.start()]), m.group(1).strip()
    parts = re.split(r"\s+[-\u2013\u2014]\s+", line)
    if len(parts) >= 2 and _looks_like_dates(parts[-1]):
        return tidy(" \u2014 ".join(parts[:-1])), parts[-1].strip()
    return None


def parse_resume(md_text: str) -> dict:
    """Parse markdown resume text into {name, contact, sections:[{title, blocks}]}.

    Block kinds: ("entry", left, right) | ("bullet", text) | ("para", text).
    """
    lines = (md_text or "").replace("\r\n", "\n").split("\n")
    name, contact = "", ""
    sections, cur = [], None

    def ensure(title=""):
        nonlocal cur
        if cur is None:
            cur = {"title": title, "blocks": []}
            sections.append(cur)

    pending_entry = None
    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            continue
        h = _HEADING_RE.match(line)
        if h:
            title = _clean(h.group(1))
            if h.group(0).lstrip().startswith("# ") and not name and not sections:
                name = title
                continue
            cur = {"title": title or " ", "blocks": []}
            sections.append(cur)
            continue
        b = _BULLET_RE.match(line)
        if b:
            ensure()
            pending_entry = None
            cur["blocks"].append(("bullet", _clean(b.group(1))))
            continue
        plain = line.strip()
        if not sections and ("@" in plain or "|" in plain or "\u00b7" in plain
                             or re.search(r"\+?\d[\d\s().-]{7,}", plain)
                             or re.search(r"(github\.com|linkedin\.com)", plain, re.I)):
            contact = (contact + " | " + plain) if contact else plain
            continue
        split = _split_entry(plain)
        if split and not _looks_like_dates(_clean(split[0])):
            ensure()
            left, right = _clean(split[0]), _clean(split[1])
            cur["blocks"].append(("entry", left, right))
            pending_entry = cur["blocks"][-1]
            continue
        if pending_entry is not None and pending_entry[2] == "" and _looks_like_dates(_clean(plain)):
            idx = cur["blocks"].index(pending_entry)
            cur["blocks"][idx] = ("entry", pending_entry[1], _clean(plain))
            pending_entry = None
            continue
        pending_entry = None
        ensure()
        cur["blocks"].append(("para", _clean(plain)))

    if not sections and md_text and md_text.strip():
        ensure()
        for para in re.split(r"\n\s*\n", md_text.strip()):
            cur["blocks"].append(("para", " ".join(para.split())))
    return {"name": name, "contact": contact,
            "sections": [s for s in sections if s["blocks"]]}


# ---------------- shared text sanitising ----------------

_SUBS = {
    # only characters NOT representable in cp1252 (the PDF core-font encoding)
    "\u00a0": " ",
    "\u2192": "->", "\u2190": "<-", "\u2194": "<->",
    "\u2021": "**", "\u2020": "*",
}
_SYMBOLS_RE = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]")


def _latin(s: str) -> str:
    for k, v in _SUBS.items():
        s = s.replace(k, v)
    s = _SYMBOLS_RE.sub("", s)
    return s.encode("cp1252", "replace").decode("cp1252")


def _latex_escape(s: str) -> str:
    s = _latin(s)
    s = s.replace("\\", r"\textbackslash{}")
    for ch, rep in (("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                    ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
                    ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")):
        s = s.replace(ch, rep)
    return s


# ---------------- PDF rendering (fpdf2) ----------------

from fpdf import FPDF  # noqa: E402

INK = (28, 28, 28)
MUTED = (85, 85, 85)
RULE = (55, 55, 55)


class _ResumePDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.core_fonts_encoding = "cp1252"
        self.set_auto_page_break(auto=True, margin=16)
        self.set_margins(16, 14, 16)
        self.set_title("Resume")
        self.add_page()
        self.set_fill_color(255, 255, 255)
        self.rect(0, 0, self.w, self.h, style="F")


def _fit(pdf: FPDF, text: str, max_w: float) -> str:
    if pdf.get_string_width(text) <= max_w:
        return text
    while text and pdf.get_string_width(text + "...") > max_w:
        text = text[:-1]
    return text + "..."


def _h_name(pdf, name):
    pdf.set_text_color(*INK)
    pdf.set_font("Helvetica", "B", 23)
    pdf.cell(0, 10.5, _latin(name), align="C", new_x="LMARGIN", new_y="NEXT")


def _h_contact(pdf, contact):
    if not contact:
        pdf.ln(1.5)
        return
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(0, 4.6, _latin(contact), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.5)


def _h_section(pdf, title):
    pdf.ln(2)
    pdf.set_text_color(*INK)
    pdf.set_font("Helvetica", "B", 11.5)
    pdf.cell(0, 5.6, _latin(title), new_x="LMARGIN", new_y="NEXT")
    y = pdf.get_y() - 1.3
    pdf.set_draw_color(*RULE)
    pdf.set_line_width(0.45)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(1.2)


def _entry(pdf, left, right):
    full_w = pdf.w - pdf.l_margin - pdf.r_margin
    right = _latin(right)
    if right:
        pdf.set_font("Helvetica", "I", 9.5)
        rw = min(full_w * 0.45, pdf.get_string_width(right) + 2)
        lw = full_w - rw
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.cell(lw, 5.2, _fit(pdf, _latin(left), lw), align="L")
        pdf.set_font("Helvetica", "I", 9.5)
        pdf.cell(rw, 5.2, right, align="R", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.multi_cell(full_w, 5.2, _latin(left), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.4)


def _body_line(pdf, text, bullet=False):
    pdf.set_text_color(*INK)
    pdf.set_font("Helvetica", "", 10)
    indent = 4.5 if bullet else 0.5
    w = pdf.w - pdf.l_margin - pdf.r_margin - indent
    if bullet:
        pdf.set_x(pdf.l_margin + 1)
        pdf.cell(3.5, 4.7, "\u2022")
    pdf.multi_cell(w, 4.7, _latin(text), new_x="LMARGIN", new_y="NEXT")


def resume_to_pdf(md_text: str) -> bytes:
    data = parse_resume(md_text)
    pdf = _ResumePDF()
    if data["name"]:
        _h_name(pdf, data["name"])
        _h_contact(pdf, data["contact"])
    for i, sec in enumerate(data["sections"]):
        if i or data["name"]:
            _h_section(pdf, sec["title"])
        for block in sec["blocks"]:
            if block[0] == "entry":
                _entry(pdf, block[1], block[2])
            elif block[0] == "bullet":
                _body_line(pdf, block[1], bullet=True)
                pdf.ln(0.4)
            else:
                _body_line(pdf, block[1])
                pdf.ln(0.8)
    return bytes(pdf.output())


# ---------------- LaTeX rendering ----------------

_LATEX_TEMPLATE = r"""%% Resume — compiled with pdflatex (e.g. upload to overleaf.com)
\documentclass[letterpaper,11pt]{article}
\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage[english]{babel}
\usepackage{helvet}
\renewcommand{\familydefault}{\sfdefault}
\input{glyphtounicode}
\pdfgentounicode=1
\pagestyle{empty}
\setlength{\tabcolsep}{0pt}

\newcommand{\namesection}[2]{%
  \begin{center}
    {\fontsize{26}{30}\selectfont\bfseries #1}\\[5pt]
    {\fontsize{9.5}{12}\selectfont #2}
  \end{center}
  \vspace{2pt}
}
\newcommand{\rsection}[1]{%
  \vspace{8pt}\par\noindent{\large\bfseries #1}\par\vspace{2pt}%
  \noindent\rule{\textwidth}{0.8pt}\vspace{3pt}\par
}
\newcommand{\rentry}[2]{%
  \noindent{\bfseries #1}\hfill{\itshape\small #2}\par\vspace{1pt}
}
\newenvironment{rbullets}
  {\begin{itemize}[topsep=2pt,itemsep=1pt,parsep=0pt,leftmargin=4mm]}
  {\end{itemize}}

\begin{document}
"""


def resume_to_latex(md_text: str) -> str:
    data = parse_resume(md_text)
    out = [_LATEX_TEMPLATE]
    if data["name"]:
        contact_parts = [_latex_escape(p.strip()) for p in data["contact"].split("|") if p.strip()]
        contact = " \\textbar{} ".join(contact_parts) if contact_parts else r"\vspace{6pt}"
        out.append(f"\\namesection{{{_latex_escape(data['name'])}}}{{%\n  {contact}%\n}}\n")
    for sec in data["sections"]:
        out.append(f"\\rsection{{{_latex_escape(sec['title'])}}}\n")
        open_env = None
        for block in sec["blocks"]:
            if block[0] == "entry":
                if open_env:
                    out.append("\\end{rbullets}\n")
                    open_env = None
                left = _latex_escape(block[1])
                right = _latex_escape(block[2]) if block[2] else r"\vphantom{}"
                out.append(f"\\rentry{{{left}}}{{{right}}}\n")
            elif block[0] == "bullet":
                if not open_env:
                    out.append("\\begin{rbullets}\n")
                    open_env = True
                out.append(f"  \\item {_latex_escape(block[1])}\n")
            else:
                if open_env:
                    out.append("\\end{rbullets}\n")
                    open_env = None
                out.append(f"\\noindent{{{_latex_escape(block[1])}}}\\par\\vspace{{2pt}}\n")
        if open_env:
            out.append("\\end{rbullets}\n")
    out.append("\\end{document}\n")
    return "".join(out)
