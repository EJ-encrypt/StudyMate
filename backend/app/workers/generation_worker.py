import logging
import random
import re
import uuid

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.assessment import (
    Assessment,
    AssessmentItem,
    AssessmentKind,
    AssessmentStatus,
    ItemKind,
)
from app.models.course import Course
from app.models.document import CourseConcept, LectureDocument
from app.services.ai import get_ai_provider
from app.services.ai.base import GeneratedItem
from app.services.ai.base import ItemKind as ProviderItemKind
from app.services.failures import describe
from app.services.grading import normalize
from app.services.quantitative import is_quantitative_course, looks_mathematical
from app.workers.extraction_worker import read_document

logger = logging.getLogger(__name__)

# An exam paper mixes question styles, weighted towards recognition and recall
# with a couple of written answers, in the order a paper would present them.
_EXAM_MIX = ((ItemKind.MCQ, 0.5), (ItemKind.FILL_BLANK, 0.25), (ItemKind.SHORT_ANSWER, 0.25))

# How many items one request asks for. Lite models given 40 at once tend to
# stop early or pad the end with near-copies; two requests of 20, the second
# told what the first asked, gives a full set of distinct questions.
BATCH_SIZE = 20

# Set sizes when the student does not choose: (minimum, maximum, characters of
# material per item). A short handout gets the minimum; a long deck scales up
# until the maximum. Flashcards and multiple choice start at 20, because a
# smaller set was too little to revise from.
_SIZES = {
    AssessmentKind.FLASHCARD: (20, 40, 450),
    AssessmentKind.MCQ: (20, 40, 450),
    AssessmentKind.FILL_BLANK: (15, 30, 700),
    AssessmentKind.SHORT_ANSWER: (8, 15, 2000),
    AssessmentKind.EXAM: (25, 40, 600),
}
MAX_ITEMS = 40

_GIVEAWAY_OPTIONS = re.compile(r"^(all|none|both|neither) of (the )?(above|these|them)\b", re.IGNORECASE)


def auto_count(kind: AssessmentKind, text: str, concept_count: int = 0) -> int:
    """How many items a set should have, from how much material there is.

    Concepts count too, at two items each: a cumulative set is generated
    from a compact concept list, whose character length understates how much
    the course actually covers.
    """
    minimum, maximum, chars_per_item = _SIZES[kind]
    by_length = len(text) // chars_per_item
    return max(minimum, min(maximum, max(by_length, concept_count * 2)))


def _exam_split(count: int) -> list[tuple[ItemKind, int]]:
    """Divide `count` questions across the exam mix, dropping kinds that don't fit.

    A short paper cannot hold one of every kind, so kinds are filled in order
    of weight and any that would get zero are left out entirely -- the total
    always matches `count`, and no kind is ever allocated a non-positive number.
    """
    allocated: list[tuple[ItemKind, int]] = []
    remaining = count

    for index, (kind, share) in enumerate(_EXAM_MIX):
        kinds_left = len(_EXAM_MIX) - index - 1
        if remaining <= 0:
            break
        if index == len(_EXAM_MIX) - 1:
            portion = remaining
        else:
            portion = max(1, round(count * share))
            # Leave at least one question for each remaining kind, while it fits.
            portion = min(portion, max(1, remaining - kinds_left))
        allocated.append((kind, portion))
        remaining -= portion

    return allocated


def tidy_mcq(item: GeneratedItem, rng: random.Random) -> GeneratedItem | None:
    """Repair or reject one multiple-choice item, and shuffle its options.

    Shuffled here because models put the right answer in the same one or two
    positions far more often than chance, which a student soon learns to
    exploit. Rejected when the answer is not actually one of the options, or
    when there are too few distinct options to be a fair question.
    """
    options: list[str] = []
    seen: set[str] = set()
    for option in item.options:
        key = normalize(option)
        if option.strip() and key not in seen and not _GIVEAWAY_OPTIONS.match(option.strip()):
            seen.add(key)
            options.append(option.strip())

    answer = next((option for option in options if option == item.answer.strip()), None)
    if answer is None:
        wanted = normalize(item.answer)
        answer = next((option for option in options if normalize(option) == wanted), None)
    if answer is None or len(options) < 3:
        return None

    chosen = [answer, *[option for option in options if option != answer][:3]]
    rng.shuffle(chosen)
    return item.model_copy(update={"options": chosen, "answer": answer})


def _generate_kind(
    source_text: str,
    kind: ItemKind,
    count: int,
    concept_names: list[str],
    quantitative: bool,
    rng: random.Random,
) -> list[GeneratedItem]:
    """Generate `count` distinct items of one kind, in batches."""
    provider = get_ai_provider()
    produced: list[GeneratedItem] = []
    seen: set[str] = set()
    # One spare request, for when a batch comes back short or full of repeats.
    requests_left = -(-count // BATCH_SIZE) + 1

    while len(produced) < count and requests_left > 0:
        requests_left -= 1
        wanted = min(BATCH_SIZE, count - len(produced))
        batch = provider.generate_assessment_items(
            source_text,
            ProviderItemKind(kind.value),
            count=wanted,
            concepts=concept_names,
            quantitative=quantitative,
            avoid=[item.question for item in produced] or None,
        )
        added = 0
        for item in batch:
            if kind is ItemKind.MCQ:
                item = tidy_mcq(item, rng)
                if item is None:
                    continue
            key = normalize(item.question)
            if not key or key in seen:
                continue
            seen.add(key)
            produced.append(item)
            added += 1
            if len(produced) == count:
                break
        if added == 0:
            # Nothing new: asking again would only produce more repeats.
            break
    return produced


def _generate_items(
    source_text: str,
    kind: AssessmentKind,
    count: int,
    concept_names: list[str],
    quantitative: bool = False,
    rng: random.Random | None = None,
) -> list[tuple[ItemKind, GeneratedItem]]:
    rng = rng or random.Random()
    if kind is AssessmentKind.EXAM:
        produced: list[tuple[ItemKind, GeneratedItem]] = []
        for item_kind, portion in _exam_split(count):
            items = _generate_kind(source_text, item_kind, portion, concept_names, quantitative, rng)
            produced.extend((item_kind, item) for item in items)
        return produced

    item_kind = ItemKind(kind.value)
    items = _generate_kind(source_text, item_kind, count, concept_names, quantitative, rng)
    return [(item_kind, item) for item in items]


def _course_concepts(db: Session, assessment: Assessment) -> list[CourseConcept]:
    return (
        db.query(CourseConcept)
        .filter(
            CourseConcept.student_id == assessment.student_id,
            CourseConcept.course_id == assessment.course_id,
        )
        .order_by(CourseConcept.created_at)
        .all()
    )


def _resolve_concept(name: str, concepts: list[CourseConcept]) -> uuid.UUID | None:
    """Map a generated item's concept tag onto the knowledge base.

    Matching is on the normalised name only: an unmatched tag leaves the item
    untied to a concept, which costs some mastery signal, whereas guessing
    would credit or penalise the wrong topic.
    """
    if not name:
        return None
    wanted = normalize(name)
    for concept in concepts:
        if normalize(concept.name) == wanted:
            return concept.id
    return None


def _source_text(db: Session, assessment: Assessment, concepts: list[CourseConcept]) -> tuple[str, bool]:
    """What to generate from, and whether it is quantitative.

    One lecture uses its stored text. A cumulative paper is built from the
    de-duplicated concepts rather than by re-reading every document, which
    keeps the request small however many lectures the student has uploaded.
    """
    course = db.get(Course, assessment.course_id)
    course_is_quantitative = bool(course and is_quantitative_course(course.code, course.name))

    if assessment.document_id is None:
        if not concepts:
            raise ValueError("This course has no concepts to draw on yet")
        text = "\n".join(f"- {concept.name}: {concept.summary}" for concept in concepts)
        return text, course_is_quantitative or looks_mathematical(text)

    document = db.get(LectureDocument, assessment.document_id)
    if document is None:
        raise ValueError("Source document no longer exists")
    return read_document(db, document)


def process_assessment(assessment_id: str, count: int | None = None) -> None:
    db = SessionLocal()
    try:
        assessment = db.get(Assessment, uuid.UUID(assessment_id))
        if assessment is None:
            return

        assessment.status = AssessmentStatus.PROCESSING
        db.commit()

        try:
            concepts = _course_concepts(db, assessment)
            source_text, quantitative = _source_text(db, assessment, concepts)
            wanted = count or auto_count(
                assessment.kind,
                source_text,
                len(concepts) if assessment.document_id is None else 0,
            )
            produced = _generate_items(
                source_text,
                assessment.kind,
                min(wanted, MAX_ITEMS),
                [c.name for c in concepts],
                quantitative,
            )
            if not produced:
                raise ValueError("The model returned no usable questions")
            logger.info(
                "Assessment %s: %s of %s items (%s)",
                assessment.id, len(produced), wanted, "quantitative" if quantitative else "text",
            )
        except Exception as exc:  # noqa: BLE001 -- surfaced via assessment.error_message
            assessment.status = AssessmentStatus.FAILED
            message, assessment.can_retry = describe(exc)
            assessment.error_message = message
            db.commit()
            return

        for position, (item_kind, item) in enumerate(produced, start=1):
            db.add(
                AssessmentItem(
                    assessment_id=assessment.id,
                    position=position,
                    kind=item_kind,
                    question=item.question,
                    answer=item.answer,
                    options=item.options,
                    explanation=item.explanation,
                    course_concept_id=_resolve_concept(item.concept, concepts),
                )
            )
        assessment.status = AssessmentStatus.COMPLETED
        db.commit()
    finally:
        db.close()
