from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .. import identity
from ..config import HindsightConfig
from ..exceptions import BackendOperationError
from ..models import BackendReceipt, MemoryHit
from .base import MemoryBackend


class HindsightBackend(MemoryBackend):
    """Hindsight REST adapter using only Python's standard library.

    This avoids importing Hermes' private bundled provider class. The endpoints
    follow Hindsight's public v1 REST API for retain, recall, reflect, health,
    and document deletion.
    """

    name = "hindsight"

    def __init__(self, config: HindsightConfig, api_key: str = "") -> None:
        self.config = config
        self.api_url = config.api_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": identity.USER_AGENT,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        url = f"{self.api_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        # HindsightConfig.validate restricts the base URL to HTTP(S).
        request = urllib.request.Request(  # noqa: S310
            url, data=data, headers=self._headers(), method=method
        )
        context = None
        if url.startswith("https://") and not self.config.verify_tls:
            context = ssl._create_unverified_context()  # noqa: S323 - explicit operator choice
        try:
            with urllib.request.urlopen(  # noqa: S310 - URL restricted to HTTP(S) above
                request,
                timeout=timeout or self.config.timeout_seconds,
                context=context,
            ) as response:
                payload = response.read().decode("utf-8", errors="replace")
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode("utf-8", errors="replace")
            raise BackendOperationError(
                f"Hindsight HTTP {exc.code} for {method} {path}: {payload[:1000]}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise BackendOperationError(
                f"Hindsight request failed for {method} {path}: {exc}"
            ) from exc

    def health(self) -> dict[str, Any]:
        errors: list[str] = []
        for path in ("/health", "/version"):
            try:
                payload = self._request(
                    "GET",
                    path,
                    timeout=min(5.0, self.config.timeout_seconds),
                )
                return {"ok": True, "endpoint": path, "details": payload}
            except Exception as exc:
                errors.append(f"{path}: {exc}")
        return {"ok": False, "error": "; ".join(errors)}

    def retain(
        self,
        *,
        content: str,
        record_id: str,
        kind: str,
        metadata: dict[str, Any],
    ) -> BackendReceipt:
        document_id = f"memory-router:{record_id}"
        bank = urllib.parse.quote(self.config.bank_id, safe="")
        item: dict[str, Any] = {
            "content": content,
            "document_id": document_id,
            "metadata": {
                **metadata,
                "memory_router_record_id": record_id,
                "memory_router_kind": kind,
            },
        }
        if self.config.tags:
            item["tags"] = self.config.tags
        payload = self._request(
            "POST",
            f"/v1/default/banks/{bank}/memories",
            {"items": [item], "async": False},
        )
        return BackendReceipt(
            backend=self.name,
            external_id=document_id,
            metadata={"response": payload},
        )

    @staticmethod
    def _parse_hits(payload: dict[str, Any], limit: int) -> list[MemoryHit]:
        raw = payload.get("results") or payload.get("items") or []
        hits: list[MemoryHit] = []
        for item in raw[:limit]:
            if isinstance(item, str):
                hits.append(MemoryHit(content=item, source="hindsight"))
                continue
            if not isinstance(item, dict):
                continue
            content = (
                item.get("text")
                or item.get("content")
                or item.get("memory")
                or item.get("fact")
                or ""
            )
            if not content:
                continue
            hits.append(
                MemoryHit(
                    content=str(content),
                    score=float(item.get("score") or item.get("relevance") or 0.0),
                    external_id=str(item.get("id") or item.get("memory_id") or "") or None,
                    source="hindsight",
                    metadata={k: v for k, v in item.items() if k not in {"text", "content"}},
                )
            )
        return hits

    def recall(self, *, query: str, limit: int) -> list[MemoryHit]:
        bank = urllib.parse.quote(self.config.bank_id, safe="")
        payload: dict[str, Any] = {
            "query": query,
            "max_tokens": self.config.recall_max_tokens,
            "budget": self.config.recall_budget,
        }
        if self.config.recall_types:
            payload["types"] = self.config.recall_types
        response = self._request(
            "POST",
            f"/v1/default/banks/{bank}/memories/recall",
            payload,
        )
        return self._parse_hits(response, limit)

    def reflect(self, *, query: str) -> dict[str, Any]:
        bank = urllib.parse.quote(self.config.bank_id, safe="")
        return self._request(
            "POST",
            f"/v1/default/banks/{bank}/reflect",
            {
                "query": query,
                "budget": self.config.recall_budget,
                "max_tokens": self.config.recall_max_tokens,
            },
        )

    def delete(self, *, external_id: str, metadata: dict[str, Any]) -> None:
        bank = urllib.parse.quote(self.config.bank_id, safe="")
        document = urllib.parse.quote(external_id, safe="")
        self._request(
            "DELETE",
            f"/v1/default/banks/{bank}/documents/{document}",
        )
