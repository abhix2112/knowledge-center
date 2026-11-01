def test_register_login_me(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "Alice@Example.com", "password": "password123", "full_name": "Alice"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "alice@example.com"  # stored lowercase
    assert "password_hash" not in response.json()

    login = client.post("/api/auth/login", data={"username": "alice@example.com", "password": "password123"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["full_name"] == "Alice"


def test_register_same_email_twice(client, alice):
    response = client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "password123", "full_name": "Again"},
    )
    assert response.status_code == 409


def test_register_short_password(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "x@example.com", "password": "short", "full_name": "X"},
    )
    assert response.status_code == 422


def test_login_wrong_password_and_unknown_email_look_the_same(client, alice):
    wrong_password = client.post("/api/auth/login", data={"username": "alice@example.com", "password": "nope-nope"})
    unknown_email = client.post("/api/auth/login", data={"username": "nobody@example.com", "password": "nope-nope"})
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_protected_endpoints_need_a_token(client):
    assert client.get("/api/articles").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
