"""Tests for cumulative knowledge-base merging.

Embeddings are stubbed so the bands are exercised deterministically: real
similarity scores were measured separately to choose the thresholds, and the
overlap they revealed is why an ambiguous band exists at all.
"""

import uuid
from contextlib import nullcontext
from unittest.mock import MagicMock, patch

import pytest

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.document import CourseConcept, DocumentStatus, KnowledgeConcept, LectureDocument
from app.models.user import User
from app.services.knowledge_base import (
    AUTO_MERGE_SIMILARITY,
    CANDIDATE_SIMILARITY,
    cosine_similarity,
    sync_document_concepts,
)


def _student_course_document(db: Session) -> tuple[User, Course, LectureDocument]:
    user = User(
        email=f"kb-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="x",
        full_name="KB Student",
    )
    db.add(user)
    db.flush()
    course = Course(name="Databases", code="CS302", owner_id=user.id)
    db.add(course)
    db.flush()
    document = LectureDocument(
        student_id=user.id,
        course_id=course.id,
        filename="week1.pdf",
        storage_path="storage/week1.pdf",
        status=DocumentStatus.COMPLETED,
    )
    db.add(document)
    db.commit()
    return user, course, document


def _add_concepts(db: Session, document: LectureDocument, pairs: list[tuple[str, str]]) -> None:
    for name, summary in pairs:
        db.add(
            KnowledgeConcept(
                document_id=document.id,
                student_id=document.student_id,
                course_id=document.course_id,
                name=name,
                summary=summary,
            )
        )
    db.commit()


EMBEDDING_MODEL = "test:embedding:8"


def _provider(
    vectors: list[list[float]],
    verdicts: list[bool] | None = None,
    embedding_model: str = EMBEDDING_MODEL,
) -> MagicMock:
    provider = MagicMock()
    # embed_tagged reports which model produced the vectors, because vectors
    # from different models must never be compared.
    provider.embed_tagged.return_value = (vectors, embedding_model)
    provider.are_same_concept.return_value = verdicts or []
    return provider


def test_cosine_similarity_basics() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_first_document_creates_one_concept_each(client, db: Session) -> None:
    _, course, document = _student_course_document(db)
    _add_concepts(db, document, [("Deadlock", "Circular waiting."), ("Paging", "Fixed-size frames.")])

    provider = _provider([[1.0, 0.0], [0.0, 1.0]])
    with patch("app.services.knowledge_base.get_ai_provider", return_value=provider):
        sync_document_concepts(db, document.id)

    canonical = db.query(CourseConcept).filter(CourseConcept.course_id == course.id).all()
    assert sorted(c.name for c in canonical) == ["Deadlock", "Paging"]
    assert all(c.course_concept_id is not None for c in db.query(KnowledgeConcept).all())


def test_high_similarity_merges_without_asking_the_model(client, db: Session) -> None:
    _, course, first = _student_course_document(db)
    _add_concepts(db, first, [("Functional dependency", "X determines Y.")])

    provider = _provider([[1.0, 0.0]])
    with patch("app.services.knowledge_base.get_ai_provider", return_value=provider):
        sync_document_concepts(db, first.id)

    second = LectureDocument(
        student_id=first.student_id,
        course_id=course.id,
        filename="week2.pdf",
        storage_path="storage/week2.pdf",
        status=DocumentStatus.COMPLETED,
    )
    db.add(second)
    db.commit()
    _add_concepts(db, second, [("Functional dependencies", "Each X maps to one Y.")])

    # Identical vector -> similarity 1.0, comfortably above the auto-merge band.
    provider = _provider([[1.0, 0.0]])
    with patch("app.services.knowledge_base.get_ai_provider", return_value=provider):
        sync_document_concepts(db, second.id)

    canonical = db.query(CourseConcept).filter(CourseConcept.course_id == course.id).all()
    assert len(canonical) == 1, "the same concept from two lectures must collapse to one entry"
    provider.are_same_concept.assert_not_called()
    assert db.query(KnowledgeConcept).filter(
        KnowledgeConcept.course_concept_id == canonical[0].id
    ).count() == 2


def test_low_similarity_creates_a_separate_concept(client, db: Session) -> None:
    _, course, first = _student_course_document(db)
    _add_concepts(db, first, [("Deadlock", "Circular waiting.")])
    provider = _provider([[1.0, 0.0]])
    with patch("app.services.knowledge_base.get_ai_provider", return_value=provider):
        sync_document_concepts(db, first.id)

    second = LectureDocument(
        student_id=first.student_id,
        course_id=course.id,
        filename="week2.pdf",
        storage_path="storage/week2.pdf",
        status=DocumentStatus.COMPLETED,
    )
    db.add(second)
    db.commit()
    _add_concepts(db, second, [("Paging", "Fixed-size frames.")])

    provider = _provider([[0.0, 1.0]])
    with patch("app.services.knowledge_base.get_ai_provider", return_value=provider):
        sync_document_concepts(db, second.id)

    assert db.query(CourseConcept).filter(CourseConcept.course_id == course.id).count() == 2
    provider.are_same_concept.assert_not_called()


def _ambiguous_vector() -> list[float]:
    """A vector whose similarity to [1, 0] lands inside the ambiguous band."""
    import math

    target = (AUTO_MERGE_SIMILARITY + CANDIDATE_SIMILARITY) / 2
    angle = math.acos(target)
    return [math.cos(angle), math.sin(angle)]


def test_ambiguous_band_merges_when_the_model_says_same(client, db: Session) -> None:
    _, course, first = _student_course_document(db)
    _add_concepts(db, first, [("Translation Lookaside Buffer", "Caches translations.")])
    with patch("app.services.knowledge_base.get_ai_provider", return_value=_provider([[1.0, 0.0]])):
        sync_document_concepts(db, first.id)

    second = LectureDocument(
        student_id=first.student_id,
        course_id=course.id,
        filename="week2.pdf",
        storage_path="storage/week2.pdf",
        status=DocumentStatus.COMPLETED,
    )
    db.add(second)
    db.commit()
    _add_concepts(db, second, [("TLB", "A cache of recent translations.")])

    provider = _provider([_ambiguous_vector()], verdicts=[True])
    with patch("app.services.knowledge_base.get_ai_provider", return_value=provider):
        sync_document_concepts(db, second.id)

    provider.are_same_concept.assert_called_once()
    assert db.query(CourseConcept).filter(CourseConcept.course_id == course.id).count() == 1


def test_ambiguous_band_stays_separate_when_the_model_says_different(client, db: Session) -> None:
    _, course, first = _student_course_document(db)
    _add_concepts(db, first, [("Second Normal Form", "No partial dependency.")])
    with patch("app.services.knowledge_base.get_ai_provider", return_value=_provider([[1.0, 0.0]])):
        sync_document_concepts(db, first.id)

    second = LectureDocument(
        student_id=first.student_id,
        course_id=course.id,
        filename="week2.pdf",
        storage_path="storage/week2.pdf",
        status=DocumentStatus.COMPLETED,
    )
    db.add(second)
    db.commit()
    _add_concepts(db, second, [("Third Normal Form", "No transitive dependency.")])

    provider = _provider([_ambiguous_vector()], verdicts=[False])
    with patch("app.services.knowledge_base.get_ai_provider", return_value=provider):
        sync_document_concepts(db, second.id)

    names = sorted(
        c.name for c in db.query(CourseConcept).filter(CourseConcept.course_id == course.id).all()
    )
    assert names == ["Second Normal Form", "Third Normal Form"], "distinct normal forms must not merge"


def test_adjudication_failure_leaves_concepts_unmerged(client, db: Session) -> None:
    _, course, first = _student_course_document(db)
    _add_concepts(db, first, [("Second Normal Form", "No partial dependency.")])
    with patch("app.services.knowledge_base.get_ai_provider", return_value=_provider([[1.0, 0.0]])):
        sync_document_concepts(db, first.id)

    second = LectureDocument(
        student_id=first.student_id,
        course_id=course.id,
        filename="week2.pdf",
        storage_path="storage/week2.pdf",
        status=DocumentStatus.COMPLETED,
    )
    db.add(second)
    db.commit()
    _add_concepts(db, second, [("Third Normal Form", "No transitive dependency.")])

    provider = _provider([_ambiguous_vector()])
    provider.are_same_concept.side_effect = RuntimeError("model down")
    with patch("app.services.knowledge_base.get_ai_provider", return_value=provider):
        sync_document_concepts(db, second.id)

    # Erring towards a duplicate, never towards losing a concept.
    assert db.query(CourseConcept).filter(CourseConcept.course_id == course.id).count() == 2


def test_duplicate_names_within_one_document_stay_distinct(client, db: Session) -> None:
    _, course, document = _student_course_document(db)
    _add_concepts(
        db,
        document,
        [("Anomaly", "An insertion anomaly."), ("Anomaly", "A deletion anomaly.")],
    )

    # Dissimilar vectors, so nothing merges and both need the same name.
    provider = _provider([[1.0, 0.0], [0.0, 1.0]])
    with patch("app.services.knowledge_base.get_ai_provider", return_value=provider):
        sync_document_concepts(db, document.id)

    names = sorted(
        c.name for c in db.query(CourseConcept).filter(CourseConcept.course_id == course.id).all()
    )
    assert names == ["Anomaly", "Anomaly (2)"]


def test_sync_is_idempotent(client, db: Session) -> None:
    _, course, document = _student_course_document(db)
    _add_concepts(db, document, [("Deadlock", "Circular waiting.")])

    provider = _provider([[1.0, 0.0]])
    with patch("app.services.knowledge_base.get_ai_provider", return_value=provider):
        sync_document_concepts(db, document.id)
        sync_document_concepts(db, document.id)

    assert db.query(CourseConcept).filter(CourseConcept.course_id == course.id).count() == 1


def test_document_is_only_completed_after_the_knowledge_base_is_updated(client, db: Session) -> None:
    """A document reporting "completed" must already be folded into the course KB.

    Syncing after the status commit let a student see "Done" while the
    knowledge base was still mid-merge.
    """
    from app.models.document import DocumentStatus
    from app.services.ai.base import ExtractedConcept
    from app.workers import extraction_worker

    _, course, document = _student_course_document(db)
    document.status = DocumentStatus.PENDING
    db.commit()

    statuses_when_synced: list[DocumentStatus] = []

    def record_status(session, document_id):
        statuses_when_synced.append(session.get(LectureDocument, document_id).status)

    provider = MagicMock()
    provider.extract_concepts.return_value = [ExtractedConcept(name="Deadlock", summary="Waiting.")]

    with patch.object(extraction_worker, "SessionLocal", return_value=db), patch.object(
        extraction_worker, "local_copy", return_value=nullcontext("lecture.txt")
    ), patch.object(
        extraction_worker, "extract_text", return_value="lecture text"
    ), patch.object(extraction_worker, "get_ai_provider", return_value=provider), patch.object(
        extraction_worker, "sync_document_concepts", side_effect=record_status
    ), patch.object(db, "close"):
        extraction_worker.process_document(str(document.id))

    assert statuses_when_synced == [DocumentStatus.PROCESSING], (
        "the knowledge base must be synced before the document reports completed"
    )
    db.refresh(document)
    assert document.status is DocumentStatus.COMPLETED


def test_vectors_from_a_different_embedding_model_are_never_compared(client, db: Session) -> None:
    """A fallback embedding must not be compared against the primary's.

    Similarity across two embedding models is meaningless, so a concept
    embedded by a fallback provider is left as a new entry - a duplicate,
    which is recoverable - rather than merged on a nonsense score.
    """
    _, course, first = _student_course_document(db)
    _add_concepts(db, first, [("Functional dependency", "X determines Y.")])
    with patch("app.services.knowledge_base.get_ai_provider", return_value=_provider([[1.0, 0.0]])):
        sync_document_concepts(db, first.id)

    second = LectureDocument(
        student_id=first.student_id,
        course_id=course.id,
        filename="week2.pdf",
        storage_path="storage/week2.pdf",
        status=DocumentStatus.COMPLETED,
    )
    db.add(second)
    db.commit()
    _add_concepts(db, second, [("Functional dependencies", "Each X maps to one Y.")])

    # Identical vector, so similarity would be 1.0 and it would normally merge -
    # but it came from a different embedding model.
    other_model = _provider([[1.0, 0.0]], embedding_model="other:embedding:8")
    with patch("app.services.knowledge_base.get_ai_provider", return_value=other_model):
        sync_document_concepts(db, second.id)

    canonical = db.query(CourseConcept).filter(CourseConcept.course_id == course.id).all()
    assert len(canonical) == 2, "a cross-model match must not merge"
    other_model.are_same_concept.assert_not_called()
    assert {c.embedding_model for c in canonical} == {EMBEDDING_MODEL, "other:embedding:8"}


def test_embedding_model_is_recorded_on_every_concept(client, db: Session) -> None:
    _, course, document = _student_course_document(db)
    _add_concepts(db, document, [("Deadlock", "Circular waiting.")])

    with patch("app.services.knowledge_base.get_ai_provider", return_value=_provider([[1.0, 0.0]])):
        sync_document_concepts(db, document.id)

    concept = db.query(CourseConcept).filter(CourseConcept.course_id == course.id).one()
    assert concept.embedding_model == EMBEDDING_MODEL


def test_too_few_embeddings_is_an_error_not_a_silent_drop(client, db: Session) -> None:
    """Regression: the embedding API once returned one vector for a whole batch.

    zip() then quietly linked only the first concept and dropped the rest from
    the knowledge base on every upload. A count mismatch must now fail loudly.
    """
    _, _, document = _student_course_document(db)
    _add_concepts(db, document, [("Deadlock", "Circular waiting."), ("Paging", "Fixed-size frames.")])

    provider = _provider([[1.0, 0.0]])
    with patch("app.services.knowledge_base.get_ai_provider", return_value=provider):
        with pytest.raises(ValueError, match="Expected 2 embeddings, got 1"):
            sync_document_concepts(db, document.id)


def test_a_finished_document_queues_the_course_summary_as_its_own_job(client, db: Session) -> None:
    """Kept out of the extraction run so one slow reply cannot breach the time limit."""
    from app.models.job import Job
    from app.services.ai.base import ExtractedConcept
    from app.workers import extraction_worker

    _, course, document = _student_course_document(db)
    provider = MagicMock()
    provider.extract_concepts.return_value = [ExtractedConcept(name="Deadlock", summary="Waiting.")]

    with patch.object(extraction_worker, "SessionLocal", return_value=db), patch.object(
        extraction_worker, "local_copy", return_value=nullcontext("lecture.txt")
    ), patch.object(extraction_worker, "extract_text", return_value="lecture text"), patch.object(
        extraction_worker, "get_ai_provider", return_value=provider
    ), patch.object(extraction_worker, "sync_document_concepts"), patch.object(db, "close"):
        extraction_worker.process_document(str(document.id))

    jobs = db.query(Job).all()
    assert [(j.kind, j.payload["course_id"]) for j in jobs] == [("refresh_course_summary", str(course.id))]
