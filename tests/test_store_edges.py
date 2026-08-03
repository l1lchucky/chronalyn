import pytest

from hermes_memory_router.store import RouterStore


def make(store, backends=None):
    return store.create_record(
        namespace="p",
        environment="production",
        kind="checkpoint",
        content="content",
        metadata={},
        backends=backends or ["hindsight"],
    )[0]


def test_record_list_stats_and_retry_all(tmp_path):
    store = RouterStore(tmp_path / "router.db")
    record_id = make(store)
    assert store.record(record_id)["content"] == "content"
    assert store.record("missing") is None
    assert store.list_records(kind="checkpoint")[0]["id"] == record_id
    due = store.due_deliveries(10)[0]
    assert store.claim(due["id"])
    store.fail(due["id"], error="x", next_attempt_at=0)
    assert store.retry_failed() == 1
    assert store.stats()["records"]["checkpoint"] == 1
    store.audit(record_id, "test", {"ok": True})
    store.close()


def test_schedule_delete_missing_record(tmp_path):
    store = RouterStore(tmp_path / "router.db")
    with pytest.raises(KeyError):
        store.schedule_delete("missing")
    store.close()


def test_complete_after_forget_schedules_delete(tmp_path):
    store = RouterStore(tmp_path / "router.db")
    record_id = make(store)
    due = store.due_deliveries(10)[0]
    assert store.claim(due["id"])
    # Simulate forget racing with an already-processing backend retain.
    store.schedule_delete(record_id)
    store.complete(due["id"], external_id="memory-router:mr", receipt={"ok": True})
    states = store.delivery_states(record_id)
    assert states["hindsight:retain"] == "complete"
    assert states["hindsight:delete"] == "pending"
    store.close()
