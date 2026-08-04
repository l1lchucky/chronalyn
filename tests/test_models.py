from chronalyn.models import BackendReceipt, CheckpointResult, MemoryHit, RecallResult


def test_model_serialization():
    hit = MemoryHit("fact", 0.9, "id", "source", {"x": 1})
    receipt = BackendReceipt("backend", "external", {"ok": True})
    recall = RecallResult([hit], "backend", True, "timeout")
    checkpoint = CheckpointResult("mr_1", False, {"backend:retain": "complete"})
    assert hit.to_dict()["content"] == "fact"
    assert receipt.to_dict()["external_id"] == "external"
    assert recall.to_dict()["hits"][0]["score"] == 0.9
    assert checkpoint.to_dict()["record_id"] == "mr_1"
