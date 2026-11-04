"""Reading a one-off upload (a timetable, a course list) for the AI to look at.

These are sent straight to the API rather than through storage: they are
read once, never kept, and small enough to fit under Vercel's request limit
once the browser has shrunk any photo.
"""

import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.services.extraction import IMAGE_TYPES, extract_text

# Under Vercel's 4.5MB request limit. The browser shrinks photos before
# sending, so this only bites for an unusually large PDF.
MAX_READ_BYTES = 4 * 1024 * 1024

_TEXT_TYPES = {".docx", ".pptx", ".txt", ".md"}


async def read_upload(file: UploadFile, what: str) -> tuple[bytes, str, str]:
    """(data, mime type, extracted text) for an uploaded image, PDF or document.

    Images and PDFs go to the model as they are, since layout is half of what
    a timetable or course list says. Word and PowerPoint files are not
    accepted by the models directly, so their text is sent instead.
    """
    data = await file.read()
    if len(data) > MAX_READ_BYTES:
        raise HTTPException(status_code=400, detail="That file is too large (max 4MB). Try a screenshot instead.")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix in IMAGE_TYPES:
        return data, IMAGE_TYPES[suffix], ""
    if suffix == ".pdf":
        return data, "application/pdf", ""
    if suffix in _TEXT_TYPES:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / f"upload{suffix}"
            target.write_bytes(data)
            return b"", "text/plain", extract_text(str(target))
    raise HTTPException(
        status_code=400,
        detail=f"Upload {what} as a photo or screenshot (PNG, JPG, WEBP), a PDF, or a Word document.",
    )
