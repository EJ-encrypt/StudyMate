import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.course import Course
from app.models.document import CourseConcept, KnowledgeConcept, LectureDocument
from app.models.user import User
from app.schemas.course import CourseConceptRead, CourseCreate, CourseRead

router = APIRouter(prefix="/courses", tags=["courses"])


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
