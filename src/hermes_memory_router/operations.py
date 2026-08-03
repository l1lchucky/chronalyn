from __future__ import annotations

import copy
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from .compatibility import (
    HermesDiscovery,
    backup_configuration,
    discover,
    is_local_endpoint,
    latest_backup,
    restore_backup,
    set_active_provider_with_hermes,
)
from .config import RouterConfig, load_config, new_config, write_config
from .exceptions import ConfigurationError
from .policy import HINDSIGHT_MNEMOSYNE, HINDSIGHT_ONLY


@dataclass(frozen=True)
class ConfigurationPlan:
    current_provider: str
    current_hindsight_bank: str
    proposed_provider: str
    primary_backend: str
    checkpoint_backend: str
    automatic_retention: str
    verified_checkpoints: str
    fallback: str
    existing_hindsight_memories: str
    migration: str
    policy: str
    cloud_endpoint: str | None = None

    def render(self) -> str:
        lines = [
            "Current configuration",
            "---------------------",
            f"Active Hermes provider: {self.current_provider or '(none)'}",
            f"Hindsight bank: {self.current_hindsight_bank or '(not detected)'}",
            "",
            "Proposed configuration",
            "----------------------",
            f"Active Hermes provider: {self.proposed_provider}",
            f"Primary backend: {self.primary_backend}",
            f"Checkpoint backend: {self.checkpoint_backend or '(none)'}",
            "",
            "Automatic retention:",
            f"  {self.automatic_retention}",
            "",
            "Verified checkpoints:",
            f"  {self.verified_checkpoints}",
            "",
            "Fallback:",
            f"  {self.fallback}",
            "",
            "Existing Hindsight memories:",
            f"  {self.existing_hindsight_memories}",
            "",
            "Migration:",
            f"  {self.migration}",
        ]
        if self.cloud_endpoint:
            lines.extend(
                [
                    "",
                    "Off-device transmission:",
                    f"  Sanitized automatic memory will be sent to {self.cloud_endpoint}",
                    "  Raw tool messages remain disabled.",
                ]
            )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def recommended_policy(state: HermesDiscovery) -> str:
    return HINDSIGHT_MNEMOSYNE if state.mnemosyne_installed else HINDSIGHT_ONLY


def build_plan(
    state: HermesDiscovery,
    *,
    policy: str,
    existing_config: RouterConfig | None = None,
) -> ConfigurationPlan:
    bank = (
        existing_config.hindsight.bank_id
        if existing_config is not None
        else state.hindsight_bank_id or ""
    )
    api_url = (
        existing_config.hindsight.api_url
        if existing_config is not None
        else state.hindsight_api_url
    )
    dual = policy == HINDSIGHT_MNEMOSYNE
    return ConfigurationPlan(
        current_provider=(
            ", ".join(state.active_providers) if state.active_providers else ""
        ),
        current_hindsight_bank=bank,
        proposed_provider="hermes_memory_router",
        primary_backend="hindsight",
        checkpoint_backend="mnemosyne" if dual else "",
        automatic_retention="Hindsight only",
        verified_checkpoints=(
            "Hindsight + Mnemosyne" if dual else "Hindsight only"
        ),
        fallback=(
            "Mnemosyne checkpoints only when Hindsight is empty or unavailable"
            if dual
            else "Disabled"
        ),
        existing_hindsight_memories="Preserved",
        migration="None",
        policy=policy,
        cloud_endpoint=(api_url if api_url and not is_local_endpoint(api_url) else None),
    )


def config_for_adoption(
    hermes_home: Path,
    state: HermesDiscovery,
    *,
    namespace: str,
    environment: str,
    policy: str,
) -> RouterConfig:
    path = hermes_home / "memory-router" / "config.json"
    if path.exists():
        config = copy.deepcopy(load_config(path))
        config.namespace = namespace
        config.environment = environment
        config.policy = policy
    else:
        config = new_config(namespace=namespace, environment=environment, policy=policy)
    if state.hindsight_api_url:
        config.hindsight.api_url = state.hindsight_api_url
    if state.hindsight_bank_id:
        config.hindsight.bank_id = state.hindsight_bank_id
    config.mnemosyne.bank = f"{namespace}-{environment}-checkpoints"
    config.apply_policy_defaults()
    config.validate()
    return config


def confirm(
    question: str,
    *,
    assume_yes: bool,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> bool:
    if assume_yes:
        return True
    input_stream = input_stream or sys.stdin
    output_stream = output_stream or sys.stdout
    if not getattr(input_stream, "isatty", lambda: False)():
        raise ConfigurationError(
            "Interactive confirmation is unavailable; rerun with --yes after reviewing --dry-run"
        )
    output_stream.write(question)
    output_stream.flush()
    answer = input_stream.readline().strip().lower()
    return answer in {"y", "yes"}


def require_cloud_approval(
    plan: ConfigurationPlan,
    *,
    allow_cloud: bool,
    assume_yes: bool,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> None:
    if not plan.cloud_endpoint or allow_cloud:
        return
    if assume_yes:
        raise ConfigurationError(
            "Non-interactive cloud activation requires the explicit --allow-cloud flag"
        )
    approved = confirm(
        "This sends sanitized automatic memory off-device. Continue? [y/N] ",
        assume_yes=assume_yes,
        input_stream=input_stream,
        output_stream=output_stream,
    )
    if not approved:
        raise ConfigurationError("Cloud activation was not approved")


def apply_plan(
    hermes_home: Path,
    *,
    config: RouterConfig,
    reason: str,
    activate_provider: bool = True,
) -> Path:
    backup = backup_configuration(hermes_home, reason=reason)
    write_config(hermes_home / "memory-router" / "config.json", config)
    try:
        if activate_provider:
            set_active_provider_with_hermes("hermes_memory_router", hermes_home)
            state = discover(hermes_home)
            if state.active_providers != ("hermes_memory_router",):
                raise ConfigurationError(
                    "Hermes did not activate the router as the sole external provider"
                )
    except Exception:
        restore_backup(hermes_home, backup)
        raise
    return backup


def add_mnemosyne(
    hermes_home: Path,
    *,
    existing: RouterConfig,
) -> RouterConfig:
    state = discover(hermes_home)
    if not state.mnemosyne_installed:
        raise ConfigurationError(
            "Mnemosyne is not installed. Install mnemosyne-memory>=3.15,<4, then rerun."
        )
    config = copy.deepcopy(existing)
    config.policy = HINDSIGHT_MNEMOSYNE
    config.mnemosyne.bank = f"{config.namespace}-{config.environment}-checkpoints"
    config.apply_policy_defaults()
    config.validate()
    return config


def remove_mnemosyne(existing: RouterConfig) -> RouterConfig:
    config = copy.deepcopy(existing)
    config.policy = HINDSIGHT_ONLY
    config.apply_policy_defaults()
    config.validate()
    return config


def rollback_latest(hermes_home: Path) -> tuple[Path, list[str]]:
    backup = latest_backup(hermes_home)
    if backup is None:
        raise ConfigurationError("No router configuration backup exists")
    restored = restore_backup(hermes_home, backup)
    return backup, restored


def plan_json(plan: ConfigurationPlan) -> str:
    return json.dumps(plan.to_dict(), indent=2)
