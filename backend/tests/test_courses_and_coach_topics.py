"""Deleting a course, where concepts are explained, and the Coach's topic explanations."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.assessment import Assessment, AssessmentItem, AssessmentKind, AssessmentStatus, ItemKind
from app.models.course import Course
from app.models.document import CourseConcept, DocumentStatus, KnowledgeConcept, LectureDocument
from app.models.game import GameSession
from app.models.mastery import ConceptMastery, TopicExplanation
from app.models.review import FlashcardReview
from app.models.schedule import LectureSlot
from app.models.social import Challenge, GameRound
from app.services.ai.base import ConceptLink
from app.services.ai.base import TopicExplanation as Written
from app.services.sources import locate
from tests.test_social_and_new_games import _student


def _course_with_everything(db: Session, student_id: uuid.UUID, course_id: str) -> dict:
    cid = uuid.UUID(course_id)
    document = LectureDocument(student_id=student_id, course_id=cid, filename="Week 1.pdf",
                               storage_path=f"{student_id}/{cid}/x_Week 1.pdf", status=DocumentStatus.COMPLETED,
                               extracted_text="Page 1\nIntro\n\nPage 2\nNormalisation removes redundancy.")
    db.add(document)
    db.flush()
    concept = CourseConcept(student_id=student_id, course_id=cid, name="Normalisation",
                            summary="Removing redundancy.", embedding=[1.0, 0.0], embedding_model="test")
    db.add(concept)
    db.flush()
    db.add(KnowledgeConcept(document_id=document.id, course_concept_id=concept.id, student_id=student_id,
                            course_id=cid, name="Normalisation", summary="Removing redundancy."))
    assessment = Assessment(student_id=student_id, course_id=cid, title="Cards",
                            kind=AssessmentKind.FLASHCARD, status=AssessmentStatus.COMPLETED)
    db.add(assessment)
    db.flush()
    item = AssessmentItem(assessment_id=assessment.id, position=0, kind=ItemKind.FLASHCARD,
                          question="Normalisation", answer="Removing redundancy.", options=[], explanation="",
                          course_concept_id=concept.id)
    db.add(item)
    db.flush()
    db.add(FlashcardReview(student_id=student_id, item_id=item.id, box=2, due_at=datetime.now(timezone.utc)))
    db.add(ConceptMastery(student_id=student_id, course_id=cid, course_concept_id=concept.id,
                          score=0.3, attempts=3, correct=1, last_seen_at=datetime.now(timezone.utc)))
    db.add(GameSession(student_id=student_id, course_id=cid, game="true_false", score=50, correct=1, total=2,
                       duration_ms=1000, xp_awarded=5))
    round_ = GameRound(student_id=student_id, course_id=cid, game="true_false", payload={},
                       submitted_at=datetime.now(timezone.utc), score=50)
    db.add(round_)
    db.flush()
    db.add(LectureSlot(student_id=student_id, course_id=cid, title="Databases", day_of_week=0,
                       start_time=datetime(2026, 1, 1, 9).time(), end_time=datetime(2026, 1, 1, 11).time()))
    db.commit()
    return {"document": document, "concept": concept, "round": round_}


# --- Deleting a course ------------------------------------------------------------


def test_deleting_a_course_removes_its_data_and_keeps_the_rest(client: TestClient, db: Session) -> None:
    headers, course_id, me = _student(client, "delete@example.com")
    other = client.post("/courses", headers=headers, json={"code": "KEEP1", "name": "Keep me"}).json()
    made = _course_with_everything(db, me, course_id)
    friend_headers, _, friend = _student(client, "friend@example.com")
    db.add(Challenge(round_id=made["round"].id, challenger_id=me, opponent_id=friend, game="true_false",
                     title="CS3", challenger_score=50, status="open",
                     expires_at=datetime.now(timezone.utc) + timedelta(hours=48)))
    db.commit()

    assert client.delete(f"/courses/{course_id}", headers=headers).status_code == 204

    assert db.get(Course, uuid.UUID(course_id)) is None
    for model in (LectureDocument, CourseConcept, KnowledgeConcept, Assessment, AssessmentItem, FlashcardReview,
                  ConceptMastery, GameSession, GameRound, Challenge):
        assert db.query(model).count() == 0, model.__name__
    # The lecture still happens; it is only unlinked from the deleted course.
    slot = db.query(LectureSlot).one()
    assert slot.course_id is None
    assert [c["id"] for c in client.get("/courses", headers=headers).json()] == [other["id"]]


def test_only_the_owner_can_delete_a_course(client: TestClient) -> None:
    _, course_id, _ = _student(client, "owner@example.com")
    stranger, _, _ = _student(client, "stranger@example.com")
    assert client.delete(f"/courses/{course_id}", headers=stranger).status_code == 404


# --- Where a concept is explained ----------------------------------------------------


def test_locate_finds_the_page_or_slide() -> None:
    text = "Slide 1\nWelcome\n\nSlide 2\nThe Translation Lookaside Buffer caches page table entries."
    assert locate(text, "Translation Lookaside Buffer (TLB)") == "Slide 2"
    assert locate("Page 1\nIntro\nPage 3\nDeadlock needs four conditions.", "Deadlock") == "Page 3"
    # No markers (older uploads, typed notes) or no mention: no location.
    assert locate("Deadlock needs four conditions.", "Deadlock") is None
    assert locate("Page 1\nNothing here", "Deadlock") is None


def test_revision_topics_carry_their_sources(client: TestClient, db: Session) -> None:
    headers, course_id, me = _student(client, "sources@example.com")
    _course_with_everything(db, me, course_id)
    topics = client.get(f"/coach/{course_id}", headers=headers).json()["topics"]
    (concept,) = topics[0]["concepts"]
    assert concept["sources"] == [
        {"document_id": concept["sources"][0]["document_id"], "filename": "Week 1.pdf", "location": "Page 2"}
    ]


# --- How a topic ties together ---------------------------------------------------------


def test_topic_explanation_is_written_once_then_kept(client: TestClient, db: Session) -> None:
    headers, course_id, me = _student(client, "explain@example.com")
    made = _course_with_everything(db, me, course_id)
    concept_id = str(made["concept"].id)
    provider = MagicMock()
    provider.explain_topic.return_value = Written(
        overview="These ideas are all about tidy tables.",
        links=[ConceptLink(name="normalisation", link="It is the method the others build on.")],
    )

    with patch("app.services.ai.get_ai_provider", return_value=provider):
        first = client.post(f"/coach/{course_id}/explain", headers=headers, json={"concept_ids": [concept_id]})
        again = client.post(f"/coach/{course_id}/explain", headers=headers, json={"concept_ids": [concept_id]})

    assert first.status_code == 200
    assert first.json() == {"overview": "These ideas are all about tidy tables.",
                            "links": {concept_id: "It is the method the others build on."}}
    assert again.json() == first.json()
    assert provider.explain_topic.call_count == 1
    (_, concepts), _ = provider.explain_topic.call_args
    assert concepts == [("Normalisation", "Removing redundancy.", True)]
    assert db.query(TopicExplanation).count() == 1


def test_topic_explanations_count_against_the_daily_limit(client: TestClient, db: Session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "limit_explanations_per_day", 0)
    headers, course_id, me = _student(client, "limit@example.com")
    made = _course_with_everything(db, me, course_id)
    refused = client.post(f"/coach/{course_id}/explain", headers=headers, json={"concept_ids": [str(made["concept"].id)]})
    assert refused.status_code == 429


def test_cannot_explain_someone_elses_concepts(client: TestClient, db: Session) -> None:
    _, course_id, owner = _student(client, "a@example.com")
    made = _course_with_everything(db, owner, course_id)
    headers, other_course, _ = _student(client, "b@example.com")
    response = client.post(f"/coach/{other_course}/explain", headers=headers, json={"concept_ids": [str(made["concept"].id)]})
    assert response.status_code == 404
