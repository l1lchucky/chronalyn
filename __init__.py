"""Chronalyn provider entry for a source checkout.

Hermes can load a standalone plugin repository directly. This module adds the
``src`` directory to ``sys.path`` so the same implementation works from a git
checkout and from an installed wheel.

The literal ``register_memory_provider`` call below is load-bearing: Hermes'
user-plugin discovery (``plugins/memory/__init__.py::_is_memory_provider_dir``)
only treats a directory as a memory provider when its ``__init__.py`` mentions
``register_memory_provider`` or ``MemoryProvider``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from chronalyn.provider import ChronalynMemoryProvider  # noqa: E402


def register(ctx) -> None:
    """Register Chronalyn as Hermes' single external memory provider."""
    ctx.register_memory_provider(ChronalynMemoryProvider())


__all__ = ["ChronalynMemoryProvider", "register"]
