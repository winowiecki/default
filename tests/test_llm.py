import httpx
import pytest

from deident.llm import OllamaClient, OllamaUnavailable, parse_spans


def test_parse_plain_array():
    raw = '[{"text": "Rosewood", "category": "site", "reason": "clinic"}]'
    assert parse_spans(raw) == [
        {"text": "Rosewood", "category": "site", "reason": "clinic"}
    ]


def test_parse_empty_array():
    assert parse_spans("[]") == []


def test_parse_object_with_spans_key():
    raw = '{"spans": [{"text": "Rosewood", "category": "site", "reason": "x"}]}'
    assert parse_spans(raw)[0]["text"] == "Rosewood"


def test_parse_code_fenced_and_prose_wrapped():
    raw = 'Here you go:\n```json\n[{"text": "Rosewood", "category": "site", "reason": "x"}]\n```'
    assert parse_spans(raw)[0]["text"] == "Rosewood"


def test_parse_unknown_category_becomes_other():
    raw = '[{"text": "Rosewood", "category": "hospital", "reason": "x"}]'
    assert parse_spans(raw)[0]["category"] == "other"


def test_parse_malformed_returns_none():
    assert parse_spans("I could not find any identifiers.") is None
    assert parse_spans('[{"text": broken') is None
    assert parse_spans("") is None


def test_detect_spans_retries_once_then_succeeds(monkeypatch):
    client = OllamaClient("http://localhost:11434", "test-model")
    replies = iter(["not json at all", '[{"text": "X", "category": "name"}]'])
    calls = []
    monkeypatch.setattr(
        client, "_chat", lambda chunk: (calls.append(1), next(replies))[1]
    )
    spans = client.detect_spans("chunk")
    assert len(calls) == 2
    assert spans == [{"text": "X", "category": "name", "reason": ""}]


def test_detect_spans_gives_up_after_two_failures(monkeypatch):
    client = OllamaClient("http://localhost:11434", "test-model")
    monkeypatch.setattr(client, "_chat", lambda chunk: "still not json")
    assert client.detect_spans("chunk") is None


def test_ensure_available_server_down(monkeypatch):
    client = OllamaClient("http://localhost:11434", "test-model")

    def boom(url):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(client._client, "get", boom)
    with pytest.raises(OllamaUnavailable, match="ollama serve"):
        client.ensure_available()


def test_ensure_available_model_not_pulled(monkeypatch):
    client = OllamaClient("http://localhost:11434", "test-model")
    response = httpx.Response(
        200,
        json={"models": [{"name": "other-model:latest"}]},
        request=httpx.Request("GET", "http://localhost:11434/api/tags"),
    )
    monkeypatch.setattr(client._client, "get", lambda url: response)
    with pytest.raises(OllamaUnavailable, match="ollama pull test-model"):
        client.ensure_available()
