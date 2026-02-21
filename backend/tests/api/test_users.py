import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.users import ALGORITHM, SECRET_KEY, User, get_password_hash
from app.api.users import router as user_router
from app.database import get_session
from app.limiter import limiter
from tests.conftest import get_test_session


def anon_app(session):
    """App without get_current_user override — uses real auth."""
    app = FastAPI()
    app.include_router(user_router)
    app.dependency_overrides[get_session] = get_test_session(session)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
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


def test_signup_rate_limit_returns_429(session):
    client = TestClient(anon_app(session))
    for i in range(3):
        resp = client.post("/signup", json={"username": f"rluser{i}", "password": "pass1234"})
        assert resp.status_code == 201

    resp = client.post("/signup", json={"username": "rluser99", "password": "pass1234"})
    assert resp.status_code == 429
    assert "rate limit" in resp.json()["error"].lower()


def test_login_rate_limit_returns_429(session):
    user = User(username="ratelimituser", hashed_password=get_password_hash("pass1234"))
    session.add(user)
    session.commit()

    client = TestClient(anon_app(session))
    for _ in range(5):
        resp = client.post("/token", data={"username": "ratelimituser", "password": "pass1234"})
        assert resp.status_code == 200

    resp = client.post("/token", data={"username": "ratelimituser", "password": "pass1234"})
    assert resp.status_code == 429
    assert "rate limit" in resp.json()["error"].lower()


def test_rate_limit_does_not_affect_other_endpoints(session):
    client = TestClient(anon_app(session))
    for _ in range(10):
        resp = client.get("/users/me")
        assert resp.status_code in (200, 401, 403)
