from pathlib import Path

from app.services.extraction.docx import extract_text_from_docx
from app.services.extraction.notes import extract_text_from_notes
from app.services.extraction.pdf import extract_text_from_pdf
from app.services.extraction.pptx import extract_text_from_pptx


class UnsupportedDocumentType(ValueError):
    pass


_EXTRACTORS = {
    ".pdf": extract_text_from_pdf,
    ".docx": extract_text_from_docx,
    ".pptx": extract_text_from_pptx,
    ".txt": extract_text_from_notes,
    ".md": extract_text_from_notes,
}

SUPPORTED_EXTENSIONS = frozenset(_EXTRACTORS)


def extract_text(path: str) -> str:
    """Pull plain text out of a lecture file, chosen by extension.

    Extension rather than the client-supplied content type: the upload
    endpoint validates the extension, so it is the value we control.
    """
    suffix = Path(path).suffix.lower()
    extractor = _EXTRACTORS.get(suffix)
    if extractor is None:
        raise UnsupportedDocumentType(f"Cannot extract text from '{suffix}' files")
    return extractor(path)
