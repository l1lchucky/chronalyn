"""Provider identity, aliasing, and real execution of the installed entries.

The plugin-entry tests assert file *layout*. These tests execute the generated
entry modules through a stand-in for Hermes' PluginContext, so a syntactically
valid entry that cannot actually register is caught here.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

from chronalyn import identity
from chronalyn.exceptions import ConfigurationError
from chronalyn.plugin_entry import entry_dir, install_plugin_entries
from chronalyn.provider import ChronalynMemoryProvider


class RecordingContext:
    """Mirrors the surface plugins/memory/__init__.py::_ProviderCollector offers."""

    def __init__(self) -> None:
        self.provider: Any = None

    def register_memory_provider(self, provider: Any) -> None:
        self.provider = provider


def _load_entry(directory: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(
        module_name,
        directory / "__init__.py",
        submodule_search_locations=[str(directory)],
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
    return module


def test_canonical_provider_reports_the_new_provider_id() -> None:
    assert ChronalynMemoryProvider().name == identity.PROVIDER_ID


def test_provider_accepts_the_legacy_id_without_duplicating_implementation() -> None:
    provider = ChronalynMemoryProvider(name=identity.LEGACY_PROVIDER_ID)
    assert provider.name == identity.LEGACY_PROVIDER_ID
    assert isinstance(provider, ChronalynMemoryProvider)


def test_provider_rejects_an_unrelated_name() -> None:
    """Guards against a typo silently registering under a foreign provider id."""
    with pytest.raises(ConfigurationError, match="Unsupported provider id"):
        ChronalynMemoryProvider(name="honcho")


def test_legacy_class_name_remains_importable() -> None:
    """Source-level compatibility for anything importing the old class."""
    from chronalyn.provider import HermesMemoryRouterProvider

    assert HermesMemoryRouterProvider is ChronalynMemoryProvider


def test_legacy_module_path_still_imports() -> None:
    """`import hermes_memory_router` keeps working for existing integrations."""
    legacy = importlib.import_module(identity.LEGACY_PACKAGE)
    assert legacy.__version__ == identity.VERSION


def test_legacy_setup_tui_module_and_attribute_are_aliased() -> None:
    legacy = importlib.import_module(identity.LEGACY_PACKAGE)
    legacy_setup_tui = importlib.import_module(f"{identity.LEGACY_PACKAGE}.setup_tui")
    canonical_setup_tui = importlib.import_module("chronalyn.setup_tui")

    assert legacy.setup_tui is canonical_setup_tui
    assert legacy_setup_tui is canonical_setup_tui


@pytest.mark.parametrize(
    ("provider_id", "expected_name"),
    [
        (identity.PROVIDER_ID, identity.PROVIDER_ID),
        (identity.LEGACY_PROVIDER_ID, identity.LEGACY_PROVIDER_ID),
    ],
)
def test_installed_entry_actually_registers(
    tmp_path: Path, provider_id: str, expected_name: str
) -> None:
    """Execute the real generated entry file, as Hermes' loader would."""
    install_plugin_entries(tmp_path)
    module = _load_entry(entry_dir(tmp_path, provider_id), f"chronalyn_entry_probe_{provider_id}")

    context = RecordingContext()
    module.register(context)

    assert context.provider is not None
    assert context.provider.name == expected_name
    assert isinstance(context.provider, ChronalynMemoryProvider)


def test_is_provider_id_recognises_both_ids_and_rejects_others() -> None:
    assert identity.is_provider_id(identity.PROVIDER_ID)
    assert identity.is_provider_id(identity.LEGACY_PROVIDER_ID)
    assert not identity.is_provider_id("hindsight")
    assert not identity.is_provider_id("")
