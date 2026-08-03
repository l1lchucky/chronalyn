from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from .exceptions import ConfigurationError

OFFICIAL_HERMES_INSTALLER = "https://hermes-agent.nousresearch.com/install.sh"
ROUTER_VERSION = "0.2.0b1"
ROUTER_TAG = "v0.2.0-beta.1"
ROUTER_WHEEL = "hermes_memory_router-0.2.0b1-py3-none-any.whl"
ROUTER_RELEASE_BASE = (
    "https://github.com/l1lchucky/hermes-memory-router/releases/download/"
    f"{ROUTER_TAG}"
)
MNEMOSYNE_SPEC = "mnemosyne-memory>=3.15,<4"

LogCallback = Callable[[str], None]


@dataclass(frozen=True)
class DownloadReceipt:
    url: str
    path: str
    sha256: str
    bytes: int

    def to_dict(self) -> dict[str, object]:
        return {
            "url": self.url,
            "path": self.path,
            "sha256": self.sha256,
            "bytes": self.bytes,
        }


@dataclass(frozen=True)
class HermesRuntime:
    command: str
    python: str
    install_dir: str

    def to_dict(self) -> dict[str, str]:
        return {
            "command": self.command,
            "python": self.python,
            "install_dir": self.install_dir,
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_https(
    url: str,
    destination: Path,
    *,
    timeout: float = 60,
    max_bytes: int = 50 * 1024 * 1024,
) -> DownloadReceipt:
    if not url.startswith("https://"):
        raise ConfigurationError(f"Refusing non-HTTPS download: {url}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": f"hermes-memory-router/{ROUTER_VERSION}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            total = 0
            fd = os.open(
                str(destination),
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                0o600,
            )
            try:
                with os.fdopen(fd, "wb") as handle:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > max_bytes:
                            raise ConfigurationError(
                                f"Download exceeds safety limit ({max_bytes} bytes): {url}"
                            )
                        handle.write(chunk)
            except BaseException:
                destination.unlink(missing_ok=True)
                raise
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        destination.unlink(missing_ok=True)
        raise ConfigurationError(f"Download failed from {url}: {exc}") from exc
    return DownloadReceipt(
        url=url,
        path=str(destination),
        sha256=sha256_file(destination),
        bytes=destination.stat().st_size,
    )


def validate_hermes_installer(path: Path) -> None:
    """Perform conservative static checks before executing the upstream script.

    These checks do not prove that a remote installer is harmless. They catch
    accidental HTML/error pages, binary payloads, unexpected origin changes,
    and grossly malformed downloads. The setup UI still shows the SHA-256 and
    requires explicit approval.
    """

    data = path.read_bytes()
    if not 10_000 <= len(data) <= 2_000_000:
        raise ConfigurationError(
            f"Official Hermes installer has unexpected size: {len(data)} bytes"
        )
    if b"\x00" in data:
        raise ConfigurationError("Official Hermes installer contains binary NUL bytes")
    text = data.decode("utf-8", errors="strict")
    required = (
        "#!/bin/bash",
        "Hermes Agent Installer",
        "https://github.com/NousResearch/hermes-agent.git",
        "HERMES_HOME",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise ConfigurationError(
            "Official Hermes installer failed identity checks; missing: "
            + ", ".join(missing)
        )


def _candidate_hermes_commands(hermes_home: Path) -> Iterable[Path]:
    command = shutil.which("hermes")
    if command:
        yield Path(command)
    for candidate in (
        Path.home() / ".local" / "bin" / "hermes",
        Path("/usr/local/bin/hermes"),
        hermes_home / "bin" / "hermes",
        hermes_home / "hermes-agent" / "hermes",
        hermes_home / "hermes-agent" / ".venv" / "bin" / "hermes",
        hermes_home / "hermes-agent" / "venv" / "bin" / "hermes",
    ):
        yield candidate


def _python_from_shebang(command: Path) -> Path | None:
    try:
        first = command.read_text(encoding="utf-8", errors="replace").splitlines()[0]
    except (OSError, IndexError):
        return None
    if not first.startswith("#!"):
        return None
    raw = first[2:].strip().split()[0]
    candidate = Path(raw)
    return candidate if candidate.is_file() and os.access(candidate, os.X_OK) else None


def find_hermes_runtime(hermes_home: Path) -> HermesRuntime | None:
    explicit = os.environ.get("HERMES_PYTHON")
    explicit_python = Path(explicit).expanduser() if explicit else None

    command_path: Path | None = None
    for candidate in _candidate_hermes_commands(hermes_home):
        if candidate.exists():
            command_path = candidate.resolve()
            break

    candidates: list[Path] = []
    if explicit_python:
        candidates.append(explicit_python)
    if command_path:
        shebang = _python_from_shebang(command_path)
        if shebang:
            candidates.append(shebang)
        candidates.append(command_path.parent / "python")
    candidates.extend(
        [
            hermes_home / "hermes-agent" / ".venv" / "bin" / "python",
            hermes_home / "hermes-agent" / "venv" / "bin" / "python",
            Path("/usr/local/lib/hermes-agent/.venv/bin/python"),
            Path("/usr/local/lib/hermes-agent/venv/bin/python"),
        ]
    )

    python_path = next(
        (
            path.expanduser().resolve()
            for path in candidates
            if path.expanduser().is_file() and os.access(path.expanduser(), os.X_OK)
        ),
        None,
    )
    if command_path is None or python_path is None:
        return None

    install_dir = python_path.parent.parent
    return HermesRuntime(
        command=str(command_path),
        python=str(python_path),
        install_dir=str(install_dir),
    )


def run_command(
    command: list[str],
    *,
    log: LogCallback | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    cwd: Path | None = None,
) -> None:
    safe_display = " ".join(command)
    if log:
        log(f"$ {safe_display}")
    try:
        process = subprocess.Popen(
            command,
            cwd=str(cwd) if cwd else None,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        try:
            assert process.stdout is not None
            for line in process.stdout:
                if log:
                    log(line.rstrip())
            returncode = process.wait(timeout=timeout)
        except BaseException:
            process.kill()
            process.wait(timeout=5)
            raise
    except (OSError, subprocess.SubprocessError) as exc:
        raise ConfigurationError(f"Command failed to start: {safe_display}: {exc}") from exc
    if returncode != 0:
        raise ConfigurationError(f"Command exited with status {returncode}: {safe_display}")


def install_official_hermes(
    hermes_home: Path,
    *,
    installer: Path,
    with_browser: bool = False,
    log: LogCallback | None = None,
) -> HermesRuntime:
    validate_hermes_installer(installer)
    command = [
        "bash",
        str(installer),
        "--skip-setup",
        "--non-interactive",
        "--hermes-home",
        str(hermes_home),
    ]
    if not with_browser:
        command.append("--skip-browser")
    # This wrapper never invokes sudo. The official installer remains visible in
    # the log and may itself request OS-package privileges on some platforms.
    run_command(command, log=log, timeout=1800)
    runtime = find_hermes_runtime(hermes_home)
    if runtime is None:
        raise ConfigurationError(
            "Hermes installer completed but its runtime could not be located"
        )
    return runtime


def _pip_install_command(
    runtime: HermesRuntime,
    specs: list[str],
    *,
    hermes_home: Path | None = None,
) -> list[str]:
    """Return an install command for Hermes' isolated Python runtime.

    uv-created virtual environments may intentionally omit pip. Prefer pip when
    it is available inside the target interpreter, otherwise use a trusted uv
    executable already installed with Hermes or present on PATH.
    """

    probe = subprocess.run(
        [runtime.python, "-m", "pip", "--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
        check=False,
    )
    if probe.returncode == 0:
        return [runtime.python, "-m", "pip", "install", "--upgrade", *specs]

    candidates: list[Path] = []
    discovered = shutil.which("uv")
    if discovered:
        candidates.append(Path(discovered))
    candidates.append(Path(runtime.command).parent / "uv")
    if hermes_home is not None:
        candidates.extend(
            [
                hermes_home / "bin" / "uv",
                hermes_home / "hermes-agent" / "bin" / "uv",
            ]
        )
    uv = next(
        (candidate for candidate in candidates if candidate.is_file() and os.access(candidate, os.X_OK)),
        None,
    )
    if uv is None:
        raise ConfigurationError(
            "Hermes' Python does not provide pip and no trusted uv executable "
            "was found. Install through the official Hermes installer and retry."
        )
    return [str(uv), "pip", "install", "--python", runtime.python, "--upgrade", *specs]


def install_router_into_runtime(
    runtime: HermesRuntime,
    *,
    package_source: str,
    dual: bool,
    hermes_home: Path | None = None,
    log: LogCallback | None = None,
) -> None:
    if not package_source:
        package_source = f"{ROUTER_RELEASE_BASE}/{ROUTER_WHEEL}"
    specs = [package_source]
    if dual:
        specs.append(MNEMOSYNE_SPEC)
    command = _pip_install_command(runtime, specs, hermes_home=hermes_home)
    run_command(command, log=log, timeout=1200)



def link_router_command(runtime: HermesRuntime) -> Path:
    source = Path(runtime.python).parent / "hermes-memory-router"
    if not source.is_file():
        raise ConfigurationError(
            f"Router console entry was not installed in Hermes runtime: {source}"
        )
    destination = Path(runtime.command).parent / "hermes-memory-router"
    if destination.exists() or destination.is_symlink():
        try:
            if destination.resolve() == source.resolve():
                return destination
        except OSError:
            pass
        if destination.is_symlink():
            destination.unlink()
        else:
            raise ConfigurationError(
                f"Refusing to replace existing non-symlink command: {destination}"
            )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(source)
    return destination

def install_plugin_entry(
    runtime: HermesRuntime,
    *,
    hermes_home: Path,
    log: LogCallback | None = None,
) -> None:
    run_command(
        [
            runtime.python,
            "-m",
            "hermes_memory_router.cli",
            "--hermes-home",
            str(hermes_home),
            "--no-animation",
            "install-plugin",
        ],
        log=log,
        timeout=60,
    )




def verify_router_in_runtime(
    runtime: HermesRuntime,
    *,
    hermes_home: Path,
    timeout: float = 120,
) -> dict[str, object]:
    """Run router health verification inside Hermes' actual Python runtime."""

    environment = os.environ.copy()
    environment["HERMES_HOME"] = str(hermes_home.expanduser())
    command = [
        runtime.python,
        "-m",
        "hermes_memory_router.cli",
        "--hermes-home",
        str(hermes_home),
        "--json",
        "--no-animation",
        "status",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=environment,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ConfigurationError(f"Router runtime verification could not start: {exc}") from exc
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise ConfigurationError(
            "Router runtime verification failed: " + details[:2000]
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(
            "Router runtime verification returned invalid JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise ConfigurationError("Router runtime verification returned an invalid payload")
    return payload


def write_secret_env(hermes_home: Path, updates: dict[str, str]) -> Path:
    path = hermes_home / ".env"
    path.parent.mkdir(parents=True, exist_ok=True)
    for key, value in updates.items():
        if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", key):
            raise ConfigurationError(f"Invalid environment variable name: {key!r}")
        if any(character in value for character in ("\r", "\n", "\x00")):
            raise ConfigurationError(f"Secret value for {key} contains a forbidden control character")
    existing: list[str] = []
    if path.exists():
        try:
            path.chmod(0o600)
        except OSError:
            pass
        existing = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    remaining = dict(updates)
    output: list[str] = []
    for line in existing:
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in remaining:
                output.append(f"{key}={remaining.pop(key)}")
                continue
        output.append(line)
    for key, value in remaining.items():
        output.append(f"{key}={value}")
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("\n".join(output).rstrip() + "\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def write_hindsight_profile_config(
    hermes_home: Path,
    *,
    mode: str,
    api_url: str,
    bank_id: str,
) -> Path:
    if mode not in {"cloud", "local_external"}:
        raise ConfigurationError(
            "The strict dual router supports Hindsight Cloud or an external "
            "self-hosted Hindsight API; embedded lifecycle mode is not managed."
        )
    path = hermes_home / "hindsight" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(
                f"Cannot safely update existing Hindsight config {path}: {exc}"
            ) from exc
        if not isinstance(existing, dict):
            raise ConfigurationError(
                f"Existing Hindsight config must be a JSON object: {path}"
            )
        payload.update(existing)
    # Preserve every unknown/advanced Hindsight setting. The router owns only
    # the connection, bank, and safe automatic-memory defaults below.
    payload.update(
        {
            "mode": mode,
            "api_url": api_url,
            "bank_id": bank_id,
            "recall_budget": payload.get("recall_budget", payload.get("budget", "mid")),
            "memory_mode": payload.get("memory_mode", "hybrid"),
            "recall_prefetch_method": payload.get(
                "recall_prefetch_method",
                payload.get("prefetch_method", "recall"),
            ),
            "auto_recall": payload.get("auto_recall", True),
            "auto_retain": payload.get("auto_retain", True),
            "retain_async": payload.get("retain_async", True),
        }
    )
    if path.exists():
        try:
            path.chmod(0o600)
        except OSError:
            pass
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return path


def make_temp_dir(prefix: str = "hmr-") -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))
