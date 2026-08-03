from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

from .adapters.base import MemoryBackend
from .config import RouterConfig
from .models import CheckpointResult, RecallResult
from .redaction import sanitize
from .store import RouterStore

logger = logging.getLogger(__name__)


class MemoryRouter:
    def __init__(
        self,
        *,
        config: RouterConfig,
        store: RouterStore,
        primary: MemoryBackend,
        checkpoint: MemoryBackend,
    ) -> None:
        self.config = config
        self.store = store
        self.backends = {
            primary.name: primary,
            checkpoint.name: checkpoint,
        }
        self.primary = primary
        self.checkpoint = checkpoint
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._worker: threading.Thread | None = None
        if config.routing.start_worker:
            self.start_worker()

    def start_worker(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="memory-router-outbox",
        )
        self._worker.start()

    def _worker_loop(self) -> None:
        while not self._stop.is_set():
            try:
                processed = self.drain_outbox()
            except Exception:
                logger.exception("Memory router outbox cycle failed")
                processed = 0
            self._wake.wait(
                0.05 if processed else self.config.routing.worker_poll_seconds
            )
            self._wake.clear()

    def _format_checkpoint(
        self,
        *,
        content: str,
        verification_level: str,
        evidence: str,
        metadata: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        clean_content = sanitize(content, self.config.redaction)
        clean_evidence = sanitize(evidence, self.config.redaction)
        clean_metadata = dict(metadata)
        clean_metadata.update({
            "verification_level": verification_level,
            "redaction_findings": sorted(
                set(clean_content.findings + clean_evidence.findings)
            ),
            "truncated": clean_content.truncated or clean_evidence.truncated,
        })
        body = (
            "[VERIFIED MEMORY CHECKPOINT]\n"
            f"Namespace: {self.config.namespace}\n"
            f"Environment: {self.config.environment}\n"
            f"Verification level: {verification_level}\n"
            "Content:\n"
            f"{clean_content.text}\n"
            "Evidence:\n"
            f"{clean_evidence.text}"
        )
        return body, clean_metadata

    def checkpoint_record(
        self,
        *,
        content: str,
        verification_level: str,
        evidence: str,
        metadata: dict[str, Any] | None = None,
    ) -> CheckpointResult:
        body, meta = self._format_checkpoint(
            content=content,
            verification_level=verification_level,
            evidence=evidence,
            metadata=metadata or {},
        )
        record_id, duplicate = self.store.create_record(
            namespace=self.config.namespace,
            environment=self.config.environment,
            kind="checkpoint",
            content=body,
            metadata=meta,
            backends=[self.primary.name, self.checkpoint.name],
        )
        self._wake.set()
        return CheckpointResult(
            record_id=record_id,
            duplicate=duplicate,
            delivery_states=self.store.delivery_states(record_id),
        )

    def retain_turn(
        self,
        *,
        user_content: str,
        assistant_content: str,
        session_id: str,
        agent_context: str,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        if agent_context not in self.config.routing.automatic_write_contexts:
            return None
        user = sanitize(user_content, self.config.redaction)
        assistant = sanitize(assistant_content, self.config.redaction)
        content = f"[USER]\n{user.text}\n[ASSISTANT]\n{assistant.text}"
        meta = {
            **(metadata or {}),
            "session_id": session_id,
            "agent_context": agent_context,
            "redaction_findings": sorted(set(user.findings + assistant.findings)),
            "truncated": user.truncated or assistant.truncated,
        }
        record_id, _duplicate = self.store.create_record(
            namespace=self.config.namespace,
            environment=self.config.environment,
            kind="turn",
            content=content,
            metadata=meta,
            backends=[self.primary.name],
        )
        self._wake.set()
        return record_id

    def recall(self, *, query: str, limit: int = 5) -> RecallResult:
        primary_error: str | None = None
        try:
            hits = self.primary.recall(query=query, limit=limit)
            if hits or not self.config.routing.fallback_on_empty:
                return RecallResult(hits=hits, backend=self.primary.name)
        except Exception as exc:
            primary_error = str(exc)
            if not self.config.routing.fallback_on_error:
                raise

        hits = self.checkpoint.recall(
            query=query,
            limit=min(limit, self.config.mnemosyne.top_k),
        )
        current = 0
        bounded = []
        for hit in hits:
            remaining = self.config.routing.fallback_max_chars - current
            if remaining <= 0:
                break
            content = hit.content[:remaining]
            bounded.append(
                type(hit)(
                    content=content,
                    score=hit.score,
                    external_id=hit.external_id,
                    source=hit.source,
                    metadata=hit.metadata,
                )
            )
            current += len(content)
        return RecallResult(
            hits=bounded,
            backend=self.checkpoint.name,
            fallback_used=True,
            primary_error=primary_error,
        )

    def reflect(self, *, query: str) -> dict[str, Any]:
        return self.primary.reflect(query=query)

    def forget(self, record_id: str) -> dict[str, Any]:
        self.store.schedule_delete(record_id)
        self._wake.set()
        return {
            "record_id": record_id,
            "delivery_states": self.store.delivery_states(record_id),
        }

    def retry(self, record_id: str | None = None) -> int:
        count = self.store.retry_failed(record_id)
        if count:
            self._wake.set()
        return count

    def drain_outbox(self, limit: int | None = None) -> int:
        limit = limit or self.config.routing.worker_batch_size
        due = self.store.due_deliveries(limit)
        processed = 0
        for delivery in due:
            if not self.store.claim(int(delivery["id"])):
                continue
            processed += 1
            backend = self.backends.get(str(delivery["backend"]))
            if backend is None:
                self._fail_delivery(delivery, RuntimeError("Unknown backend"))
                continue
            try:
                if delivery["operation"] == "retain":
                    receipt = backend.retain(
                        content=str(delivery["content"]),
                        record_id=str(delivery["record_id"]),
                        kind=str(delivery["kind"]),
                        metadata=dict(delivery["metadata"]),
                    )
                    self.store.complete(
                        int(delivery["id"]),
                        external_id=receipt.external_id,
                        receipt=receipt.to_dict(),
                    )
                elif delivery["operation"] == "delete":
                    external_id = str(delivery.get("external_id") or "")
                    if not external_id:
                        raise RuntimeError("Delete delivery has no backend external_id")
                    backend.delete(
                        external_id=external_id,
                        metadata=dict(delivery.get("receipt") or {}),
                    )
                    self.store.complete(int(delivery["id"]), external_id=external_id)
                else:
                    raise RuntimeError(f"Unknown operation {delivery['operation']}")
            except Exception as exc:
                self._fail_delivery(delivery, exc)
        return processed

    def _fail_delivery(self, delivery: dict[str, Any], exc: Exception) -> None:
        attempts = int(delivery["attempts"]) + 1
        max_attempts = self.config.routing.max_attempts
        delay = min(
            self.config.routing.retry_max_seconds,
            self.config.routing.retry_base_seconds * (2 ** min(attempts - 1, 12)),
        )
        next_attempt = time.time() + delay
        error = str(exc)
        dead = bool(max_attempts and attempts >= max_attempts)
        if dead:
            next_attempt = 0
            error = f"max attempts reached; manual retry required: {error}"
        self.store.fail(
            int(delivery["id"]),
            error=error,
            next_attempt_at=next_attempt,
            dead=dead,
        )
        logger.warning(
            "Memory delivery failed record=%s backend=%s operation=%s: %s",
            delivery["record_id"],
            delivery["backend"],
            delivery["operation"],
            exc,
        )

    def status(self) -> dict[str, Any]:
        return {
            "namespace": self.config.namespace,
            "environment": self.config.environment,
            "routing": {
                "automatic_write": "hindsight-only",
                "checkpoint_write": "hindsight+mnemosyne",
                "recall": "hindsight-first, mnemosyne fallback",
            },
            "store": self.store.stats(),
            "backends": {
                name: backend.health()
                for name, backend in self.backends.items()
            },
            "worker_alive": bool(self._worker and self._worker.is_alive()),
        }

    def close(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=10)
        # Final best-effort flush.
        try:
            for _ in range(5):
                if not self.drain_outbox():
                    break
        except Exception:
            logger.exception("Final memory-router flush failed")
        for backend in self.backends.values():
            try:
                backend.close()
            except Exception:
                logger.exception("Backend close failed: %s", backend.name)
        self.store.close()
