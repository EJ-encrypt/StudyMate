"""Deleting a student's account and everything in it.

Order matters: rows go child-first so no foreign key is left pointing at a
deleted row. Files go after the database rows commit, and the Supabase
sign-in account last. A failure deleting files leaves orphaned objects
nobody can reach, which is tidied up later; the reverse order could leave
an account that signs in to an empty profile and recreates itself.
"""

import logging
import uuid

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.assessment import Assessment, AssessmentItem, Attempt, AttemptAnswer
from app.models.course import Course, Enrollment
from app.models.document import CourseConcept, KnowledgeConcept, LectureDocument
from app.models.game import GameSession
from app.models.gamification import EarnedBadge, StudentProgress
from app.models.job import Job
from app.models.mastery import ConceptMastery, TopicExplanation
from app.models.schedule import LectureSlot, PushSubscription, SentReminder
from app.models.review import FlashcardReview
from app.models.social import Challenge, Friendship, GameRound, UserBlock, UserReport, XpEvent
from app.models.usage import AiUsage
from app.models.user import User
from app.services.storage import get_storage

logger = logging.getLogger(__name__)


def delete_account(db: Session, user: User) -> None:
    student_id = user.id
    paths = [
        path
        for (path,) in db.query(LectureDocument.storage_path).filter(LectureDocument.student_id == student_id)
    ]

    attempts = db.query(Attempt.id).filter(Attempt.student_id == student_id)
    assessments = db.query(Assessment.id).filter(Assessment.student_id == student_id)
    slots = db.query(LectureSlot.id).filter(LectureSlot.student_id == student_id)

    def gone(query) -> None:
        query.delete(synchronize_session=False)

    gone(db.query(FlashcardReview).filter(FlashcardReview.student_id == student_id))
    gone(db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id.in_(attempts.scalar_subquery())))
    gone(db.query(Attempt).filter(Attempt.student_id == student_id))
    gone(db.query(AssessmentItem).filter(AssessmentItem.assessment_id.in_(assessments.scalar_subquery())))
    gone(db.query(Assessment).filter(Assessment.student_id == student_id))
    gone(db.query(ConceptMastery).filter(ConceptMastery.student_id == student_id))
    gone(db.query(TopicExplanation).filter(TopicExplanation.student_id == student_id))
    gone(db.query(KnowledgeConcept).filter(KnowledgeConcept.student_id == student_id))
    gone(db.query(CourseConcept).filter(CourseConcept.student_id == student_id))
    gone(db.query(LectureDocument).filter(LectureDocument.student_id == student_id))
    gone(db.query(GameSession).filter(GameSession.student_id == student_id))
    gone(db.query(Challenge).filter(
        (Challenge.challenger_id == student_id) | (Challenge.opponent_id == student_id)
    ))
    gone(db.query(GameRound).filter(GameRound.student_id == student_id))
    gone(db.query(Friendship).filter(
        (Friendship.requester_id == student_id) | (Friendship.addressee_id == student_id)
    ))
    gone(db.query(UserBlock).filter((UserBlock.blocker_id == student_id) | (UserBlock.blocked_id == student_id)))
    gone(db.query(UserReport).filter(
        (UserReport.reporter_id == student_id) | (UserReport.reported_id == student_id)
    ))
    gone(db.query(AiUsage).filter(AiUsage.student_id == student_id))
    gone(db.query(XpEvent).filter(XpEvent.student_id == student_id))
    gone(db.query(EarnedBadge).filter(EarnedBadge.student_id == student_id))
    gone(db.query(StudentProgress).filter(StudentProgress.student_id == student_id))
    gone(db.query(SentReminder).filter(SentReminder.slot_id.in_(slots.scalar_subquery())))
    gone(db.query(LectureSlot).filter(LectureSlot.student_id == student_id))
    gone(db.query(PushSubscription).filter(PushSubscription.student_id == student_id))
    gone(db.query(Job).filter(Job.student_id == student_id))
    gone(db.query(Enrollment).filter(Enrollment.student_id == student_id))
    gone(db.query(Course).filter(Course.owner_id == student_id))
    db.delete(user)
    db.commit()

    try:
        get_storage().delete(paths)
    except Exception as exc:  # noqa: BLE001 -- the account is already gone
        logger.warning("Could not delete %s stored files for %s: %s", len(paths), student_id, exc)

    _delete_auth_user(student_id)


def delete_course(db: Session, course: Course) -> None:
    """Delete one course and everything that belongs to it.

    Its files, concepts, question sets and attempts, Coach progress, flashcard
    schedule, Arcade scores and rounds (with any challenges sent from them)
    all go. Lectures on the timetable stay, unlinked from the course, since
    the lecture still happens. XP and badges already earned are kept.
    """
    course_id = course.id
    documents = db.query(LectureDocument.id).filter(LectureDocument.course_id == course_id)
    paths = [path for (path,) in db.query(LectureDocument.storage_path).filter(LectureDocument.course_id == course_id)]
    assessments = db.query(Assessment.id).filter(Assessment.course_id == course_id)
    items = db.query(AssessmentItem.id).filter(AssessmentItem.assessment_id.in_(assessments.scalar_subquery()))
    attempts = db.query(Attempt.id).filter(Attempt.assessment_id.in_(assessments.scalar_subquery()))
    rounds = db.query(GameRound.id).filter(GameRound.course_id == course_id)
    queued_for = {str(i) for (i,) in documents} | {str(i) for (i,) in assessments}

    def gone(query) -> None:
        query.delete(synchronize_session=False)

    for job in db.query(Job).filter(Job.student_id == course.owner_id, Job.status.in_(("queued", "running"))):
        if {str(v) for v in (job.payload or {}).values()} & queued_for:
            db.delete(job)
    gone(db.query(FlashcardReview).filter(FlashcardReview.item_id.in_(items.scalar_subquery())))
    gone(db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id.in_(attempts.scalar_subquery())))
    gone(db.query(Attempt).filter(Attempt.assessment_id.in_(assessments.scalar_subquery())))
    gone(db.query(AssessmentItem).filter(AssessmentItem.assessment_id.in_(assessments.scalar_subquery())))
    gone(db.query(Assessment).filter(Assessment.course_id == course_id))
    gone(db.query(ConceptMastery).filter(ConceptMastery.course_id == course_id))
    gone(db.query(TopicExplanation).filter(TopicExplanation.course_id == course_id))
    gone(db.query(KnowledgeConcept).filter(KnowledgeConcept.course_id == course_id))
    gone(db.query(CourseConcept).filter(CourseConcept.course_id == course_id))
    gone(db.query(LectureDocument).filter(LectureDocument.course_id == course_id))
    gone(db.query(GameSession).filter(GameSession.course_id == course_id))
    gone(db.query(Challenge).filter(Challenge.round_id.in_(rounds.scalar_subquery())))
    gone(db.query(GameRound).filter(GameRound.course_id == course_id))
    db.query(LectureSlot).filter(LectureSlot.course_id == course_id).update(
        {LectureSlot.course_id: None}, synchronize_session=False
    )
    gone(db.query(Enrollment).filter(Enrollment.course_id == course_id))
    db.delete(course)
    db.commit()

    try:
        get_storage().delete(paths)
    except Exception as exc:  # noqa: BLE001 -- the course is already gone
        logger.warning("Could not delete %s stored files for course %s: %s", len(paths), course_id, exc)


def _delete_auth_user(student_id: uuid.UUID) -> None:
    """Remove the Supabase sign-in, so the address can be registered again."""
    if not (settings.supabase_url and settings.supabase_service_role_key):
        return
    key = settings.supabase_service_role_key
    response = httpx.delete(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{student_id}",
        headers={"Authorization": f"Bearer {key}", "apikey": key},
        timeout=15,
    )
    if response.status_code >= 400 and response.status_code != 404:
        logger.warning("Supabase refused to delete auth user %s: %s", student_id, response.status_code)
