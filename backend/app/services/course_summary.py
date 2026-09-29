"""Keep a course's overview in step with the material behind it."""

import logging
import uuid

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.document import CourseConcept, LectureDocument
from app.services.ai import get_ai_provider

logger = logging.getLogger(__name__)

# Enough to characterise a course without sending the whole knowledge base.
MAX_CONCEPTS = 40


def refresh_course_summary(db: Session, student_id: uuid.UUID, course_id: uuid.UUID) -> None:
    """Rewrite the overview if new material has landed since it was written.

    Skipped when the document count is unchanged, so repeated syncs do not
    spend quota rewriting the same paragraph.
    """
    course = db.get(Course, course_id)
    if course is None:
        return

    document_count = (
        db.query(LectureDocument).filter(LectureDocument.course_id == course_id).count()
    )
    if course.summary is not None and course.documents_at_summary == document_count:
        return

    concepts = (
        db.query(CourseConcept)
        .filter(CourseConcept.student_id == student_id, CourseConcept.course_id == course_id)
        .order_by(CourseConcept.created_at)
        .limit(MAX_CONCEPTS)
        .all()
    )
    if not concepts:
        return

    course.summary = get_ai_provider().summarise_course(
        f"{course.code} {course.name}",
        [(c.name, c.summary) for c in concepts],
    )
    course.documents_at_summary = document_count
    db.commit()
