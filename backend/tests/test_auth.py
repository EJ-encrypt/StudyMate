from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_and_login(client: TestClient) -> None:
    register_response = client.post(
        "/auth/register",
        json={
            "email": "student@example.com",
            "password": "correct-horse-battery-staple",
            "full_name": "Test Student",
        },
    )
    assert register_response.status_code == 201
    body = register_response.json()
    assert body["email"] == "student@example.com"
    assert body["role"] == "student"

    login_response = client.post(
        "/auth/login",
        json={"email": "student@example.com", "password": "correct-horse-battery-staple"},
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()


def test_login_rejects_wrong_password(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={
            "email": "wrongpass@example.com",
            "password": "correct-horse-battery-staple",
            "full_name": "Test Student",
        },
    )

    login_response = client.post(
        "/auth/login",
        json={"email": "wrongpass@example.com", "password": "not-the-password"},
    )
    assert login_response.status_code == 401


def test_register_rejects_passwords_bcrypt_cannot_hash(client: TestClient) -> None:
    too_short = client.post(
        "/auth/register",
        json={"email": "short@example.com", "password": "abc", "full_name": "Test Student"},
    )
    assert too_short.status_code == 422

    too_long = client.post(
        "/auth/register",
        json={"email": "long@example.com", "password": "x" * 73, "full_name": "Test Student"},
    )
    assert too_long.status_code == 422


def test_me_requires_and_returns_current_user(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={
            "email": "me@example.com",
            "password": "correct-horse-battery-staple",
            "full_name": "Me Example",
        },
    )

    unauthenticated = client.get("/auth/me")
    assert unauthenticated.status_code == 401

    login_response = client.post(
        "/auth/login",
        json={"email": "me@example.com", "password": "correct-horse-battery-staple"},
    )
    token = login_response.json()["access_token"]

    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "me@example.com"


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    payload = {
        "email": "dupe@example.com",
        "password": "correct-horse-battery-staple",
        "full_name": "Test Student",
    }
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/auth/register", json=payload)
    assert second.status_code == 400
