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
PAIRS_PER_ROUND = 8
MIN_PAIRS = 3
POINTS_PER_PAIR = 100
MISTAKE_PENALTY = 15
# Seconds per pair a student can take before the time bonus runs out.
PAR_SECONDS_PER_PAIR = 10
TIME_BONUS_PER_SECOND = 5
CLUE_MAX_CHARS = 120


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


@dataclass(frozen=True)
class MatchDeal:
    """A round of pairs, and how much fresh material is left behind it."""

    pairs: list[MatchPair]
    # Concepts in the material the round was drawn from.
    pool_size: int
    # Pairs in this round never matched before in a finished round.
    fresh_in_round: int
    # Concepts still never matched once this round is played.
    unseen_after: int
    rounds_played: int

    @property
    def fresh_rounds_left(self) -> int:
        """Further rounds that can still be made entirely of unseen concepts."""
        return self.unseen_after // PAIRS_PER_ROUND

    @property
    def variety(self) -> str:
        """'fresh' (all new), 'mixing' (some repeats) or 'repeating' (nothing new)."""
        if self.fresh_in_round == len(self.pairs):
            return "fresh"
        return "mixing" if self.fresh_in_round else "repeating"


def _match_pool(
    db: Session, student_id: uuid.UUID, course_id: uuid.UUID, document_id: uuid.UUID | None
) -> list[CourseConcept]:
    """The concepts a round may use: the whole course, or one file's."""
    query = db.query(CourseConcept).filter(
        CourseConcept.student_id == student_id, CourseConcept.course_id == course_id
    )
    if document_id is not None:
        from app.models.document import KnowledgeConcept

        query = query.filter(
            CourseConcept.id.in_(
                db.query(KnowledgeConcept.course_concept_id).filter(
                    KnowledgeConcept.document_id == document_id,
                    KnowledgeConcept.course_concept_id.isnot(None),
                )
            )
        )
    return query.all()


def _match_history(db: Session, student_id: uuid.UUID, course_id: uuid.UUID) -> tuple[dict[str, tuple[int, int]], int]:
    """How often, and how recently, each concept has been matched in finished rounds.

    Recency is the index of the round (0 = oldest), so a concept matched once
    long ago sorts ahead of one matched once in the last round.
    """
    sessions = (
        db.query(GameSession.concept_ids)
        .filter(
            GameSession.student_id == student_id,
            GameSession.course_id == course_id,
            GameSession.game == CONCEPT_MATCH,
        )
        .order_by(GameSession.created_at)
        .all()
    )
    seen: dict[str, tuple[int, int]] = {}
    for index, (concept_ids,) in enumerate(sessions):
        for concept_id in concept_ids or []:
            count, _ = seen.get(concept_id, (0, -1))
            seen[concept_id] = (count + 1, index)
    return seen, len(sessions)


def concept_match_round(
    db: Session,
    student_id: uuid.UUID,
    course_id: uuid.UUID,
    document_id: uuid.UUID | None = None,
    rng: random.Random | None = None,
) -> MatchDeal:
    """Deal a round, preferring concepts the student has matched least.

    Never-matched concepts come first; once every concept has been seen, the
    least-matched and least-recent are used, so repeats are spread evenly
    rather than the same few pairs coming back. A larger body of material
    therefore supports many more rounds before anything repeats, which is
    what the 'variety' on the result reports to the student.
    """
    rng = rng or random.Random()
    concepts = _match_pool(db, student_id, course_id, document_id)
    if len(concepts) < MIN_PAIRS:
        where = "this file" if document_id else "this course"
        raise NotEnoughMaterial(
            f"Concept Match needs at least three concepts from {where}. Upload "
            "more material and wait for it to finish processing."
        )

    seen, rounds_played = _match_history(db, student_id, course_id)
    rng.shuffle(concepts)
    concepts.sort(key=lambda c: seen.get(str(c.id), (0, -1)))
    chosen = concepts[: min(PAIRS_PER_ROUND, len(concepts))]
    rng.shuffle(chosen)

    unseen = [c for c in concepts if str(c.id) not in seen]
    fresh = sum(1 for c in chosen if str(c.id) not in seen)
    return MatchDeal(
        pairs=[MatchPair(c.id, c.name, make_clue(c.name, c.summary)) for c in chosen],
        pool_size=len(concepts),
        fresh_in_round=fresh,
        unseen_after=len(unseen) - fresh,
        rounds_played=rounds_played,
    )


def fresh_match_rounds(db: Session, student_id: uuid.UUID, course_id: uuid.UUID) -> int:
    """Whole-course rounds still possible from concepts never matched."""
    concepts = _match_pool(db, student_id, course_id, None)
    seen, _ = _match_history(db, student_id, course_id)
    return sum(1 for c in concepts if str(c.id) not in seen) // PAIRS_PER_ROUND


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
