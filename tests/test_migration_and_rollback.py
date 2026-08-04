"""Detection, migration planning, backup and rollback for existing installs.

These cover the upgrade path for a pre-rename Hermes Memory Router installation:
the old configuration must be detected, presented as a plan, backed up, and only
then changed — with a working rollback and no data migration.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chronalyn import identity
from chronalyn.compatibility import (
    active_memory_providers,
    backup_configuration,
    discover,
    latest_backup,
    managed_backup_paths,
    restore_backup,
)
from chronalyn.exceptions import ConfigurationError
from chronalyn.operations import build_plan, rollback_latest
from chronalyn.plugin_entry import install_plugin_entries
from chronalyn.policy import HINDSIGHT_ONLY


def _legacy_install(home: Path) -> None:
    """Create a pre-rename installation: legacy provider id + Hindsight config."""
    (home / "config.yaml").write_text(
        f"memory:\n  provider: {identity.LEGACY_PROVIDER_ID}\n", encoding="utf-8"
    )
    hindsight = home / "hindsight" / "config.json"
    hindsight.parent.mkdir(parents=True, exist_ok=True)
    hindsight.write_text(
        json.dumps(
            {
                "api_url": "http://127.0.0.1:8888",
                "bank_id": "acme-production",
                "mode": "local_external",
                "some_advanced_setting": "must-survive",
            }
        ),
        encoding="utf-8",
    )


# -- Detection --------------------------------------------------------------


def test_detects_existing_legacy_provider_configuration(tmp_path: Path) -> None:
    _legacy_install(tmp_path)

    state = discover(tmp_path)

    assert state.active_providers == (identity.LEGACY_PROVIDER_ID,)
    # A lone legacy id is this router, not a conflict.
    assert state.conflicts == ()
    assert state.hindsight_config_exists
    assert state.hindsight_bank_id == "acme-production"


def test_detects_direct_hindsight_configuration(tmp_path: Path) -> None:
    """Adopting a direct Hindsight user must be recognised, not overwritten."""
    (tmp_path / "config.yaml").write_text("memory:\n  provider: hindsight\n", encoding="utf-8")
    hindsight = tmp_path / "hindsight" / "config.json"
    hindsight.parent.mkdir(parents=True)
    hindsight.write_text(json.dumps({"api_url": "http://127.0.0.1:8888", "bank_id": "b"}))

    state = discover(tmp_path)

    assert state.active_providers == ("hindsight",)
    assert state.hindsight_bank_id == "b"
    assert state.conflicts == ()


def test_fresh_install_detects_nothing_configured(tmp_path: Path) -> None:
    state = discover(tmp_path)
    assert state.active_providers == ()
    assert state.conflicts == ()
    assert not state.router_config_exists


# -- Migration planning -----------------------------------------------------


def test_plan_preserves_memories_and_promises_no_migration(tmp_path: Path) -> None:
    _legacy_install(tmp_path)
    state = discover(tmp_path)

    plan = build_plan(state, policy=HINDSIGHT_ONLY)
    rendered = plan.render()

    assert plan.proposed_provider == identity.PROVIDER_ID
    assert plan.current_provider == identity.LEGACY_PROVIDER_ID
    assert plan.existing_hindsight_memories == "Preserved"
    assert plan.migration == "None"
    # The plan must show the user both sides of the change before anything runs.
    assert identity.LEGACY_PROVIDER_ID in rendered
    assert identity.PROVIDER_ID in rendered
    assert "acme-production" in rendered


def test_plan_keeps_hindsight_only_policy_without_mnemosyne(tmp_path: Path) -> None:
    """Mnemosyne must never be silently enabled during migration."""
    _legacy_install(tmp_path)
    plan = build_plan(discover(tmp_path), policy=HINDSIGHT_ONLY)

    assert plan.checkpoint_backend == ""
    assert plan.fallback == "Disabled"
    assert plan.verified_checkpoints == "Hindsight only"


# -- Backup -----------------------------------------------------------------


def test_backup_covers_both_provider_ids_at_the_real_discovery_root(
    tmp_path: Path,
) -> None:
    paths = [p.relative_to(tmp_path).as_posix() for p in managed_backup_paths(tmp_path)]

    for provider_id in identity.PROVIDER_IDS:
        assert f"plugins/{provider_id}/__init__.py" in paths
        assert f"plugins/{provider_id}/plugin.yaml" in paths
    # The undiscoverable pre-RC path must not be reintroduced.
    assert not any("plugins/memory/" in path for path in paths)


def test_backup_records_installed_entries_and_hindsight_config(tmp_path: Path) -> None:
    _legacy_install(tmp_path)
    install_plugin_entries(tmp_path)

    backup = backup_configuration(tmp_path, reason="migration test")
    metadata = json.loads((backup / "backup.json").read_text(encoding="utf-8"))

    assert "config.yaml" in metadata["copied"]
    assert "hindsight/config.json" in metadata["copied"]
    assert metadata["active_providers"] == [identity.LEGACY_PROVIDER_ID]
    for provider_id in identity.PROVIDER_IDS:
        assert f"plugins/{provider_id}/__init__.py" in metadata["copied"]


def test_backup_never_copies_backend_data(tmp_path: Path) -> None:
    """Backups capture configuration only; memories are never duplicated."""
    paths = [p.name for p in managed_backup_paths(tmp_path)]
    assert identity.STATE_DB_FILENAME not in paths


# -- Rollback ---------------------------------------------------------------


def test_rollback_restores_previous_provider_selection(tmp_path: Path) -> None:
    """Rollback must return Hermes to direct Hindsight."""
    (tmp_path / "config.yaml").write_text("memory:\n  provider: hindsight\n", encoding="utf-8")

    backup = backup_configuration(tmp_path, reason="pre-activation")
    # Simulate activation of Chronalyn after the backup.
    (tmp_path / "config.yaml").write_text(
        f"memory:\n  provider: {identity.PROVIDER_ID}\n", encoding="utf-8"
    )
    assert active_memory_providers(tmp_path) == (identity.PROVIDER_ID,)

    restore_backup(tmp_path, backup)

    assert active_memory_providers(tmp_path) == ("hindsight",)


def test_rollback_preserves_hindsight_advanced_settings(tmp_path: Path) -> None:
    _legacy_install(tmp_path)
    backup = backup_configuration(tmp_path, reason="pre-activation")

    hindsight = tmp_path / "hindsight" / "config.json"
    hindsight.write_text(json.dumps({"api_url": "https://elsewhere.example"}), encoding="utf-8")

    restore_backup(tmp_path, backup)

    payload = json.loads(hindsight.read_text(encoding="utf-8"))
    assert payload["some_advanced_setting"] == "must-survive"
    assert payload["bank_id"] == "acme-production"


def test_rollback_latest_picks_the_most_recent_backup(tmp_path: Path) -> None:
    (tmp_path / "config.yaml").write_text("memory:\n  provider: hindsight\n", encoding="utf-8")
    backup_configuration(tmp_path, reason="first")
    second = backup_configuration(tmp_path, reason="second")

    assert latest_backup(tmp_path) == second

    chosen, restored = rollback_latest(tmp_path)
    assert chosen == second
    assert "config.yaml" in restored


def test_rollback_without_a_backup_fails_loudly(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="No router configuration backup"):
        rollback_latest(tmp_path)


def test_rollback_never_deletes_router_state_or_backend_data(tmp_path: Path) -> None:
    (tmp_path / "config.yaml").write_text("memory:\n  provider: hindsight\n", encoding="utf-8")
    state_dir = tmp_path / identity.STATE_DIRNAME
    state_dir.mkdir(parents=True, exist_ok=True)
    database = state_dir / identity.STATE_DB_FILENAME
    database.write_bytes(b"router-state")

    backup = backup_configuration(tmp_path, reason="pre-activation")
    restore_backup(tmp_path, backup)

    assert database.read_bytes() == b"router-state"
