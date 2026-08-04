"""Install and remove Hermes memory-provider entries for Chronalyn.

The layout and content here are dictated by the *real* Hermes discovery
contract, verified against an installed Hermes rather than inferred:

1. User-installed memory providers are discovered from
   ``$HERMES_HOME/plugins/<provider-id>/`` by
   ``plugins/memory/__init__.py::_iter_provider_dirs``. A nested
   ``plugins/memory/<provider-id>/`` directory is never discovered.
2. ``_is_memory_provider_dir`` only accepts a directory whose ``__init__.py``
   contains the literal ``register_memory_provider`` or ``MemoryProvider``
   within the first 8 KiB.
3. ``plugin.yaml`` declaring ``kind: exclusive`` makes the generic plugin
   manager record the manifest without importing the module, leaving activation
   to the memory category via ``memory.provider``.

Nothing here imports a private Hermes API, edits Hermes core, or invents an
entry-point group: the installed Hermes has no entry-point path for memory
providers.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from . import identity
from .exceptions import ConfigurationError

# Marker file recording that Chronalyn owns a provider directory. Without it we
# refuse to modify or delete a directory, so an unrelated user plugin that
# happens to share the name is never clobbered.
OWNERSHIP_MARKER = ".chronalyn-managed"

_CANONICAL_ENTRY = '''"""Chronalyn memory provider entry for Hermes Agent.

Installed by `{cli} setup`. This file is intentionally tiny: it adapts the
Chronalyn implementation to Hermes' public MemoryProvider discovery contract.
"""

from chronalyn.provider import ChronalynMemoryProvider


def register(ctx):
    """Register Chronalyn as Hermes' single external memory provider."""
    ctx.register_memory_provider(ChronalynMemoryProvider())


__all__ = ["ChronalynMemoryProvider", "register"]
'''

_LEGACY_ENTRY = '''"""Compatibility entry for the former `{legacy_id}` provider id.

Existing installations may still have `memory.provider: {legacy_id}` in
config.yaml. This alias keeps that configuration loadable and delegates to the
same Chronalyn implementation, so no memory is copied, recreated or reindexed.

Migrate at your convenience with `{cli} setup`, which previews the change and
backs up configuration before applying it. This alias is temporary and will be
removed in a future major release.
"""

from chronalyn.provider import ChronalynMemoryProvider


def register(ctx):
    """Register Chronalyn under the legacy provider id."""
    ctx.register_memory_provider(ChronalynMemoryProvider(name="{legacy_id}"))


__all__ = ["ChronalynMemoryProvider", "register"]
'''

_MANIFEST = """name: {provider_id}
version: {version}
description: {description}
kind: exclusive
pip_dependencies: []
requires_env: []
"""

_CANONICAL_DESCRIPTION = (
    "Chronalyn — Hindsight-first memory orchestration with verified Mnemosyne checkpoints."
)
_LEGACY_DESCRIPTION = (
    "Compatibility alias for Chronalyn (formerly Hermes Memory Router). "
    "Prefer the 'chronalyn' provider id."
)


def _plugins_root(hermes_home: Path) -> Path:
    return hermes_home.expanduser() / "plugins"


def entry_dir(hermes_home: Path, provider_id: str) -> Path:
    """Return the discovery path Hermes actually scans for *provider_id*."""
    return _plugins_root(hermes_home) / provider_id


def _entry_source(provider_id: str) -> str:
    if provider_id == identity.PROVIDER_ID:
        return _CANONICAL_ENTRY.format(cli=identity.CLI_COMMAND)
    return _LEGACY_ENTRY.format(
        legacy_id=identity.LEGACY_PROVIDER_ID,
        cli=identity.CLI_COMMAND,
    )


def _manifest_source(provider_id: str) -> str:
    description = (
        _CANONICAL_DESCRIPTION if provider_id == identity.PROVIDER_ID else _LEGACY_DESCRIPTION
    )
    return _MANIFEST.format(
        provider_id=provider_id,
        version=identity.VERSION,
        description=description,
    )


def _assert_writable(directory: Path) -> None:
    """Refuse to touch a pre-existing directory Chronalyn does not own."""
    if not directory.exists():
        return
    if (directory / OWNERSHIP_MARKER).exists():
        return
    raise ConfigurationError(
        f"Refusing to modify {directory}: the directory exists and is not "
        f"managed by {identity.BRAND}. Move or remove it, then rerun setup."
    )


def install_plugin_entries(
    hermes_home: Path,
    *,
    include_legacy_alias: bool = True,
) -> tuple[str, ...]:
    """Install provider entries and return the provider ids written.

    Writes the canonical ``chronalyn`` entry and, by default, a legacy
    ``hermes_memory_router`` alias so an existing configuration keeps working.
    Idempotent: re-running rewrites the managed files in place.
    """
    provider_ids = identity.PROVIDER_IDS if include_legacy_alias else (identity.PROVIDER_ID,)

    # Validate every target before writing anything, so a refusal cannot leave a
    # half-installed pair of entries behind.
    targets = [entry_dir(hermes_home, provider_id) for provider_id in provider_ids]
    for directory in targets:
        _assert_writable(directory)

    for provider_id, directory in zip(provider_ids, targets, strict=True):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / OWNERSHIP_MARKER).write_text(
            f"{identity.BRAND} {identity.RELEASE_NAME}\n", encoding="utf-8"
        )
        (directory / "__init__.py").write_text(_entry_source(provider_id), encoding="utf-8")
        (directory / "plugin.yaml").write_text(_manifest_source(provider_id), encoding="utf-8")

    return provider_ids


def installed_entries(hermes_home: Path) -> tuple[str, ...]:
    """Return the Chronalyn-managed provider entries present on disk."""
    return tuple(
        provider_id
        for provider_id in identity.PROVIDER_IDS
        if (entry_dir(hermes_home, provider_id) / OWNERSHIP_MARKER).exists()
    )


def uninstall_plugin_entries(hermes_home: Path) -> tuple[str, ...]:
    """Remove only Chronalyn-managed provider entries.

    Never deletes router configuration, the state database, backups, Hindsight
    data or Mnemosyne data: package removal and data deletion stay separate.
    """
    removed: list[str] = []
    for provider_id in identity.PROVIDER_IDS:
        directory = entry_dir(hermes_home, provider_id)
        if not (directory / OWNERSHIP_MARKER).exists():
            continue
        shutil.rmtree(directory, ignore_errors=True)
        removed.append(provider_id)
    return tuple(removed)


__all__ = [
    "OWNERSHIP_MARKER",
    "entry_dir",
    "install_plugin_entries",
    "installed_entries",
    "uninstall_plugin_entries",
]
