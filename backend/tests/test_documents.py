import uuid
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
            files={"files": ("lecture1.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        )

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    assert body[0]["filename"] == "lecture1.pdf"
    assert body[0]["status"] == "pending"
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
            files={"files": (filename, b"file bytes", "application/octet-stream")},
        )

    assert response.status_code == 201
    assert response.json()[0]["filename"] == filename


def test_upload_rejects_unsupported_format(client: TestClient) -> None:
    token = _register_and_login(client, "non-pdf-uploader@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    course = client.post("/courses", json={"name": "Networks", "code": "CS401"}, headers=headers).json()

    response = client.post(
        "/documents",
        headers=headers,
        data={"course_id": course["id"]},
        files={"files": ("lecture.mp3", b"audio", "audio/mpeg")},
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
            files={"files": ("../../../evil.pdf", b"%PDF-1.4", "application/pdf")},
        )

    assert response.status_code == 201
    assert response.json()[0]["filename"] == "evil.pdf"
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
        files={"files": ("lecture1.pdf", b"%PDF-1.4 fake content", "application/pdf")},
    )
    assert response.status_code == 404


def test_retry_requeues_a_transiently_failed_document(client: TestClient, db) -> None:
    from app.models.document import DocumentStatus, LectureDocument

    token = _register_and_login(client, "retry-ok@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    course = client.post("/courses", json={"name": "OS", "code": "CS305"}, headers=headers).json()
    me = client.get("/auth/me", headers=headers).json()

    document = LectureDocument(
        student_id=uuid.UUID(me["id"]),
        course_id=uuid.UUID(course["id"]),
        filename="lecture.pdf",
        storage_path="storage/lecture.pdf",
        status=DocumentStatus.FAILED,
        error_message="The AI service has hit its usage limit for now.",
        can_retry=True,
    )
    db.add(document)
    db.commit()

    with patch("app.api.routers.documents.queue.enqueue") as enqueue:
        response = client.post(f"/documents/{document.id}/retry", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["error_message"] is None
    enqueue.assert_called_once()


def test_retry_refused_when_the_file_itself_is_the_problem(client: TestClient, db) -> None:
    from app.models.document import DocumentStatus, LectureDocument

    token = _register_and_login(client, "retry-no@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    course = client.post("/courses", json={"name": "OS", "code": "CS305"}, headers=headers).json()
    me = client.get("/auth/me", headers=headers).json()

    document = LectureDocument(
        student_id=uuid.UUID(me["id"]),
        course_id=uuid.UUID(course["id"]),
        filename="scan.pdf",
        storage_path="storage/scan.pdf",
        status=DocumentStatus.FAILED,
        error_message="No text could be read from this file.",
        can_retry=False,
    )
    db.add(document)
    db.commit()

    response = client.post(f"/documents/{document.id}/retry", headers=headers)
    assert response.status_code == 409


def test_cannot_retry_another_students_document(client: TestClient, db) -> None:
    from app.models.document import DocumentStatus, LectureDocument

    owner = _register_and_login(client, "retry-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner}"}
    course = client.post("/courses", json={"name": "OS", "code": "CS305"}, headers=owner_headers).json()
    me = client.get("/auth/me", headers=owner_headers).json()
    document = LectureDocument(
        student_id=uuid.UUID(me["id"]),
        course_id=uuid.UUID(course["id"]),
        filename="lecture.pdf",
        storage_path="storage/lecture.pdf",
        status=DocumentStatus.FAILED,
        can_retry=True,
    )
    db.add(document)
    db.commit()

    other = _register_and_login(client, "retry-other@example.com")
    response = client.post(
        f"/documents/{document.id}/retry", headers={"Authorization": f"Bearer {other}"}
    )
    assert response.status_code == 404


def test_uploads_several_files_in_one_request(client: TestClient, tmp_path) -> None:
    token = _register_and_login(client, "multi@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    course = client.post("/courses", json={"name": "OS", "code": "CS305"}, headers=headers).json()

    with patch("app.api.routers.documents.settings.storage_dir", str(tmp_path)), patch(
        "app.api.routers.documents.queue.enqueue"
    ) as enqueue:
        response = client.post(
            "/documents",
            headers=headers,
            data={"course_id": course["id"]},
            files=[
                ("files", ("week1.pdf", b"%PDF-1.4 one", "application/pdf")),
                ("files", ("week2.docx", b"docx bytes", "application/octet-stream")),
                ("files", ("notes.txt", b"typed notes", "text/plain")),
            ],
        )

    assert response.status_code == 201
    body = response.json()
    assert [d["filename"] for d in body] == ["week1.pdf", "week2.docx", "notes.txt"]
    assert enqueue.call_count == 3, "each file gets its own extraction job"


def test_one_bad_file_rejects_the_whole_batch(client: TestClient, tmp_path) -> None:
    """Nothing is stored unless every file passes.

    Otherwise a bad file halfway through a selection would leave the earlier
    ones ingested and the student unsure what actually landed.
    """
    token = _register_and_login(client, "badbatch@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    course = client.post("/courses", json={"name": "OS", "code": "CS305"}, headers=headers).json()

    with patch("app.api.routers.documents.settings.storage_dir", str(tmp_path)), patch(
        "app.api.routers.documents.queue.enqueue"
    ) as enqueue:
        response = client.post(
            "/documents",
            headers=headers,
            data={"course_id": course["id"]},
            files=[
                ("files", ("good.pdf", b"%PDF-1.4", "application/pdf")),
                ("files", ("bad.mp3", b"audio", "audio/mpeg")),
            ],
        )

    assert response.status_code == 400
    assert "bad.mp3" in response.json()["detail"]
    enqueue.assert_not_called()
    assert client.get(f"/documents?course_id={course['id']}", headers=headers).json() == []
