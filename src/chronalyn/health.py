from __future__ import annotations

import platform
import sqlite3
from typing import Any

from . import identity
from .config import CONFIG_SCHEMA_VERSION, RouterConfig
from .store import RouterStore

HEALTH_EXIT_CODES = {"healthy": 0, "warning": 0, "degraded": 1, "unsafe": 3}
ROUTER_VERSION = identity.VERSION


def collect_health(
    *,
    config: RouterConfig,
    store: RouterStore,
    expected_profile: str,
    backends: dict[str, dict[str, Any]],
    worker_alive: bool,
    optional_mnemosyne: dict[str, Any] | None = None,
    integrity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    database = store.database_info()
    binding = database["binding"]
    mismatches: list[str] = []
    expected = {
        "namespace": config.namespace,
        "environment": config.environment,
        "profile": expected_profile,
    }
    for key, value in expected.items():
        if binding.get(key) != value:
            mismatches.append(key)

    warnings: list[str] = []
    degraded: list[str] = []
    unsafe: list[str] = []
    deliveries = database["deliveries"]
    if int(deliveries.get("pending", 0)):
        warnings.append("pending deliveries require monitoring")
    if int(deliveries.get("failed", 0)):
        degraded.append("failed deliveries require retry")
    if int(deliveries.get("dead", 0)):
        degraded.append("dead deliveries require manual recovery")
    if config.routing.start_worker and not worker_alive:
        degraded.append("delivery worker is not running")
    for name, health in backends.items():
        if not bool(health.get("ok")):
            degraded.append(f"{name} backend is unhealthy")
    if (
        optional_mnemosyne
        and not optional_mnemosyne.get("enabled")
        and not optional_mnemosyne.get("installed")
    ):
        warnings.append("mnemosyne is not installed (optional and disabled)")
    if mismatches:
        unsafe.append("database identity does not match configuration")
    if integrity is not None and not integrity.get("ok"):
        unsafe.append("database integrity check failed")

    if unsafe:
        state = "unsafe"
    elif degraded:
        state = "degraded"
    elif warnings:
        state = "warning"
    else:
        state = "healthy"

    return {
        "state": state,
        "exit_code": HEALTH_EXIT_CODES[state],
        "versions": {
            "router": ROUTER_VERSION,
            "configuration_schema": CONFIG_SCHEMA_VERSION,
            "database_schema": database["schema_version"],
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
        },
        "policy": config.policy,
        "namespace": config.namespace,
        "environment": config.environment,
        "binding": {"database": binding, "expected": expected, "mismatches": mismatches},
        "backends": backends,
        "mnemosyne": optional_mnemosyne,
        "deliveries": deliveries,
        "oldest_incomplete_delivery": database["oldest_incomplete_delivery"],
        "database": {
            "path": database["path"],
            "size_bytes": database["size_bytes"],
            "wal_size_bytes": database["wal_size_bytes"],
            "shm_size_bytes": database["shm_size_bytes"],
        },
        "worker_alive": worker_alive,
        "warnings": warnings,
        "degraded": degraded,
        "unsafe": unsafe,
        "integrity": integrity,
    }
