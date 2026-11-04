"""Per-concept mastery, weak-topic detection and revision recommendations.

Mastery is an exponential moving average of correctness rather than a plain
percentage, so a student who has since learned a topic is not held back by
early wrong answers, while a single lucky guess cannot mark a topic mastered
either. Recommendations are computed from that record rather than asked of a
model: the ranking is deterministic, instant, free, and explainable to the
student, which matters more here than prose.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.assessment import AssessmentItem
from app.models.document import CourseConcept
from app.models.mastery import ConceptMastery

# Weight given to the newest answer. 0.4 moves noticeably on each answer while
# still taking roughly three consistent answers to cross a band boundary.
LEARNING_RATE = 0.4

# Below this a concept counts as weak; at or above it counts as strong. A
# concept never answered has no score and is reported separately, because
# "not practised" is different from "practised badly".
WEAK_THRESHOLD = 0.5
STRONG_THRESHOLD = 0.8

# One answer is not evidence of mastery, however it went.
CONFIDENT_ATTEMPTS = 3


@dataclass
class ConceptProgress:
    concept_id: uuid.UUID
    name: str
    summary: str
    score: float | None
    attempts: int
    correct: int
    last_seen_at: datetime | None

    @property
    def status(self) -> str:
        if self.attempts == 0:
            return "unpractised"
        if self.score is not None and self.score < WEAK_THRESHOLD:
            return "weak"
        if self.attempts < CONFIDENT_ATTEMPTS:
            return "developing"
        if self.score is not None and self.score >= STRONG_THRESHOLD:
            return "strong"
        return "developing"


def record_answers(
    db: Session,
    student_id: uuid.UUID,
    course_id: uuid.UUID,
    graded: list[tuple[AssessmentItem, bool]],
) -> None:
    """Fold a submitted attempt's results into per-concept mastery.

    Items that could not be tied to a concept are skipped rather than
    guessed at: a wrong attribution would push the wrong topic's score.
    """
    for item, was_correct in graded:
        if item.course_concept_id is None:
            continue

        mastery = (
            db.query(ConceptMastery)
            .filter(
                ConceptMastery.student_id == student_id,
                ConceptMastery.course_concept_id == item.course_concept_id,
            )
            .first()
        )
        if mastery is None:
            mastery = ConceptMastery(
                student_id=student_id,
                course_id=course_id,
                course_concept_id=item.course_concept_id,
                # Seed with the first result rather than averaging against a
                # zero that was never observed.
                score=1.0 if was_correct else 0.0,
                attempts=1,
                correct=1 if was_correct else 0,
                last_seen_at=datetime.now(timezone.utc),
            )
            db.add(mastery)
            # Sessions run with autoflush off, so without this a second answer
            # on the same concept in one submission misses the pending row and
            # inserts a duplicate, violating uq_mastery_student_concept.
            db.flush()
            continue

        observation = 1.0 if was_correct else 0.0
        mastery.score = (1 - LEARNING_RATE) * mastery.score + LEARNING_RATE * observation
        mastery.attempts += 1
        mastery.correct += 1 if was_correct else 0
        mastery.last_seen_at = datetime.now(timezone.utc)


def course_progress(
    db: Session, student_id: uuid.UUID, course_id: uuid.UUID
) -> list[ConceptProgress]:
    """Every concept in the course with whatever is known about it so far."""
    rows = (
        db.query(CourseConcept, ConceptMastery)
        .outerjoin(
            ConceptMastery,
            (ConceptMastery.course_concept_id == CourseConcept.id)
            & (ConceptMastery.student_id == student_id),
        )
        .filter(CourseConcept.student_id == student_id, CourseConcept.course_id == course_id)
        .order_by(CourseConcept.created_at)
        .all()
    )

    return [
        ConceptProgress(
            concept_id=concept.id,
            name=concept.name,
            summary=concept.summary,
            score=mastery.score if mastery else None,
            attempts=mastery.attempts if mastery else 0,
            correct=mastery.correct if mastery else 0,
            last_seen_at=mastery.last_seen_at if mastery else None,
        )
        for concept, mastery in rows
    ]


def recommend(progress: list[ConceptProgress], limit: int = 5) -> list[ConceptProgress]:
    """Which concepts to revise next.

    Weak concepts come first, worst score first, because that is where
    practice pays most. Unpractised concepts follow, since an unknown is
    worth more attention than something already answered well. Concepts
    that are merely developing come last, and strong ones are not
    recommended at all.
    """

    def rank(item: ConceptProgress) -> tuple[int, float]:
        if item.status == "weak":
            return (0, item.score if item.score is not None else 0.0)
        if item.status == "unpractised":
            return (1, 0.0)
        if item.status == "developing":
            return (2, item.score if item.score is not None else 0.0)
        return (3, item.score if item.score is not None else 1.0)

    ranked = sorted((p for p in progress if p.status != "strong"), key=rank)
    return ranked[:limit]


# --- Revision topics --------------------------------------------------------

# However many concepts need work, the Coach shows at most this many topics:
# a list of twenty separate items read as a wall of failure and put students
# off starting at all.
MAX_TOPICS = 5
# Only this many of the most urgent concepts are grouped; the rest stay in
# the full concept list. Keeps the page focused, and the grouping cheap.
MAX_GROUPED_CONCEPTS = 25
# Related enough to revise together even when there is room for more topics.
# Distinct but neighbouring concepts (Second and Third Normal Form) measured
# 0.80 to 0.85, which is exactly the kind of pair worth revising as one.
RELATED_SIMILARITY = 0.80

_STATUS_SEVERITY = {"weak": 0, "unpractised": 1, "developing": 2, "strong": 3}


@dataclass
class RevisionTopic:
    title: str
    summary: str
    status: str
    concepts: list[ConceptProgress]


def group_into_topics(
    concepts: list[ConceptProgress],
    embeddings: dict[uuid.UUID, tuple[list[float], str]],
    max_topics: int = MAX_TOPICS,
) -> list[RevisionTopic]:
    """Group concepts needing revision into at most `max_topics` related topics.

    Average-linkage clustering on the concept embeddings already stored for
    the knowledge base: repeatedly merge the two most similar groups, until
    there are few enough and the closest remaining pair is no longer
    related. Concepts embedded by different models are never compared, since
    their similarity would be meaningless; they are only merged when the
    topic limit forces it.

    `concepts` arrives in priority order, and topics keep that order: the
    topic holding the most urgent concept comes first.
    """
    from app.services.knowledge_base import cosine_similarity

    if not concepts:
        return []

    def similarity(a: ConceptProgress, b: ConceptProgress) -> float:
        left, right = embeddings.get(a.concept_id), embeddings.get(b.concept_id)
        if left is None or right is None or left[1] != right[1]:
            return 0.0
        return cosine_similarity(left[0], right[0])

    pair = {
        (i, j): similarity(concepts[i], concepts[j])
        for i in range(len(concepts))
        for j in range(i + 1, len(concepts))
    }

    def linkage(left: list[int], right: list[int]) -> float:
        scores = [pair[(min(i, j), max(i, j))] for i in left for j in right]
        return sum(scores) / len(scores)

    groups: list[list[int]] = [[index] for index in range(len(concepts))]
    while len(groups) > 1:
        best, best_pair = -1.0, (0, 1)
        for a in range(len(groups)):
            for b in range(a + 1, len(groups)):
                score = linkage(groups[a], groups[b])
                if score > best:
                    best, best_pair = score, (a, b)
        if len(groups) <= max_topics and best < RELATED_SIMILARITY:
            break
        a, b = best_pair
        groups[a] = sorted(groups[a] + groups[b])
        del groups[b]

    groups.sort(key=lambda members: members[0])
    topics = []
    for members in groups:
        # Named after its most central concept: the one closest on average to
        # the others, which best stands for the group as a whole.
        centre = max(
            members,
            key=lambda i: sum(pair[(min(i, j), max(i, j))] for j in members if j != i),
        )
        group = [concepts[i] for i in members]
        topics.append(
            RevisionTopic(
                title=concepts[centre].name,
                summary=concepts[centre].summary,
                status=min((c.status for c in group), key=lambda s: _STATUS_SEVERITY[s]),
                concepts=group,
            )
        )
    return topics


def revision_topics(
    db: Session, progress: list[ConceptProgress]
) -> tuple[list[RevisionTopic], int]:
    """The Coach's "revise these next": grouped topics, and how many were left out."""
    needing = recommend(progress, limit=len(progress))
    grouped = needing[:MAX_GROUPED_CONCEPTS]
    ids = [concept.concept_id for concept in grouped]
    embeddings = {
        concept_id: (embedding, model)
        for concept_id, embedding, model in db.query(
            CourseConcept.id, CourseConcept.embedding, CourseConcept.embedding_model
        ).filter(CourseConcept.id.in_(ids))
    } if ids else {}
    return group_into_topics(grouped, embeddings), len(needing) - len(grouped)
