from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import BackendReceipt, MemoryHit


class MemoryBackend(ABC):
    name: str

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def retain(
        self,
        *,
        content: str,
        record_id: str,
        kind: str,
        metadata: dict[str, Any],
    ) -> BackendReceipt:
        raise NotImplementedError

    @abstractmethod
    def recall(self, *, query: str, limit: int) -> list[MemoryHit]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, *, external_id: str, metadata: dict[str, Any]) -> None:
        raise NotImplementedError

    def reflect(self, *, query: str) -> dict[str, Any]:
        raise NotImplementedError(f"{self.name} does not support reflect")

    def close(self) -> None:
        return None
