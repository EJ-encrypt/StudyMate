"""The Arcade: Beat the Clock and Concept Match.

Both games are built from what the student already has, with no model call:
Beat the Clock reuses questions from multiple-choice and fill-in-the-blank
sets they generated, and Concept Match uses their course knowledge base. A
round therefore starts instantly, costs nothing against the free-tier quota,
and only ever asks about the student's own material.

Scoring is done on the server from the submitted answers, so the score and
XP reflect what was actually answered correctly. Answer times come from the
browser and are clamped, which is enough for a personal-best leaderboard.
"""

import random
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.assessment import Assessment, AssessmentItem, AssessmentStatus, ItemKind
from app.models.document import CourseConcept
from app.models.game import GameSession
from app.services.grading import is_correct, normalize

BEAT_THE_CLOCK = "beat_the_clock"
CONCEPT_MATCH = "concept_match"
GAMES = (BEAT_THE_CLOCK, CONCEPT_MATCH)

# Beat the Clock
ROUND_SIZE = 10
MIN_QUESTIONS = 4
SECONDS_PER_QUESTION = 15
BASE_POINTS = 100
MAX_SPEED_BONUS = 100
MAX_STREAK_MULTIPLIER = 2.0

# Concept Match
PAIRS_PER_ROUND = 6
MIN_PAIRS = 3
POINTS_PER_PAIR = 100
MISTAKE_PENALTY = 15
# Seconds per pair a student can take before the time bonus runs out.
PAR_SECONDS_PER_PAIR = 10
TIME_BONUS_PER_SECOND = 5
CLUE_MAX_CHARS = 140


class NotEnoughMaterial(ValueError):
    pass


# --- Beat the Clock ---------------------------------------------------------


def _question_pool(db: Session, student_id: uuid.UUID, course_id: uuid.UUID) -> list[AssessmentItem]:
    return (
        db.query(AssessmentItem)
        .join(Assessment, AssessmentItem.assessment_id == Assessment.id)
        .filter(
            Assessment.student_id == student_id,
            Assessment.course_id == course_id,
            Assessment.status == AssessmentStatus.COMPLETED,
            AssessmentItem.kind.in_([ItemKind.MCQ, ItemKind.FILL_BLANK]),
        )
        .all()
    )


def _fill_blank_choices(item: AssessmentItem, decoys: list[str], rng: random.Random) -> list[str]:
    """Turn a typed fill-in-the-blank into four buttons, which a timer needs.

    Decoys are other answers and concept names from the same course, so they
    are plausible terms rather than obviously wrong filler. When there are
    not enough, the question stays typed.
    """
    wanted = normalize(item.answer)
    seen = {wanted}
    choices = []
    for candidate in rng.sample(decoys, len(decoys)):
        key = normalize(candidate)
        if key and key not in seen and len(candidate) <= 60:
            seen.add(key)
            choices.append(candidate)
        if len(choices) == 3:
            break
    if len(choices) < 3:
        return []
    choices.append(item.answer)
    rng.shuffle(choices)
    return choices


@dataclass(frozen=True)
class ClockQuestion:
    item_id: uuid.UUID
    kind: str
    question: str
    options: list[str]
    answer: str
    explanation: str


def beat_the_clock_round(
    db: Session, student_id: uuid.UUID, course_id: uuid.UUID, rng: random.Random | None = None
) -> list[ClockQuestion]:
    rng = rng or random.Random()
    pool = _question_pool(db, student_id, course_id)
    if len(pool) < MIN_QUESTIONS:
        raise NotEnoughMaterial(
            "Beat the Clock needs at least four multiple-choice or fill-in-the-blank "
            "questions for this course. Generate a set in the Study Engine first."
        )

    concept_names = [
        name
        for (name,) in db.query(CourseConcept.name).filter(
            CourseConcept.student_id == student_id, CourseConcept.course_id == course_id
        )
    ]
    blank_answers = [item.answer for item in pool if item.kind is ItemKind.FILL_BLANK]
    decoys = blank_answers + concept_names

    # One question per distinct stem: generating twice from the same lecture
    # can produce near-identical questions, and seeing one twice in a ten-
    # question sprint feels broken.
    unique: dict[str, AssessmentItem] = {}
    for item in rng.sample(pool, len(pool)):
        unique.setdefault(normalize(item.question), item)
    chosen = list(unique.values())[:ROUND_SIZE]

    questions = []
    for item in chosen:
        if item.kind is ItemKind.MCQ:
            options = list(item.options)
            rng.shuffle(options)
        else:
            options = _fill_blank_choices(item, decoys, rng)
        questions.append(
            ClockQuestion(
                item_id=item.id,
                kind=item.kind.value,
                question=item.question,
                options=options,
                answer=item.answer,
                explanation=item.explanation,
            )
        )
    return questions


def clock_points(correct: bool, time_ms: int, streak: int) -> int:
    """Points for one answer: base + speed bonus, scaled by the running streak."""
    if not correct:
        return 0
    limit_ms = SECONDS_PER_QUESTION * 1000
    remaining = max(0, limit_ms - max(0, min(time_ms, limit_ms)))
    speed_bonus = round(MAX_SPEED_BONUS * remaining / limit_ms)
    multiplier = min(1 + 0.25 * (streak - 1), MAX_STREAK_MULTIPLIER)
    return round((BASE_POINTS + speed_bonus) * multiplier)


@dataclass(frozen=True)
class ClockAnswerResult:
    item: AssessmentItem
    response: str
    correct: bool
    points: int


def score_beat_the_clock(
    db: Session,
    student_id: uuid.UUID,
    course_id: uuid.UUID,
    answers: list[tuple[uuid.UUID, str, int]],
) -> list[ClockAnswerResult]:
    """Mark a finished round. Answers are (item_id, response, time_ms) in play order."""
    pool = {item.id: item for item in _question_pool(db, student_id, course_id)}
    unknown = [str(item_id) for item_id, _, _ in answers if item_id not in pool]
    if unknown:
        raise ValueError(f"These questions are not from this course: {', '.join(unknown)}")

    results = []
    streak = 0
    for item_id, response, time_ms in answers:
        item = pool[item_id]
        correct = time_ms <= SECONDS_PER_QUESTION * 1000 and is_correct(item.kind, item.answer, response)
        streak = streak + 1 if correct else 0
        results.append(ClockAnswerResult(item, response, correct, clock_points(correct, time_ms, streak)))
    return results


# --- Concept Match ----------------------------------------------------------


def make_clue(name: str, summary: str) -> str:
    """A short definition to pair with the concept name, without giving it away."""
    first_sentence = re.split(r"(?<=[.!?])\s+", summary.strip(), maxsplit=1)[0]
    masked = first_sentence
    for term in sorted({name, *re.findall(r"\(([^)]+)\)", name)}, key=len, reverse=True):
        bare = re.sub(r"\s*\([^)]*\)", "", term).strip()
        for variant in {term, bare} - {""}:
            masked = re.sub(re.escape(variant), "____", masked, flags=re.IGNORECASE)
    if len(masked) > CLUE_MAX_CHARS:
        masked = masked[: CLUE_MAX_CHARS - 1].rsplit(" ", 1)[0] + "…"
    return masked


@dataclass(frozen=True)
class MatchPair:
    concept_id: uuid.UUID
    name: str
    clue: str


def concept_match_round(
    db: Session, student_id: uuid.UUID, course_id: uuid.UUID, rng: random.Random | None = None
) -> list[MatchPair]:
    rng = rng or random.Random()
    concepts = (
        db.query(CourseConcept)
        .filter(CourseConcept.student_id == student_id, CourseConcept.course_id == course_id)
        .all()
    )
    if len(concepts) < MIN_PAIRS:
        raise NotEnoughMaterial(
            "Concept Match needs at least three concepts in this course. Upload "
            "some material and wait for it to finish processing."
        )
    chosen = rng.sample(concepts, min(PAIRS_PER_ROUND, len(concepts)))
    return [MatchPair(c.id, c.name, make_clue(c.name, c.summary)) for c in chosen]


def concept_match_score(pairs: int, mistakes: int, duration_ms: int) -> int:
    par_ms = pairs * PAR_SECONDS_PER_PAIR * 1000
    time_bonus = max(0, (par_ms - max(0, duration_ms)) // 1000) * TIME_BONUS_PER_SECOND
    return max(0, pairs * POINTS_PER_PAIR - mistakes * MISTAKE_PENALTY + time_bonus)


def validate_concepts(
    db: Session, student_id: uuid.UUID, course_id: uuid.UUID, concept_ids: list[uuid.UUID]
) -> int:
    found = (
        db.query(func.count(CourseConcept.id))
        .filter(
            CourseConcept.id.in_(concept_ids),
            CourseConcept.student_id == student_id,
            CourseConcept.course_id == course_id,
        )
        .scalar()
    )
    if found != len(set(concept_ids)):
        raise ValueError("Some of those concepts are not from this course")
    return found


# --- Results ----------------------------------------------------------------


def personal_best(db: Session, student_id: uuid.UUID, course_id: uuid.UUID, game: str) -> int | None:
    return (
        db.query(func.max(GameSession.score))
        .filter(
            GameSession.student_id == student_id,
            GameSession.course_id == course_id,
            GameSession.game == game,
        )
        .scalar()
    )
