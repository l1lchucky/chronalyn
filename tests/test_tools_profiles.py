from __future__ import annotations

from chronalyn.config import RouterConfig
from chronalyn.tools import tool_schemas_for


def names(config):
    return {item["name"] for item in tool_schemas_for(config)}


def test_standard_tools_include_hindsight_core_operations():
    config = RouterConfig()
    assert names(config) == {
        "memory_router_retain",
        "memory_router_checkpoint",
        "memory_router_recall",
        "memory_router_reflect",
        "memory_router_status",
    }


def test_minimal_tools_are_small():
    config = RouterConfig()
    config.tools.profile = "minimal"
    assert names(config) == {
        "memory_router_recall",
        "memory_router_reflect",
        "memory_router_status",
    }


def test_destructive_tools_are_opt_in():
    config = RouterConfig()
    assert "memory_router_forget_apply" not in names(config)
    config.tools.destructive_model_tools = True
    assert {
        "memory_router_forget_plan",
        "memory_router_forget_apply",
    } <= names(config)
