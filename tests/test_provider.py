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


# ─── Patch 2: tool-schema resolution before initialize() ─────────────────────


def test_get_tool_schemas_before_initialize(monkeypatch, tmp_path):
    """Reproduce Hermes v0.20.0 lifecycle ordering: get_tool_schemas() is
    called by MemoryManager.add_provider() BEFORE initialize().

    A freshly constructed provider must return all five Chronalyn tools
    without having been initialized.
    """
    from chronalyn.config import write_default_config

    hermes_home = tmp_path / "hermes"
    config_dir = hermes_home / "memory-router"
    config_dir.mkdir(parents=True)
    write_default_config(
        config_dir / "config.json",
        namespace="test-ns",
        environment="test-env",
    )
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    provider = HermesMemoryRouterProvider()
    # NOT initialized — this is the add_provider() phase.
    schemas = provider.get_tool_schemas()
    tool_names = [s["name"] for s in schemas]
    assert tool_names == [
        "memory_router_retain",
        "memory_router_checkpoint",
        "memory_router_recall",
        "memory_router_reflect",
        "memory_router_status",
    ]


def test_get_tool_schemas_does_not_create_duplicate_router(monkeypatch, tmp_path):
    """Repeated get_tool_schemas() calls must not spawn duplicate router
    instances or corrupt the config reference."""
    from chronalyn.config import write_default_config

    hermes_home = tmp_path / "hermes"
    config_dir = hermes_home / "memory-router"
    config_dir.mkdir(parents=True)
    write_default_config(
        config_dir / "config.json",
        namespace="dup-ns",
        environment="dup-env",
    )
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    provider = HermesMemoryRouterProvider()
    first = provider.get_tool_schemas()
    second = provider.get_tool_schemas()
    assert first == second
    assert provider._router is None  # no router created by get_tool_schemas


def test_get_tool_schemas_idempotent_after_initialize(monkeypatch, tmp_path):
    """After initialize(), get_tool_schemas() must return the same tools
    and the same config/identity must remain active."""
    from types import SimpleNamespace

    from chronalyn import provider as provider_module
    from chronalyn.config import write_default_config

    hermes_home = tmp_path / "hermes"
    config_dir = hermes_home / "memory-router"
    config_dir.mkdir(parents=True)
    write_default_config(
        config_dir / "config.json",
        namespace="persist-ns",
        environment="persist-env",
    )
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    # This test exercises the tool-schema lifecycle, not Hermes discovery;
    # a bare tmp HERMES_HOME has no Hermes install to discover, so satisfy
    # the strict-compatibility gate with a minimal fake.
    monkeypatch.setattr(
        provider_module,
        "require_strict_hermes_compatibility",
        lambda hermes_home: SimpleNamespace(hermes_home=str(hermes_home), conflicts=()),
    )

    provider = HermesMemoryRouterProvider()
    before = provider.get_tool_schemas()
    provider.initialize(
        session_id="test-session",
        hermes_home=str(hermes_home),
        platform="cli",
        agent_context="primary",
    )
    after = provider.get_tool_schemas()
    assert before == after
    assert provider._config.namespace == "persist-ns"
    assert provider._config.environment == "persist-env"
    provider.shutdown()


def test_get_tool_schemas_empty_without_config(monkeypatch, tmp_path):
    """When no config exists, get_tool_schemas() must return [] (fail safely)."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "nonexistent"))
    provider = HermesMemoryRouterProvider()
    assert provider.get_tool_schemas() == []


def test_hermes_home_isolation(monkeypatch, tmp_path):
    """Config loaded by _ensure_config_loaded must resolve from HERMES_HOME,
    not from the default ~/.hermes or another profile."""
    from chronalyn.config import write_default_config

    home_a = tmp_path / "home-a"
    home_b = tmp_path / "home-b"
    for home in (home_a, home_b):
        d = home / "memory-router"
        d.mkdir(parents=True)
        write_default_config(d / "config.json", namespace="iso", environment="iso")

    # Write distinct namespaces so we can prove which config was loaded.
    import json

    cfg_a = home_a / "memory-router" / "config.json"
    data = json.loads(cfg_a.read_text())
    data["namespace"] = "isolation-a"
    cfg_a.write_text(json.dumps(data))

    monkeypatch.setenv("HERMES_HOME", str(home_b))
    provider = HermesMemoryRouterProvider()
    provider.get_tool_schemas()
    assert provider._config.namespace == "iso"  # loaded from home_b, not home_a

    monkeypatch.setenv("HERMES_HOME", str(home_a))
    provider2 = HermesMemoryRouterProvider()
    provider2.get_tool_schemas()
    assert provider2._config.namespace == "isolation-a"


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
