from __future__ import annotations

import os
from importlib import import_module
from pathlib import Path
from typing import Any

from ..config import MnemosyneConfig
from ..exceptions import BackendOperationError, BackendUnavailable
from ..models import BackendReceipt, MemoryHit
from .base import MemoryBackend


class MnemosyneBackend(MemoryBackend):
    """Mnemosyne adapter using its public top-level Mnemosyne class."""

    name = "mnemosyne"

    def __init__(self, config: MnemosyneConfig, *, session_id: str) -> None:
        self.config = config
        if config.data_dir:
            os.environ.setdefault(
                "MNEMOSYNE_DATA_DIR",
                str(Path(config.data_dir).expanduser()),
            )
        try:
            Mnemosyne = import_module("mnemosyne").Mnemosyne
        except Exception as exc:
            raise BackendUnavailable(
                "mnemosyne-memory is not importable; install mnemosyne-memory>=3.15,<4"
            ) from exc
        try:
            self._memory = Mnemosyne(session_id=session_id, bank=config.bank)
        except Exception as exc:
            raise BackendUnavailable(f"Mnemosyne initialization failed: {exc}") from exc

    def health(self) -> dict[str, Any]:
        try:
            stats: dict[str, Any] = {}
            if hasattr(self._memory, "get_stats"):
                stats = self._memory.get_stats() or {}
            return {"ok": True, "details": stats}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def retain(
        self,
        *,
        content: str,
        record_id: str,
        kind: str,
        metadata: dict[str, Any],
    ) -> BackendReceipt:
        try:
            external_id = self._memory.remember(
                content,
                source=f"memory-router:{kind}",
                importance=0.95 if kind == "checkpoint" else 0.7,
                metadata={
                    **metadata,
                    "memory_router_record_id": record_id,
                    "memory_router_kind": kind,
                },
                scope="global",
                trust_tier="EXTERNAL_WRITE",
            )
        except TypeError:
            # Compatibility fallback for older 3.x releases.
            external_id = self._memory.remember(
                content,
                source=f"memory-router:{kind}",
                importance=0.95 if kind == "checkpoint" else 0.7,
                metadata=metadata,
            )
        except Exception as exc:
            raise BackendOperationError(f"Mnemosyne retain failed: {exc}") from exc
        if not external_id:
            raise BackendOperationError("Mnemosyne filtered or rejected the memory")
        return BackendReceipt(self.name, str(external_id))

    def recall(self, *, query: str, limit: int) -> list[MemoryHit]:
        try:
            raw = self._memory.recall(query, top_k=limit) or []
        except TypeError:
            raw = self._memory.recall(query, limit=limit) or []
        except Exception as exc:
            raise BackendOperationError(f"Mnemosyne recall failed: {exc}") from exc

        hits: list[MemoryHit] = []
        for item in raw[:limit]:
            if isinstance(item, str):
                hits.append(MemoryHit(content=item, source="mnemosyne"))
                continue
            if not isinstance(item, dict):
                continue
            content = item.get("content") or item.get("text") or ""
            if not content:
                continue
            hits.append(
                MemoryHit(
                    content=str(content),
                    score=float(item.get("score") or item.get("similarity") or 0.0),
                    external_id=str(item.get("id") or item.get("memory_id") or "") or None,
                    source="mnemosyne",
                    metadata={k: v for k, v in item.items() if k not in {"content", "text"}},
                )
            )
        return hits

    def delete(self, *, external_id: str, metadata: dict[str, Any]) -> None:
        try:
            self._memory.forget(external_id)
        except Exception as exc:
            raise BackendOperationError(f"Mnemosyne forget failed: {exc}") from exc
