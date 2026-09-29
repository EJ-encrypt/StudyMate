import uuid

from app.db.session import SessionLocal
from app.models.assessment import (
    Assessment,
    AssessmentItem,
    AssessmentKind,
    AssessmentStatus,
    ItemKind,
)
from app.models.document import LectureDocument
from app.services.ai import get_ai_provider
from app.services.ai.base import GeneratedItem
from app.services.ai.base import ItemKind as ProviderItemKind
from app.services.extraction import extract_text

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


def _generate_items(source_text: str, kind: AssessmentKind, count: int) -> list[tuple[ItemKind, GeneratedItem]]:
    provider = get_ai_provider()

    if kind is AssessmentKind.EXAM:
        produced: list[tuple[ItemKind, GeneratedItem]] = []
        for item_kind, portion in _exam_split(count):
            items = provider.generate_assessment_items(
                source_text, ProviderItemKind(item_kind.value), count=portion
            )
            produced.extend((item_kind, item) for item in items)
        return produced

    item_kind = ItemKind(kind.value)
    items = provider.generate_assessment_items(source_text, ProviderItemKind(kind.value), count=count)
    return [(item_kind, item) for item in items]


def process_assessment(assessment_id: str, count: int) -> None:
    db = SessionLocal()
    try:
        assessment = db.get(Assessment, uuid.UUID(assessment_id))
        if assessment is None:
            return

        assessment.status = AssessmentStatus.PROCESSING
        db.commit()

        try:
            document = db.get(LectureDocument, assessment.document_id)
            if document is None:
                raise ValueError("Source document no longer exists")

            source_text = extract_text(document.storage_path)
            if not source_text.strip():
                raise ValueError("No readable text found in the source document")

            produced = _generate_items(source_text, assessment.kind, count)
            if not produced:
                raise ValueError("The model returned no usable questions")
        except Exception as exc:  # noqa: BLE001 -- surfaced via assessment.error_message
            assessment.status = AssessmentStatus.FAILED
            assessment.error_message = str(exc)
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
                )
            )
        assessment.status = AssessmentStatus.COMPLETED
        db.commit()
    finally:
        db.close()
