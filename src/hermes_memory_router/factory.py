from __future__ import annotations

import os
from pathlib import Path

from .adapters.hindsight import HindsightBackend
from .adapters.mnemosyne import MnemosyneBackend
from .compatibility import profile_fingerprint, require_supported_dependencies
from .config import RouterConfig
from .policy import HINDSIGHT_MNEMOSYNE
from .router import MemoryRouter
from .store import RouterStore


def _read_profile_env_value(path: Path, key: str) -> str:
    """Read one exact key from Hermes' owner-managed .env file.

    This is deliberately a non-shell parser: no interpolation, command
    substitution, exports, or quoting rules are evaluated. Environment
    variables already present in the process always take precedence.
    """

    if not path.exists():
        return ""
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return ""
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        candidate, value = stripped.split("=", 1)
        if candidate.strip() == key:
            return value.strip()
    return ""


def build_router(
    *,
    config: RouterConfig,
    hermes_home: Path,
    session_id: str,
) -> MemoryRouter:
    require_supported_dependencies(config.policy)
    api_key = os.environ.get(config.hindsight.api_key_env, "")
    if not api_key:
        api_key = _read_profile_env_value(
            hermes_home / ".env",
            config.hindsight.api_key_env,
        )
    primary = HindsightBackend(config.hindsight, api_key=api_key)
    checkpoint = None
    if config.policy == HINDSIGHT_MNEMOSYNE:
        checkpoint = MnemosyneBackend(config.mnemosyne, session_id=session_id)
    store = RouterStore(
        config.resolved_state_db(hermes_home),
        namespace=config.namespace,
        environment=config.environment,
        profile_fingerprint=profile_fingerprint(hermes_home),
        strict_binding=True,
    )
    return MemoryRouter(
        config=config,
        store=store,
        primary=primary,
        checkpoint=checkpoint,
    )
