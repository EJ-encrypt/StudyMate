"""Where in a student's material a concept is explained: which file, which page or slide.

Slides have carried "Slide N" lines since the start; PDFs and AI
transcriptions carry "Page N" lines from November 2026 on. Older uploads have
no markers, so for them only the file is named.
"""

import re
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.document import KnowledgeConcept, LectureDocument

_MARKER = re.compile(r"^(Page|Slide) (\d+)\s*$", re.MULTILINE)
_PARENTHETICAL = re.compile(r"\s*\([^)]*\)")
_STOPWORDS = {"the", "a", "an", "of", "and", "in", "to", "for", "on", "with", "its", "their"}


@dataclass
class Source:
    document_id: uuid.UUID
    filename: str
    # "Slide 4", "Page 2", or None when the place cannot be pinned down.
    location: str | None


def _search_terms(name: str) -> list[str]:
    """The concept's name, then looser forms of it, most specific first."""
    terms = [name, _PARENTHETICAL.sub("", name)]
    inside = re.findall(r"\(([^)]+)\)", name)
    terms.extend(inside)
    words = [w for w in re.findall(r"[A-Za-z0-9']+", name) if w.lower() not in _STOPWORDS]
    if len(words) > 2:
        terms.append(" ".join(words[:2]))
    return [t.strip() for t in dict.fromkeys(terms) if len(t.strip()) >= 3]


def locate(text: str | None, name: str) -> str | None:
    """The page or slide where `name` first appears in `text`, if the text marks them."""
    if not text or not _MARKER.search(text):
        return None
    lowered = text.lower()
    for term in _search_terms(name):
        position = lowered.find(term.lower())
        if position == -1:
            continue
        marker = None
        for match in _MARKER.finditer(text, 0, position):
            marker = match
        if marker:
            return f"{marker.group(1)} {marker.group(2)}"
    return None


def concept_sources(db: Session, concept_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[Source]]:
    """Every file each concept came from, with the page or slide where possible."""
    if not concept_ids:
        return {}
    rows = (
        db.query(KnowledgeConcept.course_concept_id, KnowledgeConcept.name, LectureDocument)
        .join(LectureDocument, KnowledgeConcept.document_id == LectureDocument.id)
        .filter(KnowledgeConcept.course_concept_id.in_(concept_ids))
        .order_by(LectureDocument.created_at)
        .all()
    )
    found: dict[uuid.UUID, list[Source]] = {}
    for concept_id, mention_name, document in rows:
        sources = found.setdefault(concept_id, [])
        if any(source.document_id == document.id for source in sources):
            continue
        sources.append(Source(document.id, document.filename, locate(document.extracted_text, mention_name)))
    return found
