import pytest

from app.models.assessment import ItemKind
from app.workers.generation_worker import _exam_split


@pytest.mark.parametrize("count", range(1, 21))
def test_split_allocates_exactly_the_requested_count(count: int) -> None:
    split = _exam_split(count)

    assert sum(portion for _, portion in split) == count
    assert all(portion > 0 for _, portion in split), "a kind must never get zero questions"


def test_short_papers_drop_kinds_rather_than_allocating_nothing() -> None:
    assert _exam_split(1) == [(ItemKind.MCQ, 1)]
    assert _exam_split(2) == [(ItemKind.MCQ, 1), (ItemKind.FILL_BLANK, 1)]


def test_full_paper_mixes_every_kind() -> None:
    kinds = [kind for kind, _ in _exam_split(12)]

    assert kinds == [ItemKind.MCQ, ItemKind.FILL_BLANK, ItemKind.SHORT_ANSWER]
