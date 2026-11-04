import hashlib
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.course import Course
from app.models.document import CourseConcept, KnowledgeConcept, LectureDocument
from app.models.mastery import ConceptMastery, TopicExplanation
from app.models.user import User
from app.schemas.coach import (
    CoachSummary,
    ConceptDetailRead,
    ConceptProgressRead,
    ConceptSourceRead,
    RevisionTopicRead,
    TopicExplainRequest,
    TopicExplanationRead,
)
from app.services import limits
from app.services.coaching import ConceptProgress, course_progress, recommend, revision_topics
from app.services.sources import Source, concept_sources

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/coach", tags=["coach"])

NEEDS_WORK = ("weak", "developing")


def _source_read(source: Source) -> ConceptSourceRead:
    return ConceptSourceRead(document_id=source.document_id, filename=source.filename, location=source.location)


def _as_read(progress, sources: list[Source] | None = None) -> ConceptProgressRead:
    return ConceptProgressRead(
        concept_id=progress.concept_id,
        name=progress.name,
        summary=progress.summary,
        score=progress.score,
        attempts=progress.attempts,
        correct=progress.correct,
        status=progress.status,
        last_seen_at=progress.last_seen_at,
        sources=[_source_read(source) for source in sources or []],
    )


@router.get("/{course_id}", response_model=CoachSummary)
def coach_summary(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CoachSummary:
    """Where the student stands in one course, and what to revise next."""
    course = db.get(Course, course_id)
    if course is None or course.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Course not found")

    progress = course_progress(db, current_user.id, course_id)
    by_status = {status: 0 for status in ("strong", "developing", "weak", "unpractised")}
    for item in progress:
        by_status[item.status] += 1

    practised = [p for p in progress if p.attempts > 0]
    overall = (
        sum(p.score for p in practised if p.score is not None) / len(practised)
        if practised
        else None
    )

    topics, more_to_revise = revision_topics(db, progress)
    sources = concept_sources(db, [c.concept_id for topic in topics for c in topic.concepts])

    return CoachSummary(
        course_id=course_id,
        concept_count=len(progress),
        overall_mastery=overall,
        strong=by_status["strong"],
        developing=by_status["developing"],
        weak=by_status["weak"],
        unpractised=by_status["unpractised"],
        recommendations=[_as_read(p) for p in recommend(progress)],
        topics=[
            RevisionTopicRead(
                title=topic.title,
                summary=topic.summary,
                status=topic.status,
                concepts=[_as_read(c, sources.get(c.concept_id)) for c in topic.concepts],
            )
            for topic in topics
        ],
        more_to_revise=more_to_revise,
        concepts=[_as_read(p) for p in progress],
    )


@router.post("/{course_id}/explain", response_model=TopicExplanationRead)
def explain_topic(
    course_id: uuid.UUID,
    payload: TopicExplainRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TopicExplanationRead:
    """How a revision topic's concepts fit together, written once and then kept."""
    course = db.get(Course, course_id)
    if course is None or course.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Course not found")
    progress = {p.concept_id: p for p in course_progress(db, current_user.id, course_id)}
    concepts = [progress[concept_id] for concept_id in dict.fromkeys(payload.concept_ids) if concept_id in progress]
    if len(concepts) != len(set(payload.concept_ids)):
        raise HTTPException(status_code=404, detail="Concept not found")

    signature = ",".join(sorted(f"{c.concept_id}:{int(c.status in NEEDS_WORK)}" for c in concepts))
    key = hashlib.sha256(signature.encode()).hexdigest()
    cached = db.get(TopicExplanation, (current_user.id, key))
    if cached is None:
        from app.services.ai import get_ai_provider
        from app.services.failures import describe

        limits.spend(db, current_user.id, "explain")
        try:
            written = get_ai_provider().explain_topic(
                f"{course.code} {course.name}", [(c.name, c.summary, c.status in NEEDS_WORK) for c in concepts]
            )
        except Exception as exc:  # noqa: BLE001 -- reported to the student
            logger.warning("Topic explanation failed: %s", exc)
            message, _ = describe(exc)
            raise HTTPException(status_code=502, detail=message)
        by_name = {c.name.strip().lower(): str(c.concept_id) for c in concepts}
        links = {
            by_name[link.name.strip().lower()]: link.link.strip()
            for link in written.links
            if link.name.strip().lower() in by_name and link.link.strip()
        }
        cached = TopicExplanation(
            student_id=current_user.id, key=key, course_id=course_id, overview=written.overview.strip(), links=links
        )
        db.add(cached)
        db.commit()
    return TopicExplanationRead(overview=cached.overview, links=cached.links)


@router.get("/concept/{concept_id}", response_model=ConceptDetailRead)
def concept_detail(
    concept_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConceptDetailRead:
    """One concept in depth: how it is going, and where it came from."""
    concept = db.get(CourseConcept, concept_id)
    if concept is None or concept.student_id != current_user.id:
        raise HTTPException(status_code=404, detail="Concept not found")

    mastery = (
        db.query(ConceptMastery)
        .filter(
            ConceptMastery.student_id == current_user.id,
            ConceptMastery.course_concept_id == concept.id,
        )
        .first()
    )

    mentions = (
        db.query(KnowledgeConcept, LectureDocument)
        .join(LectureDocument, KnowledgeConcept.document_id == LectureDocument.id)
        .filter(KnowledgeConcept.course_concept_id == concept.id)
        .all()
    )

    progress = ConceptProgress(
        concept_id=concept.id,
        name=concept.name,
        summary=concept.summary,
        score=mastery.score if mastery else None,
        attempts=mastery.attempts if mastery else 0,
        correct=mastery.correct if mastery else 0,
        last_seen_at=mastery.last_seen_at if mastery else None,
    )

    return ConceptDetailRead(
        concept_id=concept.id,
        course_id=concept.course_id,
        name=concept.name,
        summary=concept.summary,
        score=progress.score,
        attempts=progress.attempts,
        correct=progress.correct,
        status=progress.status,
        last_seen_at=progress.last_seen_at,
        sources=[_source_read(source) for source in concept_sources(db, [concept.id]).get(concept.id, [])],
        mentions=[mention.summary for mention, _ in mentions],
    )
