import logging
import re
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.course import Course
from app.models.document import CourseConcept, KnowledgeConcept, LectureDocument
from app.models.user import User
from app.schemas.course import (
    CourseBulkCreate,
    CourseConceptRead,
    CourseCreate,
    CourseProposal,
    CourseRead,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/courses", tags=["courses"])


def _code_key(code: str) -> str:
    """Comparison form of a course code: "MATH 223", "math223" and "MATH-223" match."""
    return re.sub(r"[^a-z0-9]", "", code.lower())


@router.post("", response_model=CourseRead, status_code=201)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Course:
    course = Course(
        name=payload.name,
        code=payload.code,
        owner_id=current_user.id,
        # Fall back to the student's current level/semester, then to first year,
        # so a course is always placed somewhere in My Courses.
        level=payload.level or current_user.level or 100,
        semester=payload.semester or current_user.semester or 1,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return _with_counts(db, [course])[0]


@router.post("/read", response_model=list[CourseProposal])
async def read_course_list(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CourseProposal]:
    """Read an uploaded course list into proposed courses.

    Nothing is created here: a registration slip or handbook page usually
    lists more than the student takes, so they tick which ones to add.
    """
    from app.services.ai import get_ai_provider
    from app.services.failures import describe
    from app.services.uploads import read_upload

    data, mime_type, extra_text = await read_upload(file, "your course list")
    try:
        entries = get_ai_provider().read_course_list(data, mime_type, extra_text)
    except Exception as exc:  # noqa: BLE001 -- reported to the student
        logger.warning("Course list reading failed: %s", exc)
        message, _ = describe(exc)
        raise HTTPException(status_code=502, detail=message)

    existing = {
        _code_key(code)
        for (code,) in db.query(Course.code).filter(Course.owner_id == current_user.id)
    }
    proposals: list[CourseProposal] = []
    seen: set[str] = set()
    for entry in entries:
        name = entry.name.strip()[:255]
        code = entry.code.strip()[:50]
        if not name:
            continue
        key = _code_key(code) or _code_key(name)
        if key in seen:
            continue
        seen.add(key)
        proposals.append(
            CourseProposal(
                code=code,
                name=name,
                level=entry.level if 100 <= entry.level <= 900 else None,
                semester=entry.semester if entry.semester in (1, 2) else None,
                already_added=bool(code) and _code_key(code) in existing,
            )
        )
    if not proposals:
        raise HTTPException(
            status_code=422,
            detail="No courses could be read from that file. Try a clearer photo, or add them by hand.",
        )
    return proposals


@router.post("/bulk", response_model=list[CourseRead], status_code=201)
def create_courses(
    payload: CourseBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CourseRead]:
    """Add the courses ticked after an import, skipping any already added."""
    existing = {
        _code_key(code)
        for (code,) in db.query(Course.code).filter(Course.owner_id == current_user.id)
    }
    created: list[Course] = []
    for entry in payload.courses:
        key = _code_key(entry.code)
        if key in existing:
            continue
        existing.add(key)
        created.append(
            Course(
                name=entry.name,
                code=entry.code,
                owner_id=current_user.id,
                level=entry.level or current_user.level or 100,
                semester=entry.semester or current_user.semester or 1,
            )
        )
    db.add_all(created)
    db.commit()
    return _with_counts(db, created)


@router.get("", response_model=list[CourseRead])
def list_my_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CourseRead]:
    courses = (
        db.query(Course)
        .filter(Course.owner_id == current_user.id)
        .order_by(Course.level, Course.semester, Course.created_at)
        .all()
    )
    return _with_counts(db, courses)


def _with_counts(db: Session, courses: list[Course]) -> list[CourseRead]:
    """Attach how many documents each course holds.

    My Courses shows this so a student can see at a glance which courses have
    material and which are still empty.
    """
    if not courses:
        return []

    counts = dict(
        db.query(LectureDocument.course_id, func.count(LectureDocument.id))
        .filter(LectureDocument.course_id.in_([c.id for c in courses]))
        .group_by(LectureDocument.course_id)
        .all()
    )
    return [
        CourseRead(
            id=course.id,
            name=course.name,
            code=course.code,
            owner_id=course.owner_id,
            level=course.level,
            semester=course.semester,
            summary=course.summary,
            document_count=counts.get(course.id, 0),
        )
        for course in courses
    ]


@router.get("/{course_id}/concepts", response_model=list[CourseConceptRead])
def list_course_concepts(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CourseConceptRead]:
    """The student's cumulative knowledge base for one course."""
    course = db.get(Course, course_id)
    if course is None or course.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Course not found")

    rows = (
        db.query(
            CourseConcept,
            func.count(func.distinct(KnowledgeConcept.document_id)).label("document_count"),
        )
        .outerjoin(KnowledgeConcept, KnowledgeConcept.course_concept_id == CourseConcept.id)
        .filter(
            CourseConcept.student_id == current_user.id,
            CourseConcept.course_id == course_id,
        )
        .group_by(CourseConcept.id)
        .order_by(CourseConcept.created_at)
        .all()
    )

    return [
        CourseConceptRead(
            id=concept.id,
            name=concept.name,
            summary=concept.summary,
            document_count=document_count,
        )
        for concept, document_count in rows
    ]
