import time

import jwt
from fastapi.testclient import TestClient

from tests.helpers import TEST_JWT_SECRET, auth_headers, token_for, user_id_for


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_first_request_provisions_the_profile_from_the_token(client: TestClient) -> None:
    response = client.get("/auth/me", headers=auth_headers("student@example.com", "Ama Mensah"))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user_id_for("student@example.com"))
    assert body["email"] == "student@example.com"
    assert body["full_name"] == "Ama Mensah"
    assert body["role"] == "student"
    assert body["school"] is None, "a new account still needs onboarding"
    assert body["timezone"] == "Africa/Accra"


def test_later_requests_reuse_the_same_profile(client: TestClient) -> None:
    headers = auth_headers("repeat@example.com")
    first = client.get("/auth/me", headers=headers).json()
    second = client.get("/auth/me", headers=headers).json()
    assert first["id"] == second["id"]


def test_me_requires_a_token(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401


def test_rejects_a_token_signed_with_another_secret(client: TestClient) -> None:
    forged = jwt.encode(
        {"sub": str(user_id_for("x@example.com")), "aud": "authenticated", "exp": int(time.time()) + 60},
        "not-the-project-secret",
        algorithm="HS256",
    )
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_rejects_an_expired_token(client: TestClient) -> None:
    expired = token_for("old@example.com", exp=int(time.time()) - 10)
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_rejects_a_token_for_another_audience(client: TestClient) -> None:
    # Supabase's anon key is itself a JWT signed with the same secret, with
    # role "anon". It must not be accepted as a signed-in student.
    anon = jwt.encode(
        {"sub": str(user_id_for("anon@example.com")), "aud": "anon", "exp": int(time.time()) + 60},
        TEST_JWT_SECRET,
        algorithm="HS256",
    )
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {anon}"}).status_code == 401


def test_onboarding_records_profile_and_timezone(client: TestClient) -> None:
    headers = auth_headers("onboard@example.com")
    response = client.put(
        "/auth/me/onboarding",
        headers=headers,
        json={
            "school": "School of Physical and Mathematical Sciences",
            "programme": "BSc Information Technology",
            "level": 400,
            "semester": 1,
            "timezone": "Europe/London",
        },
    )
    assert response.status_code == 200
    assert response.json()["level"] == 400
    assert response.json()["timezone"] == "Europe/London"


def test_preferences_reject_an_unknown_timezone(client: TestClient) -> None:
    response = client.patch(
        "/auth/me/preferences", headers=auth_headers("tz@example.com"), json={"timezone": "Mars/Olympus"}
    )
    assert response.status_code == 422


def test_preferences_switch_reminder_channels(client: TestClient) -> None:
    headers = auth_headers("prefs@example.com")
    response = client.patch("/auth/me/preferences", headers=headers, json={"notify_email": False})
    assert response.status_code == 200
    assert response.json()["notify_email"] is False
    assert response.json()["notify_push"] is True
