import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from tests.helpers import token_for
from sqlalchemy.orm import Session

from app.models.assessment import (
    Assessment,
    AssessmentItem,
    AssessmentKind,
    AssessmentStatus,
    ItemKind,
)
from app.models.document import DocumentStatus, LectureDocument
from app.models.job import Job
from app.services.ai.base import ShortAnswerGrade


def _register_and_login(client: TestClient, email: str) -> str:
    """A Supabase-style token; the account is created on its first request."""
    return token_for(email)


def _course_and_document(
    client: TestClient,
    db: Session,
    headers: dict,
    status: DocumentStatus = DocumentStatus.COMPLETED,
) -> tuple[str, LectureDocument]:
    course = client.post("/courses", json={"name": "OS", "code": "CS305"}, headers=headers).json()
    me = client.get("/auth/me", headers=headers).json()
    document = LectureDocument(
        student_id=uuid.UUID(me["id"]),
        course_id=uuid.UUID(course["id"]),
        filename="lecture.pdf",
        storage_path="storage/lecture.pdf",
        status=status,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return course["id"], document


def test_create_assessment_enqueues_generation(client: TestClient, db: Session) -> None:
    headers = {"Authorization": f"Bearer {_register_and_login(client, 'gen@example.com')}"}
    _, document = _course_and_document(client, db, headers)

    response = client.post(
        "/assessments",
        headers=headers,
        json={"document_id": str(document.id), "kind": "mcq", "count": 5},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["kind"] == "mcq"
    assert body["title"] == "Multiple choice - lecture.pdf"
    jobs = db.query(Job).all()
    assert len(jobs) == 1
    assert jobs[0].kind == "process_assessment"
    assert jobs[0].payload == {"assessment_id": body["id"], "count": 5}


def test_cannot_generate_from_unprocessed_document(client: TestClient, db: Session) -> None:
    headers = {"Authorization": f"Bearer {_register_and_login(client, 'pending-doc@example.com')}"}
    _, document = _course_and_document(client, db, headers, status=DocumentStatus.PENDING)

    response = client.post(
        "/assessments",
        headers=headers,
        json={"document_id": str(document.id), "kind": "mcq"},
    )
    assert response.status_code == 409


def test_cannot_generate_from_another_students_document(client: TestClient, db: Session) -> None:
    owner_headers = {"Authorization": f"Bearer {_register_and_login(client, 'doc-owner@example.com')}"}
    _, document = _course_and_document(client, db, owner_headers)
    other_headers = {"Authorization": f"Bearer {_register_and_login(client, 'intruder@example.com')}"}

    response = client.post(
        "/assessments",
        headers=other_headers,
        json={"document_id": str(document.id), "kind": "mcq"},
    )
    assert response.status_code == 404


def _completed_mcq(db: Session, student_id: uuid.UUID, course_id: uuid.UUID, document_id: uuid.UUID):
    assessment = Assessment(
        student_id=student_id,
        course_id=course_id,
        document_id=document_id,
        title="Multiple choice - lecture.pdf",
        kind=AssessmentKind.MCQ,
        status=AssessmentStatus.COMPLETED,
    )
    db.add(assessment)
    db.flush()
    items = [
        AssessmentItem(
            assessment_id=assessment.id,
            position=1,
            kind=ItemKind.MCQ,
            question="What must hold for deadlock?",
            answer="Circular wait",
            options=["Circular wait", "Preemption", "Paging", "Thrashing"],
            explanation="All four Coffman conditions are required.",
        ),
        AssessmentItem(
            assessment_id=assessment.id,
            position=2,
            kind=ItemKind.MCQ,
            question="What does the TLB cache?",
            answer="Page table entries",
            options=["Page table entries", "Disk blocks", "Registers", "Sockets"],
            explanation="It caches recent translations.",
        ),
    ]
    db.add_all(items)
    db.commit()
    for item in items:
        db.refresh(item)
    db.refresh(assessment)
    return assessment, items


def test_graded_items_withhold_the_answer_key(client: TestClient, db: Session) -> None:
    headers = {"Authorization": f"Bearer {_register_and_login(client, 'noleak@example.com')}"}
    course_id, document = _course_and_document(client, db, headers)
    me = client.get("/auth/me", headers=headers).json()
    assessment, _ = _completed_mcq(db, uuid.UUID(me["id"]), uuid.UUID(course_id), document.id)

    body = client.get(f"/assessments/{assessment.id}", headers=headers).json()

    assert len(body["items"]) == 2
    for item in body["items"]:
        assert item["answer"] is None
        assert item["explanation"] is None
        assert len(item["options"]) == 4


def test_flashcards_include_their_answer(client: TestClient, db: Session) -> None:
    headers = {"Authorization": f"Bearer {_register_and_login(client, 'cards@example.com')}"}
    course_id, document = _course_and_document(client, db, headers)
    me = client.get("/auth/me", headers=headers).json()

    assessment = Assessment(
        student_id=uuid.UUID(me["id"]),
        course_id=uuid.UUID(course_id),
        document_id=document.id,
        title="Flashcards - lecture.pdf",
        kind=AssessmentKind.FLASHCARD,
        status=AssessmentStatus.COMPLETED,
    )
    db.add(assessment)
    db.flush()
    db.add(
        AssessmentItem(
            assessment_id=assessment.id,
            position=1,
            kind=ItemKind.FLASHCARD,
            question="What is a deadlock?",
            answer="Processes each waiting on another in the set.",
            options=[],
        )
    )
    db.commit()
    db.refresh(assessment)

    body = client.get(f"/assessments/{assessment.id}", headers=headers).json()

    assert body["items"][0]["answer"] == "Processes each waiting on another in the set."


def test_submit_attempt_grades_and_reveals_answers(client: TestClient, db: Session) -> None:
    headers = {"Authorization": f"Bearer {_register_and_login(client, 'attempt@example.com')}"}
    course_id, document = _course_and_document(client, db, headers)
    me = client.get("/auth/me", headers=headers).json()
    assessment, items = _completed_mcq(db, uuid.UUID(me["id"]), uuid.UUID(course_id), document.id)

    response = client.post(
        f"/assessments/{assessment.id}/attempts",
        headers=headers,
        json={
            "answers": [
                {"item_id": str(items[0].id), "response": "circular wait"},
                {"item_id": str(items[1].id), "response": "Disk blocks"},
            ]
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["correct_count"] == 1
    assert body["total_count"] == 2
    graded = {a["item_id"]: a for a in body["answers"]}
    assert graded[str(items[0].id)]["is_correct"] is True
    assert graded[str(items[1].id)]["correct_answer"] == "Page table entries"
    assert graded[str(items[1].id)]["explanation"]


def test_attempt_rejects_items_from_another_assessment(client: TestClient, db: Session) -> None:
    headers = {"Authorization": f"Bearer {_register_and_login(client, 'mixed@example.com')}"}
    course_id, document = _course_and_document(client, db, headers)
    me = client.get("/auth/me", headers=headers).json()
    assessment, _ = _completed_mcq(db, uuid.UUID(me["id"]), uuid.UUID(course_id), document.id)

    response = client.post(
        f"/assessments/{assessment.id}/attempts",
        headers=headers,
        json={"answers": [{"item_id": str(uuid.uuid4()), "response": "whatever"}]},
    )
    assert response.status_code == 400


def test_cannot_attempt_an_unfinished_assessment(client: TestClient, db: Session) -> None:
    headers = {"Authorization": f"Bearer {_register_and_login(client, 'notready@example.com')}"}
    course_id, document = _course_and_document(client, db, headers)
    me = client.get("/auth/me", headers=headers).json()
    assessment = Assessment(
        student_id=uuid.UUID(me["id"]),
        course_id=uuid.UUID(course_id),
        document_id=document.id,
        title="Multiple choice - lecture.pdf",
        kind=AssessmentKind.MCQ,
        status=AssessmentStatus.PENDING,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    response = client.post(
        f"/assessments/{assessment.id}/attempts",
        headers=headers,
        json={"answers": []},
    )
    assert response.status_code == 409


def test_assessments_are_siloed_per_student(client: TestClient, db: Session) -> None:
    owner_headers = {"Authorization": f"Bearer {_register_and_login(client, 'a-owner@example.com')}"}
    course_id, document = _course_and_document(client, db, owner_headers)
    me = client.get("/auth/me", headers=owner_headers).json()
    assessment, _ = _completed_mcq(db, uuid.UUID(me["id"]), uuid.UUID(course_id), document.id)

    other_headers = {"Authorization": f"Bearer {_register_and_login(client, 'a-other@example.com')}"}
    assert client.get(f"/assessments/{assessment.id}", headers=other_headers).status_code == 404
    assert client.get("/assessments", headers=other_headers).json() == []


def _completed_short_answer(db: Session, student_id: uuid.UUID, course_id: uuid.UUID, document_id: uuid.UUID):
    assessment = Assessment(
        student_id=student_id,
        course_id=course_id,
        document_id=document_id,
        title="Short answer - lecture.pdf",
        kind=AssessmentKind.SHORT_ANSWER,
        status=AssessmentStatus.COMPLETED,
    )
    db.add(assessment)
    db.flush()
    item = AssessmentItem(
        assessment_id=assessment.id,
        position=1,
        kind=ItemKind.SHORT_ANSWER,
        question="Why does normalization reduce update anomalies?",
        answer="It removes redundancy so each fact is stored once.",
        options=[],
        explanation="Must mention redundancy or storing a fact once.",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    db.refresh(assessment)
    return assessment, item


def test_short_answers_are_marked_by_the_ai_judge(client: TestClient, db: Session) -> None:
    headers = {"Authorization": f"Bearer {_register_and_login(client, 'judge@example.com')}"}
    course_id, document = _course_and_document(client, db, headers)
    me = client.get("/auth/me", headers=headers).json()
    assessment, item = _completed_short_answer(db, uuid.UUID(me["id"]), uuid.UUID(course_id), document.id)

    grade = ShortAnswerGrade(
        reference=str(item.id),
        is_correct=True,
        feedback="Good - you identified that redundancy is removed.",
    )
    provider = MagicMock()
    provider.grade_short_answers.return_value = [grade]

    with patch("app.api.routers.assessments.get_ai_provider", return_value=provider):
        response = client.post(
            f"/assessments/{assessment.id}/attempts",
            headers=headers,
            json={"answers": [{"item_id": str(item.id), "response": "each fact lives in one place"}]},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["correct_count"] == 1
    assert body["answers"][0]["explanation"] == "Good - you identified that redundancy is removed."

    submitted = provider.grade_short_answers.call_args.args[0]
    assert len(submitted) == 1
    assert submitted[0].student_answer == "each fact lives in one place"
    assert submitted[0].expected_answer == "It removes redundancy so each fact is stored once."


def test_attempt_survives_judge_failure(client: TestClient, db: Session) -> None:
    headers = {"Authorization": f"Bearer {_register_and_login(client, 'judgefail@example.com')}"}
    course_id, document = _course_and_document(client, db, headers)
    me = client.get("/auth/me", headers=headers).json()
    assessment, item = _completed_short_answer(db, uuid.UUID(me["id"]), uuid.UUID(course_id), document.id)

    provider = MagicMock()
    provider.grade_short_answers.side_effect = RuntimeError("model unavailable")

    with patch("app.api.routers.assessments.get_ai_provider", return_value=provider):
        response = client.post(
            f"/assessments/{assessment.id}/attempts",
            headers=headers,
            json={"answers": [{"item_id": str(item.id), "response": "some answer"}]},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["correct_count"] == 0
    # The student is told marking did not run, rather than silently scored zero.
    assert "unavailable" in body["answers"][0]["explanation"].lower()
    assert body["answers"][0]["correct_answer"] == "It removes redundancy so each fact is stored once."


def test_deterministic_quiz_never_calls_the_model(client: TestClient, db: Session) -> None:
    headers = {"Authorization": f"Bearer {_register_and_login(client, 'nomodel@example.com')}"}
    course_id, document = _course_and_document(client, db, headers)
    me = client.get("/auth/me", headers=headers).json()
    assessment, items = _completed_mcq(db, uuid.UUID(me["id"]), uuid.UUID(course_id), document.id)

    with patch("app.api.routers.assessments.get_ai_provider") as provider:
        response = client.post(
            f"/assessments/{assessment.id}/attempts",
            headers=headers,
            json={"answers": [{"item_id": str(items[0].id), "response": "Circular wait"}]},
        )

    assert response.status_code == 201
    provider.assert_not_called()


def test_can_request_an_exam_paper(client: TestClient, db: Session) -> None:
    headers = {"Authorization": f"Bearer {_register_and_login(client, 'exam@example.com')}"}
    _, document = _course_and_document(client, db, headers)

    response = client.post(
        "/assessments",
        headers=headers,
        json={"document_id": str(document.id), "kind": "exam", "count": 12},
    )

    assert response.status_code == 201
    assert response.json()["kind"] == "exam"
    assert response.json()["title"] == "Exam paper - lecture.pdf"
