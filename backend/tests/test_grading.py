import pytest

from app.models.assessment import ItemKind
from app.services.grading import is_correct, normalize


@pytest.mark.parametrize(
    ("expected", "response"),
    [
        ("Deadlock", "deadlock"),
        ("Deadlock", "  Deadlock  "),
        ("Page table", "page  table"),
        ("Mutual exclusion", "Mutual exclusion."),
        ("the page table", "page table"),
        ("Résumé", "resume"),
    ],
)
def test_accepts_equivalent_answers(expected: str, response: str) -> None:
    assert is_correct(ItemKind.FILL_BLANK, expected, response)


@pytest.mark.parametrize(
    ("expected", "response"),
    [
        ("Deadlock", "livelock"),
        ("Page table", "page fault"),
        ("Deadlock", ""),
        ("Deadlock", "   "),
        ("Mutual exclusion", "exclusion"),
    ],
)
def test_rejects_wrong_answers(expected: str, response: str) -> None:
    assert not is_correct(ItemKind.FILL_BLANK, expected, response)


def test_flashcards_are_never_auto_marked() -> None:
    assert not is_correct(ItemKind.FLASHCARD, "Deadlock", "Deadlock")


def test_normalize_collapses_noise() -> None:
    assert normalize("  The   Page-Table!! ") == "page table"
