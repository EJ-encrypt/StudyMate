import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.assessment import AssessmentItem
from app.models.course import Course
from app.models.document import CourseConcept, LectureDocument
from app.models.game import GameSession
from app.models.social import GameRound
from app.models.user import User
from app.schemas.assessment import NewBadge
from app.schemas.game import (
    AnswerResult,
    CourseGameStats,
    GameResult,
    GameStats,
    RoundRead,
    RoundSubmit,
)
from app.services import arcade, games
from app.services.coaching import record_answers
from app.services.gamification import record_game

router = APIRouter(prefix="/games", tags=["games"])

# URL name for each game.
SLUGS = {
    "beat-the-clock": arcade.BEAT_THE_CLOCK,
    "concept-match": arcade.CONCEPT_MATCH,
    "true-false": arcade.TRUE_FALSE,
    "odd-one-out": arcade.ODD_ONE_OUT,
    "three-strikes": arcade.THREE_STRIKES,
}


def _own_course(db: Session, course_id: uuid.UUID, user: User) -> Course:
    course = db.get(Course, course_id)
    if course is None or course.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def course_title(course: Course | None) -> str:
    return f"{course.code} · {course.name}" if course else "A course"


def round_view(db: Session, round_: GameRound, personal_best: int | None, challenge=None) -> RoundRead:
    return RoundRead(
        **round_.payload,
        round_id=round_.id,
        game=round_.game,
        course_id=round_.course_id,
        title=course_title(db.get(Course, round_.course_id)),
        personal_best=personal_best,
        challenge=challenge,
    )


@router.get("/{course_id}/stats", response_model=CourseGameStats)
def course_stats(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseGameStats:
    _own_course(db, course_id, current_user)
    rows = {
        game: (plays, best, last)
        for game, plays, best, last in db.query(
            GameSession.game,
            func.count(GameSession.id),
            func.max(GameSession.score),
            func.max(GameSession.created_at),
        )
        .filter(GameSession.student_id == current_user.id, GameSession.course_id == course_id)
        .group_by(GameSession.game)
        .all()
    }
    concepts = (
        db.query(func.count(CourseConcept.id))
        .filter(CourseConcept.student_id == current_user.id, CourseConcept.course_id == course_id)
        .scalar()
    )
    return CourseGameStats(
        course_id=course_id,
        games=[
            GameStats(
                game=game,
                plays=rows.get(game, (0, None, None))[0],
                best=rows.get(game, (0, None, None))[1],
                last_played_at=rows.get(game, (0, None, None))[2],
            )
            for game in arcade.GAMES
        ],
        clock_questions_available=len(games._question_pool(db, current_user.id, course_id)),
        concepts_available=concepts,
        match_fresh_rounds=games.fresh_match_rounds(db, current_user.id, course_id),
    )


@router.get("/{course_id}/{slug}", response_model=RoundRead)
def start_round(
    course_id: uuid.UUID,
    slug: str,
    document_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoundRead:
    """Deal a round of any game. The answers come with it, for instant feedback."""
    game = SLUGS.get(slug)
    if game is None:
        raise HTTPException(status_code=404, detail="No such game")
    _own_course(db, course_id, current_user)
    if document_id is not None:
        if game != arcade.CONCEPT_MATCH:
            raise HTTPException(status_code=400, detail="Only Concept Match can be played on one file")
        document = db.get(LectureDocument, document_id)
        if document is None or document.student_id != current_user.id or document.course_id != course_id:
            raise HTTPException(status_code=404, detail="File not found in this course")
    try:
        round_ = arcade.deal(db, current_user.id, course_id, game, document_id)
    except games.NotEnoughMaterial as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return round_view(db, round_, games.personal_best(db, current_user.id, course_id, game))


def _answers(payload: RoundSubmit) -> list[arcade.Answer]:
    return [arcade.Answer(a.key, a.response, a.time_ms) for a in payload.answers]


@router.post("/rounds/{round_id}/submit", response_model=GameResult, status_code=status.HTTP_201_CREATED)
def submit_round(
    round_id: uuid.UUID,
    payload: RoundSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameResult:
    round_ = db.get(GameRound, round_id)
    if round_ is None or round_.student_id != current_user.id:
        raise HTTPException(status_code=404, detail="Round not found")
    if round_.submitted_at is not None:
        raise HTTPException(status_code=409, detail="This round has already been scored")
    try:
        marked = arcade.mark(round_.game, round_.payload, _answers(payload), payload.mistakes, payload.duration_ms)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Answers to the student's own questions are real evidence of what they
    # know, so they move mastery exactly as a quiz answer would. Matching and
    # true-or-false are weaker signals, so those games leave mastery alone.
    if marked.item_results:
        items = {
            item.id: item
            for item in db.query(AssessmentItem).filter(
                AssessmentItem.id.in_([item_id for item_id, _ in marked.item_results])
            )
        }
        own = {item.id for item in games._question_pool(db, current_user.id, round_.course_id)}
        record_answers(
            db,
            current_user.id,
            round_.course_id,
            [(items[item_id], correct) for item_id, correct in marked.item_results if item_id in own],
        )

    previous_best = games.personal_best(db, current_user.id, round_.course_id, round_.game)
    is_best = previous_best is None or marked.score > previous_best
    xp, badges = record_game(
        db, current_user.id, round_.game, marked.xp, marked.score, marked.mistakes,
        is_best and previous_best is not None,
    )
    db.add(
        GameSession(
            student_id=current_user.id,
            course_id=round_.course_id,
            game=round_.game,
            score=marked.score,
            correct=marked.correct,
            total=marked.total,
            mistakes=marked.mistakes,
            duration_ms=marked.duration_ms,
            xp_awarded=xp,
            concept_ids=arcade.concept_ids(round_.game, round_.payload),
        )
    )
    round_.submitted_at = datetime.now(timezone.utc)
    round_.score = marked.score
    db.commit()
    return GameResult(
        game=round_.game,
        round_id=round_.id,
        score=marked.score,
        correct=marked.correct,
        total=marked.total,
        xp_awarded=xp,
        personal_best=max(marked.score, previous_best or 0),
        is_personal_best=is_best,
        new_badges=[NewBadge(code=b.code, name=b.name, description=b.description) for b in badges],
        answers=[AnswerResult(key=key, correct=correct, points=points) for key, correct, points in marked.answers],
    )
