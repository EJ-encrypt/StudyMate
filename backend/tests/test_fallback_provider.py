from unittest.mock import MagicMock

import pytest

from app.services.ai.base import ExtractedConcept, ItemKind, ShortAnswerGrade, ShortAnswerSubmission
from app.services.ai.fallback import FallbackProvider


def _provider(name: str, *, embedding_model: str | None = None) -> MagicMock:
    provider = MagicMock()
    provider.__class__.__name__ = name
    provider.embedding_model_id = embedding_model or f"{name}:embed"
    return provider


CONCEPTS = [ExtractedConcept(name="Deadlock", summary="Circular waiting.")]


def test_requires_at_least_one_provider() -> None:
    with pytest.raises(ValueError):
        FallbackProvider([])


def test_uses_the_first_provider_when_it_works() -> None:
    first, second = _provider("First"), _provider("Second")
    first.extract_concepts.return_value = CONCEPTS

    result = FallbackProvider([first, second]).extract_concepts("text")

    assert result == CONCEPTS
    second.extract_concepts.assert_not_called()


def test_falls_through_to_the_next_provider_on_failure() -> None:
    first, second = _provider("First"), _provider("Second")
    first.extract_concepts.side_effect = RuntimeError("rate limited")
    second.extract_concepts.return_value = CONCEPTS

    result = FallbackProvider([first, second]).extract_concepts("text")

    assert result == CONCEPTS
    first.extract_concepts.assert_called_once()
    second.extract_concepts.assert_called_once()


def test_raises_the_last_error_when_every_provider_fails() -> None:
    first, second = _provider("First"), _provider("Second")
    first.extract_concepts.side_effect = RuntimeError("first down")
    second.extract_concepts.side_effect = RuntimeError("second down")

    with pytest.raises(RuntimeError, match="second down"):
        FallbackProvider([first, second]).extract_concepts("text")


def test_generation_falls_through() -> None:
    first, second = _provider("First"), _provider("Second")
    first.generate_assessment_items.side_effect = RuntimeError("busy")
    second.generate_assessment_items.return_value = []

    FallbackProvider([first, second]).generate_assessment_items("text", ItemKind.MCQ, 5, ["A"])

    # Arguments must survive the hand-off unchanged, or the fallback would
    # quietly produce a different quiz from the one that was asked for.
    second.generate_assessment_items.assert_called_once_with("text", ItemKind.MCQ, 5, ["A"], quantitative=False, avoid=None)


def test_marking_falls_through() -> None:
    first, second = _provider("First"), _provider("Second")
    submissions = [
        ShortAnswerSubmission(
            reference="r1", question="Q", expected_answer="A", student_answer="B"
        )
    ]
    grades = [ShortAnswerGrade(reference="r1", is_correct=True, feedback="ok")]
    first.grade_short_answers.side_effect = RuntimeError("busy")
    second.grade_short_answers.return_value = grades

    assert FallbackProvider([first, second]).grade_short_answers(submissions) == grades


def test_concept_adjudication_falls_through() -> None:
    first, second = _provider("First"), _provider("Second")
    first.are_same_concept.side_effect = RuntimeError("busy")
    second.are_same_concept.return_value = [True]

    assert FallbackProvider([first, second]).are_same_concept([("a", "b")]) == [True]


def test_plain_embed_is_refused() -> None:
    """Embeddings must not be handed out without saying which model made them."""
    chain = FallbackProvider([_provider("First")])

    with pytest.raises(NotImplementedError, match="embed_tagged"):
        chain.embed(["text"])


def test_embed_tagged_reports_the_primary_model_when_it_works() -> None:
    first = _provider("First", embedding_model="first:embed")
    second = _provider("Second", embedding_model="second:embed")
    first.embed.return_value = [[1.0, 0.0]]

    vectors, model = FallbackProvider([first, second]).embed_tagged(["text"])

    assert vectors == [[1.0, 0.0]]
    assert model == "first:embed"
    second.embed.assert_not_called()


def test_embed_tagged_reports_the_fallback_model_when_it_is_used() -> None:
    """The whole point: a fallback vector must not be labelled as the primary's.

    Similarity between vectors from two different embedding models is
    meaningless, so mislabelling one would corrupt concept de-duplication
    rather than merely degrade it.
    """
    first = _provider("First", embedding_model="first:embed")
    second = _provider("Second", embedding_model="second:embed")
    first.embed.side_effect = RuntimeError("quota")
    second.embed.return_value = [[0.0, 1.0]]

    vectors, model = FallbackProvider([first, second]).embed_tagged(["text"])

    assert vectors == [[0.0, 1.0]]
    assert model == "second:embed", "a fallback vector must carry the fallback's model id"


def test_embedding_model_id_reports_the_primary() -> None:
    first = _provider("First", embedding_model="first:embed")
    second = _provider("Second", embedding_model="second:embed")

    assert FallbackProvider([first, second]).embedding_model_id == "first:embed"


def test_a_single_provider_chain_still_works() -> None:
    only = _provider("Only")
    only.extract_concepts.return_value = CONCEPTS

    assert FallbackProvider([only]).extract_concepts("text") == CONCEPTS
