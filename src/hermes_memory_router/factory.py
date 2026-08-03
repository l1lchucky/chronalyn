from __future__ import annotations

import os
from pathlib import Path

from .adapters.hindsight import HindsightBackend
from .adapters.mnemosyne import MnemosyneBackend
from .config import RouterConfig
from .router import MemoryRouter
from .store import RouterStore


def build_router(
    *,
    config: RouterConfig,
    hermes_home: Path,
    session_id: str,
) -> MemoryRouter:
    api_key = os.environ.get(config.hindsight.api_key_env, "")
    primary = HindsightBackend(config.hindsight, api_key=api_key)
    checkpoint = MnemosyneBackend(config.mnemosyne, session_id=session_id)
    store = RouterStore(config.resolved_state_db(hermes_home))
    return MemoryRouter(
        config=config,
        store=store,
        primary=primary,
        checkpoint=checkpoint,
    )
