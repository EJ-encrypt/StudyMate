import uuid

from app.db.session import SessionLocal
from app.models.assessment import (
    Assessment,
    AssessmentItem,
    AssessmentKind,
    AssessmentStatus,
    ItemKind,
)
from sqlalchemy.orm import Session

from app.models.document import CourseConcept, LectureDocument
from app.services.ai import get_ai_provider
from app.services.ai.base import GeneratedItem
from app.services.ai.base import ItemKind as ProviderItemKind
from app.services.extraction import extract_text
from app.services.failures import describe
from app.services.grading import normalize

# An exam paper mixes question styles, weighted towards recognition and recall
# with a couple of written answers, in the order a paper would present them.
_EXAM_MIX = ((ItemKind.MCQ, 0.5), (ItemKind.FILL_BLANK, 0.25), (ItemKind.SHORT_ANSWER, 0.25))


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


def _generate_items(
    source_text: str,
    kind: AssessmentKind,
    count: int,
    concept_names: list[str],
) -> list[tuple[ItemKind, GeneratedItem]]:
    provider = get_ai_provider()

    if kind is AssessmentKind.EXAM:
        produced: list[tuple[ItemKind, GeneratedItem]] = []
        for item_kind, portion in _exam_split(count):
            items = provider.generate_assessment_items(
                source_text,
                ProviderItemKind(item_kind.value),
                count=portion,
                concepts=concept_names,
            )
            produced.extend((item_kind, item) for item in items)
        return produced

    item_kind = ItemKind(kind.value)
    items = provider.generate_assessment_items(
        source_text, ProviderItemKind(kind.value), count=count, concepts=concept_names
    )
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


def _source_text(db: Session, assessment: Assessment) -> str:
    """What to generate from: one lecture, or the whole course knowledge base.

    A cumulative paper is built from the de-duplicated concepts rather than by
    re-reading every document, which keeps the request small however many
    lectures the student has uploaded.
    """
    if assessment.document_id is None:
        concepts = (
            db.query(CourseConcept)
            .filter(
                CourseConcept.student_id == assessment.student_id,
                CourseConcept.course_id == assessment.course_id,
            )
            .order_by(CourseConcept.created_at)
            .all()
        )
        if not concepts:
            raise ValueError("This course has no concepts to draw on yet")
        return "\n".join(f"- {concept.name}: {concept.summary}" for concept in concepts)

    document = db.get(LectureDocument, assessment.document_id)
    if document is None:
        raise ValueError("Source document no longer exists")

    text = extract_text(document.storage_path)
    if not text.strip():
        raise ValueError("No readable text found in the source document")
    return text


def process_assessment(assessment_id: str, count: int) -> None:
    db = SessionLocal()
    try:
        assessment = db.get(Assessment, uuid.UUID(assessment_id))
        if assessment is None:
            return

        assessment.status = AssessmentStatus.PROCESSING
        db.commit()

        try:
            source_text = _source_text(db, assessment)

            concepts = _course_concepts(db, assessment)
            produced = _generate_items(
                source_text, assessment.kind, count, [c.name for c in concepts]
            )
            if not produced:
                raise ValueError("The model returned no usable questions")
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
