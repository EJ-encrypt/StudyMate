"""Dealing and marking every Arcade round, against a stored copy of what was dealt.

Each game's round is built from the student's own material with no model
call (see app.services.games for the building blocks), saved as a GameRound,
and sent to the browser with its answers so feedback after each move is
instant. The score is then worked out here from the saved round, never from
anything the browser claims was right - which is also what lets a friend be
challenged to the identical round later.

Games:
- Beat the Clock: ten questions, fifteen seconds each.
- Concept Match: pair concepts with their meanings.
- True or False Blitz: as many statements as you can judge in sixty seconds.
- Odd One Out: spot the concept that does not belong with the other three.
- Three Strikes: questions until the third wrong answer, with less time as you go.
"""

import random
import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.assessment import AssessmentItem, ItemKind
from app.models.document import CourseConcept
from app.models.social import GameRound
from app.services import games
from app.services.games import NotEnoughMaterial
from app.services.grading import is_correct, normalize

BEAT_THE_CLOCK = games.BEAT_THE_CLOCK
CONCEPT_MATCH = games.CONCEPT_MATCH
TRUE_FALSE = "true_false"
ODD_ONE_OUT = "odd_one_out"
THREE_STRIKES = "three_strikes"
GAMES = (BEAT_THE_CLOCK, CONCEPT_MATCH, TRUE_FALSE, ODD_ONE_OUT, THREE_STRIKES)

# True or False Blitz
BLITZ_SECONDS = 60
BLITZ_STATEMENTS = 40
MIN_STATEMENTS = 6
BLITZ_POINTS = 100
BLITZ_MAX_MULTIPLIER = 3.0

# Odd One Out
PUZZLES_PER_ROUND = 6
MIN_ODD_CONCEPTS = 6
ODD_POINTS = 150
ODD_MAX_SPEED_BONUS = 100
ODD_PAR_SECONDS = 20
# The three that belong must be clearly closer to each other than to the odd
# one; below this gap the puzzle is a coin toss, so it is not dealt.
ODD_MIN_GAP = 0.05

# Three Strikes
STRIKES = 3
STRIKES_MAX_QUESTIONS = 60
MIN_STRIKES_QUESTIONS = 6
STRIKES_POINTS = 100
STRIKES_START_SECONDS = 20
STRIKES_MIN_SECONDS = 7
# Grace for the network between the browser's clock running out and the answer
# being recorded, so a last-moment answer is not marked late.
_GRACE_MS = 1500


def strikes_seconds(correct_so_far: int) -> int:
    """Time allowed for the next question: two seconds less every three right answers."""
    return max(STRIKES_MIN_SECONDS, STRIKES_START_SECONDS - (correct_so_far // 3) * 2)


def strikes_level(correct_so_far: int) -> int:
    """Points multiplier, rising every five right answers."""
    return 1 + correct_so_far // 5


# --- Dealing ----------------------------------------------------------------


def _clock_question(item: AssessmentItem, decoys: list[str], rng: random.Random) -> dict:
    if item.kind is ItemKind.MCQ:
        options = list(item.options)
        rng.shuffle(options)
    else:
        options = games._fill_blank_choices(item, decoys, rng)
    return {
        "item_id": str(item.id),
        "kind": item.kind.value,
        "question": item.question,
        "options": options,
        "answer": item.answer,
        "explanation": item.explanation,
    }


def _decoys(db: Session, student_id: uuid.UUID, course_id: uuid.UUID, pool: list[AssessmentItem]) -> list[str]:
    names = [
        name
        for (name,) in db.query(CourseConcept.name).filter(
            CourseConcept.student_id == student_id, CourseConcept.course_id == course_id
        )
    ]
    return [item.answer for item in pool if item.kind is ItemKind.FILL_BLANK] + names


def _distinct(items: list[AssessmentItem], rng: random.Random) -> list[AssessmentItem]:
    unique: dict[str, AssessmentItem] = {}
    for item in rng.sample(items, len(items)):
        unique.setdefault(normalize(item.question), item)
    return list(unique.values())


def _deal_clock(db, student_id, course_id, rng) -> dict:
    questions = games.beat_the_clock_round(db, student_id, course_id, rng)
    return {
        "seconds_per_question": games.SECONDS_PER_QUESTION,
        "questions": [
            {**q.__dict__, "item_id": str(q.item_id)} for q in questions
        ],
    }


def _deal_strikes(db, student_id, course_id, rng) -> dict:
    pool = games._question_pool(db, student_id, course_id)
    distinct = _distinct(pool, rng)
    if len(distinct) < MIN_STRIKES_QUESTIONS:
        raise NotEnoughMaterial(
            "Three Strikes needs at least six multiple-choice or fill-in-the-blank questions "
            "for this course. Generate a set in the Study Engine first."
        )
    decoys = _decoys(db, student_id, course_id, pool)
    # Recognition first, recall later: multiple choice, then fill in the blank,
    # so the run gets harder as well as faster.
    distinct.sort(key=lambda item: 0 if item.kind is ItemKind.MCQ else 1)
    return {
        "questions": [_clock_question(item, decoys, rng) for item in distinct[:STRIKES_MAX_QUESTIONS]],
        "strikes": STRIKES,
    }


def _deal_match(db, student_id, course_id, rng, document_id) -> dict:
    deal = games.concept_match_round(db, student_id, course_id, document_id, rng)
    return {
        "document_id": str(document_id) if document_id else None,
        "pairs": [{"concept_id": str(p.concept_id), "name": p.name, "clue": p.clue} for p in deal.pairs],
        "pool_size": deal.pool_size,
        "fresh_in_round": deal.fresh_in_round,
        "fresh_rounds_left": deal.fresh_rounds_left,
        "rounds_played": deal.rounds_played,
        "variety": deal.variety,
    }


def _first_sentence(text: str) -> str:
    return re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0]


def _without_name(claim: str, name: str) -> str:
    """Remove a concept's own name from a definition borrowed for another concept.

    Otherwise "Paging: Paging splits memory into pages" shown under the
    heading "Segmentation" would be false at a glance.
    """
    bare = re.sub(r"\s*\([^)]*\)", "", name).strip()
    abbreviations = re.findall(r"\(([^)]+)\)", name)
    for variant in sorted({name, bare, *abbreviations} - {""}, key=len, reverse=True):
        # Any article goes too, so "A TLB caches" reads "This caches", not "A it caches".
        claim = re.sub(rf"\b(?:(a|an|the)\s+)?{re.escape(variant)}\b", "this", claim, flags=re.IGNORECASE)
    return claim[:1].upper() + claim[1:] if claim.startswith("this") else claim


def _concept_vectors(concepts: list[CourseConcept]) -> list[CourseConcept]:
    """The concepts sharing the commonest embedding model, so similarities compare."""
    by_model: dict[str, list[CourseConcept]] = {}
    for concept in concepts:
        by_model.setdefault(concept.embedding_model, []).append(concept)
    return max(by_model.values(), key=len) if by_model else []


def _deal_blitz(db, student_id, course_id, rng) -> dict:
    from app.services.knowledge_base import cosine_similarity

    concepts = (
        db.query(CourseConcept)
        .filter(CourseConcept.student_id == student_id, CourseConcept.course_id == course_id)
        .all()
    )
    statements: list[dict] = []

    # From concepts: the real definition, or the closest other concept's -
    # the closest, so a false statement is plausible rather than absurd.
    comparable = _concept_vectors(concepts)
    for concept in concepts:
        claim = _first_sentence(concept.summary)
        if not claim:
            continue
        others = [c for c in concepts if c.id != concept.id and _first_sentence(c.summary)]
        if rng.random() < 0.5 or not others:
            statements.append({
                "key": f"c:{concept.id}:{concept.id}",
                "subject": concept.name,
                "claim": claim,
                "is_true": True,
                "explanation": f"That is what {concept.name} means.",
            })
            continue
        if concept in comparable and len(comparable) > 2:
            ranked = sorted(
                (c for c in comparable if c.id != concept.id),
                key=lambda c: cosine_similarity(concept.embedding, c.embedding),
                reverse=True,
            )
            impostor = rng.choice(ranked[:3])
        else:
            impostor = rng.choice(others)
        statements.append({
            "key": f"c:{concept.id}:{impostor.id}",
            "subject": concept.name,
            "claim": _without_name(_first_sentence(impostor.summary), impostor.name),
            "is_true": False,
            "explanation": f"That describes {impostor.name}. {concept.name}: {claim}",
        })

    # From multiple-choice questions: the right answer, or a wrong option.
    for item in games._question_pool(db, student_id, course_id):
        if item.kind is not ItemKind.MCQ or not item.options:
            continue
        wrong = [index for index, option in enumerate(item.options) if normalize(option) != normalize(item.answer)]
        right = [index for index, option in enumerate(item.options) if normalize(option) == normalize(item.answer)]
        if not right:
            continue
        use_true = rng.random() < 0.5 or not wrong
        index = right[0] if use_true else rng.choice(wrong)
        statements.append({
            "key": f"q:{item.id}:{index}",
            "subject": item.question,
            "claim": item.options[index],
            "is_true": use_true,
            "explanation": item.explanation or f"The answer is {item.answer}.",
        })

    if len(statements) < MIN_STATEMENTS:
        raise NotEnoughMaterial(
            "True or False Blitz needs a little more material for this course. Upload a "
            "lecture or generate a multiple-choice set first."
        )
    rng.shuffle(statements)
    return {"seconds": BLITZ_SECONDS, "statements": statements[:BLITZ_STATEMENTS]}


def _deal_odd(db, student_id, course_id, rng) -> dict:
    from app.services.knowledge_base import cosine_similarity

    concepts = _concept_vectors(
        db.query(CourseConcept)
        .filter(CourseConcept.student_id == student_id, CourseConcept.course_id == course_id)
        .all()
    )
    if len(concepts) < MIN_ODD_CONCEPTS:
        raise NotEnoughMaterial(
            "Odd One Out needs at least six concepts in this course. Upload more material "
            "and wait for it to finish processing."
        )

    similarity = {
        (a.id, b.id): cosine_similarity(a.embedding, b.embedding) for a in concepts for b in concepts if a.id != b.id
    }
    puzzles = []
    used_anchors: set[uuid.UUID] = set()
    for anchor in rng.sample(concepts, len(concepts)):
        if len(puzzles) == PUZZLES_PER_ROUND:
            break
        if anchor.id in used_anchors:
            continue
        neighbours = sorted(
            (c for c in concepts if c.id != anchor.id), key=lambda c: similarity[(anchor.id, c.id)], reverse=True
        )[:2]
        group = [anchor, *neighbours]
        within = min(similarity[(a.id, b.id)] for a in group for b in group if a.id != b.id)
        outsiders = sorted(
            (c for c in concepts if c not in group),
            key=lambda c: sum(similarity[(c.id, g.id)] for g in group) / len(group),
        )
        # From the least related third, so the same outsider does not keep coming back.
        candidates = [
            c for c in outsiders[: max(1, len(outsiders) // 3)]
            if within - max(similarity[(c.id, g.id)] for g in group) >= ODD_MIN_GAP
        ]
        if not candidates:
            continue
        odd = rng.choice(candidates)
        # Named after the most central of the three, which best stands for them.
        centre = max(group, key=lambda g: sum(similarity[(g.id, o.id)] for o in group if o.id != g.id))
        options = [*group, odd]
        rng.shuffle(options)
        used_anchors.update(c.id for c in group)
        puzzles.append({
            "options": [{"concept_id": str(c.id), "name": c.name, "summary": c.summary} for c in options],
            "odd_id": str(odd.id),
            "theme": centre.name,
        })

    if len(puzzles) < 3:
        raise NotEnoughMaterial(
            "Odd One Out could not find clearly related groups in this course yet. Upload "
            "more material on its different topics."
        )
    return {"puzzles": puzzles}


def deal(
    db: Session,
    student_id: uuid.UUID,
    course_id: uuid.UUID,
    game: str,
    document_id: uuid.UUID | None = None,
    rng: random.Random | None = None,
) -> GameRound:
    rng = rng or random.Random()
    if game == BEAT_THE_CLOCK:
        payload = _deal_clock(db, student_id, course_id, rng)
    elif game == CONCEPT_MATCH:
        payload = _deal_match(db, student_id, course_id, rng, document_id)
    elif game == TRUE_FALSE:
        payload = _deal_blitz(db, student_id, course_id, rng)
    elif game == ODD_ONE_OUT:
        payload = _deal_odd(db, student_id, course_id, rng)
    elif game == THREE_STRIKES:
        payload = _deal_strikes(db, student_id, course_id, rng)
    else:
        raise ValueError(f"Unknown game {game!r}")
    round_ = GameRound(student_id=student_id, course_id=course_id, game=game, payload=payload)
    db.add(round_)
    db.commit()
    db.refresh(round_)
    return round_


# --- Marking ----------------------------------------------------------------


@dataclass
class Answer:
    key: str
    response: str
    time_ms: int


@dataclass
class Marked:
    score: int
    correct: int
    total: int
    mistakes: int
    duration_ms: int
    xp: int
    # (key, correct, points) per answer, for the results screen.
    answers: list[tuple[str, bool, int]] = field(default_factory=list)
    # Assessment items answered, for mastery: only meaningful to the dealer.
    item_results: list[tuple[uuid.UUID, bool]] = field(default_factory=list)


def _mark_clock(payload: dict, answers: list[Answer]) -> Marked:
    questions = {q["item_id"]: q for q in payload["questions"]}
    limit_ms = payload["seconds_per_question"] * 1000
    marked = Marked(0, 0, 0, 0, 0, 0)
    streak = 0
    for answer in answers:
        question = questions.get(answer.key)
        if question is None:
            raise ValueError("That answer is not for a question in this round")
        correct = answer.time_ms <= limit_ms + _GRACE_MS and is_correct(
            ItemKind(question["kind"]), question["answer"], answer.response
        )
        streak = streak + 1 if correct else 0
        points = games.clock_points(correct, answer.time_ms, streak)
        marked.answers.append((answer.key, correct, points))
        marked.item_results.append((uuid.UUID(answer.key), correct))
        marked.score += points
        marked.correct += correct
        marked.duration_ms += min(answer.time_ms, limit_ms)
    marked.total = len(answers)
    marked.mistakes = marked.total - marked.correct
    marked.xp = marked.correct * 3
    return marked


def _mark_strikes(payload: dict, answers: list[Answer]) -> Marked:
    questions = {q["item_id"]: q for q in payload["questions"]}
    marked = Marked(0, 0, 0, 0, 0, 0)
    for answer in answers:
        if marked.mistakes >= payload.get("strikes", STRIKES):
            break
        question = questions.get(answer.key)
        if question is None:
            raise ValueError("That answer is not for a question in this round")
        allowed_ms = strikes_seconds(marked.correct) * 1000
        correct = answer.time_ms <= allowed_ms + _GRACE_MS and is_correct(
            ItemKind(question["kind"]), question["answer"], answer.response
        )
        points = STRIKES_POINTS * strikes_level(marked.correct) if correct else 0
        marked.answers.append((answer.key, correct, points))
        marked.item_results.append((uuid.UUID(answer.key), correct))
        marked.score += points
        marked.correct += correct
        marked.mistakes += not correct
        marked.duration_ms += min(answer.time_ms, allowed_ms)
    marked.total = len(marked.answers)
    marked.xp = marked.correct * 3
    return marked


def _mark_blitz(payload: dict, answers: list[Answer]) -> Marked:
    statements = {s["key"]: s for s in payload["statements"]}
    budget_ms = payload["seconds"] * 1000 + _GRACE_MS
    marked = Marked(0, 0, 0, 0, 0, 0)
    streak = 0
    for answer in answers:
        statement = statements.get(answer.key)
        if statement is None:
            raise ValueError("That answer is not for a statement in this round")
        if marked.duration_ms + max(0, answer.time_ms) > budget_ms:
            break
        marked.duration_ms += max(0, answer.time_ms)
        correct = (answer.response.strip().lower() == "true") == statement["is_true"]
        streak = streak + 1 if correct else 0
        multiplier = min(1 + 0.25 * (streak - 1), BLITZ_MAX_MULTIPLIER) if correct else 0
        points = round(BLITZ_POINTS * multiplier)
        marked.answers.append((answer.key, correct, points))
        marked.score += points
        marked.correct += correct
    marked.total = len(marked.answers)
    marked.mistakes = marked.total - marked.correct
    marked.xp = marked.correct * 2
    return marked


def _mark_odd(payload: dict, answers: list[Answer]) -> Marked:
    puzzles = payload["puzzles"]
    marked = Marked(0, 0, 0, 0, 0, 0)
    for answer in answers:
        try:
            puzzle = puzzles[int(answer.key)]
        except (ValueError, IndexError):
            raise ValueError("That answer is not for a puzzle in this round")
        correct = answer.response == puzzle["odd_id"]
        par_ms = ODD_PAR_SECONDS * 1000
        bonus = round(ODD_MAX_SPEED_BONUS * max(0, par_ms - max(0, answer.time_ms)) / par_ms)
        points = ODD_POINTS + bonus if correct else 0
        marked.answers.append((answer.key, correct, points))
        marked.score += points
        marked.correct += correct
        marked.duration_ms += max(0, answer.time_ms)
    marked.total = len(puzzles)
    marked.mistakes = len(marked.answers) - marked.correct
    marked.xp = marked.correct * 3
    return marked


def _mark_match(payload: dict, mistakes: int, duration_ms: int) -> Marked:
    pairs = len(payload["pairs"])
    return Marked(
        score=games.concept_match_score(pairs, mistakes, duration_ms),
        correct=pairs,
        total=pairs,
        mistakes=mistakes,
        duration_ms=duration_ms,
        xp=pairs * 2,
    )


def mark(game: str, payload: dict, answers: list[Answer], mistakes: int = 0, duration_ms: int = 0) -> Marked:
    if game == BEAT_THE_CLOCK:
        return _mark_clock(payload, answers)
    if game == THREE_STRIKES:
        return _mark_strikes(payload, answers)
    if game == TRUE_FALSE:
        return _mark_blitz(payload, answers)
    if game == ODD_ONE_OUT:
        return _mark_odd(payload, answers)
    if game == CONCEPT_MATCH:
        return _mark_match(payload, mistakes, duration_ms)
    raise ValueError(f"Unknown game {game!r}")


def concept_ids(game: str, payload: dict) -> list[str] | None:
    """Which concepts a round used, for Concept Match's freshness history."""
    if game == CONCEPT_MATCH:
        return [pair["concept_id"] for pair in payload["pairs"]]
    return None
