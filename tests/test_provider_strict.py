from __future__ import annotations

from chronalyn.config import RouterConfig
from chronalyn.models import MemoryHit
from chronalyn.provider import HermesMemoryRouterProvider


class RouterStub:
    def recall(self, *, query, limit):
        from chronalyn.models import RecallResult

        return RecallResult(
            hits=[MemoryHit("fact", source="hindsight")],
            backend="hindsight",
        )


def test_prefetch_returns_plain_content_without_custom_fence():
    provider = HermesMemoryRouterProvider()
    provider._router = RouterStub()
    provider._config = RouterConfig()
    result = provider.prefetch("query")
    assert "fact" in result
    assert "<memory_router_context>" not in result
    assert "<memory-context>" not in result


def test_disabled_destructive_tool_is_rejected():
    provider = HermesMemoryRouterProvider()
    provider._router = RouterStub()
    provider._config = RouterConfig()
    result = provider.handle_tool_call(
        "memory_router_forget_apply",
        {"record_id": "mr_1", "confirmation_token": "token"},
    )
    assert "disabled by strict profile" in result
