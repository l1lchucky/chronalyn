from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .exceptions import ConfigurationError
from .policy import HINDSIGHT_MNEMOSYNE, HINDSIGHT_ONLY

ROUTER_PROVIDER = "hermes_memory_router"
CHILD_PROVIDERS = {"hindsight", "mnemosyne"}
_REQUIRED_MEMORY_METHODS = {
    "is_available",
    "initialize",
    "get_tool_schemas",
    "handle_tool_call",
    "get_config_schema",
    "save_config",
}


@dataclass(frozen=True)
class HermesDiscovery:
    hermes_home: str
    config_path: str
    config_exists: bool
    active_providers: tuple[str, ...]
    active_provider: str
    hermes_command: str | None
    hermes_version: str | None
    contract_available: bool
    contract_missing_methods: tuple[str, ...]
    hindsight_config_path: str
    hindsight_config_exists: bool
    hindsight_api_url: str | None
    hindsight_bank_id: str | None
    hindsight_mode: str | None
    hindsight_is_cloud: bool | None
    hindsight_is_remote: bool | None
    mnemosyne_installed: bool
    mnemosyne_version: str | None
    router_config_exists: bool
    conflicts: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def profile_fingerprint(hermes_home: Path) -> str:
    resolved = str(hermes_home.expanduser().resolve())
    return hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:20]


def is_local_endpoint(url: str) -> bool:
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return False
    return host in {"", "localhost", "127.0.0.1", "::1"}


def _package_version(*names: str) -> str | None:
    for name in names:
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return None


def _strip_scalar(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if value[0:1] in {"\"", "'"} and value[-1:] == value[0]:
        return value[1:-1]
    return value


def _inline_yaml_list(value: str) -> tuple[str, ...]:
    text = value.strip()
    if not (text.startswith("[") and text.endswith("]")):
        return ()
    inner = text[1:-1].strip()
    if not inner:
        return ()
    return tuple(
        item
        for item in (_strip_scalar(part) for part in inner.split(","))
        if item
    )


def active_memory_providers(hermes_home: Path) -> tuple[str, ...]:
    """Read only Hermes' small memory-provider YAML surface.

    The bootstrap intentionally avoids a general YAML dependency. It accepts the
    official singular form, an inline provider list, and an indented block list.
    Provider slugs are simple scalars; all unrelated Hermes configuration is
    ignored rather than interpreted.
    """

    path = hermes_home / "config.yaml"
    if not path.exists():
        return ()
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise ConfigurationError(f"Cannot read Hermes config {path}: {exc}") from exc

    memory_indent: int | None = None
    singular = ""
    plural: list[str] = []
    collecting_list = False

    for raw in lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()

        if memory_indent is None:
            if stripped == "memory:" or stripped.startswith("memory: #"):
                memory_indent = indent
            continue

        if indent <= memory_indent:
            break

        content = stripped.split(" #", 1)[0].rstrip()
        if collecting_list:
            if content.startswith("-"):
                item = _strip_scalar(content[1:])
                if item:
                    plural.append(item)
                continue
            collecting_list = False

        if content.startswith("providers:"):
            value = content.split(":", 1)[1].strip()
            if value:
                plural.extend(_inline_yaml_list(value))
            else:
                collecting_list = True
            continue
        if content.startswith("provider:"):
            singular = _strip_scalar(content.split(":", 1)[1])

    cleaned = tuple(item for item in plural if item)
    return cleaned or ((singular,) if singular else ())


def _numeric_version(value: str) -> tuple[int, int, int]:
    match = re.match(r"^\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?", value)
    if not match:
        raise ConfigurationError(f"Cannot interpret dependency version: {value}")
    return tuple(int(part or 0) for part in match.groups())  # type: ignore[return-value]

def _find_first(payload: Any, keys: set[str]) -> Any:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key).lower() in keys and value not in (None, ""):
                return value
        for value in payload.values():
            found = _find_first(value, keys)
            if found not in (None, ""):
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _find_first(value, keys)
            if found not in (None, ""):
                return found
    return None


def read_hindsight_config(hermes_home: Path) -> dict[str, Any]:
    path = hermes_home / "hindsight" / "config.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Cannot parse Hindsight config {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigurationError(f"Hindsight config root must be an object: {path}")
    # Keys are compared case-insensitively. Include camelCase aliases after
    # lowercasing because Hermes' official Hindsight schema accepts apiUrl and
    # bankId for backwards compatibility.
    api_url = _find_first(
        payload,
        {"api_url", "apiurl", "base_url", "baseurl", "url", "endpoint"},
    )
    bank_id = _find_first(
        payload,
        {"bank_id", "bankid", "bank", "memory_bank", "memorybank"},
    )
    mode = _find_first(payload, {"mode"})
    return {
        "path": str(path),
        "raw": payload,
        "api_url": str(api_url) if api_url else None,
        "bank_id": str(bank_id) if bank_id else None,
        "mode": str(mode) if mode else None,
    }


def inspect_memory_contract() -> tuple[bool, tuple[str, ...]]:
    try:
        from agent.memory_provider import MemoryProvider
    except Exception:
        return False, tuple(sorted(_REQUIRED_MEMORY_METHODS))
    missing = tuple(
        sorted(name for name in _REQUIRED_MEMORY_METHODS if not hasattr(MemoryProvider, name))
    )
    return not missing, missing


def discover(hermes_home: Path) -> HermesDiscovery:
    providers = active_memory_providers(hermes_home)
    contract_ok, missing = inspect_memory_contract()
    hindsight = read_hindsight_config(hermes_home)
    mnemosyne_version = _package_version("mnemosyne-memory", "mnemosyne")
    conflicts: list[str] = []
    if ROUTER_PROVIDER in providers and providers != (ROUTER_PROVIDER,):
        conflicts.append(
            "The router must be the sole active external memory provider; leave only "
            "hermes_memory_router in Hermes memory configuration."
        )
    if len(set(providers)) != len(providers):
        conflicts.append("Hermes memory provider list contains duplicate names.")
    api_url = hindsight.get("api_url")
    return HermesDiscovery(
        hermes_home=str(hermes_home),
        config_path=str(hermes_home / "config.yaml"),
        config_exists=(hermes_home / "config.yaml").exists(),
        active_providers=providers,
        active_provider=providers[0] if len(providers) == 1 else "",
        hermes_command=find_hermes_command(hermes_home),
        hermes_version=_package_version("hermes-agent", "hermes_agent"),
        contract_available=contract_ok,
        contract_missing_methods=missing,
        hindsight_config_path=str(hermes_home / "hindsight" / "config.json"),
        hindsight_config_exists=bool(hindsight),
        hindsight_api_url=api_url,
        hindsight_bank_id=hindsight.get("bank_id"),
        hindsight_mode=hindsight.get("mode"),
        hindsight_is_cloud=(
            hindsight.get("mode") == "cloud"
            if hindsight.get("mode")
            else (False if api_url and is_local_endpoint(api_url) else None)
        ),
        hindsight_is_remote=(not is_local_endpoint(api_url)) if api_url else None,
        mnemosyne_installed=importlib.util.find_spec("mnemosyne") is not None,
        mnemosyne_version=mnemosyne_version,
        router_config_exists=(hermes_home / "memory-router" / "config.json").exists(),
        conflicts=tuple(conflicts),
    )


def require_supported_dependencies(policy: str) -> None:
    if policy != HINDSIGHT_MNEMOSYNE:
        return
    raw = _package_version("mnemosyne-memory", "mnemosyne")
    if raw is None:
        raise ConfigurationError(
            "Mnemosyne policy requires mnemosyne-memory>=3.15,<4; package is not installed"
        )
    version = _numeric_version(raw)
    if not ((3, 15, 0) <= version < (4, 0, 0)):
        raise ConfigurationError(
            f"Unsupported Mnemosyne version {raw}; supported range is >=3.15,<4"
        )


def require_strict_hermes_compatibility(hermes_home: Path) -> HermesDiscovery:
    state = discover(hermes_home)
    if state.conflicts:
        raise ConfigurationError(" ".join(state.conflicts))
    if not state.contract_available:
        missing = ", ".join(state.contract_missing_methods)
        raise ConfigurationError(
            "Unsupported Hermes MemoryProvider contract; missing methods: " + missing
        )
    return state


def backup_configuration(hermes_home: Path, *, reason: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = hermes_home / "memory-router" / "backups" / stamp
    target.mkdir(parents=True, exist_ok=False)
    try:
        target.chmod(0o700)
    except OSError:
        pass
    copied: list[str] = []
    absent: list[str] = []
    managed = (
        hermes_home / "config.yaml",
        hermes_home / "memory-router" / "config.json",
        hermes_home / "hindsight" / "config.json",
        hermes_home / ".env",
        hermes_home / "plugins" / "memory" / "hermes_memory_router" / "__init__.py",
        hermes_home / "plugins" / "memory" / "hermes_memory_router" / "plugin.yaml",
    )
    for source in managed:
        relative = str(source.relative_to(hermes_home))
        if source.exists():
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied.append(relative)
        else:
            absent.append(relative)
    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "hermes_home": str(hermes_home),
        "copied": copied,
        "absent": absent,
        "active_providers": list(active_memory_providers(hermes_home)),
    }
    (target / "backup.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return target


def latest_backup(hermes_home: Path) -> Path | None:
    root = hermes_home / "memory-router" / "backups"
    if not root.exists():
        return None
    candidates = sorted(path for path in root.iterdir() if path.is_dir())
    return candidates[-1] if candidates else None


def restore_backup(hermes_home: Path, backup: Path) -> list[str]:
    metadata_path = backup / "backup.json"
    if not metadata_path.exists():
        raise ConfigurationError(f"Invalid router backup: {backup}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    restored: list[str] = []
    for relative in metadata.get("copied", []):
        source = backup / relative
        destination = hermes_home / relative
        if source.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            restored.append(relative)
    for relative in metadata.get("absent", []):
        destination = hermes_home / relative
        if destination.exists():
            destination.unlink()
            restored.append(f"removed:{relative}")
    return restored


def find_hermes_command(hermes_home: Path | None = None) -> str | None:
    candidates: list[Path] = []
    discovered = shutil.which("hermes")
    if discovered:
        candidates.append(Path(discovered))
    candidates.extend(
        [
            Path.home() / ".local" / "bin" / "hermes",
            Path("/usr/local/bin/hermes"),
        ]
    )
    if hermes_home is not None:
        candidates.extend(
            [
                hermes_home / "bin" / "hermes",
                hermes_home / "hermes-agent" / "hermes",
                hermes_home / "hermes-agent" / ".venv" / "bin" / "hermes",
                hermes_home / "hermes-agent" / "venv" / "bin" / "hermes",
            ]
        )
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def set_active_provider_with_hermes(
    provider: str,
    hermes_home: Path | None = None,
) -> None:
    hermes = find_hermes_command(hermes_home)
    if not hermes:
        raise ConfigurationError(
            "Hermes CLI is not available; configuration was not activated. "
            "Run `hermes config set memory.provider hermes_memory_router` manually."
        )
    environment = os.environ.copy()
    if hermes_home is not None:
        environment["HERMES_HOME"] = str(hermes_home.expanduser())
    result = subprocess.run(
        [hermes, "config", "set", "memory.provider", provider],
        capture_output=True,
        text=True,
        timeout=30,
        env=environment,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise ConfigurationError(f"Hermes provider activation failed: {details}")
