"""Chronalyn — long-term memory orchestration for Hermes Agent.

Hindsight provides deeper history and semantic recall; Mnemosyne keeps
verified checkpoints and acts only as a bounded fallback. Hermes' native
memory (MEMORY.md / USER.md) and Skills remain independent layers.

Console, change-intelligence, bug-discovery and deployment-analysis modules are
roadmap items and are not implemented.
"""

from .config import RouterConfig, load_config
from .identity import VERSION as __version__
from .router import MemoryRouter

__all__ = ["MemoryRouter", "RouterConfig", "__version__", "load_config"]
