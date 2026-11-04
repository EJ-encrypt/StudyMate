"""Spotting maths-heavy material, which needs different handling.

Two things go wrong with quantitative material treated like any other. Text
extraction mangles it: pdfplumber turns typeset equations into runs of loose
symbols, or "(cid:12)" placeholders where a maths font has no text mapping.
And recall questions miss the point: a calculus student needs to practise
differentiating, not to define a derivative. So a quantitative document is
transcribed by the AI with its equations as LaTeX, and its questions include
worked problems.

Detection is deliberately generous. Treating a discursive course as
quantitative costs a slower first read and some LaTeX in its summaries;
missing a maths course costs every quiz in it.
"""

import re

_NAME_WORDS = re.compile(
    r"calculus|algebra|statistic|probabilit|math|econom|physics|accounting|financ|"
    r"quantitative|numerical|mechanics|thermodynamic|differential|integral|"
    r"trigonometr|geometry|actuarial|operations research|signals|circuits|"
    r"electromagnet|kinematics|optimi[sz]ation|stochastic|regression",
    re.IGNORECASE,
)
_CODE_PREFIXES = re.compile(
    r"^\s*(MATH|MTH|MAT|STAT|STA|ECON|ECN|ECO|PHYS|PHY|ACCT|ACC|FIN|FINC|QM|EENG|MECH)\s*\d",
    re.IGNORECASE,
)
# No ASCII hyphen: prose is full of them ("well-known", "real-time").
_MATH_SYMBOLS = re.compile(r"[=+−×÷^√∑∏∫∂≤≥≠≈±∞πθλμσαβγδΔ∈∀∃→⇒]")
_LATEX = re.compile(r"\\(frac|sum|int|sqrt|lim|partial|alpha|beta|sigma|mu)\b|\$[^$\n]{1,80}\$")
_GARBLED = re.compile(r"\(cid:\d+\)")

# Per thousand characters. Measured on extracted text: prose lecture notes
# sit around 2 to 5, worked-example slides for calculus and statistics 25+.
_SYMBOL_DENSITY = 15


def is_quantitative_course(code: str, name: str) -> bool:
    return bool(_NAME_WORDS.search(name or "") or _CODE_PREFIXES.match(code or ""))


def looks_mathematical(text: str) -> bool:
    if not text:
        return False
    if len(_GARBLED.findall(text)) >= 5 or len(_LATEX.findall(text)) >= 5:
        return True
    symbols = len(_MATH_SYMBOLS.findall(text))
    return symbols * 1000 / max(len(text), 1) >= _SYMBOL_DENSITY


def has_garbled_text(text: str) -> bool:
    """Whether extraction left font placeholders instead of characters."""
    return len(_GARBLED.findall(text)) >= 5
