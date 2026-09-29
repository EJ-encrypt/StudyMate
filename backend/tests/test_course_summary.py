"""The course overview has to describe the whole course, not whichever file
happened to finish first, and must not be rewritten once per file in a batch.
"""

import uuid

import pytest

from app.models.course import Course
from app.models.document import CourseConcept, DocumentStatus, LectureDocument
from app.models.user import User
from app.services import course_summary
from app.services.ai.base import AIProvider


class _CountingProvider(AIProvider):
    """Records how often an overview was actually asked for."""

    def __init__(self) -> None:
        self.calls: list[list[tuple[str, str]]] = []

    @property
    def embedding_model_id(self) -> str:  # pragma: no cover - unused here
        return "test"

    def summarise_course(self, course_name: str, concepts: list[tuple[str, str]]) -> str:
        self.calls.append(list(concepts))
        return f"Covers {len(concepts)} concept(s)."

    def extract_concepts(self, text, max_concepts=10):  # pragma: no cover - unused
        raise NotImplementedError

    def generate_assessment_items(self, source_text, kind, count=10, concepts=None):  # pragma: no cover
        raise NotImplementedError

    def grade_short_answers(self, submissions):  # pragma: no cover - unused
        raise NotImplementedError

    def embed(self, texts):  # pragma: no cover - unused
        raise NotImplementedError

    def are_same_concept(self, pairs):  # pragma: no cover - unused
        raise NotImplementedError


@pytest.fixture()
def provider(monkeypatch) -> _CountingProvider:
    fake = _CountingProvider()
    monkeypatch.setattr(course_summary, "get_ai_provider", lambda: fake)
    return fake


def _course_with_documents(db, statuses: list[DocumentStatus]):
    student = User(
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        full_name="Ama Mensah",
        hashed_password="x",
    )
    db.add(student)
    db.flush()

    course = Course(owner_id=student.id, name="Database Systems", code="CS302")
    db.add(course)
    db.flush()

    for index, status in enumerate(statuses):
        db.add(
            LectureDocument(
                student_id=student.id,
                course_id=course.id,
                filename=f"lecture{index}.pdf",
                storage_path=f"/tmp/lecture{index}.pdf",
                status=status,
            )
        )
        db.add(
            CourseConcept(
                student_id=student.id,
                course_id=course.id,
                name=f"Concept {index}",
                summary=f"What lecture {index} was about.",
                embedding=[0.1, 0.2],
                embedding_model="test",
            )
        )
    db.commit()
    return student, course


def test_waits_for_the_rest_of_a_batch(db, provider):
    """One file done, four still processing: writing now would describe one
    lecture and then mark the overview as covering all five."""
    student, course = _course_with_documents(
        db,
        [DocumentStatus.COMPLETED] + [DocumentStatus.PROCESSING] * 4,
    )

    course_summary.refresh_course_summary(db, student.id, course.id)

    assert provider.calls == [], "should not summarise while files are still processing"
    db.refresh(course)
    assert course.summary is None


def test_summarises_every_file_once_the_batch_lands(db, provider):
    student, course = _course_with_documents(db, [DocumentStatus.COMPLETED] * 5)

    course_summary.refresh_course_summary(db, student.id, course.id)

    assert len(provider.calls) == 1
    # The whole batch, not just the first file.
    assert len(provider.calls[0]) == 5
    db.refresh(course)
    assert course.documents_at_summary == 5


def test_does_not_rewrite_when_nothing_changed(db, provider):
    student, course = _course_with_documents(db, [DocumentStatus.COMPLETED] * 2)

    course_summary.refresh_course_summary(db, student.id, course.id)
    course_summary.refresh_course_summary(db, student.id, course.id)

    assert len(provider.calls) == 1, "an unchanged course should not spend quota again"


def test_failed_documents_do_not_hold_the_overview_back(db, provider):
    """A file that failed will never complete; the rest should still be described."""
    student, course = _course_with_documents(
        db,
        [DocumentStatus.COMPLETED, DocumentStatus.COMPLETED, DocumentStatus.FAILED],
    )

    course_summary.refresh_course_summary(db, student.id, course.id)

    assert len(provider.calls) == 1
    db.refresh(course)
    assert course.documents_at_summary == 2
