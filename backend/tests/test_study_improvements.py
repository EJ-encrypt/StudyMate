"""Bigger, harder question sets; maths material; course import; Coach topics; accounts."""

import random
import uuid
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.assessment import AssessmentKind, ItemKind
from app.models.course import Course
from app.models.document import CourseConcept, DocumentStatus, LectureDocument
from app.models.user import User
from app.services.ai.base import CourseEntry, GeneratedItem, ItemDraft
from app.services.coaching import ConceptProgress, group_into_topics
from app.services.grading import is_correct
from app.services.latex import repair
from app.services.quantitative import is_quantitative_course, looks_mathematical
from app.workers import extraction_worker, generation_worker
from tests.helpers import auth_headers


def _item(question: str, answer: str = "A", options: list[str] | None = None, kind=ItemKind.MCQ) -> GeneratedItem:
    return GeneratedItem(
        kind=kind,
        question=question,
        answer=answer,
        options=options if options is not None else ["A", "B", "C", "D"],
        explanation="",
        concept="",
    )


# --- Set size and quality ---------------------------------------------------


def test_flashcards_and_mcq_default_to_at_least_twenty_and_scale_with_material() -> None:
    assert generation_worker.auto_count(AssessmentKind.MCQ, "x" * 1000) == 20
    assert generation_worker.auto_count(AssessmentKind.FLASHCARD, "x" * 1000) == 20
    assert generation_worker.auto_count(AssessmentKind.MCQ, "x" * 13_500) == 30
    assert generation_worker.auto_count(AssessmentKind.MCQ, "x" * 500_000) == 40
    # A cumulative set is sized by its concepts, not its short concept list.
    assert generation_worker.auto_count(AssessmentKind.FLASHCARD, "short", concept_count=16) == 32


def test_large_sets_are_written_in_batches_without_repeats() -> None:
    provider = MagicMock()
    provider.generate_assessment_items.side_effect = [
        [_item(f"Question {i}?") for i in range(20)],
        # The second batch repeats one question, which is dropped.
        [_item("Question 3?")] + [_item(f"Question {i}?") for i in range(20, 30)],
    ]
    with patch.object(generation_worker, "get_ai_provider", return_value=provider):
        items = generation_worker._generate_kind("text", ItemKind.MCQ, 30, [], False, random.Random(1))

    assert len(items) == 30
    assert len({item.question for item in items}) == 30
    first, second = provider.generate_assessment_items.call_args_list
    assert first.kwargs["count"] == 20 and first.kwargs["avoid"] is None
    # The second batch is told what the first already asked.
    assert second.kwargs["count"] == 10 and len(second.kwargs["avoid"]) == 20


def test_mcq_options_are_shuffled_so_the_answer_is_not_always_first() -> None:
    rng = random.Random(7)
    positions = {
        generation_worker.tidy_mcq(_item(f"Q{i}", "Right", ["Right", "W1", "W2", "W3"]), rng).options.index("Right")
        for i in range(40)
    }
    assert len(positions) == 4


def test_mcq_without_its_answer_among_the_options_is_dropped() -> None:
    assert generation_worker.tidy_mcq(_item("Q", "E", ["A", "B", "C", "D"]), random.Random()) is None


def test_mcq_giveaway_options_are_removed() -> None:
    item = generation_worker.tidy_mcq(
        _item("Q", "A", ["A", "B", "C", "All of the above", "D"]), random.Random()
    )
    assert item is not None and "All of the above" not in item.options and len(item.options) == 4


# --- Maths ------------------------------------------------------------------


@pytest.mark.parametrize(
    "code,name,expected",
    [
        ("MATH 223", "Calculus II", True),
        ("STAT 101", "Introduction to Probability", True),
        ("ECON 201", "Intermediate Microeconomics", True),
        ("DCIT 205", "Mathematical Foundations of Computing", True),
        ("CSCD 418", "Software Engineering", False),
        ("HIST 101", "History of West Africa", False),
    ],
)
def test_quantitative_courses_are_recognised(code: str, name: str, expected: bool) -> None:
    assert is_quantitative_course(code, name) is expected


def test_equation_heavy_text_is_recognised() -> None:
    assert looks_mathematical("f(x) = x^2 + 3x, so f'(x) = 2x + 3 and f''(x) = 2. " * 10)
    assert not looks_mathematical("A deadlock happens when two processes each wait for the other. " * 10)
    assert looks_mathematical("(cid:12)(cid:3) " * 6)


def test_numeric_answers_are_compared_as_numbers() -> None:
    assert is_correct(ItemKind.FILL_BLANK, "0.25", "1/4")
    assert is_correct(ItemKind.FILL_BLANK, "0.25", "25%")
    assert is_correct(ItemKind.FILL_BLANK, "3.14159", "3.14")
    assert is_correct(ItemKind.FILL_BLANK, "12", "x = 12")
    assert not is_correct(ItemKind.FILL_BLANK, "3.14", "3.2")
    # The plain text comparison strips punctuation, minus signs included.
    assert not is_correct(ItemKind.FILL_BLANK, "3", "-3")


def test_latex_that_lost_its_backslashes_in_json_is_repaired() -> None:
    # "\f", "\t" and "\n" are JSON escapes, so an unescaped \frac, \theta or
    # \nabla arrives as a control character.
    assert repair("$\x0crac{1}{2}$") == r"$\frac{1}{2}$"
    assert repair("angle \theta") == r"angle \theta"
    assert repair("$\nabla f$") == r"$\nabla f$"
    # Ordinary line breaks outside mathematics are left alone.
    assert repair("first line\nsecond line") == "first line\nsecond line"


def test_drafts_drop_their_working_and_repair_latex() -> None:
    draft = ItemDraft(
        kind=ItemKind.FILL_BLANK, question="Differentiate $x^2$", working="d/dx x^2 = 2x",
        answer="2x", options=[], explanation="Power rule: $\x0crac{d}{dx}x^n = nx^{n-1}$", concept="",
    )
    item = draft.to_item()
    assert not hasattr(item, "working")
    assert r"\frac" in item.explanation


def _document(db: Session, client: TestClient, email: str, filename: str, course_code="CSCD 101", course_name="Notes"):
    headers = auth_headers(email)
    course = client.post("/courses", json={"code": course_code, "name": course_name}, headers=headers).json()
    me = client.get("/auth/me", headers=headers).json()
    document = LectureDocument(
        student_id=uuid.UUID(me["id"]), course_id=uuid.UUID(course["id"]),
        filename=filename, storage_path=f"x/{filename}", status=DocumentStatus.PENDING,
    )
    db.add(document)
    db.commit()
    return document


def test_a_photo_of_notes_is_transcribed_and_the_text_is_kept(client: TestClient, db: Session, tmp_path: Path) -> None:
    document = _document(db, client, "photo@example.com", "board.jpg")
    photo = tmp_path / "board.jpg"
    photo.write_bytes(b"\xff\xd8jpeg")
    provider = MagicMock()
    provider.transcribe_document.return_value = "Newton's second law: $F = ma$"

    with patch.object(extraction_worker, "local_copy", return_value=nullcontext(str(photo))), patch.object(
        extraction_worker, "get_ai_provider", return_value=provider
    ):
        text, _ = extraction_worker.read_document(db, document)

    assert text == "Newton's second law: $F = ma$"
    provider.transcribe_document.assert_called_once_with(b"\xff\xd8jpeg", "image/jpeg")
    db.refresh(document)
    assert document.extracted_text == text

    # A second read - a quiz, or a retry after a timeout - does not pay again.
    with patch.object(extraction_worker, "get_ai_provider", return_value=provider):
        extraction_worker.read_document(db, document)
    assert provider.transcribe_document.call_count == 1


def test_a_maths_pdf_falls_back_to_plain_text_when_transcription_fails(
    client: TestClient, db: Session, tmp_path: Path
) -> None:
    document = _document(db, client, "calc@example.com", "week1.pdf", "MATH 223", "Calculus II")
    pdf = tmp_path / "week1.pdf"
    pdf.write_bytes(b"%PDF")
    provider = MagicMock()
    provider.transcribe_document.side_effect = RuntimeError("busy")
    plain = "Limits and continuity. " * 20

    with patch.object(extraction_worker, "local_copy", return_value=nullcontext(str(pdf))), patch.object(
        extraction_worker, "extract_text", return_value=plain
    ), patch.object(extraction_worker, "pdf_page_count", return_value=2), patch.object(
        extraction_worker, "get_ai_provider", return_value=provider
    ):
        text, quantitative = extraction_worker.read_document(db, document)

    assert text == plain
    assert quantitative is True


def test_ordinary_pdfs_with_text_are_not_sent_for_transcription(client: TestClient, db: Session, tmp_path: Path) -> None:
    document = _document(db, client, "prose@example.com", "week1.pdf")
    pdf = tmp_path / "week1.pdf"
    pdf.write_bytes(b"%PDF")
    provider = MagicMock()

    with patch.object(extraction_worker, "local_copy", return_value=nullcontext(str(pdf))), patch.object(
        extraction_worker, "extract_text", return_value="A process is a program in execution. " * 30
    ), patch.object(extraction_worker, "pdf_page_count", return_value=2), patch.object(
        extraction_worker, "get_ai_provider", return_value=provider
    ):
        _, quantitative = extraction_worker.read_document(db, document)

    provider.transcribe_document.assert_not_called()
    assert quantitative is False


# --- Course import ----------------------------------------------------------


def test_a_course_list_is_read_into_proposals_without_creating_anything(client: TestClient, db: Session) -> None:
    headers = auth_headers("import@example.com")
    client.post("/courses", json={"code": "MATH 223", "name": "Calculus II"}, headers=headers)
    provider = MagicMock()
    provider.read_course_list.return_value = [
        CourseEntry(code="MATH223", name="Calculus II", level=200, semester=2),
        CourseEntry(code="STAT 201", name="Probability", level=0, semester=0),
        CourseEntry(code="STAT 201", name="Probability", level=0, semester=0),
        CourseEntry(code="", name="", level=0, semester=0),
    ]

    with patch("app.services.ai.get_ai_provider", return_value=provider):
        response = client.post(
            "/courses/read", headers=headers, files={"file": ("slip.png", b"\x89PNG", "image/png")}
        )

    assert response.status_code == 200
    proposals = response.json()
    assert [(p["code"], p["already_added"]) for p in proposals] == [("MATH223", True), ("STAT 201", False)]
    assert proposals[1]["level"] is None and proposals[1]["semester"] is None
    assert len(client.get("/courses", headers=headers).json()) == 1


def test_ticked_courses_are_added_once(client: TestClient) -> None:
    headers = auth_headers("bulk@example.com")
    client.post("/courses", json={"code": "MATH 223", "name": "Calculus II"}, headers=headers)
    response = client.post(
        "/courses/bulk",
        headers=headers,
        json={"courses": [
            {"code": "math-223", "name": "Calculus II"},
            {"code": "STAT 201", "name": "Probability", "level": 200, "semester": 1},
            {"code": "STAT201", "name": "Probability again"},
        ]},
    )
    assert response.status_code == 201
    assert [c["code"] for c in response.json()] == ["STAT 201"]
    assert len(client.get("/courses", headers=headers).json()) == 2


# --- Coach topics -----------------------------------------------------------


def _progress(name: str, status_score: float | None, attempts: int) -> ConceptProgress:
    return ConceptProgress(
        concept_id=uuid.uuid4(), name=name, summary=f"{name} summary", score=status_score,
        attempts=attempts, correct=0, last_seen_at=None,
    )


def test_revision_is_grouped_into_at_most_five_topics() -> None:
    concepts = [_progress(f"Concept {i}", 0.1, 3) for i in range(12)]
    # Four families of three near-identical vectors, all weak.
    embeddings = {}
    for index, concept in enumerate(concepts):
        family = index % 4
        vector = [0.0] * 4
        vector[family] = 1.0
        vector[(family + 1) % 4] = 0.05 * (index // 4)
        embeddings[concept.concept_id] = (vector, "test")

    topics = group_into_topics(concepts, embeddings)

    assert len(topics) == 4
    assert all(len(topic.concepts) == 3 for topic in topics)
    for topic in topics:
        families = {concepts.index(c) % 4 for c in topic.concepts}
        assert len(families) == 1


def test_unrelated_concepts_are_forced_into_five_topics() -> None:
    concepts = [_progress(f"Concept {i}", 0.2, 3) for i in range(9)]
    embeddings = {}
    for index, concept in enumerate(concepts):
        vector = [0.0] * 9
        vector[index] = 1.0
        embeddings[concept.concept_id] = (vector, "test")

    topics = group_into_topics(concepts, embeddings)

    assert len(topics) == 5
    assert sum(len(topic.concepts) for topic in topics) == 9
    # Priority order survives: the most urgent concept leads the first topic.
    assert topics[0].concepts[0] is concepts[0]


def test_coach_summary_returns_topics(client: TestClient, db: Session) -> None:
    headers = auth_headers("topics@example.com")
    course = client.post("/courses", json={"code": "CS1", "name": "Systems"}, headers=headers).json()
    me = client.get("/auth/me", headers=headers).json()
    db.add_all(
        CourseConcept(
            student_id=uuid.UUID(me["id"]), course_id=uuid.UUID(course["id"]),
            name=f"Concept {i}", summary="s", embedding=[float(i == j) for j in range(8)], embedding_model="test",
        )
        for i in range(8)
    )
    db.commit()

    summary = client.get(f"/coach/{course['id']}", headers=headers).json()

    assert 1 <= len(summary["topics"]) <= 5
    assert sum(len(t["concepts"]) for t in summary["topics"]) == 8
    assert summary["more_to_revise"] == 0


# --- Settings ---------------------------------------------------------------


def test_usernames_are_lowercased_unique_and_clearable(client: TestClient) -> None:
    first, second = auth_headers("u1@example.com"), auth_headers("u2@example.com")

    me = client.patch("/auth/me/preferences", headers=first, json={"username": "@Kofi_M"}).json()
    assert me["username"] == "kofi_m"

    taken = client.patch("/auth/me/preferences", headers=second, json={"username": "KOFI_M"})
    assert taken.status_code == 409

    invalid = client.patch("/auth/me/preferences", headers=second, json={"username": "no spaces"})
    assert invalid.status_code == 422

    cleared = client.patch("/auth/me/preferences", headers=first, json={"username": ""}).json()
    assert cleared["username"] is None


def test_tutorial_and_semester_are_saved(client: TestClient) -> None:
    headers = auth_headers("prefs@example.com")
    assert client.get("/auth/me", headers=headers).json()["tutorial_seen"] is False
    me = client.patch(
        "/auth/me/preferences", headers=headers, json={"tutorial_seen": True, "level": 300, "semester": 2}
    ).json()
    assert (me["tutorial_seen"], me["level"], me["semester"]) == (True, 300, 2)


def test_deleting_an_account_removes_everything(client: TestClient, db: Session) -> None:
    headers = auth_headers("leaving@example.com")
    course = client.post("/courses", json={"code": "CS1", "name": "Systems"}, headers=headers).json()
    client.post("/schedule", headers=headers, json={
        "title": "Systems", "course_id": course["id"], "day_of_week": 0,
        "start_time": "08:00", "end_time": "10:00", "venue": "",
    })
    me = client.get("/auth/me", headers=headers).json()
    student_id = uuid.UUID(me["id"])

    with patch("app.services.accounts.get_storage") as storage:
        response = client.delete("/auth/me", headers=headers)

    assert response.status_code == 204
    storage.return_value.delete.assert_called_once()
    db.expire_all()
    assert db.get(User, student_id) is None
    assert db.query(Course).filter(Course.owner_id == student_id).count() == 0


# --- Concept Match variety --------------------------------------------------


def _match_course(client: TestClient, db: Session, email: str, count: int):
    headers = auth_headers(email)
    course = client.post("/courses", json={"code": "CS9", "name": "Systems"}, headers=headers).json()
    me = client.get("/auth/me", headers=headers).json()
    concepts = [
        CourseConcept(
            student_id=uuid.UUID(me["id"]), course_id=uuid.UUID(course["id"]), name=f"Concept {i}",
            summary=f"Idea number {i}.", embedding=[0.0], embedding_model="test",
        )
        for i in range(count)
    ]
    db.add_all(concepts)
    db.commit()
    return headers, course["id"], concepts


def _play(client: TestClient, headers: dict, course_id: str, document_id: str | None = None) -> dict:
    params = {"document_id": document_id} if document_id else {}
    round_ = client.get(f"/games/{course_id}/concept-match", headers=headers, params=params).json()
    client.post("/games/concept-match", headers=headers, json={
        "course_id": course_id, "concept_ids": [p["concept_id"] for p in round_["pairs"]],
        "mistakes": 0, "duration_ms": 20_000,
    })
    return round_


def test_rounds_use_unseen_concepts_first_and_then_warn_about_repeats(client: TestClient, db: Session) -> None:
    from app.services import games

    headers, course_id, _ = _match_course(client, db, "variety@example.com", 20)
    stats = client.get(f"/games/{course_id}/stats", headers=headers).json()
    assert stats["match_fresh_rounds"] == 20 // games.PAIRS_PER_ROUND

    first = _play(client, headers, course_id)
    second = _play(client, headers, course_id)
    assert first["variety"] == second["variety"] == "fresh"
    # No concept repeats until all have been seen.
    assert not {p["concept_id"] for p in first["pairs"]} & {p["concept_id"] for p in second["pairs"]}

    third = _play(client, headers, course_id)
    assert third["variety"] == "mixing"
    assert third["fresh_in_round"] == 20 - 2 * games.PAIRS_PER_ROUND
    assert third["fresh_rounds_left"] == 0

    fourth = client.get(f"/games/{course_id}/concept-match", headers=headers).json()
    assert fourth["variety"] == "repeating"
    assert fourth["rounds_played"] == 3


def test_a_round_can_come_from_one_file(client: TestClient, db: Session) -> None:
    from app.models.document import KnowledgeConcept

    headers, course_id, concepts = _match_course(client, db, "onefile@example.com", 12)
    student_id = concepts[0].student_id
    document = LectureDocument(student_id=student_id, course_id=uuid.UUID(course_id), filename="week1.pdf",
                               storage_path="x/week1.pdf", status=DocumentStatus.COMPLETED)
    db.add(document)
    db.flush()
    for concept in concepts[:4]:
        db.add(KnowledgeConcept(document_id=document.id, course_concept_id=concept.id, student_id=student_id,
                                course_id=uuid.UUID(course_id), name=concept.name, summary=concept.summary))
    db.commit()

    round_ = client.get(f"/games/{course_id}/concept-match", headers=headers, params={"document_id": str(document.id)}).json()

    assert round_["pool_size"] == 4
    assert {p["concept_id"] for p in round_["pairs"]} == {str(c.id) for c in concepts[:4]}

    other = client.get(f"/games/{course_id}/concept-match", headers=auth_headers("stranger@example.com"),
                       params={"document_id": str(document.id)})
    assert other.status_code == 404
