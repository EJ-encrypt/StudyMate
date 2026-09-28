import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.course import Course
from app.models.document import LectureDocument
from app.models.user import User
from app.schemas.document import DocumentDetail, DocumentRead, NotesCreate
from app.services.extraction import SUPPORTED_EXTENSIONS
from app.workers.extraction_worker import process_document
from app.workers.queue import queue

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._ -]")


def _safe_filename(filename: str) -> str:
    """Reduce a client-supplied name to a bare, path-safe filename.

    The result is interpolated into a storage path, so directory
    components and separators must not survive.
    """
    base = Path(filename).name.replace("..", "")
    cleaned = _SAFE_FILENAME.sub("_", base).strip(" .")
    return cleaned or "document"


def _require_own_course(db: Session, course_id: uuid.UUID, current_user: User) -> Course:
    course = db.get(Course, course_id)
    if course is None or course.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def _store_document(
    db: Session,
    current_user: User,
    course_id: uuid.UUID,
    safe_name: str,
    contents: bytes,
) -> LectureDocument:
    """Persist an already-sanitised filename; callers validate the extension."""
    document_id = uuid.uuid4()
    student_dir = Path(settings.storage_dir) / str(current_user.id) / str(course_id)
    student_dir.mkdir(parents=True, exist_ok=True)
    storage_path = student_dir / f"{document_id}_{safe_name}"
    storage_path.write_bytes(contents)

    document = LectureDocument(
        id=document_id,
        student_id=current_user.id,
        course_id=course_id,
        filename=safe_name,
        storage_path=str(storage_path),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    queue.enqueue(process_document, str(document.id))
    return document


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    course_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LectureDocument:
    safe_name = _safe_filename(file.filename or "")
    if Path(safe_name).suffix.lower() not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Supported: {supported}")

    _require_own_course(db, course_id, current_user)

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")

    return _store_document(db, current_user, course_id, safe_name, contents)


@router.post("/notes", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_notes(
    payload: NotesCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LectureDocument:
    """Typed notes take the same path as uploads: saved as a .txt and queued."""
    _require_own_course(db, payload.course_id, current_user)

    safe_name = f"{_safe_filename(payload.title)}.txt"
    return _store_document(
        db, current_user, payload.course_id, safe_name, payload.content.encode("utf-8")
    )


@router.get("", response_model=list[DocumentRead])
def list_documents(
    course_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LectureDocument]:
    documents_query = db.query(LectureDocument).filter(LectureDocument.student_id == current_user.id)
    if course_id is not None:
        documents_query = documents_query.filter(LectureDocument.course_id == course_id)
    return documents_query.order_by(LectureDocument.created_at.desc()).all()


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LectureDocument:
    document = db.get(LectureDocument, document_id)
    if document is None or document.student_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
