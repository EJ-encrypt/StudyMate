"""Merge a document's extracted concepts into a course-level knowledge base.

Why this is not a single similarity threshold: measured on real concept text
(name plus summary, gemini-embedding-2), the pairs that must merge and the
pairs that must not overlap.

    SAME  "TLB" / "Translation Lookaside Buffer"               0.850
    CLOSE "Second Normal Form (2NF)" / "Third Normal Form"     0.852

So similarity is used to sort candidates into three bands: confidently the
same, confidently different, and an ambiguous middle the AI provider
adjudicates. A missed merge only leaves a duplicate entry; a wrong merge
silently deletes a concept from the student's knowledge base, so every
uncertain case defaults to not merging.
"""

import logging
import uuid

from sqlalchemy.orm import Session

from app.models.document import CourseConcept, KnowledgeConcept
from app.services.ai import get_ai_provider

logger = logging.getLogger(__name__)

# Above this, similarity alone is trusted; the highest scoring distinct pair
# measured was 0.852, so this keeps clear air above it.
AUTO_MERGE_SIMILARITY = 0.93
# Below this, treated as a different concept without asking the model.
CANDIDATE_SIMILARITY = 0.80


def render_for_embedding(name: str, summary: str) -> str:
    """Names alone are not separable enough; the summary carries the definition."""
    return f"{name}: {summary}"


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sum(a * a for a in left) ** 0.5
    right_norm = sum(b * b for b in right) ** 0.5
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def sync_document_concepts(db: Session, document_id: uuid.UUID) -> None:
    """Fold one document's concepts into its course knowledge base."""
    pending = (
        db.query(KnowledgeConcept)
        .filter(
            KnowledgeConcept.document_id == document_id,
            KnowledgeConcept.course_concept_id.is_(None),
        )
        .all()
    )
    if not pending:
        return

    student_id = pending[0].student_id
    course_id = pending[0].course_id

    existing = (
        db.query(CourseConcept)
        .filter(CourseConcept.student_id == student_id, CourseConcept.course_id == course_id)
        .all()
    )

    provider = get_ai_provider()
    vectors, embedding_model = provider.embed_tagged(
        [render_for_embedding(c.name, c.summary) for c in pending]
    )
    # zip() below would otherwise stop at the shorter list and quietly leave
    # the remaining concepts out of the knowledge base.
    if len(vectors) != len(pending):
        raise ValueError(f"Expected {len(pending)} embeddings, got {len(vectors)}")

    # Work out the best existing match for each incoming concept first, so the
    # ambiguous ones can be adjudicated together in a single call.
    # Only vectors from the same embedding model are comparable. When a
    # fallback provider produced this batch, existing concepts embedded by the
    # primary are simply not candidates - which can leave a duplicate, the safe
    # direction, rather than merging on a meaningless similarity score.
    comparable = [c for c in existing if c.embedding_model == embedding_model]
    if len(comparable) != len(existing):
        logger.info(
            "%s of %s existing concepts share the current embedding model; the rest "
            "cannot be compared",
            len(comparable),
            len(existing),
        )

    best_matches: list[tuple[KnowledgeConcept, list[float], CourseConcept | None, float]] = []
    for concept, vector in zip(pending, vectors):
        best: CourseConcept | None = None
        best_score = 0.0
        for candidate in comparable:
            score = cosine_similarity(vector, candidate.embedding)
            if score > best_score:
                best, best_score = candidate, score
        best_matches.append((concept, vector, best, best_score))

    ambiguous = [
        (index, match)
        for index, match in enumerate(best_matches)
        if match[2] is not None and CANDIDATE_SIMILARITY <= match[3] < AUTO_MERGE_SIMILARITY
    ]

    verdicts: dict[int, bool] = {}
    if ambiguous:
        pairs = [
            (
                render_for_embedding(match[0].name, match[0].summary),
                render_for_embedding(match[2].name, match[2].summary),
            )
            for _, match in ambiguous
        ]
        try:
            answers = provider.are_same_concept(pairs)
            verdicts = {index: answer for (index, _), answer in zip(ambiguous, answers)}
        except Exception as exc:  # noqa: BLE001 -- fall back to keeping them separate
            logger.warning("Concept adjudication failed, leaving %s pair(s) unmerged: %s", len(pairs), exc)

    for index, (concept, vector, best, score) in enumerate(best_matches):
        merge = best is not None and (
            score >= AUTO_MERGE_SIMILARITY or verdicts.get(index, False)
        )

        if merge:
            concept.course_concept_id = best.id
            continue

        canonical = CourseConcept(
            student_id=student_id,
            course_id=course_id,
            name=_unique_name(db, student_id, course_id, concept.name),
            summary=concept.summary,
            embedding=vector,
            embedding_model=embedding_model,
        )
        db.add(canonical)
        db.flush()
        concept.course_concept_id = canonical.id
        # Visible to later concepts in this same batch, so a document that
        # mentions one idea twice does not create two canonical entries.
        comparable.append(canonical)

    db.commit()


def _unique_name(db: Session, student_id: uuid.UUID, course_id: uuid.UUID, name: str) -> str:
    """Keep names unique per (student, course) without losing the distinction.

    Two genuinely different concepts can share a name once truncated; the
    unique constraint exists so the knowledge base reads as a glossary.
    """
    candidate = name[:255]
    suffix = 2
    while (
        db.query(CourseConcept)
        .filter(
            CourseConcept.student_id == student_id,
            CourseConcept.course_id == course_id,
            CourseConcept.name == candidate,
        )
        .first()
        is not None
    ):
        candidate = f"{name[:248]} ({suffix})"
        suffix += 1
    return candidate
