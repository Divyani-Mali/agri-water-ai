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