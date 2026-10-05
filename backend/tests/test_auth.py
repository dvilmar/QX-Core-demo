import secrets

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import auth_session as session
from main import app

PASSWORD = secrets.token_urlsafe(12)
WRONG = secrets.token_urlsafe(12)
KEY = secrets.token_hex(8)


@pytest.fixture()
def configured(monkeypatch):
    monkeypatch.setenv("DASHBOARD_ADMIN_USER", "admin")
    monkeypatch.setenv("DASHBOARD_ADMIN_PASSWORD_HASH", session.hash_password(PASSWORD))
    monkeypatch.setenv("DASHBOARD_SESSION_SECRET", secrets.token_hex(16))
    monkeypatch.setenv("DASHBOARD_COOKIE_SECURE", "0")
    session._attempts.clear()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_password_hash_roundtrip():
    stored = session.hash_password(PASSWORD)
    assert session.verify_password(PASSWORD, stored)
    assert not session.verify_password(WRONG, stored)
    assert not session.verify_password(PASSWORD, "garbage")
    assert session.hash_password(PASSWORD) != stored


def test_token_roundtrip_and_tampering(configured):
    token = session.create_token("admin")
    assert session.verify_token(token)
    payload, sig = token.split(".")
    assert not session.verify_token(f"{payload}.{sig[:-2]}AA")
    assert not session.verify_token(None)
    assert not session.verify_token("nodot")


def test_expired_token_is_rejected(configured, monkeypatch):
    token = session.create_token("admin")
    monkeypatch.setattr("auth_session.time.time", lambda: 10**11)
    assert not session.verify_token(token)


def test_token_for_other_user_is_rejected(configured, monkeypatch):
    token = session.create_token("admin")
    monkeypatch.setenv("DASHBOARD_ADMIN_USER", "someone-else")
    assert not session.verify_token(token)


def test_login_flow_protects_api(configured, client):
    assert client.get("/api/snapshot").status_code == 401
    assert client.get("/api/auth/verify").status_code == 401
    bad = client.post("/api/auth/login", json={"username": "admin", "password": WRONG})
    assert bad.status_code == 401
    ok = client.post("/api/auth/login", json={"username": "admin", "password": PASSWORD})
    assert ok.status_code == 200 and session.COOKIE_NAME in ok.cookies
    assert client.get("/api/auth/verify").status_code == 200
    assert client.get("/api/snapshot").status_code == 200
    client.post("/api/auth/logout")
    assert client.get("/api/snapshot").status_code == 401


def test_login_is_rate_limited(configured, client):
    for _ in range(session.MAX_ATTEMPTS):
        client.post("/api/auth/login", json={"username": "admin", "password": WRONG})
    blocked = client.post("/api/auth/login", json={"username": "admin", "password": PASSWORD})
    assert blocked.status_code == 429


def test_verify_is_open_when_login_not_configured(client):
    assert client.get("/api/auth/verify").status_code == 200


def test_api_key_still_works_alongside_login(configured, client, monkeypatch):
    monkeypatch.setattr("auth.API_KEY", KEY)
    assert client.get("/api/snapshot", headers={"X-API-Key": KEY}).status_code == 200
    assert client.get("/api/snapshot", headers={"X-API-Key": WRONG}).status_code == 401


def test_websocket_open_when_nothing_is_configured(client):
    with client.websocket_connect("/api/ws") as ws:
        assert "equity" in ws.receive_json()


def test_websocket_rejects_without_credentials(configured, client):
    with pytest.raises(WebSocketDisconnect) as exc, client.websocket_connect("/api/ws"):
        pass
    assert exc.value.code == 4401


def test_websocket_accepts_api_key_query(client, monkeypatch):
    monkeypatch.setattr("auth.API_KEY", KEY)
    with pytest.raises(WebSocketDisconnect), client.websocket_connect(f"/api/ws?api_key={WRONG}"):
        pass
    with client.websocket_connect(f"/api/ws?api_key={KEY}") as ws:
        assert "equity" in ws.receive_json()


def test_websocket_accepts_session_cookie(configured, client):
    client.post("/api/auth/login", json={"username": "admin", "password": PASSWORD})
    with client.websocket_connect("/api/ws") as ws:
        assert "equity" in ws.receive_json()
