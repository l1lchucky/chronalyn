"""Hermes provider-entry installation against the real discovery contract.

The expectations below were derived by probing the installed Hermes, not from
documentation:

* ``plugins/memory/__init__.py::_iter_provider_dirs`` scans
  ``$HERMES_HOME/plugins/<name>/`` for user-installed providers. A nested
  ``plugins/memory/<name>/`` directory is never discovered.
* ``_is_memory_provider_dir`` gates user directories on the literal substring
  ``register_memory_provider`` or ``MemoryProvider`` appearing in the first
  8 KiB of ``__init__.py``.
* ``hermes_cli/plugins.py`` skips manifests declaring ``kind: exclusive``, so
  the generic plugin manager records but does not import a memory provider.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chronalyn import identity
from chronalyn.plugin_entry import (
    install_plugin_entries,
    installed_entries,
    uninstall_plugin_entries,
)

# Mirrors plugins/memory/__init__.py::_is_memory_provider_dir in Hermes.
HERMES_HEURISTIC_MARKERS = ("register_memory_provider", "MemoryProvider")


def _hermes_discovers(directory: Path) -> bool:
    """Reimplement Hermes' user-provider directory heuristic exactly."""
    init_file = directory / "__init__.py"
    if not init_file.exists():
        return False
    source = init_file.read_text(errors="replace", encoding="utf-8")[:8192]
    return any(marker in source for marker in HERMES_HEURISTIC_MARKERS)


def test_entries_install_at_the_flat_user_plugin_root(tmp_path: Path) -> None:
    """Hermes only scans $HERMES_HOME/plugins/<name>; never plugins/memory/<name>."""
    install_plugin_entries(tmp_path)

    canonical = tmp_path / "plugins" / identity.PROVIDER_ID
    assert (canonical / "__init__.py").is_file()
    assert (canonical / "plugin.yaml").is_file()

    # The pre-RC layout was never discoverable and must not be recreated.
    assert not (tmp_path / "plugins" / "memory" / identity.PROVIDER_ID).exists()
    assert not (tmp_path / "plugins" / "memory" / identity.LEGACY_PROVIDER_ID).exists()


def test_entry_satisfies_hermes_discovery_heuristic(tmp_path: Path) -> None:
    """The old entry failed this gate; the RC entry must satisfy it."""
    install_plugin_entries(tmp_path)

    for provider_id in identity.PROVIDER_IDS:
        directory = tmp_path / "plugins" / provider_id
        assert _hermes_discovers(directory), provider_id
        source = (directory / "__init__.py").read_text(encoding="utf-8")
        assert "register_memory_provider" in source


def test_manifest_declares_exclusive_kind_and_matching_name(tmp_path: Path) -> None:
    install_plugin_entries(tmp_path)

    for provider_id in identity.PROVIDER_IDS:
        manifest = (tmp_path / "plugins" / provider_id / "plugin.yaml").read_text(encoding="utf-8")
        assert "kind: exclusive" in manifest
        assert f"name: {provider_id}" in manifest


def test_root_manifest_matches_canonical_public_identity() -> None:
    """The checked-in root manifest is a release input, not another identity source."""
    manifest = Path("plugin.yaml").read_text(encoding="utf-8")

    assert f"name: {identity.PROVIDER_ID}" in manifest
    assert f"version: {identity.RELEASE_NAME.removeprefix('v')}" in manifest
    assert f"description: {identity.BRAND}" in manifest


def test_legacy_provider_id_remains_loadable(tmp_path: Path) -> None:
    """An existing memory.provider: hermes_memory_router must keep resolving."""
    install_plugin_entries(tmp_path)

    legacy = tmp_path / "plugins" / identity.LEGACY_PROVIDER_ID
    assert (legacy / "__init__.py").is_file()
    source = (legacy / "__init__.py").read_text(encoding="utf-8")
    # The alias must delegate to the same implementation, not duplicate it.
    assert "chronalyn" in source


def test_install_is_idempotent(tmp_path: Path) -> None:
    first = install_plugin_entries(tmp_path)
    second = install_plugin_entries(tmp_path)
    assert first == second
    assert sorted(installed_entries(tmp_path)) == sorted(identity.PROVIDER_IDS)


def test_canonical_only_install_omits_legacy_alias(tmp_path: Path) -> None:
    install_plugin_entries(tmp_path, include_legacy_alias=False)
    assert installed_entries(tmp_path) == (identity.PROVIDER_ID,)


def test_uninstall_removes_entries_but_never_touches_data(tmp_path: Path) -> None:
    """Package/plugin removal and data deletion are separate actions."""
    install_plugin_entries(tmp_path)

    state = tmp_path / identity.STATE_DIRNAME
    state.mkdir(parents=True, exist_ok=True)
    database = state / identity.STATE_DB_FILENAME
    database.write_bytes(b"durable-router-state")
    router_config = state / identity.CONFIG_FILENAME
    router_config.write_text("{}", encoding="utf-8")
    hindsight = tmp_path / "hindsight" / "config.json"
    hindsight.parent.mkdir(parents=True, exist_ok=True)
    hindsight.write_text('{"bank_id": "keep-me"}', encoding="utf-8")

    removed = uninstall_plugin_entries(tmp_path)

    assert sorted(removed) == sorted(identity.PROVIDER_IDS)
    assert installed_entries(tmp_path) == ()
    # No backend or durable state may be deleted by plugin removal.
    assert database.read_bytes() == b"durable-router-state"
    assert router_config.exists()
    assert hindsight.read_text(encoding="utf-8") == '{"bank_id": "keep-me"}'


def test_uninstall_is_safe_when_nothing_is_installed(tmp_path: Path) -> None:
    assert uninstall_plugin_entries(tmp_path) == ()


def test_install_refuses_to_clobber_a_foreign_directory(tmp_path: Path) -> None:
    """Never overwrite a directory Chronalyn did not create."""
    foreign = tmp_path / "plugins" / identity.LEGACY_PROVIDER_ID
    foreign.mkdir(parents=True)
    (foreign / "__init__.py").write_text("# unrelated user plugin\n", encoding="utf-8")

    with pytest.raises(Exception) as excinfo:
        install_plugin_entries(tmp_path)

    assert "not managed by" in str(excinfo.value).lower() or "refus" in str(excinfo.value).lower()
    # The foreign file must survive the refusal untouched.
    assert (foreign / "__init__.py").read_text(encoding="utf-8") == ("# unrelated user plugin\n")
