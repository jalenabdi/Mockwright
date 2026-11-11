def register(client, email="ada@example.com", password="correct-horse"):
    return client.post("/auth/register", json={"email": email, "password": password})


def login(client, email="ada@example.com", password="correct-horse"):
    return client.post("/auth/token", data={"username": email, "password": password})


def test_register_creates_account_with_normalized_email(client):
    response = register(client, email="  Ada@Example.COM ")
    assert response.status_code == 201
    assert response.json()["email"] == "ada@example.com"
    assert "password" not in response.text


def test_register_rejects_duplicate_email(client):
    register(client)
    response = register(client, email="ADA@example.com")
    assert response.status_code == 409


def test_register_rejects_short_password_and_bad_email(client):
    assert register(client, password="short").status_code == 422
    assert register(client, email="not-an-email").status_code == 422


def test_login_returns_bearer_token_that_identifies_the_user(client):
    register(client)
    token = login(client, email="ADA@example.com").json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "ada@example.com"


def test_login_rejects_wrong_password_and_unknown_email_the_same_way(client):
    register(client)
    wrong_password = login(client, password="wrong-password")
    unknown_email = login(client, email="nobody@example.com")
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_protected_route_rejects_missing_or_bad_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_accounts_hashed_with_older_argon2_settings_can_still_log_in(client, session_factory):
    from pwdlib import PasswordHash

    from backend.app.models import User

    older = PasswordHash.recommended()  # m=65536, t=3, p=4: what accounts were created with before
    with session_factory() as db:
        db.add(User(email="old@example.com", hashed_password=older.hash("correct-horse")))
        db.commit()

    first = login(client, email="old@example.com")
    second = login(client, email="old@example.com")

    assert first.status_code == second.status_code == 200
    assert login(client, email="old@example.com", password="wrong-password").status_code == 401
