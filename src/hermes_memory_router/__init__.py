"""Policy-based multi-backend memory routing for Hermes Agent."""

from .config import RouterConfig, load_config
from .router import MemoryRouter

__version__ = "0.2.0b1"
__all__ = ["MemoryRouter", "RouterConfig", "__version__", "load_config"]
