from fastapi.testclient import TestClient

from tests.helpers import token_for


def _register_and_login(client: TestClient, email: str) -> str:
    """A Supabase-style token; the account is created on its first request."""
    return token_for(email)


def test_create_and_list_own_courses(client: TestClient) -> None:
    token = _register_and_login(client, "course-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post("/courses", json={"name": "Data Structures", "code": "CS201"}, headers=headers)
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["name"] == "Data Structures"
    assert body["code"] == "CS201"

    list_response = client.get("/courses", headers=headers)
    assert list_response.status_code == 200
    courses = list_response.json()
    assert len(courses) == 1
    assert courses[0]["id"] == body["id"]


def test_courses_are_siloed_per_student(client: TestClient) -> None:
    token_a = _register_and_login(client, "student-a@example.com")
    token_b = _register_and_login(client, "student-b@example.com")

    client.post(
        "/courses",
        json={"name": "Algorithms", "code": "CS301"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    b_courses = client.get("/courses", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert b_courses == []
