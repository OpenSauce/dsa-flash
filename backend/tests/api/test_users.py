import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.users import ALGORITHM, SECRET_KEY, User, get_password_hash
from app.api.users import router as user_router
from app.database import get_session
from tests.conftest import get_test_session


def anon_app(session):
    """App without get_current_user override — uses real auth."""
    app = FastAPI()
    app.include_router(user_router)
    app.dependency_overrides[get_session] = get_test_session(session)
    return app


def test_signup_returns_access_token(session):
    client = TestClient(anon_app(session))
    resp = client.post("/signup", json={"username": "alice", "password": "pass1234"})
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body


def test_signup_token_is_valid(session):
    client = TestClient(anon_app(session))
    resp = client.post("/signup", json={"username": "bob", "password": "pass1234"})
    token = resp.json()["access_token"]
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "bob"


def test_signup_duplicate_username_returns_400(session):
    user = User(username="charlie", hashed_password=get_password_hash("pass1234"))
    session.add(user)
    session.commit()

    client = TestClient(anon_app(session))
    resp = client.post("/signup", json={"username": "charlie", "password": "otherpass"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Username already taken"


def test_signup_short_username_returns_422(session):
    client = TestClient(anon_app(session))
    resp = client.post("/signup", json={"username": "ab", "password": "pass1234"})
    assert resp.status_code == 422


def test_signup_special_chars_in_username_returns_422(session):
    client = TestClient(anon_app(session))
    resp = client.post("/signup", json={"username": "bad!user", "password": "pass1234"})
    assert resp.status_code == 422


def test_signup_short_password_returns_422(session):
    client = TestClient(anon_app(session))
    resp = client.post("/signup", json={"username": "alice", "password": "short"})
    assert resp.status_code == 422


def test_signup_empty_username_returns_422(session):
    client = TestClient(anon_app(session))
    resp = client.post("/signup", json={"username": "", "password": "pass1234"})
    assert resp.status_code == 422


def test_signup_empty_password_returns_422(session):
    client = TestClient(anon_app(session))
    resp = client.post("/signup", json={"username": "alice", "password": ""})
    assert resp.status_code == 422
