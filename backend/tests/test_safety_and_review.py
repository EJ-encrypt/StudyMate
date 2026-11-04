"""AI usage limits, blocking and reporting, flashcard spaced repetition, the daily goal."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.assessment import Assessment, AssessmentItem, AssessmentKind, AssessmentStatus, ItemKind
from app.models.document import CourseConcept
from app.models.review import FlashcardReview
from app.models.social import Challenge, GameRound, UserReport
from app.models.usage import AiUsage
from app.services import review
from tests.helpers import auth_headers
from tests.test_social_and_new_games import _befriend, _student


def _concept(db: Session, student_id: uuid.UUID, course_id: str) -> None:
    db.add(CourseConcept(student_id=student_id, course_id=uuid.UUID(course_id), name="Normalisation",
                         summary="Removing redundancy.", embedding=[1.0, 0.0], embedding_model="test"))
    db.commit()


def _flashcards(db: Session, student_id: uuid.UUID, course_id: str, count: int = 3) -> list[AssessmentItem]:
    assessment = Assessment(student_id=student_id, course_id=uuid.UUID(course_id), title="Cards",
                            kind=AssessmentKind.FLASHCARD, status=AssessmentStatus.COMPLETED)
    db.add(assessment)
    db.flush()
    items = [
        AssessmentItem(assessment_id=assessment.id, position=i, kind=ItemKind.FLASHCARD,
                       question=f"Term {i}", answer=f"Definition {i}", options=[], explanation="")
        for i in range(count)
    ]
    db.add_all(items)
    db.commit()
    return items


# --- AI usage limits ------------------------------------------------------------


def test_question_sets_stop_at_the_daily_limit(client: TestClient, db: Session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "limit_generate_per_day", 2)
    headers, course_id, me = _student(client, "limit@example.com")
    _concept(db, me, course_id)

    for _ in range(2):
        assert client.post("/assessments", headers=headers, json={"course_id": course_id, "kind": "mcq"}).status_code == 201
    refused = client.post("/assessments", headers=headers, json={"course_id": course_id, "kind": "mcq"})
    assert refused.status_code == 429
    assert "limit of 2 new question sets" in refused.json()["detail"]

    # A rolling window: usage from over a day ago no longer counts.
    for row in db.query(AiUsage).filter(AiUsage.student_id == me):
        row.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
    db.commit()
    assert client.post("/assessments", headers=headers, json={"course_id": course_id, "kind": "mcq"}).status_code == 201


def test_limits_are_per_student(client: TestClient, db: Session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "limit_generate_per_day", 1)
    first, course_a, a = _student(client, "first@example.com")
    second, course_b, b = _student(client, "second@example.com")
    _concept(db, a, course_a)
    _concept(db, b, course_b)
    assert client.post("/assessments", headers=first, json={"course_id": course_a, "kind": "mcq"}).status_code == 201
    assert client.post("/assessments", headers=first, json={"course_id": course_a, "kind": "mcq"}).status_code == 429
    assert client.post("/assessments", headers=second, json={"course_id": course_b, "kind": "mcq"}).status_code == 201


def test_uploads_are_refused_before_any_file_is_sent(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "limit_documents_per_day", 2)
    headers, course_id, _ = _student(client, "uploads@example.com")
    for title in ("One", "Two"):
        assert client.post("/documents/notes", headers=headers,
                           json={"course_id": course_id, "title": title, "content": "Some notes."}).status_code == 201
    refused = client.post("/documents/uploads", headers=headers,
                          json={"course_id": course_id, "files": [{"filename": "a.pdf", "size": 100}]})
    assert refused.status_code == 429
    assert client.post("/documents/notes", headers=headers,
                       json={"course_id": course_id, "title": "Three", "content": "More."}).status_code == 429


# --- Blocking and reporting -------------------------------------------------------


def test_blocking_ends_the_friendship_and_hides_the_blocker(client: TestClient, db: Session) -> None:
    ama, course_id, ama_id = _student(client, "ama@example.com", "ama")
    kofi, _, kofi_id = _student(client, "kofi@example.com", "kofi")
    _befriend(client, ama, kofi, "kofi")

    round_ = GameRound(student_id=ama_id, course_id=uuid.UUID(course_id), game="true_false", payload={},
                       submitted_at=datetime.now(timezone.utc), score=100)
    db.add(round_)
    db.flush()
    db.add(Challenge(round_id=round_.id, challenger_id=ama_id, opponent_id=kofi_id, game="true_false",
                     title="CS3", challenger_score=100, status="open",
                     expires_at=datetime.now(timezone.utc) + timedelta(hours=48)))
    db.commit()

    assert client.post(f"/users/{kofi_id}/block", headers=ama).status_code == 204
    assert client.get("/friends", headers=ama).json()["friends"] == []
    assert db.query(Challenge).one().status == "expired"
    assert [b["username"] for b in client.get("/blocks", headers=ama).json()] == ["kofi"]

    # To Kofi, Ama's username now looks like nobody's; and Ama cannot add Kofi either.
    hidden = client.post("/friends/requests", headers=kofi, json={"username": "ama"})
    assert hidden.status_code == 404
    assert "Nobody has that username" in hidden.json()["detail"]
    assert client.post("/friends/requests", headers=ama, json={"username": "kofi"}).status_code == 404

    assert client.delete(f"/users/{kofi_id}/block", headers=ama).status_code == 204
    assert client.post("/friends/requests", headers=kofi, json={"username": "ama"}).status_code == 201


def test_blocked_students_leave_the_programme_board(client: TestClient) -> None:
    ama, _, _ = _student(client, "ama@example.com", "ama")
    yaw, _, yaw_id = _student(client, "yaw@example.com", "yaw")
    for headers in (ama, yaw):
        client.patch("/auth/me/preferences", headers=headers, json={"public_leaderboard": True})

    def board(headers):
        return [s["username"] for s in client.get("/leaderboard", headers=headers,
                                                   params={"scope": "programme", "period": "all"}).json()["standings"]]

    assert sorted(board(ama)) == ["ama", "yaw"]
    client.post(f"/users/{yaw_id}/block", headers=ama)
    assert board(ama) == ["ama"]
    assert board(yaw) == ["yaw"]


def test_report_is_stored_and_blocks_by_default(client: TestClient, db: Session) -> None:
    ama, _, ama_id = _student(client, "ama@example.com", "ama")
    _, _, spam_id = _student(client, "spam@example.com", "spammer")

    sent = client.post(f"/users/{spam_id}/report", headers=ama,
                       json={"reason": "spam", "details": "Sends requests all day."})
    assert sent.status_code == 201
    report = db.query(UserReport).one()
    assert (report.reporter_id, report.reported_id, report.reason, report.status) == (ama_id, spam_id, "spam", "open")
    assert [b["username"] for b in client.get("/blocks", headers=ama).json()] == ["spammer"]

    assert client.post(f"/users/{spam_id}/report", headers=ama, json={"reason": "nonsense"}).status_code == 422
    assert client.post(f"/users/{ama_id}/report", headers=ama, json={"reason": "spam"}).status_code == 400


def test_deleting_an_account_removes_its_blocks_reports_and_usage(client: TestClient, db: Session) -> None:
    ama, course_id, ama_id = _student(client, "ama@example.com", "ama")
    _, _, kofi_id = _student(client, "kofi@example.com", "kofi")
    client.post(f"/users/{kofi_id}/report", headers=ama, json={"reason": "username"})
    client.post("/documents/notes", headers=ama, json={"course_id": course_id, "title": "N", "content": "Notes."})
    items = _flashcards(db, ama_id, course_id, 1)
    client.post(f"/flashcards/{items[0].id}/review", headers=ama, json={"remembered": True})

    assert client.delete("/auth/me", headers=ama).status_code == 204
    assert db.query(UserReport).count() == 0
    assert db.query(AiUsage).count() == 0
    assert db.query(FlashcardReview).count() == 0


# --- Spaced repetition --------------------------------------------------------------


def test_cards_move_through_the_boxes(client: TestClient, db: Session) -> None:
    headers, course_id, me = _student(client, "cards@example.com")
    known, missed, _ = _flashcards(db, me, course_id)

    first = client.post(f"/flashcards/{known.id}/review", headers=headers, json={"remembered": True}).json()
    assert first["box"] == 2
    again = client.post(f"/flashcards/{missed.id}/review", headers=headers, json={"remembered": False}).json()
    assert again["box"] == 1

    # Nothing is due straight after a review.
    assert client.get("/flashcards/due", headers=headers).json()["items"] == []

    # The missed card is due after one day, the known one after three.
    db.query(FlashcardReview).filter(FlashcardReview.item_id == missed.id).one().due_at -= timedelta(days=1)
    db.commit()
    assert [i["id"] for i in client.get("/flashcards/due", headers=headers).json()["items"]] == [str(missed.id)]
    db.query(FlashcardReview).filter(FlashcardReview.item_id == known.id).one().due_at -= timedelta(days=3)
    db.commit()
    due = client.get("/flashcards/due", headers=headers, params={"course_id": course_id}).json()["items"]
    assert {item["id"] for item in due} == {str(known.id), str(missed.id)}
    assert all(item["answer"] for item in due), "flashcards carry their answers"
    per_course = client.get("/flashcards/due/courses", headers=headers).json()
    assert per_course == [{"course_id": course_id, "code": "CS3", "name": "Systems", "due": 2}]

    # Remembering moves a card up; forgetting sends it back to the first box.
    assert client.post(f"/flashcards/{known.id}/review", headers=headers, json={"remembered": True}).json()["box"] == 3
    assert client.post(f"/flashcards/{known.id}/review", headers=headers, json={"remembered": False}).json()["box"] == 1


def test_top_box_and_intervals() -> None:
    assert [review.INTERVAL_DAYS[box] for box in range(1, 6)] == [1, 3, 7, 14, 30]
    assert review.TOP_BOX == 5


def test_only_your_own_flashcards_can_be_reviewed(client: TestClient, db: Session) -> None:
    _, course_id, owner = _student(client, "owner@example.com")
    (card,) = _flashcards(db, owner, course_id, 1)
    other = auth_headers("other@example.com")
    assert client.post(f"/flashcards/{card.id}/review", headers=other, json={"remembered": True}).status_code == 404


# --- Daily goal -----------------------------------------------------------------------


def test_daily_goal_counts_rounds_quizzes_and_cards(client: TestClient, db: Session) -> None:
    headers, course_id, me = _student(client, "goal@example.com")
    progress = client.get("/profile/progress", headers=headers).json()
    assert (progress["daily_goal"], progress["done_today"]) == (3, 0)

    db.add(GameRound(student_id=me, course_id=uuid.UUID(course_id), game="true_false", payload={},
                     submitted_at=datetime.now(timezone.utc), score=10))
    # Dealt but never finished: does not count.
    db.add(GameRound(student_id=me, course_id=uuid.UUID(course_id), game="true_false", payload={}))
    db.commit()
    for card in _flashcards(db, me, course_id, 10):
        client.post(f"/flashcards/{card.id}/review", headers=headers, json={"remembered": True})

    assert client.patch("/auth/me/preferences", headers=headers, json={"daily_goal": 5}).status_code == 200
    progress = client.get("/profile/progress", headers=headers).json()
    assert (progress["daily_goal"], progress["done_today"]) == (5, 2)
    assert client.patch("/auth/me/preferences", headers=headers, json={"daily_goal": 0}).status_code == 422


def test_deep_health_check_reaches_the_database(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/health", params={"deep": 1}).json() == {"status": "ok", "database": "ok"}
