from unittest.mock import patch

import pytest
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


@pytest.mark.parametrize("filename", ["lecture.pdf", "lecture.docx", "slides.pptx", "notes.txt", "notes.md"])
def test_upload_accepts_every_supported_format(client: TestClient, tmp_path, filename: str) -> None:
    token = _register_and_login(client, f"fmt-{filename.replace('.', '-')}@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    course = client.post("/courses", json={"name": "Networks", "code": "CS401"}, headers=headers).json()

    with patch("app.api.routers.documents.settings.storage_dir", str(tmp_path)), patch(
        "app.api.routers.documents.queue.enqueue"
    ):
        response = client.post(
            "/documents",
            headers=headers,
            data={"course_id": course["id"]},
            files={"file": (filename, b"file bytes", "application/octet-stream")},
        )

    assert response.status_code == 201
    assert response.json()["filename"] == filename


def test_upload_rejects_unsupported_format(client: TestClient) -> None:
    token = _register_and_login(client, "non-pdf-uploader@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    course = client.post("/courses", json={"name": "Networks", "code": "CS401"}, headers=headers).json()

    response = client.post(
        "/documents",
        headers=headers,
        data={"course_id": course["id"]},
        files={"file": ("lecture.mp3", b"audio", "audio/mpeg")},
    )
    assert response.status_code == 400


def test_upload_strips_path_traversal_from_filename(client: TestClient, tmp_path) -> None:
    token = _register_and_login(client, "traversal@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    course = client.post("/courses", json={"name": "Networks", "code": "CS401"}, headers=headers).json()

    with patch("app.api.routers.documents.settings.storage_dir", str(tmp_path)), patch(
        "app.api.routers.documents.queue.enqueue"
    ):
        response = client.post(
            "/documents",
            headers=headers,
            data={"course_id": course["id"]},
            files={"file": ("../../../evil.pdf", b"%PDF-1.4", "application/pdf")},
        )

    assert response.status_code == 201
    assert response.json()["filename"] == "evil.pdf"
    written = list(tmp_path.rglob("*evil.pdf"))
    assert len(written) == 1
    assert tmp_path in written[0].parents


def test_create_typed_notes(client: TestClient, tmp_path) -> None:
    token = _register_and_login(client, "notes-writer@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    course = client.post("/courses", json={"name": "Networks", "code": "CS401"}, headers=headers).json()

    with patch("app.api.routers.documents.settings.storage_dir", str(tmp_path)), patch(
        "app.api.routers.documents.queue.enqueue"
    ) as mock_enqueue:
        response = client.post(
            "/documents/notes",
            headers=headers,
            json={
                "course_id": course["id"],
                "title": "Week 5 - Normalization",
                "content": "A candidate key is a minimal determinant of every attribute.",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "Week 5 - Normalization.txt"
    assert body["status"] == "pending"
    mock_enqueue.assert_called_once()

    saved = list(tmp_path.rglob("*.txt"))
    assert len(saved) == 1
    assert "candidate key" in saved[0].read_text(encoding="utf-8")


def test_create_notes_rejects_empty_content(client: TestClient) -> None:
    token = _register_and_login(client, "empty-notes@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    course = client.post("/courses", json={"name": "Networks", "code": "CS401"}, headers=headers).json()

    response = client.post(
        "/documents/notes",
        headers=headers,
        json={"course_id": course["id"], "title": "Empty", "content": ""},
    )
    assert response.status_code == 422


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
