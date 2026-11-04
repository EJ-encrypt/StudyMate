import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.assessment import Assessment, AssessmentItem, AssessmentKind, AssessmentStatus, ItemKind
from app.models.document import CourseConcept
from app.models.game import GameSession
from app.models.mastery import ConceptMastery
from app.services import games
from tests.helpers import auth_headers


def _setup(client: TestClient, email: str) -> tuple[dict, str, uuid.UUID]:
    headers = auth_headers(email)
    course = client.post("/courses", json={"name": "Databases", "code": "CS302"}, headers=headers).json()
    me = client.get("/auth/me", headers=headers).json()
    return headers, course["id"], uuid.UUID(me["id"])


def _concepts(db: Session, student_id: uuid.UUID, course_id: str, count: int) -> list[CourseConcept]:
    concepts = [
        CourseConcept(
            student_id=student_id,
            course_id=uuid.UUID(course_id),
            name=f"Concept {i}",
            summary=f"Concept {i} is the idea number {i}. More detail follows.",
            embedding=[0.0],
            embedding_model="test",
        )
        for i in range(count)
    ]
    db.add_all(concepts)
    db.commit()
    return concepts


def _question_bank(db: Session, student_id: uuid.UUID, course_id: str, concept: CourseConcept | None = None):
    assessment = Assessment(
        student_id=student_id,
        course_id=uuid.UUID(course_id),
        title="MCQ",
        kind=AssessmentKind.MCQ,
        status=AssessmentStatus.COMPLETED,
    )
    db.add(assessment)
    db.flush()
    items = []
    for i in range(5):
        items.append(
            AssessmentItem(
                assessment_id=assessment.id,
                position=i,
                kind=ItemKind.MCQ,
                question=f"Question {i}?",
                answer=f"Right {i}",
                options=[f"Right {i}", "Wrong A", "Wrong B", "Wrong C"],
                explanation="Because.",
                course_concept_id=concept.id if concept else None,
            )
        )
    db.add_all(items)
    db.commit()
    return items


def test_clock_points_reward_speed_and_streaks() -> None:
    assert games.clock_points(False, 1000, 3) == 0
    instant = games.clock_points(True, 0, 1)
    slow = games.clock_points(True, 14_000, 1)
    assert instant == games.BASE_POINTS + games.MAX_SPEED_BONUS
    assert games.BASE_POINTS <= slow < instant
    assert games.clock_points(True, 0, 3) > instant, "a streak multiplies the score"
    assert games.clock_points(True, 0, 50) == round(instant * games.MAX_STREAK_MULTIPLIER)


def test_clue_hides_the_concept_name() -> None:
    clue = games.make_clue(
        "Second Normal Form (2NF)",
        "Second normal form (2NF) removes partial dependencies on a composite key. It builds on 1NF.",
    )
    assert "second normal form" not in clue.lower()
    assert "2NF" not in clue
    assert "partial dependencies" in clue
    assert "builds on 1NF" not in clue, "only the first sentence is used"


def test_beat_the_clock_needs_questions_first(client: TestClient) -> None:
    headers, course_id, _ = _setup(client, "noclock@example.com")
    response = client.get(f"/games/{course_id}/beat-the-clock", headers=headers)
    assert response.status_code == 409
    assert "Study Engine" in response.json()["detail"]


def _submit(client: TestClient, headers: dict, round_id: str, **body) -> dict:
    response = client.post(f"/games/rounds/{round_id}/submit", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_beat_the_clock_round_and_scoring(client: TestClient, db: Session) -> None:
    headers, course_id, student_id = _setup(client, "clock@example.com")
    concept = _concepts(db, student_id, course_id, 1)[0]
    _question_bank(db, student_id, course_id, concept)

    round_ = client.get(f"/games/{course_id}/beat-the-clock", headers=headers).json()
    questions = round_["questions"]
    assert len(questions) == 5
    assert all(len(q["options"]) == 4 for q in questions)
    assert round_["personal_best"] is None

    answers = [
        {"key": q["item_id"], "response": q["answer"] if i < 3 else "Wrong A", "time_ms": 2000}
        for i, q in enumerate(questions)
    ]
    result = _submit(client, headers, round_["round_id"], answers=answers)

    assert result["correct"] == 3
    assert result["total"] == 5
    assert result["score"] > 0
    assert result["is_personal_best"] is True
    assert result["xp_awarded"] > 0
    assert {b["code"] for b in result["new_badges"]} >= {"first_game"}
    assert db.query(GameSession).count() == 1
    # Game answers count as evidence for mastery, like quiz answers.
    mastery = db.query(ConceptMastery).one()
    assert mastery.attempts == 5

    # A round is scored once.
    again = client.post(f"/games/rounds/{round_['round_id']}/submit", headers=headers, json={"answers": answers})
    assert again.status_code == 409


def test_beat_the_clock_rejects_answers_after_the_timer(client: TestClient, db: Session) -> None:
    headers, course_id, student_id = _setup(client, "late@example.com")
    _question_bank(db, student_id, course_id)
    round_ = client.get(f"/games/{course_id}/beat-the-clock", headers=headers).json()
    question = round_["questions"][0]
    result = _submit(
        client, headers, round_["round_id"],
        answers=[{"key": question["item_id"], "response": question["answer"], "time_ms": 20_000}],
    )
    assert result["correct"] == 0


def test_answers_are_marked_against_the_dealt_round_only(client: TestClient, db: Session) -> None:
    _, owner_course, owner_id = _setup(client, "q-owner@example.com")
    items = _question_bank(db, owner_id, owner_course)
    headers, course_id, student_id = _setup(client, "q-thief@example.com")
    _question_bank(db, student_id, course_id)
    round_ = client.get(f"/games/{course_id}/beat-the-clock", headers=headers).json()

    response = client.post(
        f"/games/rounds/{round_['round_id']}/submit",
        headers=headers,
        json={"answers": [{"key": str(items[0].id), "response": "x", "time_ms": 1}]},
    )
    assert response.status_code == 400


def test_a_round_can_only_be_submitted_by_its_player(client: TestClient, db: Session) -> None:
    headers, course_id, student_id = _setup(client, "dealer@example.com")
    _concepts(db, student_id, course_id, 4)
    round_ = client.get(f"/games/{course_id}/concept-match", headers=headers).json()
    other = auth_headers("someone-else@example.com")
    response = client.post(f"/games/rounds/{round_['round_id']}/submit", headers=other, json={"mistakes": 0})
    assert response.status_code == 404


def test_concept_match_round_and_scoring(client: TestClient, db: Session) -> None:
    headers, course_id, student_id = _setup(client, "match@example.com")
    _concepts(db, student_id, course_id, 8)

    round_ = client.get(f"/games/{course_id}/concept-match", headers=headers).json()
    assert len(round_["pairs"]) == games.PAIRS_PER_ROUND
    for pair in round_["pairs"]:
        assert pair["name"].lower() not in pair["clue"].lower()

    result = _submit(client, headers, round_["round_id"], mistakes=0, duration_ms=30_000)
    assert result["score"] == games.concept_match_score(games.PAIRS_PER_ROUND, 0, 30_000)
    assert "perfect_memory" in {b["code"] for b in result["new_badges"]}

    stats = client.get(f"/games/{course_id}/stats", headers=headers).json()
    by_game = {g["game"]: g for g in stats["games"]}
    assert by_game["concept_match"]["plays"] == 1
    assert by_game["concept_match"]["best"] == result["score"]
    assert by_game["beat_the_clock"]["plays"] == 0


def test_concept_match_needs_a_few_concepts(client: TestClient, db: Session) -> None:
    headers, course_id, student_id = _setup(client, "fewconcepts@example.com")
    _concepts(db, student_id, course_id, 2)
    assert client.get(f"/games/{course_id}/concept-match", headers=headers).status_code == 409


def test_personal_best_only_counts_a_higher_score(client: TestClient, db: Session) -> None:
    headers, course_id, student_id = _setup(client, "best@example.com")
    _concepts(db, student_id, course_id, 4)

    def play(mistakes: int) -> dict:
        round_ = client.get(f"/games/{course_id}/concept-match", headers=headers).json()
        return _submit(client, headers, round_["round_id"], mistakes=mistakes, duration_ms=60_000)

    first = play(2)
    worse = play(5)
    better = play(0)
    assert first["is_personal_best"] is True
    assert worse["is_personal_best"] is False
    assert worse["personal_best"] == first["score"]
    assert better["is_personal_best"] is True
    assert better["xp_awarded"] > worse["xp_awarded"], "beating a best earns a bonus"
