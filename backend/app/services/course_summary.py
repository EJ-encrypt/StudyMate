"""Keep a course's overview in step with the material behind it."""

import logging
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.document import CourseConcept, DocumentStatus, LectureDocument
from app.services.ai import get_ai_provider

logger = logging.getLogger(__name__)

# Enough to characterise a course without sending the whole knowledge base.
MAX_CONCEPTS = 40


def refresh_course_summary(db: Session, student_id: uuid.UUID, course_id: uuid.UUID) -> None:
    """Rewrite the overview if new material has landed since it was written.

    Counts only documents that finished processing. Counting every row instead
    breaks a multi-file upload: all the rows exist the moment the files are
    accepted, so the first document to finish would write a summary of itself,
    record it as covering the whole batch, and every later document would then
    skip as up to date -- leaving an overview that silently described one file
    out of five.

    While other files in the batch are still processing this returns early, so
    a batch of five costs one summary call at the end rather than five, four of
    them immediately superseded.
    """
    course = db.get(Course, course_id)
    if course is None:
        return

    counts = dict(
        db.query(LectureDocument.status, func.count())
        .filter(LectureDocument.course_id == course_id)
        .group_by(LectureDocument.status)
        .all()
    )
    still_working = counts.get(DocumentStatus.PENDING, 0) + counts.get(
        DocumentStatus.PROCESSING, 0
    )
    if still_working:
        return

    document_count = counts.get(DocumentStatus.COMPLETED, 0)
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
