from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class MemoryHit:
    content: str
    score: float = 0.0
    external_id: str | None = None
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BackendReceipt:
    backend: str
    external_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecallResult:
    hits: list[MemoryHit]
    backend: str
    fallback_used: bool = False
    primary_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "hits": [hit.to_dict() for hit in self.hits],
            "backend": self.backend,
            "fallback_used": self.fallback_used,
            "primary_error": self.primary_error,
        }


@dataclass(frozen=True)
class CheckpointResult:
    record_id: str
    duplicate: bool
    delivery_states: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
