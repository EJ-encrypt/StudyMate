import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.course import Course
from app.models.document import CourseConcept
from app.models.game import GameSession
from app.models.user import User
from app.schemas.assessment import NewBadge
from app.schemas.game import (
    ClockAnswerResult,
    ClockQuestionRead,
    ClockRound,
    ClockSubmit,
    CourseGameStats,
    GameResult,
    GameStats,
    MatchPairRead,
    MatchRound,
    MatchSubmit,
)
from app.services import games
from app.services.coaching import record_answers
from app.services.gamification import record_game

router = APIRouter(prefix="/games", tags=["games"])


def _own_course(db: Session, course_id: uuid.UUID, user: User) -> Course:
    course = db.get(Course, course_id)
    if course is None or course.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def _finish(
    db: Session,
    user: User,
    course_id: uuid.UUID,
    game: str,
    score: int,
    correct: int,
    total: int,
    mistakes: int,
    duration_ms: int,
    game_xp: int,
) -> GameResult:
    previous_best = games.personal_best(db, user.id, course_id, game)
    is_best = previous_best is None or score > previous_best
    xp, badges = record_game(db, user.id, game, game_xp, score, mistakes, is_best and previous_best is not None)

    db.add(
        GameSession(
            student_id=user.id,
            course_id=course_id,
            game=game,
            score=score,
            correct=correct,
            total=total,
            mistakes=mistakes,
            duration_ms=duration_ms,
            xp_awarded=xp,
        )
    )
    db.commit()
    return GameResult(
        game=game,
        score=score,
        correct=correct,
        total=total,
        xp_awarded=xp,
        personal_best=max(score, previous_best or 0),
        is_personal_best=is_best,
        new_badges=[NewBadge(code=b.code, name=b.name, description=b.description) for b in badges],
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
            for game in games.GAMES
        ],
        clock_questions_available=len(games._question_pool(db, current_user.id, course_id)),
        concepts_available=concepts,
    )


@router.get("/{course_id}/beat-the-clock", response_model=ClockRound)
def start_beat_the_clock(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClockRound:
    _own_course(db, course_id, current_user)
    try:
        questions = games.beat_the_clock_round(db, current_user.id, course_id)
    except games.NotEnoughMaterial as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ClockRound(
        course_id=course_id,
        seconds_per_question=games.SECONDS_PER_QUESTION,
        questions=[ClockQuestionRead(**q.__dict__) for q in questions],
        personal_best=games.personal_best(db, current_user.id, course_id, games.BEAT_THE_CLOCK),
    )


@router.post("/beat-the-clock", response_model=GameResult, status_code=status.HTTP_201_CREATED)
def submit_beat_the_clock(
    payload: ClockSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameResult:
    _own_course(db, payload.course_id, current_user)
    try:
        results = games.score_beat_the_clock(
            db,
            current_user.id,
            payload.course_id,
            [(a.item_id, a.response, a.time_ms) for a in payload.answers],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Game answers are real evidence of what the student knows, so they move
    # mastery exactly as a quiz answer would.
    record_answers(db, current_user.id, payload.course_id, [(r.item, r.correct) for r in results])

    correct = sum(1 for r in results if r.correct)
    result = _finish(
        db,
        current_user,
        payload.course_id,
        games.BEAT_THE_CLOCK,
        score=sum(r.points for r in results),
        correct=correct,
        total=len(results),
        mistakes=len(results) - correct,
        duration_ms=sum(min(a.time_ms, games.SECONDS_PER_QUESTION * 1000) for a in payload.answers),
        game_xp=correct * 3,
    )
    result.answers = [ClockAnswerResult(item_id=r.item.id, correct=r.correct, points=r.points) for r in results]
    return result


@router.get("/{course_id}/concept-match", response_model=MatchRound)
def start_concept_match(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MatchRound:
    _own_course(db, course_id, current_user)
    try:
        pairs = games.concept_match_round(db, current_user.id, course_id)
    except games.NotEnoughMaterial as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return MatchRound(
        course_id=course_id,
        pairs=[MatchPairRead(**p.__dict__) for p in pairs],
        personal_best=games.personal_best(db, current_user.id, course_id, games.CONCEPT_MATCH),
    )


@router.post("/concept-match", response_model=GameResult, status_code=status.HTTP_201_CREATED)
def submit_concept_match(
    payload: MatchSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameResult:
    _own_course(db, payload.course_id, current_user)
    try:
        pairs = games.validate_concepts(db, current_user.id, payload.course_id, payload.concept_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Matching is recognition, a weaker signal than answering a question, so
    # it earns XP but deliberately leaves mastery scores alone.
    return _finish(
        db,
        current_user,
        payload.course_id,
        games.CONCEPT_MATCH,
        score=games.concept_match_score(pairs, payload.mistakes, payload.duration_ms),
        correct=pairs,
        total=pairs,
        mistakes=payload.mistakes,
        duration_ms=payload.duration_ms,
        game_xp=pairs * 2,
    )
