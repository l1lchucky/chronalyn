"""Hermes plugin entry point for a source checkout.

Hermes may load a standalone plugin repository directly. Add the src directory
to sys.path so the same implementation also works when installed as a normal
Python package.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hermes_memory_router.provider import HermesMemoryRouterProvider, register

__all__ = ["HermesMemoryRouterProvider", "register"]
