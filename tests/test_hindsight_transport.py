
import io
import json
import urllib.error

import pytest

from hermes_memory_router.adapters.hindsight import HindsightBackend
from hermes_memory_router.config import HindsightConfig
from hermes_memory_router.exceptions import BackendOperationError


class Response:
    def __init__(self, payload=b"{}"):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return self.payload


def backend():
    return HindsightBackend(HindsightConfig(bank_id="bank"), api_key="key")


def test_request_success_and_headers(monkeypatch):
    seen = {}
    def fake_open(request, timeout, context=None):
        seen["request"] = request
        return Response(json.dumps({"ok": True}).encode())
    monkeypatch.setattr("urllib.request.urlopen", fake_open)
    result = backend()._request("POST", "/x", {"a": 1})
    assert result["ok"] is True
    assert seen["request"].headers["Authorization"] == "Bearer key"


def test_request_http_error(monkeypatch):
    error = urllib.error.HTTPError(
        "http://x", 500, "bad", {}, io.BytesIO(b"failure")
    )
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: (_ for _ in ()).throw(error))
    with pytest.raises(BackendOperationError, match="HTTP 500"):
        backend()._request("GET", "/x")


def test_request_invalid_json(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: Response(b"not-json"))
    with pytest.raises(BackendOperationError):
        backend()._request("GET", "/x")


def test_health_and_reflect(monkeypatch):
    b = backend()
    calls = []
    def request(method, path, body=None, timeout=None):
        calls.append((method, path, body))
        return {"text": "answer"}
    b._request = request
    assert b.health()["ok"] is True
    assert b.reflect(query="why")["text"] == "answer"
    assert calls[-1][1].endswith("/reflect")


def test_health_failure():
    b = backend()
    b._request = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down"))
    assert b.health()["ok"] is False


def test_parse_string_and_skips_invalid():
    hits = HindsightBackend._parse_hits(
        {"items": ["one", 2, {"content": "two", "relevance": 0.5}]}, 5
    )
    assert [hit.content for hit in hits] == ["one", "two"]
