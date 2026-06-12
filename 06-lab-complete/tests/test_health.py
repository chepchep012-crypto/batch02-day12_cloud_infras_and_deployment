"""Tests cho health/readiness/info endpoints."""
from fastapi.testclient import TestClient

from app.main import app


def test_health_ok():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["llm"] == "rule-based"  # CI không có OPENAI_API_KEY


def test_root_info():
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["app"]


def test_ready_after_startup():
    # Context manager kích hoạt lifespan -> _is_ready = True
    with TestClient(app) as client:
        r = client.get("/ready")
        assert r.status_code == 200
        assert r.json()["ready"] is True


def test_security_headers_present():
    client = TestClient(app)
    r = client.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
