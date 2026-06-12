"""Unit tests cho service layer (gọi trực tiếp, không qua HTTP)."""
import asyncio

from app.services.chatbot import _rule_based_reply, get_travel_response


def test_rule_based_matches_keyword():
    assert _rule_based_reply("kế hoạch du lịch hè") is not None


def test_rule_based_matches_city():
    assert "Tokyo" in (_rule_based_reply("I want to visit tokyo") or "")


def test_rule_based_returns_none_for_unknown():
    assert _rule_based_reply("qwertyuiop") is None


def test_get_travel_response_fallback_city():
    reply = asyncio.run(
        get_travel_response([{"role": "user", "content": "Bangkok please"}])
    )
    assert "Bangkok" in reply


def test_get_travel_response_default_when_unknown():
    reply = asyncio.run(
        get_travel_response([{"role": "user", "content": "qqqwww eee"}])
    )
    assert "điểm đến" in reply.lower()
