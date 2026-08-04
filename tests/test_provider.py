import json
from types import SimpleNamespace

from chronalyn import identity
from chronalyn.provider import HermesMemoryRouterProvider
from chronalyn.tools import TOOL_SCHEMAS


def test_provider_name_and_tools():
    provider = HermesMemoryRouterProvider()
    assert provider.name == "chronalyn"
    names = {schema["name"] for schema in TOOL_SCHEMAS}
    assert "memory_router_checkpoint" in names
    assert "memory_router_status" in names


def test_uninitialized_tool_fails_cleanly():
    provider = HermesMemoryRouterProvider()
    payload = json.loads(provider.handle_tool_call("memory_router_status", {}))
    assert payload["ok"] is False


def test_system_prompt_uses_canonical_brand():
    provider = HermesMemoryRouterProvider()
    provider._config = SimpleNamespace(
        namespace="project",
        environment="staging",
        policy="hindsight-only",
    )

    prompt = provider.system_prompt_block()

    assert prompt.startswith(f"{identity.BRAND} policy\n")
    assert "Hermes Memory Router policy" not in prompt
