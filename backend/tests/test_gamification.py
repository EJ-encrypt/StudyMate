import uuid
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.assessment import Assessment, AssessmentKind, AssessmentStatus
from app.models.course import Course
from app.models.gamification import EarnedBadge, StudentProgress
from app.models.user import User
from app.services.gamification import (
    XP_PER_ATTEMPT,
    XP_PER_CORRECT_ANSWER,
    record_attempt,
    summary,
)


def _student(db: Session) -> User:
    user = User(
        email=f"gam-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="x",
        full_name="Gamified Student",
    )
    db.add(user)
    db.commit()
    return user


def _assessment(db: Session, student: User, kind: AssessmentKind = AssessmentKind.MCQ) -> Assessment:
    course = Course(name="OS", code="CS305", owner_id=student.id)
    db.add(course)
    db.flush()
    assessment = Assessment(
        student_id=student.id,
        course_id=course.id,
        document_id=None,
        title="Quiz",
        kind=kind,
        status=AssessmentStatus.COMPLETED,
    )
    db.add(assessment)
    db.commit()
    return assessment


def test_xp_rewards_attempting_and_being_right(client, db: Session) -> None:
    student = _student(db)
    assessment = _assessment(db, student)

    record_attempt(db, student.id, assessment, correct_count=3, total_count=5)
    db.commit()

    progress = db.get(StudentProgress, student.id)
    assert progress.xp == XP_PER_ATTEMPT + 3 * XP_PER_CORRECT_ANSWER


def test_first_quiz_and_perfect_score_badges(client, db: Session) -> None:
    student = _student(db)
    assessment = _assessment(db, student)

    earned = record_attempt(db, student.id, assessment, correct_count=5, total_count=5)
    db.commit()

    codes = {badge.code for badge in earned}
    assert "first_quiz" in codes
    assert "perfect_score" in codes


def test_imperfect_score_earns_no_perfect_badge(client, db: Session) -> None:
    student = _student(db)
    assessment = _assessment(db, student)

    earned = record_attempt(db, student.id, assessment, correct_count=4, total_count=5)
    db.commit()

    assert "perfect_score" not in {badge.code for badge in earned}


def test_badges_are_not_awarded_twice(client, db: Session) -> None:
    student = _student(db)
    assessment = _assessment(db, student)

    record_attempt(db, student.id, assessment, correct_count=5, total_count=5)
    db.commit()
    second = record_attempt(db, student.id, assessment, correct_count=5, total_count=5)
    db.commit()

    assert "perfect_score" not in {badge.code for badge in second}
    assert db.query(EarnedBadge).filter(
        EarnedBadge.student_id == student.id, EarnedBadge.code == "perfect_score"
    ).count() == 1


def test_streak_counts_consecutive_days(client, db: Session) -> None:
    student = _student(db)
    assessment = _assessment(db, student)
    start = date(2026, 3, 1)

    for offset in range(3):
        record_attempt(db, student.id, assessment, 1, 1, today=start + timedelta(days=offset))
    db.commit()

    progress = db.get(StudentProgress, student.id)
    assert progress.current_streak == 3
    assert progress.longest_streak == 3


def test_several_attempts_in_one_day_count_once(client, db: Session) -> None:
    student = _student(db)
    assessment = _assessment(db, student)
    today = date(2026, 3, 1)

    for _ in range(4):
        record_attempt(db, student.id, assessment, 1, 1, today=today)
    db.commit()

    assert db.get(StudentProgress, student.id).current_streak == 1


def test_missing_a_day_resets_the_streak_but_keeps_the_record(client, db: Session) -> None:
    student = _student(db)
    assessment = _assessment(db, student)
    start = date(2026, 3, 1)

    for offset in range(3):
        record_attempt(db, student.id, assessment, 1, 1, today=start + timedelta(days=offset))
    record_attempt(db, student.id, assessment, 1, 1, today=start + timedelta(days=9))
    db.commit()

    progress = db.get(StudentProgress, student.id)
    assert progress.current_streak == 1
    assert progress.longest_streak == 3, "a broken streak should not erase the best run"


def test_three_day_streak_earns_its_badge(client, db: Session) -> None:
    student = _student(db)
    assessment = _assessment(db, student)
    start = date(2026, 3, 1)

    earned_codes = set()
    for offset in range(3):
        earned = record_attempt(db, student.id, assessment, 1, 1, today=start + timedelta(days=offset))
        earned_codes |= {badge.code for badge in earned}
    db.commit()

    assert "streak_3" in earned_codes
    assert "streak_7" not in earned_codes


def test_exam_paper_earns_the_exam_badge(client, db: Session) -> None:
    student = _student(db)
    exam = _assessment(db, student, kind=AssessmentKind.EXAM)

    earned = record_attempt(db, student.id, exam, correct_count=2, total_count=5)
    db.commit()

    assert "exam_ready" in {badge.code for badge in earned}


def test_summary_lists_unearned_badges_too(client, db: Session) -> None:
    student = _student(db)
    assessment = _assessment(db, student)
    record_attempt(db, student.id, assessment, correct_count=1, total_count=2)
    db.commit()

    result = summary(db, student.id)

    assert result["xp"] > 0
    earned = [b for b in result["badges"] if b["earned_at"] is not None]
    unearned = [b for b in result["badges"] if b["earned_at"] is None]
    assert {b["code"] for b in earned} == {"first_quiz"}
    assert unearned, "the profile should show what is still available"
