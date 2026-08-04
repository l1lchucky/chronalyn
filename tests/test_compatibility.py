from __future__ import annotations

import json

import pytest

from chronalyn import identity
from chronalyn.compatibility import (
    active_memory_providers,
    backup_configuration,
    discover,
    is_local_endpoint,
    restore_backup,
    set_active_provider_with_hermes,
)
from chronalyn.exceptions import ConfigurationError


def test_active_provider_reads_singular_and_plural(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("memory:\n  provider: hindsight\n")
    assert active_memory_providers(tmp_path) == ("hindsight",)
    config.write_text("memory:\n  providers: [hermes_memory_router, mnemosyne]\n")
    # Values are reported verbatim from config; discovery never rewrites the
    # user's configured provider id.
    assert active_memory_providers(tmp_path) == (
        "hermes_memory_router",
        "mnemosyne",
    )


def test_router_plus_any_other_provider_is_conflict(tmp_path):
    (tmp_path / "config.yaml").write_text("memory:\n  providers: [hermes_memory_router, honcho]\n")
    state = discover(tmp_path)
    assert state.conflicts
    assert "sole active" in state.conflicts[0]


def test_hindsight_config_discovery(tmp_path):
    path = tmp_path / "hindsight/config.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"deployment": {"api_url": "http://127.0.0.1:8888"}, "bank_id": "bank"})
    )
    state = discover(tmp_path)
    assert state.hindsight_api_url == "http://127.0.0.1:8888"
    assert state.hindsight_bank_id == "bank"
    assert state.hindsight_is_cloud is False


def test_local_endpoint_detection():
    assert is_local_endpoint("http://localhost:8888")
    assert is_local_endpoint("http://127.0.0.1:8888")
    assert not is_local_endpoint("https://cloud.example.test")


def test_backup_restore_removes_files_that_were_absent(tmp_path):
    (tmp_path / "config.yaml").write_text("memory:\n  provider: hindsight\n")
    backup = backup_configuration(tmp_path, reason="test")
    new_router = tmp_path / "memory-router/config.json"
    new_router.parent.mkdir(parents=True, exist_ok=True)
    new_router.write_text("{}")
    restored = restore_backup(tmp_path, backup)
    assert not new_router.exists()
    assert "removed:memory-router/config.json" in restored


def test_manual_activation_instruction_uses_canonical_provider_id(monkeypatch):
    monkeypatch.setattr(
        "chronalyn.compatibility.find_hermes_command",
        lambda home=None: None,
    )

    with pytest.raises(ConfigurationError) as excinfo:
        set_active_provider_with_hermes(identity.PROVIDER_ID)

    message = str(excinfo.value)
    assert f"hermes config set memory.provider {identity.PROVIDER_ID}" in message
    assert identity.LEGACY_PROVIDER_ID not in message


def test_activation_uses_selected_hermes_home(tmp_path, monkeypatch):
    hermes = tmp_path / "bin/hermes"
    hermes.parent.mkdir()
    hermes.write_text("#!/bin/sh\n")
    hermes.chmod(0o755)
    captured = {}

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(
        "chronalyn.compatibility.find_hermes_command",
        lambda home=None: str(hermes),
    )

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["env"] = kwargs["env"]
        return Result()

    monkeypatch.setattr("chronalyn.compatibility.subprocess.run", fake_run)
    set_active_provider_with_hermes("chronalyn", tmp_path)
    assert captured["env"]["HERMES_HOME"] == str(tmp_path)
    assert captured["command"][-1] == "chronalyn"


def test_hindsight_config_supports_official_camelcase_aliases(tmp_path):
    path = tmp_path / "hindsight/config.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "mode": "local_external",
                "apiUrl": "https://memory.internal.example",
                "bankId": "project-production",
            }
        )
    )
    state = discover(tmp_path)
    assert state.hindsight_api_url == "https://memory.internal.example"
    assert state.hindsight_bank_id == "project-production"
    assert state.hindsight_mode == "local_external"
    assert state.hindsight_is_cloud is False
    assert state.hindsight_is_remote is True


def test_active_provider_reads_block_list_without_yaml_dependency(tmp_path):
    (tmp_path / "config.yaml").write_text(
        "model:\n  provider: openai\n"
        "memory:\n"
        "  providers:\n"
        "    - hermes_memory_router\n"
        "    - hindsight\n"
        "tools:\n  enabled: true\n"
    )
    assert active_memory_providers(tmp_path) == (
        "hermes_memory_router",
        "hindsight",
    )


def test_legacy_provider_id_plus_other_provider_is_still_a_conflict(tmp_path):
    """A pre-rename installation must not lose conflict detection."""
    (tmp_path / "config.yaml").write_text("memory:\n  providers: [hermes_memory_router, honcho]\n")
    state = discover(tmp_path)
    assert state.conflicts
    assert "sole active" in state.conflicts[0]


def test_backup_restore_removes_new_plugin_entry(tmp_path):
    """Rollback must remove entries created after the backup was taken.

    The entry lives at Hermes' real discovery root, $HERMES_HOME/plugins/<id>/.
    """
    backup = backup_configuration(tmp_path, reason="plugin rollback")
    plugin = tmp_path / "plugins" / "chronalyn"
    plugin.mkdir(parents=True)
    (plugin / "__init__.py").write_text("new")
    (plugin / "plugin.yaml").write_text("new")
    restored = restore_backup(tmp_path, backup)
    assert not (plugin / "__init__.py").exists()
    assert not (plugin / "plugin.yaml").exists()
    assert "removed:plugins/chronalyn/__init__.py" in restored
