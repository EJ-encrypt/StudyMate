"""True or False Blitz, Odd One Out, Three Strikes; friends, leaderboards, challenges."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.assessment import Assessment, AssessmentItem, AssessmentKind, AssessmentStatus, ItemKind
from app.models.document import CourseConcept
from app.models.social import Challenge
from app.services import arcade
from app.services.social import programme_key
from tests.helpers import auth_headers


def _student(client: TestClient, email: str, username: str | None = None, programme: str = "BSc IT"):
    headers = auth_headers(email, full_name=email.split("@")[0].title())
    client.put("/auth/me/onboarding", headers=headers, json={
        "school": "UG", "programme": programme, "level": 300, "semester": 1,
    })
    if username:
        client.patch("/auth/me/preferences", headers=headers, json={"username": username})
    course = client.post("/courses", json={"code": "CS3", "name": "Systems"}, headers=headers).json()
    me = client.get("/auth/me", headers=headers).json()
    return headers, course["id"], uuid.UUID(me["id"])


def _families(db: Session, student_id: uuid.UUID, course_id: str, families: int = 3, per_family: int = 3):
    """Concepts in clearly separate topic families, by embedding."""
    concepts = []
    for family in range(families):
        for member in range(per_family):
            vector = [0.0] * families
            vector[family] = 1.0
            concepts.append(CourseConcept(
                student_id=student_id, course_id=uuid.UUID(course_id),
                name=f"Topic{family} idea {member}", summary=f"Idea {member} of topic {family}. More.",
                embedding=[v + 0.01 * member for v in vector], embedding_model="test",
            ))
    db.add_all(concepts)
    db.commit()
    return concepts


def _mcqs(db: Session, student_id: uuid.UUID, course_id: str, count: int = 8, kind=ItemKind.MCQ):
    assessment = Assessment(student_id=student_id, course_id=uuid.UUID(course_id), title="Q",
                            kind=AssessmentKind.MCQ, status=AssessmentStatus.COMPLETED)
    db.add(assessment)
    db.flush()
    db.add_all(
        AssessmentItem(assessment_id=assessment.id, position=i, kind=kind, question=f"Question {i}?",
                       answer=f"Right {i}", options=[f"Right {i}", f"Wrong {i}a", f"Wrong {i}b", f"Wrong {i}c"],
                       explanation="Because.")
        for i in range(count)
    )
    db.commit()


def _submit(client, headers, round_id, **body):
    response = client.post(f"/games/rounds/{round_id}/submit", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


# --- True or False Blitz ------------------------------------------------------


def test_blitz_mixes_true_and_false_statements_and_marks_them(client: TestClient, db: Session) -> None:
    headers, course_id, student_id = _student(client, "blitz@example.com")
    _families(db, student_id, course_id)
    _mcqs(db, student_id, course_id)

    round_ = client.get(f"/games/{course_id}/true-false", headers=headers).json()
    statements = round_["statements"]
    assert len(statements) >= arcade.MIN_STATEMENTS
    assert {s["is_true"] for s in statements} == {True, False}

    answers = [{"key": s["key"], "response": "true" if s["is_true"] else "false", "time_ms": 1000} for s in statements[:5]]
    answers.append({"key": statements[5]["key"], "response": "false" if statements[5]["is_true"] else "true", "time_ms": 1000})
    result = _submit(client, headers, round_["round_id"], answers=answers)
    assert result["correct"] == 5 and result["total"] == 6
    # The streak multiplier makes five in a row worth more than five singles.
    assert result["score"] > 5 * arcade.BLITZ_POINTS


def test_blitz_ignores_answers_after_sixty_seconds(client: TestClient, db: Session) -> None:
    headers, course_id, student_id = _student(client, "slowblitz@example.com")
    _mcqs(db, student_id, course_id)
    round_ = client.get(f"/games/{course_id}/true-false", headers=headers).json()
    answers = [
        {"key": s["key"], "response": "true" if s["is_true"] else "false", "time_ms": 25_000}
        for s in round_["statements"][:4]
    ]
    result = _submit(client, headers, round_["round_id"], answers=answers)
    assert result["total"] == 2, "only what fits in the minute counts"


# --- Odd One Out --------------------------------------------------------------


def test_odd_one_out_puzzles_have_one_concept_from_another_topic(client: TestClient, db: Session) -> None:
    headers, course_id, student_id = _student(client, "odd@example.com")
    concepts = _families(db, student_id, course_id)
    family = {str(c.id): c.name.split()[0] for c in concepts}

    round_ = client.get(f"/games/{course_id}/odd-one-out", headers=headers).json()
    puzzles = round_["puzzles"]
    assert len(puzzles) >= 3
    for puzzle in puzzles:
        topics = [family[option["concept_id"]] for option in puzzle["options"]]
        odd_topic = family[puzzle["odd_id"]]
        assert topics.count(odd_topic) == 1
        assert len(set(topics)) == 2

    answers = [{"key": str(i), "response": p["odd_id"], "time_ms": 3000} for i, p in enumerate(puzzles)]
    answers[0]["response"] = next(o["concept_id"] for o in puzzles[0]["options"] if o["concept_id"] != puzzles[0]["odd_id"])
    result = _submit(client, headers, round_["round_id"], answers=answers)
    assert result["correct"] == len(puzzles) - 1


def test_odd_one_out_needs_distinct_topics(client: TestClient, db: Session) -> None:
    headers, course_id, student_id = _student(client, "flat@example.com")
    _families(db, student_id, course_id, families=1, per_family=6)
    assert client.get(f"/games/{course_id}/odd-one-out", headers=headers).status_code == 409


# --- Three Strikes ------------------------------------------------------------


def test_time_shrinks_and_points_rise_as_the_run_goes_on() -> None:
    assert arcade.strikes_seconds(0) == arcade.STRIKES_START_SECONDS
    assert arcade.strikes_seconds(3) < arcade.strikes_seconds(0)
    assert arcade.strikes_seconds(100) == arcade.STRIKES_MIN_SECONDS
    assert arcade.strikes_level(10) > arcade.strikes_level(0)


def test_three_strikes_ends_on_the_third_wrong_answer(client: TestClient, db: Session) -> None:
    headers, course_id, student_id = _student(client, "strikes@example.com")
    _mcqs(db, student_id, course_id, count=12)
    round_ = client.get(f"/games/{course_id}/three-strikes", headers=headers).json()
    questions = round_["questions"]
    assert len(questions) == 12

    pattern = [True, True, False, True, False, False, True, True]
    answers = [
        {"key": q["item_id"], "response": q["answer"] if right else "nope", "time_ms": 2000}
        for q, right in zip(questions, pattern)
    ]
    result = _submit(client, headers, round_["round_id"], answers=answers)
    assert result["total"] == 6, "answers after the third strike do not count"
    assert result["correct"] == 3


# --- Friends and leaderboards -------------------------------------------------


def _befriend(client, a_headers, b_headers, b_username):
    assert client.post("/friends/requests", headers=a_headers, json={"username": b_username}).status_code == 201
    request_id = client.get("/friends", headers=b_headers).json()["incoming"][0]["request_id"]
    assert client.post(f"/friends/requests/{request_id}/accept", headers=b_headers).status_code == 200


def test_friend_requests_by_username(client: TestClient) -> None:
    ama, _, _ = _student(client, "ama@example.com", "ama")
    kofi, _, _ = _student(client, "kofi@example.com", "kofi")

    assert client.post("/friends/requests", headers=ama, json={"username": "nobody"}).status_code == 404
    assert client.post("/friends/requests", headers=ama, json={"username": "ama"}).status_code == 400
    assert client.post("/friends/requests", headers=ama, json={"username": "@KOFI"}).status_code == 201
    assert client.post("/friends/requests", headers=ama, json={"username": "kofi"}).status_code == 409
    assert client.get("/friends", headers=ama).json()["outgoing"][0]["user"]["username"] == "kofi"

    request_id = client.get("/friends", headers=kofi).json()["incoming"][0]["request_id"]
    accepted = client.post(f"/friends/requests/{request_id}/accept", headers=kofi)
    assert accepted.status_code == 200
    assert [f["username"] for f in client.get("/friends", headers=ama).json()["friends"]] == ["kofi"]


def test_sending_a_request_back_accepts_it(client: TestClient) -> None:
    yaa, _, _ = _student(client, "yaa@example.com", "yaa")
    kwame, _, _ = _student(client, "kwame@example.com", "kwame")
    client.post("/friends/requests", headers=yaa, json={"username": "kwame"})
    client.post("/friends/requests", headers=kwame, json={"username": "yaa"})
    assert len(client.get("/friends", headers=yaa).json()["friends"]) == 1


def test_friend_leaderboard_counts_this_weeks_xp(client: TestClient, db: Session) -> None:
    efua, efua_course, efua_id = _student(client, "efua@example.com", "efua")
    kojo, _, _ = _student(client, "kojo@example.com", "kojo")
    _befriend(client, efua, kojo, "kojo")
    _families(db, efua_id, efua_course, families=2, per_family=2)
    round_ = client.get(f"/games/{efua_course}/concept-match", headers=efua).json()
    _submit(client, efua, round_["round_id"], mistakes=0, duration_ms=10_000)

    board = client.get("/leaderboard", headers=kojo, params={"scope": "friends", "period": "week"}).json()
    names = [s["username"] for s in board["standings"]]
    assert names == ["efua", "kojo"]
    assert board["standings"][0]["xp"] > 0
    assert board["standings"][1]["is_me"] is True


def test_programme_leaderboard_is_opt_in_and_groups_spellings(client: TestClient) -> None:
    assert programme_key("BSc. Information Technology") == programme_key("Bachelor of Science in IT")
    a, _, _ = _student(client, "p1@example.com", "p_one", programme="BSc IT")
    b, _, _ = _student(client, "p2@example.com", "p_two", programme="Bachelor of Science in Information Technology")
    _student(client, "p3@example.com", "p_three", programme="BSc Information Technology")  # not opted in
    _student(client, "p4@example.com", "p_four", programme="BA Economics")
    for headers in (a, b):
        client.patch("/auth/me/preferences", headers=headers, json={"public_leaderboard": True})

    board = client.get("/leaderboard", headers=a, params={"scope": "programme", "period": "all"}).json()
    assert board["joined"] is True
    assert sorted(s["name"] for s in board["standings"]) == ["@p_one", "@p_two"]


# --- Challenges ---------------------------------------------------------------


def test_a_friend_plays_the_same_round_and_the_winner_is_rewarded(client: TestClient, db: Session) -> None:
    abena, abena_course, abena_id = _student(client, "abena@example.com", "abena")
    yaw, _, _ = _student(client, "yaw@example.com", "yaw")
    _befriend(client, abena, yaw, "yaw")
    _mcqs(db, abena_id, abena_course, count=5)

    round_ = client.get(f"/games/{abena_course}/beat-the-clock", headers=abena).json()
    questions = round_["questions"]
    # Challenging before finishing is refused.
    early = client.post("/challenges", headers=abena, json={"round_id": round_["round_id"], "friend_ids": []})
    assert early.status_code == 422
    _submit(client, abena, round_["round_id"], answers=[
        {"key": q["item_id"], "response": q["answer"] if i < 2 else "x", "time_ms": 5000} for i, q in enumerate(questions)
    ])
    yaw_id = client.get("/auth/me", headers=yaw).json()["id"]
    created = client.post("/challenges", headers=abena, json={"round_id": round_["round_id"], "friend_ids": [yaw_id]})
    assert created.status_code == 201
    challenge_id = created.json()[0]["id"]

    # Yaw has no such course, but plays the exact round.
    their_round = client.get(f"/challenges/{challenge_id}/round", headers=yaw).json()
    assert [q["item_id"] for q in their_round["questions"]] == [q["item_id"] for q in questions]
    assert their_round["challenge"]["challenger_score"] > 0

    result = client.post(f"/challenges/{challenge_id}/submit", headers=yaw, json={"answers": [
        {"key": q["item_id"], "response": q["answer"], "time_ms": 1000} for q in their_round["questions"]
    ]}).json()
    assert result["is_personal_best"] is True
    assert "challenge_won" in {b["code"] for b in result["new_badges"]}

    mine = client.get("/challenges", headers=abena).json()[0]
    assert (mine["status"], mine["outcome"], mine["direction"]) == ("completed", "lost", "sent")
    theirs = client.get("/challenges", headers=yaw).json()[0]
    assert theirs["outcome"] == "won"
    # Played once only.
    assert client.get(f"/challenges/{challenge_id}/round", headers=yaw).status_code == 409


def test_only_friends_can_be_challenged_and_challenges_expire(client: TestClient, db: Session) -> None:
    esi, esi_course, esi_id = _student(client, "esi@example.com", "esi")
    stranger, _, _ = _student(client, "stranger2@example.com", "stranger2")
    _families(db, esi_id, esi_course, families=2, per_family=2)
    round_ = client.get(f"/games/{esi_course}/concept-match", headers=esi).json()
    _submit(client, esi, round_["round_id"], mistakes=1, duration_ms=10_000)
    stranger_id = client.get("/auth/me", headers=stranger).json()["id"]

    refused = client.post("/challenges", headers=esi, json={"round_id": round_["round_id"], "friend_ids": [stranger_id]})
    assert refused.status_code == 403

    _befriend(client, esi, stranger, "stranger2")
    challenge_id = client.post(
        "/challenges", headers=esi, json={"round_id": round_["round_id"], "friend_ids": [stranger_id]}
    ).json()[0]["id"]
    row = db.get(Challenge, uuid.UUID(challenge_id))
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    assert client.get(f"/challenges/{challenge_id}/round", headers=stranger).status_code == 409
    assert client.get("/challenges", headers=esi).json()[0]["status"] == "expired"


def test_deleting_an_account_removes_friendships_and_challenges(client: TestClient, db: Session) -> None:
    from unittest.mock import patch

    gone, gone_course, gone_id = _student(client, "gone@example.com", "gone")
    stays, _, _ = _student(client, "stays@example.com", "stays")
    _befriend(client, gone, stays, "stays")
    _families(db, gone_id, gone_course, families=2, per_family=2)
    round_ = client.get(f"/games/{gone_course}/concept-match", headers=gone).json()
    _submit(client, gone, round_["round_id"], mistakes=0, duration_ms=5_000)
    stays_id = client.get("/auth/me", headers=stays).json()["id"]
    client.post("/challenges", headers=gone, json={"round_id": round_["round_id"], "friend_ids": [stays_id]})

    with patch("app.services.accounts.get_storage"):
        assert client.delete("/auth/me", headers=gone).status_code == 204
    assert client.get("/friends", headers=stays).json()["friends"] == []
    assert client.get("/challenges", headers=stays).json() == []


def test_a_borrowed_definition_does_not_name_its_real_concept() -> None:
    assert arcade._without_name("Paging splits memory into pages.", "Paging") == "This splits memory into pages."
    assert arcade._without_name("A TLB caches translations.", "Translation Lookaside Buffer (TLB)") == "This caches translations."
    assert arcade._without_name("Memory is split by paging.", "Paging") == "Memory is split by this."
