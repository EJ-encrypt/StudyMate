from fastapi.testclient import TestClient


def _register_and_login(client: TestClient, email: str) -> str:
    client.post(
        "/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "full_name": "Test Student"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    return login_response.json()["access_token"]


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
