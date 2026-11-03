import logging
import re
import uuid
from datetime import time
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.course import Course
from app.models.schedule import LectureSlot
from app.models.user import User
from app.schemas.assessment import NewBadge
from app.schemas.schedule import (
    ReflectionCreate,
    ReflectionResult,
    SlotBulkCreate,
    SlotCreate,
    SlotProposal,
    SlotRead,
    SlotUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedule", tags=["schedule"])

# Under Vercel's 4.5MB request limit. The browser shrinks photos before
# sending, so this only bites for an unusually large PDF.
MAX_TIMETABLE_BYTES = 4 * 1024 * 1024

_IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
_TEXT_TYPES = {".docx", ".pptx", ".txt", ".md"}
_HHMM = re.compile(r"^(\d{1,2}):(\d{2})")


def _course_codes(db: Session, student_id: uuid.UUID) -> dict[uuid.UUID, str]:
    return dict(db.query(Course.id, Course.code).filter(Course.owner_id == student_id).all())


def _as_read(slot: LectureSlot, codes: dict[uuid.UUID, str]) -> SlotRead:
    read = SlotRead.model_validate(slot)
    read.course_code = codes.get(slot.course_id) if slot.course_id else None
    return read


def _check_course(db: Session, course_id: uuid.UUID | None, user: User) -> None:
    if course_id is None:
        return
    course = db.get(Course, course_id)
    if course is None or course.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Course not found")


def _own_slot(db: Session, slot_id: uuid.UUID, user: User) -> LectureSlot:
    slot = db.get(LectureSlot, slot_id)
    if slot is None or slot.student_id != user.id:
        raise HTTPException(status_code=404, detail="Lecture not found")
    return slot


@router.get("", response_model=list[SlotRead])
def list_slots(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[SlotRead]:
    slots = (
        db.query(LectureSlot)
        .filter(LectureSlot.student_id == current_user.id)
        .order_by(LectureSlot.day_of_week, LectureSlot.start_time)
        .all()
    )
    codes = _course_codes(db, current_user.id)
    return [_as_read(slot, codes) for slot in slots]


@router.post("", response_model=SlotRead, status_code=status.HTTP_201_CREATED)
def create_slot(
    payload: SlotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SlotRead:
    _check_course(db, payload.course_id, current_user)
    slot = LectureSlot(student_id=current_user.id, **payload.model_dump())
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return _as_read(slot, _course_codes(db, current_user.id))


@router.post("/bulk", response_model=list[SlotRead], status_code=status.HTTP_201_CREATED)
def create_slots(
    payload: SlotBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SlotRead]:
    """Save a whole confirmed timetable at once."""
    for slot in payload.slots:
        _check_course(db, slot.course_id, current_user)
    if payload.replace:
        db.query(LectureSlot).filter(LectureSlot.student_id == current_user.id).delete()

    created = [LectureSlot(student_id=current_user.id, **slot.model_dump()) for slot in payload.slots]
    db.add_all(created)
    db.commit()
    codes = _course_codes(db, current_user.id)
    return [_as_read(slot, codes) for slot in created]


@router.get("/{slot_id}", response_model=SlotRead)
def get_slot(
    slot_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SlotRead:
    return _as_read(_own_slot(db, slot_id, current_user), _course_codes(db, current_user.id))


@router.patch("/{slot_id}", response_model=SlotRead)
def update_slot(
    slot_id: uuid.UUID,
    payload: SlotUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SlotRead:
    slot = _own_slot(db, slot_id, current_user)
    changes = payload.model_dump(exclude_unset=True)
    if "course_id" in changes:
        _check_course(db, changes["course_id"], current_user)
    for field, value in changes.items():
        setattr(slot, field, value)
    if slot.start_time == slot.end_time:
        raise HTTPException(status_code=422, detail="A lecture must end after it starts")
    db.commit()
    db.refresh(slot)
    return _as_read(slot, _course_codes(db, current_user.id))


@router.delete("/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_slot(
    slot_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    db.delete(_own_slot(db, slot_id, current_user))
    db.commit()


def _parse_time(value: str) -> time | None:
    match = _HHMM.match(value.strip())
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        return None
    return time(hour, minute)


def _match_course(code: str, title: str, courses: list[Course]) -> Course | None:
    def squash(text: str) -> str:
        return re.sub(r"[^a-z0-9]", "", text.lower())

    wanted = {squash(code), squash(title)} - {""}
    for course in courses:
        # Contained rather than equal: timetables often write "CSCD 418 (L)".
        key = squash(course.code)
        if key and any(key in candidate for candidate in wanted):
            return course
    return None


@router.post("/read", response_model=list[SlotProposal])
async def read_timetable(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SlotProposal]:
    """Read an uploaded timetable into proposed slots for the student to confirm.

    Nothing is saved here: a misread time would mistime every reminder for the
    semester, so the student reviews and edits the rows first.
    """
    data = await file.read()
    if len(data) > MAX_TIMETABLE_BYTES:
        raise HTTPException(status_code=400, detail="That file is too large (max 4MB). Try a screenshot instead.")

    suffix = Path(file.filename or "").suffix.lower()
    extra_text = ""
    if suffix in _IMAGE_TYPES:
        mime_type = _IMAGE_TYPES[suffix]
    elif suffix == ".pdf":
        mime_type = "application/pdf"
    elif suffix in _TEXT_TYPES:
        import tempfile

        from app.services.extraction import extract_text

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / f"timetable{suffix}"
            target.write_bytes(data)
            extra_text = extract_text(str(target))
        data, mime_type = b"", "text/plain"
    else:
        raise HTTPException(
            status_code=400,
            detail="Upload a photo or screenshot (PNG, JPG, WEBP), a PDF, or a Word document.",
        )

    courses = db.query(Course).filter(Course.owner_id == current_user.id).all()

    from app.services.ai import get_ai_provider
    from app.services.failures import describe

    try:
        entries = get_ai_provider().read_timetable(
            data, mime_type, [(c.code, c.name) for c in courses], extra_text
        )
    except Exception as exc:  # noqa: BLE001 -- reported to the student
        logger.warning("Timetable reading failed: %s", exc)
        message, _ = describe(exc)
        raise HTTPException(status_code=502, detail=message)

    proposals = []
    for entry in entries:
        start, end = _parse_time(entry.start_time), _parse_time(entry.end_time)
        if start is None or end is None or start == end or not 0 <= entry.day_of_week <= 6:
            continue
        course = _match_course(entry.course_code, entry.title, courses)
        proposals.append(
            SlotProposal(
                title=entry.title.strip()[:255] or entry.course_code,
                course_id=course.id if course else None,
                course_code=course.code if course else entry.course_code,
                day_of_week=entry.day_of_week,
                start_time=start,
                end_time=end,
                venue=entry.venue.strip()[:255],
            )
        )
    if not proposals:
        raise HTTPException(
            status_code=422,
            detail="No lectures could be read from that file. Try a clearer photo, or add them by hand.",
        )
    return proposals


@router.post("/{slot_id}/reflection", response_model=ReflectionResult, status_code=status.HTTP_201_CREATED)
def add_reflection(
    slot_id: uuid.UUID,
    payload: ReflectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReflectionResult:
    """Save what the student says they learnt, as notes in that course.

    Filed as an ordinary typed-notes document, so it is read for concepts and
    feeds the knowledge base, quizzes and games like any other material.
    """
    from datetime import date

    from app.api.routers.documents import _register, _safe_filename, _storage_path
    from app.services.gamification import record_reflection
    from app.services.storage import get_storage

    slot = _own_slot(db, slot_id, current_user)
    course_id = payload.course_id or slot.course_id
    if course_id is None:
        raise HTTPException(status_code=400, detail="Choose which course these notes belong to.")
    _check_course(db, course_id, current_user)
    if slot.course_id is None:
        # Remember the choice, so next week's prompt goes straight there.
        slot.course_id = course_id

    safe_name = f"{_safe_filename(f'{slot.title} - reflection {date.today().isoformat()}')}.txt"
    document_id = uuid.uuid4()
    get_storage().upload(
        _storage_path(current_user.id, course_id, document_id, safe_name),
        payload.content.encode("utf-8"),
        "text/plain; charset=utf-8",
    )
    document = _register(db, current_user, course_id, document_id, safe_name)
    badges = record_reflection(db, current_user.id)
    db.commit()
    return ReflectionResult(
        document_id=document.id,
        course_id=course_id,
        new_badges=[NewBadge(code=b.code, name=b.name, description=b.description) for b in badges],
    )
