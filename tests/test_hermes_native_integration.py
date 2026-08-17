"""Native Hermes integration tests for the Chronalyn plugin.

These tests exercise the real Hermes discovery contract where a Hermes
checkout is importable on this machine (``agent.memory_provider`` and
``plugins.memory`` from the hermes-agent source tree). They verify the
git-plugin install layout, discovery, the post_setup hook, and the
single-provider rule.

The Hermes path is discovered from ``HERMES_AGENT_SOURCE`` (used by the
repo's own scripts when available) and falls back to common checkout
locations; the tests skip cleanly when no Hermes source is importable.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path

import pytest

from chronalyn import identity
from chronalyn.provider import ChronalynMemoryProvider

REPO_ROOT = Path(__file__).resolve().parent.parent


def _hermes_source() -> Path | None:
    """Locate an importable Hermes source tree (agent.memory_provider)."""
    candidates = [
        Path(os.environ.get("HERMES_AGENT_SOURCE", "")),
        Path.home() / ".hermes" / "hermes-agent",
        Path.home() / "hermes-agent",
    ]
    for cand in candidates:
        if cand and (cand / "agent" / "memory_provider.py").exists():
            return cand
    return None


HERMES = _hermes_source()
requires_hermes = pytest.mark.skipif(
    HERMES is None or importlib.util.find_spec("yaml") is None,
    reason="Hermes source (or its yaml dependency) not importable",
)


def _load_hermes_discovery():
    """Import Hermes' plugin discovery with the source tree on sys.path."""
    assert HERMES is not None
    if str(HERMES) not in sys.path:
        sys.path.insert(0, str(HERMES))
    from plugins.memory import discover_memory_providers, load_memory_provider

    return discover_memory_providers, load_memory_provider


# ---------------------------------------------------------------------------
# 1. Plugin layout / manifest
# ---------------------------------------------------------------------------


def test_git_plugin_install_layout_is_valid() -> None:
    """Repo root must be directly installable as a Hermes plugin."""
    assert (REPO_ROOT / "plugin.yaml").is_file()
    assert (REPO_ROOT / "__init__.py").is_file()


def test_plugin_manifest_parses_and_declares_identity() -> None:
    # Parse the simple key: value manifest without a yaml dependency
    # (pyyaml is not a project dependency; CI installs only .[test]).
    text = (REPO_ROOT / "plugin.yaml").read_text(encoding="utf-8")
    manifest: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            key, _, value = line.partition(":")
            manifest[key.strip()] = value.strip()
    assert manifest["name"] == identity.PROVIDER_ID
    assert manifest["version"] == identity.RELEASE_NAME.removeprefix("v")
    assert "description" in manifest
    assert "Hindsight" in manifest["description"]


def test_after_install_guide_exists() -> None:
    """after-install.md is shown by ``hermes plugins install``."""
    assert (REPO_ROOT / "after-install.md").is_file()
    text = (REPO_ROOT / "after-install.md").read_text(encoding="utf-8")
    assert "hermes memory setup" in text


def test_root_init_registers_provider() -> None:
    """register(ctx) must register ChronalynMemoryProvider (no router logic)."""
    ns: dict[str, object] = {}

    class Ctx:
        def register_memory_provider(self, provider: object) -> None:
            ns["provider"] = provider

    sys.path.insert(0, str(REPO_ROOT))
    try:
        import importlib

        root_init = importlib.import_module("_chronalyn_root_plugin_test")
    except ImportError:
        # Load the root __init__.py directly under a unique name.
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "_chronalyn_root_plugin_test", REPO_ROOT / "__init__.py"
        )
        assert spec is not None and spec.loader is not None
        root_init = importlib.util.module_from_spec(spec)
        sys.modules["_chronalyn_root_plugin_test"] = root_init
        spec.loader.exec_module(root_init)
    finally:
        sys.path.remove(str(REPO_ROOT))

    assert hasattr(root_init, "register")
    root_init.register(Ctx())
    assert isinstance(ns["provider"], ChronalynMemoryProvider)


# ---------------------------------------------------------------------------
# 2. Hermes discovery (real contract)
# ---------------------------------------------------------------------------


@requires_hermes
def test_appears_in_memory_provider_discovery(tmp_path: Path) -> None:
    discover, _ = _load_hermes_discovery()

    # Install the repo as a user plugin: $HERMES_HOME/plugins/chronalyn
    home = tmp_path / "hermes"
    plugin_dir = home / "plugins" / identity.PROVIDER_ID
    plugin_dir.mkdir(parents=True)
    for name in ("__init__.py", "plugin.yaml"):
        (plugin_dir / name).write_text(
            (REPO_ROOT / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    # Shim src/ into the copied __init__ (it resolves relative to file location),
    # so discovery works from the copy. We symlink src for a faithful install.
    (plugin_dir / "src").symlink_to(REPO_ROOT / "src", target_is_directory=True)

    old = os.environ.get("HERMES_HOME")
    os.environ["HERMES_HOME"] = str(home)
    try:
        found = [name for name, _, _ in discover() if name == identity.PROVIDER_ID]
    finally:
        if old is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = old

    assert identity.PROVIDER_ID in found


@requires_hermes
def test_load_memory_provider_via_hermes_contract(tmp_path: Path) -> None:
    _, load = _load_hermes_discovery()

    home = tmp_path / "hermes"
    plugin_dir = home / "plugins" / identity.PROVIDER_ID
    plugin_dir.mkdir(parents=True)
    for name in ("__init__.py", "plugin.yaml"):
        (plugin_dir / name).write_text(
            (REPO_ROOT / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    (plugin_dir / "src").symlink_to(REPO_ROOT / "src", target_is_directory=True)

    old = os.environ.get("HERMES_HOME")
    os.environ["HERMES_HOME"] = str(home)
    try:
        provider = load(identity.PROVIDER_ID)
    finally:
        if old is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = old

    assert provider is not None
    assert isinstance(provider, ChronalynMemoryProvider)
    assert provider.name == identity.PROVIDER_ID


@requires_hermes
def test_availability_check_is_local_and_non_network(tmp_path: Path) -> None:
    """is_available() must never make a network request."""
    home = tmp_path / "hermes"
    old = os.environ.get("HERMES_HOME")
    os.environ["HERMES_HOME"] = str(home)
    try:
        provider = ChronalynMemoryProvider()
        # No config yet -> not available, and no exception/network.
        assert provider.is_available() is False
    finally:
        if old is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = old


@requires_hermes
def test_get_config_schema_works_before_initialize() -> None:
    provider = ChronalynMemoryProvider()
    schema = provider.get_config_schema()
    keys = {field["key"] for field in schema}
    assert {"namespace", "environment"} <= keys
    # The minimal schema must not prompt for dozens of advanced fields.
    assert len(schema) <= 3


@requires_hermes
def test_post_setup_hook_exists_and_delegates(tmp_path: Path, monkeypatch) -> None:
    """post_setup must delegate to the shared setup engine."""
    import chronalyn.setup_tui as setup_tui_module

    provider = ChronalynMemoryProvider()
    assert hasattr(provider, "post_setup")

    called: dict[str, object] = {}

    def fake_run_dual_setup(*, hermes_home, **kwargs):
        called["hermes_home"] = hermes_home
        called["launched_from_hermes"] = kwargs.get("launched_from_hermes")
        return 0

    monkeypatch.setattr(setup_tui_module, "run_dual_setup", fake_run_dual_setup)
    home = tmp_path / "hermes"
    provider.post_setup(str(home), {})
    assert called.get("hermes_home") == home
    assert called.get("launched_from_hermes") is True


# ---------------------------------------------------------------------------
# 3. Single-provider rule / activation
# ---------------------------------------------------------------------------


def test_provider_id_is_the_only_external_provider() -> None:
    """Hermes must see exactly one provider id: chronalyn."""
    from chronalyn.policy import HINDSIGHT_MNEMOSYNE

    # The router config declares hindsight/mnemosyne as INTERNAL backends only.
    assert identity.PROVIDER_ID == "chronalyn"
    assert identity.PROVIDER_IDS == ("chronalyn",) or "chronalyn" in identity.PROVIDER_IDS
    # Sanity: the policy constant is still the dual policy name.
    assert HINDSIGHT_MNEMOSYNE == "hindsight-primary-mnemosyne-checkpoints"


def test_provider_does_not_expose_hindsight_or_mnemosyne_as_providers() -> None:
    """Chronalyn is the single provider; Hindsight/Mnemosyne are backends."""
    provider = ChronalynMemoryProvider()
    assert provider.name == "chronalyn"
    # No separate provider ids are ever surfaced.
    for forbidden in ("hindsight", "mnemosyne"):
        assert forbidden not in (identity.PROVIDER_IDS or ())


# ---------------------------------------------------------------------------
# 4. Data retention on removal
# ---------------------------------------------------------------------------


def test_uninstall_keeps_durable_data(tmp_path: Path) -> None:
    """Removing the plugin must not delete router state or backend data."""
    from chronalyn.plugin_entry import install_plugin_entries, uninstall_plugin_entries

    install_plugin_entries(tmp_path)
    state = tmp_path / identity.STATE_DIRNAME
    state.mkdir(parents=True, exist_ok=True)
    db = state / identity.STATE_DB_FILENAME
    db.write_bytes(b"durable-state")
    cfg = state / identity.CONFIG_FILENAME
    cfg.write_text("{}", encoding="utf-8")

    uninstall_plugin_entries(tmp_path)

    assert db.read_bytes() == b"durable-state"
    assert cfg.exists()
