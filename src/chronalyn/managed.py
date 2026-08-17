"""Managed lightweight local Hindsight for Chronalyn 1.1.

Encodes the proven production stack into a self-contained installer:

- isolated venv under ``$HERMES_HOME/hindsight-managed/venv``
- ``hindsight-api-slim[embedded-db]`` (no torch/transformers/local ML extras)
- embedded PostgreSQL + pgvector via ``pg0``
- remote OpenAI-compatible LLM + embeddings, batch 64
- automatic embedding-dimension detection
- reranker disabled, RRF/text-search passthrough enabled
- one API worker, access log off, loopback only
- daemonized ``hindsight-api`` with port-bind dedup

Nothing here requires sudo, installs local models, or exposes Hindsight
outside 127.0.0.1. Secrets live only in the owner-readable env file.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .bootstrap import run_command
from .exceptions import ConfigurationError

# The lightest supported Hindsight runtime for this stack. The [embedded-db]
# extra brings pg0-embedded (PostgreSQL + pgvector); the heavyweight local ML
# extras ([all], [local-ml], [local-onnx], [local-llm]) are deliberately NOT
# installed.
HINDSIGHT_PACKAGE = "hindsight-api-slim[embedded-db]"
HINDSIGHT_VERSION = "0.9.1"

MANAGED_DIRNAME = "hindsight-managed"
ENV_FILENAME = ".env"
LAUNCHER_FILENAME = "start-hindsight.sh"
HEALTH_PATH = "/health"
DEFAULT_PORT = 8888
DEFAULT_HOST = "127.0.0.1"
EMBEDDING_BATCH_SIZE = 64
HEALTH_TIMEOUT_SECONDS = 90
HEALTH_POLL_SECONDS = 1.5
START_TIMEOUT_SECONDS = 300

# systemd --user service identity for the Chronalyn-managed Hindsight instance.
SYSTEMD_SERVICE_NAME = "chronalyn-hindsight"
SYSTEMD_UNIT_FILENAME = f"{SYSTEMD_SERVICE_NAME}.service"
SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"

Log = Callable[[str], None]


def _silent_log(_line: str) -> None:
    pass


@dataclass
class ManagedHindsightState:
    """Facts about a managed Hindsight installation."""

    hermes_home: Path
    env_dir: Path = field(init=False)
    venv_dir: Path = field(init=False)
    env_file: Path = field(init=False)
    api_url: str = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}"
    installed: bool = False
    running: bool = False
    healthy: bool = False
    pid: int | None = None
    error: str = ""

    def __post_init__(self) -> None:
        self.env_dir = self.hermes_home / MANAGED_DIRNAME
        self.venv_dir = self.env_dir / "venv"
        self.env_file = self.env_dir / ENV_FILENAME
        self.installed = self.venv_dir.exists() and (self.venv_dir / "bin" / "python").exists()


def managed_dir(hermes_home: Path) -> Path:
    return hermes_home / MANAGED_DIRNAME


def managed_env_file(hermes_home: Path) -> Path:
    return managed_dir(hermes_home) / ENV_FILENAME


def managed_state(hermes_home: Path) -> ManagedHindsightState:
    state = ManagedHindsightState(hermes_home=hermes_home)
    if state.installed:
        state.running = _service_running(state)
        if state.running:
            state.healthy = _probe_health(state.api_url)
    return state


def _service_running(state: ManagedHindsightState) -> bool:
    """Port-bind is the authoritative liveness signal (same rule the package
    uses for daemon dedup)."""
    return _port_in_use(DEFAULT_HOST, DEFAULT_PORT)


def _port_in_use(host: str, port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        try:
            sock.connect((host, port))
            return True
        except OSError:
            return False


def _probe_health(api_url: str, timeout: float = 3.0) -> bool:
    url = api_url.rstrip("/") + HEALTH_PATH
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            status: int = resp.status
            return 200 <= status < 300
    except (OSError, urllib.error.URLError):
        return False


def detect_embedding_dimensions(
    *,
    api_url: str,
    api_key: str,
    model: str,
    timeout: float = 30.0,
) -> int:
    """Probe the OpenAI-compatible /v1/embeddings endpoint for vector width."""
    url = api_url.rstrip("/") + "/v1/embeddings"
    payload = {"model": model, "input": "dimension probe"}
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    body = json.dumps(payload).encode("utf-8")
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, data=body, headers=headers, method="POST"),
            timeout=timeout,
        ) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Cannot reach the embedding endpoint {url}: {exc}") from exc
    data = result.get("data") if isinstance(result, dict) else None
    if not isinstance(data, list) or not data:
        raise ConfigurationError(f"The embedding endpoint returned no vectors for model {model!r}")
    vector = data[0].get("embedding")
    if not isinstance(vector, list) or not vector:
        raise ConfigurationError(
            f"The embedding endpoint returned no embedding vector for model {model!r}"
        )
    return len(vector)


def build_env_file(
    hermes_home: Path,
    *,
    llm_base_url: str,
    llm_api_key: str,
    llm_model: str,
    embedding_base_url: str,
    embedding_api_key: str,
    embedding_model: str,
    embedding_dimensions: int,
    embedding_batch_size: int = EMBEDDING_BATCH_SIZE,
    port: int = DEFAULT_PORT,
    host: str = DEFAULT_HOST,
) -> Path:
    """Write the managed Hindsight env file (owner-only, no secrets in logs)."""
    env_dir = managed_dir(hermes_home)
    env_dir.mkdir(parents=True, exist_ok=True)
    path = env_dir / ENV_FILENAME
    lines = [
        "# Managed by Chronalyn 1.1. Owner-readable only.",
        "# LLM (remote OpenAI-compatible)",
        "HINDSIGHT_API_LLM_PROVIDER=openai",
        f"HINDSIGHT_API_LLM_BASE_URL={llm_base_url.rstrip('/')}",
        f"HINDSIGHT_API_LLM_MODEL={llm_model}",
        f"HINDSIGHT_API_LLM_API_KEY={llm_api_key}",
        "",
        "# Embeddings (remote OpenAI-compatible, batch 64)",
        "HINDSIGHT_API_EMBEDDINGS_PROVIDER=openai",
        f"HINDSIGHT_API_EMBEDDINGS_OPENAI_BASE_URL={embedding_base_url.rstrip('/')}",
        f"HINDSIGHT_API_EMBEDDINGS_OPENAI_MODEL={embedding_model}",
        f"HINDSIGHT_API_EMBEDDINGS_OPENAI_DIMENSIONS={embedding_dimensions}",
        f"HINDSIGHT_API_EMBEDDINGS_OPENAI_BATCH_SIZE={embedding_batch_size}",
        f"HINDSIGHT_API_EMBEDDINGS_OPENAI_API_KEY={embedding_api_key}",
        "",
        "# Persistence: embedded PostgreSQL + pgvector (pg0)",
        "HINDSIGHT_API_DATABASE_BACKEND=pg0",
        "",
        "# Server: loopback only, one worker, no access log",
        f"HINDSIGHT_API_HOST={host}",
        f"HINDSIGHT_API_PORT={port}",
        "HINDSIGHT_API_WORKERS=1",
        "HINDSIGHT_API_ACCESS_LOG=false",
        "",
        "# Retrieval: RRF/text-search passthrough, neural reranker disabled",
        "HINDSIGHT_API_ENABLE_RERANKING=false",
        "HINDSIGHT_API_RERANKER_PROVIDER=none",
        "HINDSIGHT_API_TEXT_SEARCH_EXTENSION=pgvector",
        "",
    ]
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")
    if path.exists():
        path.chmod(0o600)
    return path


def install_hindsight(
    hermes_home: Path,
    *,
    log: Log = _silent_log,
    timeout: int = START_TIMEOUT_SECONDS,
) -> Path:
    """Create the managed venv and install the lightest Hindsight runtime."""
    state = ManagedHindsightState(hermes_home=hermes_home)
    env_dir = state.env_dir
    venv = state.venv_dir
    if state.installed:
        log(f"Managed Hindsight venv already present at {venv}")
        return venv
    env_dir.mkdir(parents=True, exist_ok=True)
    python = sys.executable
    log(f"Creating isolated venv at {venv}")
    run_command([python, "-m", "venv", str(venv)], timeout=timeout)
    pip = venv / "bin" / "python"
    log(f"Installing {HINDSIGHT_PACKAGE}=={HINDSIGHT_VERSION}")
    run_command(
        [
            str(pip),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            f"{HINDSIGHT_PACKAGE}=={HINDSIGHT_VERSION}",
        ],
        timeout=timeout,
    )
    # The daemon entry point must exist after install.
    bin_dir = venv / "bin"
    cli = bin_dir / "hindsight-api"
    if not cli.exists():
        raise ConfigurationError(f"hindsight-api entry point missing after install: {cli}")
    log(f"Managed Hindsight installed at {venv}")
    return venv


def start_hindsight(
    hermes_home: Path,
    *,
    log: Log = _silent_log,
    timeout: int = HEALTH_TIMEOUT_SECONDS,
) -> None:
    """Start the daemon (port-bind dedup) and wait until healthy."""
    state = ManagedHindsightState(hermes_home=hermes_home)
    if not state.installed:
        raise ConfigurationError("Managed Hindsight is not installed; run install_hindsight first")
    if _service_running(state):
        log(f"Hindsight already listening on {state.api_url}")
        if _probe_health(state.api_url):
            return
        raise ConfigurationError(
            f"Port {DEFAULT_PORT} is in use but {state.api_url}{HEALTH_PATH} is unhealthy"
        )
    cli = state.venv_dir / "bin" / "hindsight-api"
    env = os.environ.copy()
    # Hindsight's entry point loads the env file itself via
    # load_dotenv_for_entrypoint() (override=True), so we only need to point
    # the child at the right working directory and pass nothing secret.
    log(f"Starting managed Hindsight: {cli} --daemon")
    try:
        run_command([str(cli), "--daemon"], timeout=timeout, cwd=state.env_dir, env=env)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ConfigurationError(f"Could not start managed Hindsight: {exc}") from exc
    deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if _probe_health(state.api_url):
            log(f"Managed Hindsight healthy at {state.api_url}")
            return
        time.sleep(HEALTH_POLL_SECONDS)
    raise ConfigurationError(
        f"Managed Hindsight did not become healthy at {state.api_url} "
        f"within {HEALTH_TIMEOUT_SECONDS}s"
    )


def stop_hindsight(
    hermes_home: Path,
    *,
    log: Log = _silent_log,
) -> None:
    """Stop the managed daemon if it is running (best-effort, no sudo)."""
    state = ManagedHindsightState(hermes_home=hermes_home)
    if not _service_running(state):
        return

    pid = _find_hindsight_pid(state)
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            log(f"Sent SIGTERM to managed Hindsight pid {pid}")
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and _service_running(state):
                time.sleep(0.5)
            return
        except (OSError, ProcessLookupError):
            pass
    # Fallback: the package's own CLI has no stop; the port will clear when
    # the parent (daemonize re-exec) exits. Nothing further is safe to do
    # without sudo.
    log("Managed Hindsight stop requested; process handles SIGTERM itself")


def _find_hindsight_pid(state: ManagedHindsightState) -> int | None:
    """Find the daemon pid by matching the venv's hindsight-api command."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"{state.venv_dir}/bin/hindsight-api"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    return None


def write_launcher(
    hermes_home: Path,
    *,
    log: Log = _silent_log,
) -> Path:
    """Write the internal launcher script for the managed Hindsight daemon.

    This is the single safe way to start the managed instance; the systemd
    user unit (when available) and manual fallback both call it. The launcher
    loads the generated env file and starts hindsight-api with the managed
    venv, foreground-style (systemd manages the process itself).
    """
    state = ManagedHindsightState(hermes_home=hermes_home)
    launcher = state.env_dir / LAUNCHER_FILENAME
    cli = state.venv_dir / "bin" / "hindsight-api"
    script = f"""#!/usr/bin/env bash
# Chronalyn-managed Hindsight launcher (generated; do not edit).
# Loads the managed environment and starts the local Hindsight API.
set -euo pipefail
umask 077
cd "{state.env_dir}"
export HINDSIGHT_API_HOST="{DEFAULT_HOST}"
export HINDSIGHT_API_PORT="{DEFAULT_PORT}"
exec "{cli}" --daemon
"""
    fd = os.open(str(launcher), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o700)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(script)
    log(f"Wrote launcher script {launcher}")
    return launcher


def _systemd_available() -> bool:
    """True when systemd --user can run units on this host."""
    if not shutil.which("systemctl"):
        return False
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-system-running"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode in (0, 1, 2)
    except (OSError, subprocess.SubprocessError):
        return False


def register_systemd_user_service(
    hermes_home: Path,
    *,
    log: Log = _silent_log,
) -> bool:
    """Register the managed Hindsight as a systemd --user service.

    Returns True when the unit was registered and enabled; False when
    systemd --user is unavailable (the caller then falls back to the launcher
    script and reports the limitation).
    """
    if not _systemd_available():
        return False
    state = ManagedHindsightState(hermes_home=hermes_home)
    launcher = state.env_dir / LAUNCHER_FILENAME
    unit_dir = SYSTEMD_USER_DIR
    unit_dir.mkdir(parents=True, exist_ok=True)
    unit = unit_dir / SYSTEMD_UNIT_FILENAME
    unit_text = f"""[Unit]
Description=Chronalyn-managed Hindsight memory API
After=network-online.target

[Service]
Type=simple
ExecStart={launcher}
Restart=on-failure
RestartSec=5
EnvironmentFile={state.env_file}

[Install]
WantedBy=default.target
"""
    fd = os.open(str(unit), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(unit_text)
    try:
        run_command(["systemctl", "--user", "daemon-reload"], log=log)
        run_command(["systemctl", "--user", "enable", SYSTEMD_SERVICE_NAME], log=log)
        run_command(["systemctl", "--user", "start", SYSTEMD_SERVICE_NAME], log=log)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ConfigurationError(f"Could not register systemd user service: {exc}") from exc
    log(f"Registered systemd --user service {SYSTEMD_SERVICE_NAME}")
    return True


def register_managed_service(
    hermes_home: Path,
    *,
    log: Log = _silent_log,
) -> str:
    """Register the managed Hindsight lifecycle.

    Returns a short description of the mechanism used:
    - "systemd-user" when a systemd --user unit was created and started;
    - "launcher" when the fallback launcher script is the mechanism.

    The launcher fallback never fails the install: the managed service is
    still running and usable; only reboot auto-start is unavailable.
    """
    write_launcher(hermes_home, log=log)
    if register_systemd_user_service(hermes_home, log=log):
        return "systemd-user"
    log(
        "Automatic startup after reboot is unavailable on this environment "
        "(no systemd --user). Use the launcher script to start the service."
    )
    return "launcher"


def uninstall_hindsight(
    hermes_home: Path,
    *,
    log: Log = _silent_log,
) -> None:
    """Remove the managed venv, env file, and any registered service.

    Never touches external Hindsight data.
    """
    stop_hindsight(hermes_home, log=log)
    if SYSTEMD_USER_DIR.exists():
        unit = SYSTEMD_USER_DIR / SYSTEMD_UNIT_FILENAME
        if unit.exists():
            try:
                run_command(["systemctl", "--user", "disable", SYSTEMD_SERVICE_NAME], log=log)
                unit.unlink()
            except (OSError, subprocess.SubprocessError):
                log("Could not disable the systemd user service (best-effort)")
    env_dir = managed_dir(hermes_home)
    if env_dir.exists():
        shutil.rmtree(env_dir)
        log(f"Removed managed Hindsight directory {env_dir}")
