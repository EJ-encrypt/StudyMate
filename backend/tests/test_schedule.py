import uuid
from datetime import date, datetime, time, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import LectureDocument
from app.models.schedule import LectureSlot, SentReminder
from app.models.user import User
from app.services import reminders
from app.services.ai.base import TimetableEntry
from tests.helpers import auth_headers

# A Monday, so day_of_week 0 is "today" in these tests.
MONDAY = date(2026, 11, 2)


def _slot_payload(**overrides) -> dict:
    payload = {
        "title": "Database Systems",
        "day_of_week": 0,
        "start_time": "09:00",
        "end_time": "11:00",
        "venue": "JQB 19",
    }
    payload.update(overrides)
    return payload


def test_create_list_update_delete_a_lecture(client: TestClient) -> None:
    headers = auth_headers("timetable@example.com")
    course = client.post("/courses", json={"name": "Databases", "code": "CS302"}, headers=headers).json()

    created = client.post("/schedule", headers=headers, json=_slot_payload(course_id=course["id"]))
    assert created.status_code == 201
    assert created.json()["course_code"] == "CS302"

    client.post("/schedule", headers=headers, json=_slot_payload(title="Networks", day_of_week=2))
    listed = client.get("/schedule", headers=headers).json()
    assert [s["title"] for s in listed] == ["Database Systems", "Networks"]

    slot_id = created.json()["id"]
    updated = client.patch(f"/schedule/{slot_id}", headers=headers, json={"venue": "N Block"}).json()
    assert updated["venue"] == "N Block"

    assert client.delete(f"/schedule/{slot_id}", headers=headers).status_code == 204
    assert len(client.get("/schedule", headers=headers).json()) == 1


def test_rejects_a_lecture_with_no_length(client: TestClient) -> None:
    response = client.post(
        "/schedule", headers=auth_headers("zero@example.com"), json=_slot_payload(end_time="09:00")
    )
    assert response.status_code == 422


def test_lectures_are_private(client: TestClient) -> None:
    slot = client.post("/schedule", headers=auth_headers("owner@example.com"), json=_slot_payload()).json()
    other = auth_headers("snoop@example.com")
    assert client.get(f"/schedule/{slot['id']}", headers=other).status_code == 404
    assert client.get("/schedule", headers=other).json() == []


def test_bulk_save_can_replace_the_timetable(client: TestClient) -> None:
    headers = auth_headers("bulk@example.com")
    client.post("/schedule", headers=headers, json=_slot_payload(title="Old"))
    response = client.post(
        "/schedule/bulk",
        headers=headers,
        json={"replace": True, "slots": [_slot_payload(title="New A"), _slot_payload(title="New B", day_of_week=4)]},
    )
    assert response.status_code == 201
    assert [s["title"] for s in client.get("/schedule", headers=headers).json()] == ["New A", "New B"]


def test_reading_a_timetable_proposes_slots_and_matches_courses(client: TestClient) -> None:
    headers = auth_headers("reader@example.com")
    course = client.post("/courses", json={"name": "Databases", "code": "CSCD 302"}, headers=headers).json()

    provider = MagicMock()
    provider.read_timetable.return_value = [
        TimetableEntry(title="Databases", course_code="CSCD302", day_of_week=1, start_time="08:30",
                       end_time="10:30", venue="JQB"),
        TimetableEntry(title="Ethics", course_code="", day_of_week=3, start_time="13:00", end_time="14:00", venue=""),
        # Unreadable rows are dropped rather than saved with a guessed time.
        TimetableEntry(title="Mystery", course_code="", day_of_week=9, start_time="??", end_time="", venue=""),
    ]
    with patch("app.services.ai.get_ai_provider", return_value=provider):
        response = client.post(
            "/schedule/read", headers=headers, files={"file": ("timetable.png", b"\x89PNG fake", "image/png")}
        )

    assert response.status_code == 200, response.text
    proposals = response.json()
    assert [p["title"] for p in proposals] == ["Databases", "Ethics"]
    assert proposals[0]["course_id"] == course["id"]
    assert proposals[0]["start_time"] == "08:30:00"
    assert proposals[1]["course_id"] is None
    assert provider.read_timetable.call_args.args[1] == "image/png"
    # Nothing is saved until the student confirms.
    assert client.get("/schedule", headers=headers).json() == []


def test_reading_rejects_unsupported_files(client: TestClient) -> None:
    response = client.post(
        "/schedule/read", headers=auth_headers("mp3@example.com"), files={"file": ("x.mp3", b"id3", "audio/mpeg")}
    )
    assert response.status_code == 400


def test_reflection_is_filed_as_notes_and_remembers_the_course(client: TestClient, db: Session) -> None:
    headers = auth_headers("reflect@example.com")
    course = client.post("/courses", json={"name": "Databases", "code": "CS302"}, headers=headers).json()
    slot = client.post("/schedule", headers=headers, json=_slot_payload()).json()

    missing_course = client.post(f"/schedule/{slot['id']}/reflection", headers=headers, json={"content": "x"})
    assert missing_course.status_code == 400

    response = client.post(
        f"/schedule/{slot['id']}/reflection",
        headers=headers,
        json={"content": "Today we covered BCNF and lossless joins.", "course_id": course["id"]},
    )
    assert response.status_code == 201
    assert "reflective" in {b["code"] for b in response.json()["new_badges"]}
    document = db.get(LectureDocument, uuid.UUID(response.json()["document_id"]))
    assert document.filename.startswith("Database Systems - reflection")
    assert client.get(f"/schedule/{slot['id']}", headers=headers).json()["course_id"] == course["id"]


# --- Reminder timing ---------------------------------------------------------


def _student_with_slot(db: Session, tz: str = "Africa/Accra", **slot) -> tuple[User, LectureSlot]:
    user = User(id=uuid.uuid4(), email=f"{uuid.uuid4().hex[:8]}@example.com", full_name="R", timezone=tz)
    db.add(user)
    db.flush()
    lecture = LectureSlot(
        student_id=user.id,
        title=slot.get("title", "Databases"),
        day_of_week=slot.get("day_of_week", 0),
        start_time=slot.get("start_time", time(9, 0)),
        end_time=slot.get("end_time", time(11, 0)),
        venue="JQB",
    )
    db.add(lecture)
    db.commit()
    return user, lecture


def _at(hour: int, minute: int, day: date = MONDAY) -> datetime:
    # Accra is UTC+0 all year, which keeps these readable.
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=timezone.utc)


def test_reminders_fire_before_at_start_and_after(db: Session) -> None:
    _student_with_slot(db)
    assert [r.kind for r in reminders.find_due(db, _at(7, 59))] == []
    assert [r.kind for r in reminders.find_due(db, _at(8, 0))] == ["before"]
    assert [r.kind for r in reminders.find_due(db, _at(9, 5))] == ["start"]
    assert [r.kind for r in reminders.find_due(db, _at(11, 2))] == ["after"]
    assert [r.kind for r in reminders.find_due(db, _at(11, 30))] == [], "the window has passed"


def test_reminders_use_the_students_time_zone(db: Session) -> None:
    # A 09:00 lecture in Lagos (UTC+1) starts at 08:00 UTC.
    _student_with_slot(db, tz="Africa/Lagos")
    assert [r.kind for r in reminders.find_due(db, _at(8, 0))] == ["start"]


def test_reminders_skip_other_days_and_opted_out_students(db: Session) -> None:
    user, _ = _student_with_slot(db, day_of_week=3)
    assert reminders.find_due(db, _at(9, 0)) == []
    user.notify_push = user.notify_email = False
    db.commit()
    assert reminders.find_due(db, _at(9, 0, date(2026, 11, 5))) == []


def test_each_reminder_is_sent_once(db: Session) -> None:
    _student_with_slot(db)
    with patch("app.services.reminders.notify") as notify:
        assert reminders.send_due(db, _at(9, 0)) == 1
        assert reminders.send_due(db, _at(9, 1)) == 0
        assert reminders.send_due(db, _at(9, 4)) == 0
    notify.assert_called_once()
    assert db.query(SentReminder).count() == 1


def test_after_lecture_reminder_links_to_the_reflection_page(db: Session) -> None:
    _, slot = _student_with_slot(db)
    due = [r for r in reminders.find_due(db, _at(11, 0)) if r.kind == "after"][0]
    note = reminders.compose(db, due)
    assert note.path == f"/lectures/{slot.id}/reflect"
    assert "learnt" in note.body
