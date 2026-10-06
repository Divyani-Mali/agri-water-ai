def auth_headers(client, email):
    client.post(
        "/api/auth/register",
        json={"email": email, "full_name": "Test User", "password": "Test1234"},
    )
    r = client.post("/api/auth/login", data={"username": email, "password": "Test1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def my_id(client, h):
    return client.get("/api/auth/me", headers=h).json()["id"]


def test_admin_lists_users(client):
    admin = auth_headers(client, "admin@test.com")
    auth_headers(client, "a@test.com")
    r = client.get("/api/admin/users", headers=admin)
    assert r.status_code == 200 and len(r.json()) == 2


def test_farmer_cannot_use_admin_api(client):
    auth_headers(client, "admin@test.com")
    farmer = auth_headers(client, "a@test.com")
    assert client.get("/api/admin/users", headers=farmer).status_code == 403
    assert client.get("/api/admin/stats", headers=farmer).status_code == 403


def test_disabled_user_loses_access(client):
    admin = auth_headers(client, "admin@test.com")
    farmer = auth_headers(client, "a@test.com")
    fid = my_id(client, farmer)

    r = client.patch(f"/api/admin/users/{fid}", json={"is_active": False}, headers=admin)
    assert r.status_code == 200 and r.json()["is_active"] is False

    # the old token stops working immediately, and a new login is refused
    assert client.get("/api/auth/me", headers=farmer).status_code == 403
    login = client.post("/api/auth/login", data={"username": "a@test.com", "password": "Test1234"})
    assert login.status_code == 403


def test_admin_cannot_change_own_account(client):
    admin = auth_headers(client, "admin@test.com")
    aid = my_id(client, admin)
    r = client.patch(f"/api/admin/users/{aid}", json={"is_active": False}, headers=admin)
    assert r.status_code == 400


def test_admin_changes_role(client):
    admin = auth_headers(client, "admin@test.com")
    farmer = auth_headers(client, "a@test.com")
    fid = my_id(client, farmer)
    r = client.patch(f"/api/admin/users/{fid}", json={"role": "admin"}, headers=admin)
    assert r.json()["role"] == "admin"


def test_empty_update_rejected(client):
    admin = auth_headers(client, "admin@test.com")
    farmer = auth_headers(client, "a@test.com")
    fid = my_id(client, farmer)
    assert client.patch(f"/api/admin/users/{fid}", json={}, headers=admin).status_code == 400


def test_unknown_user_404(client):
    admin = auth_headers(client, "admin@test.com")
    r = client.patch("/api/admin/users/999", json={"is_active": False}, headers=admin)
    assert r.status_code == 404


def test_admin_stats(client):
    admin = auth_headers(client, "admin@test.com")
    body = client.get("/api/admin/stats", headers=admin).json()
    assert body["users"] == 1
    assert set(body) == {"users", "farms", "fields", "readings", "unread_alerts"}