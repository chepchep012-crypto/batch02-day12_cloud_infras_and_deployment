"""Tests cho chat endpoint /api/chat/ (rule-based, không cần API key)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _ask(text: str):
    return client.post("/api/chat/", json={"messages": [{"role": "user", "content": text}]})


def test_chat_known_destination():
    r = _ask("Cho tôi thông tin về Hà Nội")
    assert r.status_code == 200
    assert "Hà Nội" in r.json()["reply"]


def test_chat_greeting():
    r = _ask("hello")
    assert r.status_code == 200
    assert "TravelBot" in r.json()["reply"]


def test_chat_generic_travel_keyword():
    r = _ask("tôi muốn đi du lịch")
    assert r.status_code == 200
    assert len(r.json()["reply"]) > 0


def test_chat_unknown_returns_fallback():
    r = _ask("zxcvbnm qwerty")
    assert r.status_code == 200
    assert "điểm đến" in r.json()["reply"].lower()


def test_chat_validation_error_when_no_messages():
    r = client.post("/api/chat/", json={})
    assert r.status_code == 422
