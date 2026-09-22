from unittest.mock import patch

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


def test_upload_document_enqueues_extraction_job(client: TestClient, tmp_path) -> None:
    token = _register_and_login(client, "uploader@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    course = client.post("/courses", json={"name": "Networks", "code": "CS401"}, headers=headers).json()

    with patch("app.api.routers.documents.settings.storage_dir", str(tmp_path)), patch(
        "app.api.routers.documents.queue.enqueue"
    ) as mock_enqueue:
        response = client.post(
            "/documents",
            headers=headers,
            data={"course_id": course["id"]},
            files={"file": ("lecture1.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "lecture1.pdf"
    assert body["status"] == "pending"
    mock_enqueue.assert_called_once()

    list_response = client.get(f"/documents?course_id={course['id']}", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_upload_rejects_non_pdf(client: TestClient) -> None:
    token = _register_and_login(client, "non-pdf-uploader@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    course = client.post("/courses", json={"name": "Networks", "code": "CS401"}, headers=headers).json()

    response = client.post(
        "/documents",
        headers=headers,
        data={"course_id": course["id"]},
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )
    assert response.status_code == 400


def test_upload_rejects_course_owned_by_another_student(client: TestClient) -> None:
    owner_token = _register_and_login(client, "course-owner-2@example.com")
    other_token = _register_and_login(client, "other-student@example.com")

    course = client.post(
        "/courses",
        json={"name": "Databases", "code": "CS501"},
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()

    response = client.post(
        "/documents",
        headers={"Authorization": f"Bearer {other_token}"},
        data={"course_id": course["id"]},
        files={"file": ("lecture1.pdf", b"%PDF-1.4 fake content", "application/pdf")},
    )
    assert response.status_code == 404
