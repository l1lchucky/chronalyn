from __future__ import annotations

from typing import Any

import pytest

from hermes_memory_router.adapters.base import MemoryBackend
from hermes_memory_router.config import RouterConfig
from hermes_memory_router.models import BackendReceipt, MemoryHit
from hermes_memory_router.policy import HINDSIGHT_MNEMOSYNE
from hermes_memory_router.router import MemoryRouter
from hermes_memory_router.store import RouterStore


class FakeBackend(MemoryBackend):
    def __init__(self, name: str) -> None:
        self.name = name
        self.retained: dict[str, dict[str, Any]] = {}
        self.deleted: list[str] = []
        self.hits: list[MemoryHit] = []
        self.fail_retain = 0
        self.fail_recall = 0
        self.fail_delete = 0
        self.reflect_payload = {"text": "reflected"}

    def health(self):
        return {"ok": True}

    def retain(self, *, content, record_id, kind, metadata):
        if self.fail_retain:
            self.fail_retain -= 1
            raise RuntimeError(f"{self.name} retain failure")
        external = f"{self.name}:{record_id}"
        self.retained[external] = {
            "content": content,
            "record_id": record_id,
            "kind": kind,
            "metadata": metadata,
        }
        return BackendReceipt(self.name, external)

    def recall(self, *, query, limit):
        if self.fail_recall:
            self.fail_recall -= 1
            raise RuntimeError(f"{self.name} recall failure")
        return self.hits[:limit]

    def delete(self, *, external_id, metadata):
        if self.fail_delete:
            self.fail_delete -= 1
            raise RuntimeError(f"{self.name} delete failure")
        self.deleted.append(external_id)
        self.retained.pop(external_id, None)

    def reflect(self, *, query):
        return {**self.reflect_payload, "query": query}


@pytest.fixture
def config():
    cfg = RouterConfig(
        namespace="project",
        environment="staging",
        policy=HINDSIGHT_MNEMOSYNE,
    )
    cfg.apply_policy_defaults()
    cfg.hindsight.bank_id = "project-staging"
    cfg.mnemosyne.bank = "project-staging-checkpoints"
    cfg.routing.start_worker = False
    cfg.routing.retry_base_seconds = 0.1
    cfg.routing.retry_max_seconds = 1.0
    cfg.validate()
    return cfg


@pytest.fixture
def router(tmp_path, config):
    primary = FakeBackend("hindsight")
    checkpoint = FakeBackend("mnemosyne")
    instance = MemoryRouter(
        config=config,
        store=RouterStore(
            tmp_path / "router.db",
            namespace=config.namespace,
            environment=config.environment,
            profile_fingerprint="test-profile",
            strict_binding=True,
        ),
        primary=primary,
        checkpoint=checkpoint,
    )
    yield instance, primary, checkpoint
    instance.close()
