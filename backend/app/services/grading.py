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


def is_correct(kind: ItemKind, expected: str, response: str) -> bool:
    """Grade one answer that can be marked by comparison alone."""
    if kind not in DETERMINISTIC_KINDS:
        return False
    return bool(normalize(response)) and normalize(response) == normalize(expected)
