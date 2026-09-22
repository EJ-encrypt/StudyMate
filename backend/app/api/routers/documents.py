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
from app.schemas.document import DocumentDetail, DocumentRead
from app.workers.extraction_worker import process_document
from app.workers.queue import queue

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    course_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LectureDocument:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported right now")

    course = db.get(Course, course_id)
    if course is None or course.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Course not found")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")

    document_id = uuid.uuid4()
    student_dir = Path(settings.storage_dir) / str(current_user.id) / str(course_id)
    student_dir.mkdir(parents=True, exist_ok=True)
    storage_path = student_dir / f"{document_id}_{file.filename}"
    storage_path.write_bytes(contents)

    document = LectureDocument(
        id=document_id,
        student_id=current_user.id,
        course_id=course_id,
        filename=file.filename,
        storage_path=str(storage_path),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    queue.enqueue(process_document, str(document.id))

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
