import os
from datetime import timedelta
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.auth import create_access_token
from app.database import get_session
from app.main import app


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    yield engine

    app.dependency_overrides.clear()


@pytest.fixture()
def client(engine) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def create_user_and_token(client: TestClient):
    def _create_user(email: str, password: str = "secret123") -> dict:
        register_response = client.post(
            "/auth/register",
            json={"email": email, "password": password},
        )
        assert register_response.status_code == 201, register_response.text
        user = register_response.json()

        login_response = client.post(
            "/auth/login",
            data={"username": email, "password": password},
        )
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        return {"user": user, "token": token, "password": password}

    return _create_user


@pytest.fixture()
def auth_client(client: TestClient, create_user_and_token) -> TestClient:
    credentials = create_user_and_token("user1@example.com")
    with TestClient(app, headers={"Authorization": f"Bearer {credentials['token']}"}) as test_client:
        yield test_client


@pytest.fixture()
def second_auth_client(client: TestClient, create_user_and_token) -> TestClient:
    credentials = create_user_and_token("user2@example.com")
    with TestClient(app, headers={"Authorization": f"Bearer {credentials['token']}"}) as test_client:
        yield test_client


@pytest.fixture()
def expired_token(client: TestClient, create_user_and_token) -> str:
    credentials = create_user_and_token("expired@example.com")
    return create_access_token(
        int(credentials["user"]["id"]),
        expires_delta=timedelta(seconds=-1),
    )


def create_account(client: TestClient, name: str = "Main account") -> dict:
    response = client.post(
        "/accounts",
        json={
            "name": name,
            "type": "personal",
            "balance": 1000.0,
            "currency": "EUR",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
