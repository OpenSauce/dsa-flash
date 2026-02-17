import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.users import ALGORITHM, SECRET_KEY, User, get_password_hash
from app.api.users import router as user_router
from app.database import get_session


def _get_test_session(session):
    def get_test_session():
        with Session(session.get_bind()) as s:
            yield s

    return get_test_session


def anon_app(session):
    """App without get_current_user override — uses real auth."""
    app = FastAPI()
    app.include_router(user_router)
    app.dependency_overrides[get_session] = _get_test_session(session)
    return app


def test_signup_returns_access_token(session):
    client = TestClient(anon_app(session))
    resp = client.post("/signup", json={"username": "alice", "password": "pass123"})
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body


def test_signup_token_is_valid(session):
    client = TestClient(anon_app(session))
    resp = client.post("/signup", json={"username": "bob", "password": "pass123"})
    token = resp.json()["access_token"]
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "bob"


def test_signup_duplicate_username_returns_400(session):
    user = User(username="charlie", hashed_password=get_password_hash("pass123"))
    session.add(user)
    session.commit()

    client = TestClient(anon_app(session))
    resp = client.post("/signup", json={"username": "charlie", "password": "other"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Username already taken"
