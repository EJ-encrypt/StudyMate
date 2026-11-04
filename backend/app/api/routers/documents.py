import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.course import Course
from app.models.document import DocumentStatus, LectureDocument
from app.models.user import User
from app.schemas.document import (
    DocumentDetail,
    DocumentRead,
    NotesCreate,
    UploadComplete,
    UploadRequest,
    UploadTargetRead,
)
from app.services import limits
from app.services.extraction import SUPPORTED_EXTENSIONS
from app.services.storage import LocalStorage, get_storage
from app.workers.jobs import PROCESS_DOCUMENT, enqueue

router = APIRouter(prefix="/documents", tags=["documents"])
storage_router = APIRouter(prefix="/storage", tags=["storage"])

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


def _storage_path(student_id: uuid.UUID, course_id: uuid.UUID, document_id: uuid.UUID, safe_name: str) -> str:
    # Derived on the server from ids it controls, never taken from the client,
    # so a student can only ever register files under their own prefix.
    return f"{student_id}/{course_id}/{document_id}_{safe_name}"


def _require_own_course(db: Session, course_id: uuid.UUID, current_user: User) -> Course:
    course = db.get(Course, course_id)
    if course is None or course.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def _validated_name(filename: str) -> str:
    safe_name = _safe_filename(filename)
    # Checked after sanitising, so it matches what the worker later dispatches on.
    if Path(safe_name).suffix.lower() not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"{filename}: unsupported file type. Supported: {supported}",
        )
    return safe_name


def _register(
    db: Session, current_user: User, course_id: uuid.UUID, document_id: uuid.UUID, safe_name: str
) -> LectureDocument:
    limits.spend(db, current_user.id, "document")
    document = LectureDocument(
        id=document_id,
        student_id=current_user.id,
        course_id=course_id,
        filename=safe_name,
        storage_path=_storage_path(current_user.id, course_id, document_id, safe_name),
    )
    db.add(document)
    db.flush()
    enqueue(db, PROCESS_DOCUMENT, {"document_id": str(document.id)}, current_user.id)
    return document


@router.post("/uploads", response_model=list[UploadTargetRead])
def request_uploads(
    payload: UploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UploadTargetRead]:
    """Step 1 of an upload: hand out a signed URL per file.

    Every file is validated before any URL is issued, so a bad file in the
    middle of a selection does not leave the earlier ones half-uploaded.
    """
    _require_own_course(db, payload.course_id, current_user)
    # Checked before anything is uploaded; counted when the uploads complete.
    limits.check(db, current_user.id, "document", len(payload.files))

    prepared: list[tuple[str, str]] = []
    for spec in payload.files:
        safe_name = _validated_name(spec.filename)
        if spec.size > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=400, detail=f"{spec.filename}: too large (max 20MB)")
        prepared.append((spec.filename, safe_name))

    storage = get_storage()
    targets = []
    for original, safe_name in prepared:
        document_id = uuid.uuid4()
        target = storage.create_upload(
            _storage_path(current_user.id, payload.course_id, document_id, safe_name)
        )
        targets.append(
            UploadTargetRead(
                document_id=document_id,
                filename=safe_name,
                original_filename=original,
                method=target.method,
                path=target.path,
                token=target.token,
                url=target.url,
            )
        )
    return targets


@router.post("/complete", response_model=list[DocumentRead], status_code=status.HTTP_201_CREATED)
def complete_uploads(
    payload: UploadComplete,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LectureDocument]:
    """Step 2: record the files the browser has finished uploading, and queue them."""
    _require_own_course(db, payload.course_id, current_user)

    documents = []
    for upload in payload.uploads:
        if db.get(LectureDocument, upload.document_id) is not None:
            raise HTTPException(status_code=409, detail=f"{upload.filename} was already added")
        documents.append(
            _register(db, current_user, payload.course_id, upload.document_id, _validated_name(upload.filename))
        )
    db.commit()
    for document in documents:
        db.refresh(document)
    return documents


@router.post("/notes", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_notes(
    payload: NotesCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LectureDocument:
    """Typed notes take the same path as uploads: saved as a .txt and queued."""
    _require_own_course(db, payload.course_id, current_user)

    safe_name = f"{_safe_filename(payload.title)}.txt"
    document_id = uuid.uuid4()
    get_storage().upload(
        _storage_path(current_user.id, payload.course_id, document_id, safe_name),
        payload.content.encode("utf-8"),
        "text/plain; charset=utf-8",
    )
    document = _register(db, current_user, payload.course_id, document_id, safe_name)
    db.commit()
    db.refresh(document)
    return document


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


@router.post("/{document_id}/retry", response_model=DocumentRead)
def retry_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LectureDocument:
    """Re-queue a document whose processing failed for a transient reason.

    The file is already stored, so this costs nothing but another attempt at
    the AI service - which is the whole point when the failure was a rate
    limit rather than a bad document.
    """
    document = db.get(LectureDocument, document_id)
    if document is None or document.student_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status is not DocumentStatus.FAILED:
        raise HTTPException(status_code=409, detail="This document has not failed")
    if not document.can_retry:
        raise HTTPException(
            status_code=409,
            detail="This document cannot be processed by retrying; the problem is with the file itself.",
        )

    document.status = DocumentStatus.PENDING
    document.error_message = None
    document.can_retry = False
    enqueue(db, PROCESS_DOCUMENT, {"document_id": str(document.id)}, current_user.id)
    db.commit()
    db.refresh(document)
    return document


@storage_router.put("/local/{token}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
async def local_upload(token: str, request: Request) -> None:
    """Stand-in for Supabase's signed upload URL when running without Supabase.

    The token is an HMAC over the path the API itself chose in step 1, so this
    cannot be used to write anywhere else.
    """
    if settings.uses_supabase_storage or settings.is_production:
        raise HTTPException(status_code=404)
    path = LocalStorage.verify_token(token)
    if path is None:
        raise HTTPException(status_code=403, detail="Invalid upload token")
    body = await request.body()
    if len(body) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")
    get_storage().upload(path, body)
