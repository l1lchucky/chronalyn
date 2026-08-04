from __future__ import annotations

from conftest import FakeBackend
from hermes_memory_router.config import new_config
from hermes_memory_router.policy import HINDSIGHT_MNEMOSYNE, HINDSIGHT_ONLY
from hermes_memory_router.router import MemoryRouter
from hermes_memory_router.store import RouterStore


def test_hindsight_only_policy_has_no_fallback(tmp_path):
    config = new_config(namespace="project", environment="staging", policy=HINDSIGHT_ONLY)
    config.routing.start_worker = False
    primary = FakeBackend("hindsight")
    checkpoint = FakeBackend("mnemosyne")
    checkpoint.hits = []
    router = MemoryRouter(
        config=config,
        store=RouterStore(tmp_path / "router.db"),
        primary=primary,
        checkpoint=None,
    )
    result = router.checkpoint_record(
        content="Verified Hindsight-only checkpoint.",
        verification_level="tested",
        evidence="unit test",
    )
    router.drain_outbox(10)
    assert router.store.delivery_states(result.record_id) == {"hindsight:retain": "complete"}
    assert router.recall(query="missing").fallback_used is False
    router.close()


def test_dual_policy_uses_checkpoint_backend(tmp_path):
    config = new_config(
        namespace="project",
        environment="staging",
        policy=HINDSIGHT_MNEMOSYNE,
    )
    config.routing.start_worker = False
    primary = FakeBackend("hindsight")
    checkpoint = FakeBackend("mnemosyne")
    router = MemoryRouter(
        config=config,
        store=RouterStore(tmp_path / "router.db"),
        primary=primary,
        checkpoint=checkpoint,
    )
    result = router.checkpoint_record(
        content="Verified dual checkpoint.",
        verification_level="tested",
        evidence="unit test",
    )
    router.drain_outbox(10)
    assert router.store.delivery_states(result.record_id) == {
        "hindsight:retain": "complete",
        "mnemosyne:retain": "complete",
    }
    router.close()


def test_explicit_retain_is_hindsight_only(router):
    instance, primary, checkpoint = router
    result = instance.retain_memory(content="Remember this", context="project")
    instance.drain_outbox(10)
    assert result.delivery_states == {"hindsight:retain": "pending"}
    assert len(primary.retained) == 1
    assert checkpoint.retained == {}
