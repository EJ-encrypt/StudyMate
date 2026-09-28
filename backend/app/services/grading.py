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


def is_correct(kind: ItemKind, expected: str, response: str) -> bool:
    """Grade one answer.

    Flashcards are self-reviewed rather than marked, so they never count
    towards a score; callers filter them out before building an attempt.
    """
    if kind is ItemKind.FLASHCARD:
        return False
    return bool(normalize(response)) and normalize(response) == normalize(expected)


GRADED_KINDS = (ItemKind.MCQ, ItemKind.FILL_BLANK)
