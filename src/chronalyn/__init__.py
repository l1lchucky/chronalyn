"""Chronalyn — a persistent engineering-intelligence layer for AI agents.

The v1.0.0 release candidate implements reliable memory orchestration for
Hermes Agent: Hindsight is the automatic memory authority, Mnemosyne stores
verified checkpoints and acts only as a bounded fallback.

Console, change-intelligence, bug-discovery and deployment-analysis modules are
roadmap items and are not implemented in this release candidate.
"""

from .config import RouterConfig, load_config
from .identity import VERSION as __version__
from .router import MemoryRouter

__all__ = ["MemoryRouter", "RouterConfig", "__version__", "load_config"]
