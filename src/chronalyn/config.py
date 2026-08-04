from __future__ import annotations

import json
import os
import re
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from .exceptions import ConfigurationError
from .policy import HINDSIGHT_MNEMOSYNE, HINDSIGHT_ONLY, POLICIES

CONFIG_SCHEMA_VERSION = 2
T = TypeVar("T")
_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")
_ALLOWED_CONTEXTS = {"primary", "subagent", "cron", "flush"}
_ALLOWED_BUDGETS = {"low", "mid", "high"}
_ALLOWED_REDACTION_MODES = {"redact", "reject", "off"}
_ALLOWED_TOOL_PROFILES = {"minimal", "standard"}


@dataclass
class HindsightConfig:
    api_url: str = "http://127.0.0.1:8888"
    api_key_env: str = "HINDSIGHT_API_KEY"
    bank_id: str = "hermes"
    timeout_seconds: float = 15.0
    recall_budget: str = "mid"
    recall_max_tokens: int = 1600
    recall_types: list[str] = field(default_factory=lambda: ["observation"])
    tags: list[str] = field(default_factory=list)
    verify_tls: bool = True

    def validate(self) -> None:
        if not self.api_url.startswith(("http://", "https://")):
            raise ConfigurationError("hindsight.api_url must use http:// or https://")
        if not _NAME_RE.fullmatch(self.bank_id):
            raise ConfigurationError("hindsight.bank_id contains unsupported characters")
        if self.recall_budget not in _ALLOWED_BUDGETS:
            raise ConfigurationError("hindsight.recall_budget must be low, mid, or high")
        if not 1 <= self.recall_max_tokens <= 65536:
            raise ConfigurationError("hindsight.recall_max_tokens is out of range")
        if not 0.2 <= self.timeout_seconds <= 300:
            raise ConfigurationError("hindsight.timeout_seconds is out of range")


@dataclass
class MnemosyneConfig:
    bank: str = "hermes-checkpoints"
    data_dir: str = ""
    top_k: int = 5

    def validate(self) -> None:
        if not _NAME_RE.fullmatch(self.bank):
            raise ConfigurationError("mnemosyne.bank contains unsupported characters")
        if not 1 <= self.top_k <= 100:
            raise ConfigurationError("mnemosyne.top_k is out of range")


@dataclass
class RedactionConfig:
    mode: str = "redact"
    replacement: str = "[REDACTED]"
    max_record_chars: int = 24000
    custom_patterns: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if self.mode not in _ALLOWED_REDACTION_MODES:
            raise ConfigurationError("redaction.mode must be redact, reject, or off")
        if not 256 <= self.max_record_chars <= 1_000_000:
            raise ConfigurationError("redaction.max_record_chars is out of range")
        for pattern in self.custom_patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ConfigurationError(f"Invalid custom redaction regex: {exc}") from exc


@dataclass
class RoutingConfig:
    recall_policy: str = "primary_only"
    automatic_write_policy: str = "primary_only"
    checkpoint_write_policy: str = "primary_only"
    fallback_on_empty: bool = False
    fallback_on_error: bool = False
    fallback_max_chars: int = 4000
    automatic_write_contexts: list[str] = field(default_factory=lambda: ["primary"])
    include_tool_messages: bool = False
    start_worker: bool = True
    worker_poll_seconds: float = 1.0
    worker_batch_size: int = 20
    retry_base_seconds: float = 5.0
    retry_max_seconds: float = 3600.0
    max_attempts: int = 0

    def validate(self, *, policy: str) -> None:
        if self.automatic_write_policy != "primary_only":
            raise ConfigurationError("Only automatic_write_policy=primary_only is supported")
        expected_recall = (
            "primary_then_fallback" if policy == HINDSIGHT_MNEMOSYNE else "primary_only"
        )
        expected_checkpoint = (
            "primary_and_checkpoint" if policy == HINDSIGHT_MNEMOSYNE else "primary_only"
        )
        if self.recall_policy != expected_recall:
            raise ConfigurationError(f"Policy {policy} requires recall_policy={expected_recall}")
        if self.checkpoint_write_policy != expected_checkpoint:
            raise ConfigurationError(
                f"Policy {policy} requires checkpoint_write_policy={expected_checkpoint}"
            )
        if policy == HINDSIGHT_ONLY and (self.fallback_on_empty or self.fallback_on_error):
            raise ConfigurationError("Hindsight-only policy cannot enable a fallback backend")
        unknown = set(self.automatic_write_contexts) - _ALLOWED_CONTEXTS
        if unknown:
            raise ConfigurationError(f"Unknown automatic_write_contexts: {sorted(unknown)}")
        if not 256 <= self.fallback_max_chars <= 100_000:
            raise ConfigurationError("routing.fallback_max_chars is out of range")
        if not 0.1 <= self.worker_poll_seconds <= 60:
            raise ConfigurationError("routing.worker_poll_seconds is out of range")
        if not 1 <= self.worker_batch_size <= 1000:
            raise ConfigurationError("routing.worker_batch_size is out of range")
        if not 0.1 <= self.retry_base_seconds <= self.retry_max_seconds:
            raise ConfigurationError("Invalid retry timing")
        if self.include_tool_messages:
            raise ConfigurationError(
                "include_tool_messages=true is not supported in strict compatibility mode"
            )


@dataclass
class CompatibilityConfig:
    mode: str = "strict"
    refuse_child_provider_conflict: bool = True
    require_supported_contract: bool = True
    private_hermes_imports: bool = False
    core_monkeypatching: bool = False

    def validate(self) -> None:
        if self.mode != "strict":
            raise ConfigurationError("Only compatibility.mode=strict is supported")
        if self.private_hermes_imports or self.core_monkeypatching:
            raise ConfigurationError(
                "Strict compatibility forbids private Hermes imports and core monkeypatching"
            )


@dataclass
class PrivacyConfig:
    include_tool_messages: bool = False
    telemetry: bool = False
    require_cloud_confirmation: bool = True

    def validate(self) -> None:
        if self.include_tool_messages:
            raise ConfigurationError("Raw tool-message retention is forbidden")
        if self.telemetry:
            raise ConfigurationError("Telemetry is not implemented or permitted")


@dataclass
class ToolsConfig:
    profile: str = "standard"
    destructive_model_tools: bool = False
    native_provider_passthrough: bool = False

    def validate(self) -> None:
        if self.profile not in _ALLOWED_TOOL_PROFILES:
            raise ConfigurationError(
                f"tools.profile must be one of {sorted(_ALLOWED_TOOL_PROFILES)}"
            )
        if self.native_provider_passthrough:
            raise ConfigurationError(
                "Native provider passthrough is forbidden; use the compact router tool surface"
            )


@dataclass
class IsolationConfig:
    bind_database_to_profile: bool = True
    bind_database_to_environment: bool = True
    refuse_cross_environment_open: bool = True
    require_distinct_bank_names: bool = True

    def validate(self) -> None:
        if not (
            self.bind_database_to_profile
            and self.bind_database_to_environment
            and self.refuse_cross_environment_open
        ):
            raise ConfigurationError("Strict mode requires profile and environment DB binding")


@dataclass
class RouterConfig:
    schema_version: int = CONFIG_SCHEMA_VERSION
    namespace: str = "default-project"
    environment: str = "development"
    policy: str = HINDSIGHT_ONLY
    state_db: str = ""
    primary_backend: str = "hindsight"
    checkpoint_backend: str = ""
    hindsight: HindsightConfig = field(default_factory=HindsightConfig)
    mnemosyne: MnemosyneConfig = field(default_factory=MnemosyneConfig)
    redaction: RedactionConfig = field(default_factory=RedactionConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    compatibility: CompatibilityConfig = field(default_factory=CompatibilityConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    tools: ToolsConfig = field(default_factory=ToolsConfig)
    isolation: IsolationConfig = field(default_factory=IsolationConfig)

    def apply_policy_defaults(self) -> None:
        self.primary_backend = "hindsight"
        if self.policy == HINDSIGHT_MNEMOSYNE:
            self.checkpoint_backend = "mnemosyne"
            self.routing.recall_policy = "primary_then_fallback"
            self.routing.checkpoint_write_policy = "primary_and_checkpoint"
            self.routing.fallback_on_empty = True
            self.routing.fallback_on_error = True
        elif self.policy == HINDSIGHT_ONLY:
            self.checkpoint_backend = ""
            self.routing.recall_policy = "primary_only"
            self.routing.checkpoint_write_policy = "primary_only"
            self.routing.fallback_on_empty = False
            self.routing.fallback_on_error = False

    def validate(self) -> None:
        if self.schema_version != CONFIG_SCHEMA_VERSION:
            raise ConfigurationError(
                f"Unsupported config schema {self.schema_version}; expected {CONFIG_SCHEMA_VERSION}"
            )
        if not _NAME_RE.fullmatch(self.namespace):
            raise ConfigurationError("namespace contains unsupported characters")
        if not _NAME_RE.fullmatch(self.environment):
            raise ConfigurationError("environment contains unsupported characters")
        if self.policy not in POLICIES:
            raise ConfigurationError(f"Unsupported routing policy: {self.policy}")
        if self.primary_backend != "hindsight":
            raise ConfigurationError("primary_backend must remain hindsight")
        expected_checkpoint = "mnemosyne" if self.policy == HINDSIGHT_MNEMOSYNE else ""
        if self.checkpoint_backend != expected_checkpoint:
            raise ConfigurationError(
                f"Policy {self.policy} requires checkpoint_backend={expected_checkpoint!r}"
            )
        if (
            self.policy == HINDSIGHT_MNEMOSYNE
            and self.isolation.require_distinct_bank_names
            and self.hindsight.bank_id == self.mnemosyne.bank
        ):
            raise ConfigurationError("Use visibly different Hindsight and Mnemosyne bank names")
        self.hindsight.validate()
        self.mnemosyne.validate()
        self.redaction.validate()
        self.routing.validate(policy=self.policy)
        self.compatibility.validate()
        self.privacy.validate()
        self.tools.validate()
        self.isolation.validate()

    def resolved_state_db(self, hermes_home: Path) -> Path:
        if self.state_db:
            return Path(os.path.expandvars(self.state_db)).expanduser()
        return hermes_home / "memory-router" / "router.db"

    def to_safe_dict(self) -> dict[str, Any]:
        return asdict(self)


def _nested_dataclass(cls: type[T], payload: dict[str, Any] | None) -> T:
    try:
        return cls(**(payload or {}))
    except TypeError as exc:
        raise ConfigurationError(f"Invalid {cls.__name__} configuration: {exc}") from exc


def _upgrade_v1(raw: dict[str, Any]) -> dict[str, Any]:
    upgraded = dict(raw)
    upgraded["schema_version"] = CONFIG_SCHEMA_VERSION
    upgraded["policy"] = HINDSIGHT_MNEMOSYNE
    upgraded.setdefault("compatibility", {})
    upgraded.setdefault("privacy", {})
    upgraded.setdefault("tools", {})
    upgraded.setdefault("isolation", {})
    upgraded["primary_backend"] = "hindsight"
    upgraded["checkpoint_backend"] = "mnemosyne"
    return upgraded


def load_config(path: Path) -> RouterConfig:
    if not path.exists():
        raise ConfigurationError(f"Router config does not exist: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Cannot read router config {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigurationError("Router config root must be a JSON object")
    if "schema_version" not in raw:
        raw = _upgrade_v1(raw)

    known = {
        "schema_version",
        "namespace",
        "environment",
        "policy",
        "state_db",
        "primary_backend",
        "checkpoint_backend",
        "hindsight",
        "mnemosyne",
        "redaction",
        "routing",
        "compatibility",
        "privacy",
        "tools",
        "isolation",
    }
    unknown = set(raw) - known
    if unknown:
        raise ConfigurationError(f"Unknown top-level config keys: {sorted(unknown)}")

    config = RouterConfig(
        schema_version=int(raw.get("schema_version", CONFIG_SCHEMA_VERSION)),
        namespace=raw.get("namespace", "default-project"),
        environment=raw.get("environment", "development"),
        policy=raw.get("policy", HINDSIGHT_ONLY),
        state_db=raw.get("state_db", ""),
        primary_backend=raw.get("primary_backend", "hindsight"),
        checkpoint_backend=raw.get("checkpoint_backend", ""),
        hindsight=_nested_dataclass(HindsightConfig, raw.get("hindsight")),
        mnemosyne=_nested_dataclass(MnemosyneConfig, raw.get("mnemosyne")),
        redaction=_nested_dataclass(RedactionConfig, raw.get("redaction")),
        routing=_nested_dataclass(RoutingConfig, raw.get("routing")),
        compatibility=_nested_dataclass(CompatibilityConfig, raw.get("compatibility")),
        privacy=_nested_dataclass(PrivacyConfig, raw.get("privacy")),
        tools=_nested_dataclass(ToolsConfig, raw.get("tools")),
        isolation=_nested_dataclass(IsolationConfig, raw.get("isolation")),
    )
    config.validate()
    return config


def write_config(path: Path, config: RouterConfig) -> None:
    config.validate()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(config.to_safe_dict(), indent=2) + "\n", encoding="utf-8")
    with suppress(OSError):
        temporary.chmod(0o600)
    temporary.replace(path)


def new_config(*, namespace: str, environment: str, policy: str) -> RouterConfig:
    config = RouterConfig(namespace=namespace, environment=environment, policy=policy)
    config.hindsight.bank_id = f"{namespace}-{environment}"
    config.mnemosyne.bank = f"{namespace}-{environment}-checkpoints"
    config.redaction.mode = "reject" if environment.lower() == "production" else "redact"
    config.apply_policy_defaults()
    config.validate()
    return config


def write_default_config(
    path: Path,
    *,
    namespace: str,
    environment: str,
    policy: str = HINDSIGHT_ONLY,
) -> None:
    write_config(path, new_config(namespace=namespace, environment=environment, policy=policy))
