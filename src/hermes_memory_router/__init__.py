"""Deprecated import alias for :mod:`chronalyn`.

Chronalyn was previously published as ``hermes-memory-router``. This shim keeps
``import hermes_memory_router`` working for existing integrations and scripts.

It deliberately does **not** re-implement anything: every attribute and
submodule resolves to the identical object in :mod:`chronalyn`, so
``isinstance`` checks and class identity hold across both import paths.

This alias is temporary and will be removed in a future major release. Import
``chronalyn`` directly instead.
"""

from __future__ import annotations

import importlib
import sys
import warnings
from typing import Any

import chronalyn as _chronalyn
from chronalyn import identity as _identity

__version__ = _identity.VERSION

# Submodules aliased eagerly so ``from hermes_memory_router.provider import X``
# resolves to the SAME module object as ``chronalyn.provider``. Setting
# ``__path__`` instead would let Python load a second, independent copy of each
# module, producing duplicate classes that fail isinstance checks.
_SUBMODULES = (
    "adapters",
    "bootstrap",
    "cli",
    "compatibility",
    "config",
    "exceptions",
    "factory",
    "health",
    "identity",
    "models",
    "operations",
    "plugin_entry",
    "policy",
    "provider",
    "redaction",
    "router",
    "setup_tui",
    "store",
    "tools",
    "ui",
)

_DEPRECATION = (
    "hermes_memory_router is deprecated; import chronalyn instead. "
    "This alias will be removed in a future major release."
)

warnings.warn(_DEPRECATION, DeprecationWarning, stacklevel=2)


def _alias_submodules() -> None:
    for name in _SUBMODULES:
        try:
            module = importlib.import_module(f"chronalyn.{name}")
        except ImportError:  # pragma: no cover - optional/absent submodule
            continue
        sys.modules[f"{__name__}.{name}"] = module
        globals().setdefault(name, module)


_alias_submodules()


def __getattr__(name: str) -> Any:
    """Resolve anything else from :mod:`chronalyn` on demand."""
    try:
        return getattr(_chronalyn, name)
    except AttributeError:
        pass
    try:
        module = importlib.import_module(f"chronalyn.{name}")
    except ModuleNotFoundError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    sys.modules[f"{__name__}.{name}"] = module
    return module


MemoryRouter = _chronalyn.MemoryRouter
RouterConfig = _chronalyn.RouterConfig
load_config = _chronalyn.load_config

__all__ = ["MemoryRouter", "RouterConfig", "__version__", "load_config"]
