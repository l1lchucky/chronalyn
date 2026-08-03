from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .exceptions import ConfigurationError

_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")
_ALLOWED_CONTEXTS = {"primary", "subagent", "cron", "flush"}
_ALLOWED_BUDGETS = {"low", "mid", "high"}
_ALLOWED_REDACTION_MODES = {"redact", "reject", "off"}


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
    recall_policy: str = "primary_then_fallback"
    automatic_write_policy: str = "primary_only"
    checkpoint_write_policy: str = "primary_and_checkpoint"
    fallback_on_empty: bool = True
    fallback_on_error: bool = True
    fallback_max_chars: int = 4000
    automatic_write_contexts: list[str] = field(default_factory=lambda: ["primary"])
    include_tool_messages: bool = False
    start_worker: bool = True
    worker_poll_seconds: float = 1.0
    worker_batch_size: int = 20
    retry_base_seconds: float = 5.0
    retry_max_seconds: float = 3600.0
    max_attempts: int = 0  # 0 = unlimited

    def validate(self) -> None:
        if self.recall_policy != "primary_then_fallback":
            raise ConfigurationError("Only recall_policy=primary_then_fallback is supported")
        if self.automatic_write_policy != "primary_only":
            raise ConfigurationError("Only automatic_write_policy=primary_only is supported")
        if self.checkpoint_write_policy != "primary_and_checkpoint":
            raise ConfigurationError(
                "Only checkpoint_write_policy=primary_and_checkpoint is supported"
            )
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


@dataclass
class RouterConfig:
    namespace: str = "default-project"
    environment: str = "development"
    state_db: str = ""
    primary_backend: str = "hindsight"
    checkpoint_backend: str = "mnemosyne"
    hindsight: HindsightConfig = field(default_factory=HindsightConfig)
    mnemosyne: MnemosyneConfig = field(default_factory=MnemosyneConfig)
    redaction: RedactionConfig = field(default_factory=RedactionConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)

    def validate(self) -> None:
        if not _NAME_RE.fullmatch(self.namespace):
            raise ConfigurationError("namespace contains unsupported characters")
        if not _NAME_RE.fullmatch(self.environment):
            raise ConfigurationError("environment contains unsupported characters")
        if self.primary_backend != "hindsight":
            raise ConfigurationError("This release requires primary_backend=hindsight")
        if self.checkpoint_backend != "mnemosyne":
            raise ConfigurationError("This release requires checkpoint_backend=mnemosyne")
        if self.hindsight.bank_id == self.mnemosyne.bank:
            raise ConfigurationError(
                "Use visibly different Hindsight and Mnemosyne bank names"
            )
        self.hindsight.validate()
        self.mnemosyne.validate()
        self.redaction.validate()
        self.routing.validate()

    def resolved_state_db(self, hermes_home: Path) -> Path:
        if self.state_db:
            return Path(os.path.expandvars(self.state_db)).expanduser()
        return hermes_home / "memory-router" / "router.db"

    def to_safe_dict(self) -> dict[str, Any]:
        return asdict(self)


def _nested_dataclass(cls, payload: dict[str, Any] | None):
    return cls(**(payload or {}))


def load_config(path: Path) -> RouterConfig:
    if not path.exists():
        raise ConfigurationError(f"Router config does not exist: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Cannot read router config {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigurationError("Router config root must be a JSON object")

    known = {
        "namespace", "environment", "state_db", "primary_backend",
        "checkpoint_backend", "hindsight", "mnemosyne", "redaction", "routing",
    }
    unknown = set(raw) - known
    if unknown:
        raise ConfigurationError(f"Unknown top-level config keys: {sorted(unknown)}")

    config = RouterConfig(
        namespace=raw.get("namespace", "default-project"),
        environment=raw.get("environment", "development"),
        state_db=raw.get("state_db", ""),
        primary_backend=raw.get("primary_backend", "hindsight"),
        checkpoint_backend=raw.get("checkpoint_backend", "mnemosyne"),
        hindsight=_nested_dataclass(HindsightConfig, raw.get("hindsight")),
        mnemosyne=_nested_dataclass(MnemosyneConfig, raw.get("mnemosyne")),
        redaction=_nested_dataclass(RedactionConfig, raw.get("redaction")),
        routing=_nested_dataclass(RoutingConfig, raw.get("routing")),
    )
    config.validate()
    return config


def write_default_config(path: Path, *, namespace: str, environment: str) -> None:
    config = RouterConfig(namespace=namespace, environment=environment)
    config.hindsight.bank_id = f"{namespace}-{environment}"
    config.mnemosyne.bank = f"{namespace}-{environment}-checkpoints"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.to_safe_dict(), indent=2) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
