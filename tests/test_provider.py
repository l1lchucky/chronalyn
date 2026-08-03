import json

from hermes_memory_router.provider import HermesMemoryRouterProvider
from hermes_memory_router.tools import TOOL_SCHEMAS


def test_provider_name_and_tools():
    provider = HermesMemoryRouterProvider()
    assert provider.name == "hermes_memory_router"
    names = {schema["name"] for schema in TOOL_SCHEMAS}
    assert "memory_router_checkpoint" in names
    assert "memory_router_status" in names


def test_uninitialized_tool_fails_cleanly():
    provider = HermesMemoryRouterProvider()
    payload = json.loads(provider.handle_tool_call("memory_router_status", {}))
    assert payload["ok"] is False
