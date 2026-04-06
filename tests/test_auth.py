from app.auth import create_access_token


def test_register_login_and_me_flow(client):
    register_response = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "secret123"},
    )
    assert register_response.status_code == 201
    assert register_response.json()["email"] == "alice@example.com"

    login_response = client.post(
        "/auth/login",
        data={"username": "alice@example.com", "password": "secret123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "alice@example.com"


def test_register_rejects_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "secret123"}
    assert client.post("/auth/register", json=payload).status_code == 201

    duplicate_response = client.post("/auth/register", json=payload)
    assert duplicate_response.status_code == 400
    assert duplicate_response.json()["detail"] == "Email déjà utilisé"


def test_login_rejects_bad_credentials(client, create_user_and_token):
    create_user_and_token("badcreds@example.com", "secret123")

    response = client.post(
        "/auth/login",
        data={"username": "badcreds@example.com", "password": "wrongpass"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email ou mot de passe incorrect"


def test_me_rejects_expired_token(client, expired_token):
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Token invalide ou expiré"


def test_me_rejects_invalid_token(client):
    invalid_token = create_access_token(999999)
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {invalid_token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Token invalide ou expiré"
