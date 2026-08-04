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
