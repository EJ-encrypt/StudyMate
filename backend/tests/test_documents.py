import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import DocumentStatus, LectureDocument
from app.models.job import Job
from tests.helpers import auth_headers


def _course(client: TestClient, headers: dict) -> dict:
    return client.post("/courses", json={"name": "Networks", "code": "CS401"}, headers=headers).json()


def _upload(client: TestClient, headers: dict, course_id: str, files: list[tuple[str, bytes]]):
    """Run the full browser flow: ask for URLs, send the bytes, confirm."""
    targets = client.post(
        "/documents/uploads",
        headers=headers,
        json={"course_id": course_id, "files": [{"filename": n, "size": len(b)} for n, b in files]},
    )
    assert targets.status_code == 200, targets.text
    for target, (_, contents) in zip(targets.json(), files):
        assert target["method"] == "local"
        put = client.put(target["url"], content=contents)
        assert put.status_code == 204
    return client.post(
        "/documents/complete",
        headers=headers,
        json={
            "course_id": course_id,
            "uploads": [{"document_id": t["document_id"], "filename": t["filename"]} for t in targets.json()],
        },
    )


def test_upload_document_queues_an_extraction_job(client: TestClient, db: Session, _isolated_storage) -> None:
    headers = auth_headers("uploader@example.com")
    course = _course(client, headers)

    response = _upload(client, headers, course["id"], [("lecture1.pdf", b"%PDF-1.4 fake content")])

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    assert body[0]["filename"] == "lecture1.pdf"
    assert body[0]["status"] == "pending"

    jobs = db.query(Job).all()
    assert [(j.kind, j.payload) for j in jobs] == [("process_document", {"document_id": body[0]["id"]})]
    assert list(_isolated_storage.rglob("*lecture1.pdf"))[0].read_bytes() == b"%PDF-1.4 fake content"

    listed = client.get(f"/documents?course_id={course['id']}", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


@pytest.mark.parametrize("filename", ["lecture.pdf", "lecture.docx", "slides.pptx", "notes.txt", "notes.md"])
def test_upload_accepts_every_supported_format(client: TestClient, filename: str) -> None:
    headers = auth_headers(f"fmt-{filename.replace('.', '-')}@example.com")
    course = _course(client, headers)

    response = _upload(client, headers, course["id"], [(filename, b"file bytes")])

    assert response.status_code == 201
    assert response.json()[0]["filename"] == filename


def test_upload_rejects_unsupported_format(client: TestClient) -> None:
    headers = auth_headers("non-pdf-uploader@example.com")
    course = _course(client, headers)

    response = client.post(
        "/documents/uploads",
        headers=headers,
        json={"course_id": course["id"], "files": [{"filename": "lecture.mp3", "size": 5}]},
    )
    assert response.status_code == 400


def test_upload_rejects_oversized_files_before_any_upload(client: TestClient) -> None:
    headers = auth_headers("big-file@example.com")
    course = _course(client, headers)

    response = client.post(
        "/documents/uploads",
        headers=headers,
        json={"course_id": course["id"], "files": [{"filename": "huge.pdf", "size": 25 * 1024 * 1024}]},
    )
    assert response.status_code == 400
    assert "too large" in response.json()["detail"]


def test_upload_strips_path_traversal_from_filename(client: TestClient, _isolated_storage) -> None:
    headers = auth_headers("traversal@example.com")
    course = _course(client, headers)

    response = _upload(client, headers, course["id"], [("../../../evil.pdf", b"%PDF-1.4")])

    assert response.status_code == 201
    assert response.json()[0]["filename"] == "evil.pdf"
    written = list(_isolated_storage.rglob("*evil.pdf"))
    assert len(written) == 1
    assert _isolated_storage in written[0].parents


def test_storage_path_is_chosen_by_the_server(client: TestClient, db: Session) -> None:
    """A student can only register files under their own prefix."""
    headers = auth_headers("prefix@example.com")
    course = _course(client, headers)
    document_id = uuid.uuid4()

    response = client.post(
        "/documents/complete",
        headers=headers,
        json={"course_id": course["id"], "uploads": [{"document_id": str(document_id), "filename": "x.pdf"}]},
    )

    assert response.status_code == 201
    stored = db.get(LectureDocument, document_id)
    me = client.get("/auth/me", headers=headers).json()
    assert stored.storage_path == f"{me['id']}/{course['id']}/{document_id}_x.pdf"


def test_local_upload_rejects_a_forged_token(client: TestClient) -> None:
    response = client.put("/storage/local/Zm9vL2Jhci5wZGY.deadbeef", content=b"data")
    assert response.status_code == 403


def test_create_typed_notes(client: TestClient, db: Session, _isolated_storage) -> None:
    headers = auth_headers("notes-writer@example.com")
    course = _course(client, headers)

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
    assert db.query(Job).count() == 1

    saved = list(_isolated_storage.rglob("*.txt"))
    assert len(saved) == 1
    assert "candidate key" in saved[0].read_text(encoding="utf-8")


def test_create_notes_rejects_empty_content(client: TestClient) -> None:
    headers = auth_headers("empty-notes@example.com")
    course = _course(client, headers)

    response = client.post(
        "/documents/notes",
        headers=headers,
        json={"course_id": course["id"], "title": "Empty", "content": ""},
    )
    assert response.status_code == 422


def test_upload_rejects_course_owned_by_another_student(client: TestClient) -> None:
    course = _course(client, auth_headers("course-owner-2@example.com"))

    response = client.post(
        "/documents/uploads",
        headers=auth_headers("other-student@example.com"),
        json={"course_id": course["id"], "files": [{"filename": "lecture1.pdf", "size": 10}]},
    )
    assert response.status_code == 404


def _failed_document(client: TestClient, db: Session, headers: dict, can_retry: bool) -> LectureDocument:
    course = _course(client, headers)
    me = client.get("/auth/me", headers=headers).json()
    document = LectureDocument(
        student_id=uuid.UUID(me["id"]),
        course_id=uuid.UUID(course["id"]),
        filename="lecture.pdf",
        storage_path="x/lecture.pdf",
        status=DocumentStatus.FAILED,
        error_message="The AI service has hit its usage limit for now.",
        can_retry=can_retry,
    )
    db.add(document)
    db.commit()
    return document


def test_retry_requeues_a_transiently_failed_document(client: TestClient, db: Session) -> None:
    headers = auth_headers("retry-ok@example.com")
    document = _failed_document(client, db, headers, can_retry=True)

    response = client.post(f"/documents/{document.id}/retry", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["error_message"] is None
    assert db.query(Job).count() == 1


def test_retry_refused_when_the_file_itself_is_the_problem(client: TestClient, db: Session) -> None:
    headers = auth_headers("retry-no@example.com")
    document = _failed_document(client, db, headers, can_retry=False)

    response = client.post(f"/documents/{document.id}/retry", headers=headers)
    assert response.status_code == 409


def test_cannot_retry_another_students_document(client: TestClient, db: Session) -> None:
    document = _failed_document(client, db, auth_headers("retry-owner@example.com"), can_retry=True)

    response = client.post(f"/documents/{document.id}/retry", headers=auth_headers("retry-other@example.com"))
    assert response.status_code == 404


def test_uploads_several_files_in_one_request(client: TestClient, db: Session) -> None:
    headers = auth_headers("multi@example.com")
    course = _course(client, headers)

    response = _upload(
        client,
        headers,
        course["id"],
        [("week1.pdf", b"%PDF-1.4 one"), ("week2.docx", b"docx bytes"), ("notes.txt", b"typed notes")],
    )

    assert response.status_code == 201
    assert [d["filename"] for d in response.json()] == ["week1.pdf", "week2.docx", "notes.txt"]
    assert db.query(Job).count() == 3, "each file gets its own extraction job"


def test_one_bad_file_rejects_the_whole_batch(client: TestClient, db: Session) -> None:
    """No upload URL is issued unless every file passes.

    Otherwise a bad file halfway through a selection would leave the earlier
    ones ingested and the student unsure what actually landed.
    """
    headers = auth_headers("badbatch@example.com")
    course = _course(client, headers)

    response = client.post(
        "/documents/uploads",
        headers=headers,
        json={
            "course_id": course["id"],
            "files": [{"filename": "good.pdf", "size": 8}, {"filename": "bad.mp3", "size": 5}],
        },
    )

    assert response.status_code == 400
    assert "bad.mp3" in response.json()["detail"]
    assert db.query(Job).count() == 0
    assert client.get(f"/documents?course_id={course['id']}", headers=headers).json() == []
