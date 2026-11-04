import re
import unicodedata

from app.models.assessment import ItemKind

_PUNCTUATION = re.compile(r"[^\w\s]")
_WHITESPACE = re.compile(r"\s+")
_ARTICLES = {"a", "an", "the"}


def normalize(text: str) -> str:
    """Case-, accent-, punctuation- and article-insensitive comparison form."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    cleaned = _PUNCTUATION.sub(" ", stripped.lower())
    words = [word for word in _WHITESPACE.split(cleaned) if word and word not in _ARTICLES]
    return " ".join(words)


# Kinds an exact comparison can mark. Short answers are free text, so they go
# to the AI provider's judge instead (PROJECT_PLAN.md open item, settled as
# LLM-as-judge); flashcards are self-reviewed and never machine-marked.
DETERMINISTIC_KINDS = (ItemKind.MCQ, ItemKind.FILL_BLANK)


_FRACTION = re.compile(r"^(-?\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)$")
_LATEX_FRACTION = re.compile(r"^(-?)\\d?frac\{(-?[\d.]+)\}\{([\d.]+)\}$")
_NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")
_THOUSANDS = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$")
# Relative, so 3.14 matches pi's 3.14159 and 0.33 matches a third, while
# 3.2 does not match 3.14.
_TOLERANCE = 0.006


def as_number(text: str) -> float | None:
    """Read an answer as a number, if it is one: 0.25, 1/4, \\frac{1}{4}, 25%, x = -3."""
    cleaned = text.strip().strip("$").strip()
    if "=" in cleaned:
        # "x = 3": the value is what follows the last equals sign.
        cleaned = cleaned.rsplit("=", 1)[1].strip()
    cleaned = cleaned.replace("−", "-").replace(" ", "").rstrip(".")
    if _THOUSANDS.match(cleaned):
        cleaned = cleaned.replace(",", "")
    percent = cleaned.endswith("%")
    cleaned = cleaned.rstrip("%")

    value: float | None = None
    if _NUMBER.match(cleaned):
        value = float(cleaned)
    elif match := _FRACTION.match(cleaned):
        denominator = float(match.group(2))
        value = float(match.group(1)) / denominator if denominator else None
    elif match := _LATEX_FRACTION.match(cleaned):
        denominator = float(match.group(3))
        sign = -1 if match.group(1) else 1
        value = sign * float(match.group(2)) / denominator if denominator else None
    if value is None:
        return None
    return value / 100 if percent else value


def _same_number(expected: float, response: float) -> bool:
    if expected == 0:
        return abs(response) < 1e-9
    return abs(response - expected) <= abs(expected) * _TOLERANCE


def is_correct(kind: ItemKind, expected: str, response: str) -> bool:
    """Grade one answer that can be marked by comparison alone.

    A numeric answer is compared as a number, so "0.25", "1/4" and "25%"
    all count. normalize() alone would also drop the minus sign, marking
    "-3" correct for an answer of 3.
    """
    if kind not in DETERMINISTIC_KINDS:
        return False
    expected_number, response_number = as_number(expected), as_number(response)
    if expected_number is not None:
        return response_number is not None and _same_number(expected_number, response_number)
    return bool(normalize(response)) and normalize(response) == normalize(expected)
