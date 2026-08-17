import json

from chronalyn.adapters.hindsight import HindsightBackend
from chronalyn.config import HindsightConfig


class StubHindsight(HindsightBackend):
    def __init__(self):
        super().__init__(HindsightConfig(bank_id="bank"))
        self.requests = []
        self.responses = []

    def _request(self, method, path, body=None, *, timeout=None):
        self.requests.append((method, path, body))
        return self.responses.pop(0) if self.responses else {}


def test_retain_uses_router_document_id():
    backend = StubHindsight()
    receipt = backend.retain(
        content="checkpoint", record_id="mr_123", kind="checkpoint", metadata={}
    )
    method, _path, body = backend.requests[0]
    assert method == "POST"
    assert body["items"][0]["document_id"] == "memory-router:mr_123"
    assert receipt.external_id == "memory-router:mr_123"


def test_recall_parses_flexible_results():
    backend = StubHindsight()
    backend.responses = [{"results": [{"text": "fact", "score": 0.9, "id": "m1"}]}]
    hits = backend.recall(query="q", limit=5)
    assert hits[0].content == "fact"
    assert hits[0].external_id == "m1"


def test_delete_uses_document_endpoint():
    backend = StubHindsight()
    backend.delete(external_id="memory-router:mr_1", metadata={})
    method, path, _ = backend.requests[0]
    assert method == "DELETE"
    assert "/documents/" in path


def test_retain_normalizes_metadata_to_strings():
    backend = StubHindsight()
    backend.retain(
        content="checkpoint",
        record_id="mr_meta",
        kind="checkpoint",
        metadata={
            "existing": "keep",
            "flag": False,
            "items": ["a", "b"],
            "nested": {"b": 2, "a": 1},
            "nothing": None,
        },
    )
    _method, _path, body = backend.requests[0]
    meta = body["items"][0]["metadata"]
    assert meta["existing"] == "keep"
    assert meta["flag"] == "false"
    assert meta["items"] == '["a","b"]'
    # Deterministic ordering via sort_keys=True, compact separators.
    assert meta["nested"] == '{"a":1,"b":2}'
    assert meta["nothing"] == "null"
    assert meta["memory_router_record_id"] == "mr_meta"
    assert meta["memory_router_kind"] == "checkpoint"
    assert all(isinstance(value, str) for value in meta.values())


def test_retain_does_not_mutate_caller_metadata():
    backend = StubHindsight()
    original = {"flag": False, "items": ["a", "b"]}
    before = json.dumps(original, sort_keys=True)
    backend.retain(
        content="checkpoint",
        record_id="mr_x",
        kind="checkpoint",
        metadata=original,
    )
    after = json.dumps(original, sort_keys=True)
    assert before == after
    assert original["flag"] is False
    assert original["items"] == ["a", "b"]
