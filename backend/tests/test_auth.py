from urllib.parse import parse_qs, urlparse

from app.core.config import settings

USER = {"email": "a@test.com", "full_name": "Test User", "password": "Test1234"}


def register(client, data=USER):
    return client.post("/api/auth/register", json=data)


def login(client, email="a@test.com", password="Test1234"):
    return client.post("/api/auth/login", data={"username": email, "password": password})


def test_register_success_first_user_is_admin(client):
    r = register(client)
    assert r.status_code == 201
    assert r.json()["role"] == "admin"


def test_second_user_is_farmer(client):
    register(client)
    r = register(client, {**USER, "email": "b@test.com"})
    assert r.json()["role"] == "farmer"


def test_duplicate_email_rejected(client):
    register(client)
    assert register(client).status_code == 400


def test_weak_password_rejected(client):
    r = register(client, {**USER, "password": "abcdefgh"})
    assert r.status_code == 422


def test_login_wrong_password(client):
    register(client)
    assert login(client, password="Wrong1234").status_code == 401


def test_login_and_me(client):
    register(client)
    token = login(client).json()["access_token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@test.com"


def test_me_without_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_password_reset_changes_password_and_token_is_single_use(client, monkeypatch):
    register(client)
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "SMTP_FROM", "")
    monkeypatch.setattr(settings, "PASSWORD_RESET_DEV_MODE", True)

    requested = client.post("/api/auth/password-reset/request", json={"email": USER["email"]})
    assert requested.status_code == 200
    token = parse_qs(urlparse(requested.json()["reset_url"]).query)["token"][0]

    changed = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "password": "NewPassword123"},
    )
    assert changed.status_code == 200
    assert login(client).status_code == 401
    assert login(client, password="NewPassword123").status_code == 200
    assert client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "password": "AnotherPassword123"},
    ).status_code == 400


def test_password_reset_unknown_email_does_not_return_reset_link(client, monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "SMTP_FROM", "")
    monkeypatch.setattr(settings, "PASSWORD_RESET_DEV_MODE", True)

    response = client.post(
        "/api/auth/password-reset/request",
        json={"email": "unknown@test.com"},
    )

    assert response.status_code == 200
    assert "reset_url" not in response.json()


def test_password_reset_fails_closed_without_delivery_configuration(client, monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "SMTP_FROM", "")
    monkeypatch.setattr(settings, "PASSWORD_RESET_DEV_MODE", False)

    response = client.post(
        "/api/auth/password-reset/request",
        json={"email": "unknown@test.com"},
    )

    assert response.status_code == 503