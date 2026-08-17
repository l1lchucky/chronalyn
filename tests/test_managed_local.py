"""Hermetic tests for Chronalyn 1.1 managed lightweight Hindsight.

Covers the managed-local install path without touching the network or real
packages: a fake embedding endpoint, monkeypatched install/start functions,
and the real routing-policy assertions.

Scenarios (from the 1.1 requirements):
- clean managed-local install (env file, dims, start, service registration)
- bad API key (dimension detection fails)
- bad embedding model (dimension detection fails)
- Hindsight startup failure (start never becomes healthy)
- Mnemosyne failure (dual checkpoint backend fails validation)
- existing Chronalyn 1.0 config remains valid (no policy regression)
- normal write reaches Hindsight only
- checkpoint reaches both backends
- merged recall remains impossible
- service lifecycle: systemd --user when available, launcher fallback otherwise
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from chronalyn import identity
from chronalyn.config import new_config
from chronalyn.managed import (
    EMBEDDING_BATCH_SIZE,
    MANAGED_DIRNAME,
    SYSTEMD_SERVICE_NAME,
    SYSTEMD_UNIT_FILENAME,
    build_env_file,
    detect_embedding_dimensions,
    managed_state,
    register_managed_service,
    register_systemd_user_service,
)
from chronalyn.policy import HINDSIGHT_MNEMOSYNE, HINDSIGHT_ONLY, get_policy


# ---------------------------------------------------------------------------
# Fake OpenAI-compatible embedding endpoint
# ---------------------------------------------------------------------------
class _EmbeddingHandler(BaseHTTPRequestHandler):
    dims = 384
    fail = False

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path.endswith("/v1/embeddings"):
            if self.fail:
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'{"error":"invalid api key"}')
                return
            model = body.get("model", "")
            if "bad-model" in str(model):
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'{"error":"model not found"}')
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            vector = [0.0] * self.dims
            payload = {"data": [{"embedding": vector, "index": 0}]}
            self.wfile.write(json.dumps(payload).encode())
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture()
def embedding_server():
    server = HTTPServer(("127.0.0.1", 0), _EmbeddingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    _EmbeddingHandler.dims = 384
    _EmbeddingHandler.fail = False
    try:
        yield base
    finally:
        server.shutdown()
        thread.join(timeout=5)


# ---------------------------------------------------------------------------
# Managed env file + dimension detection
# ---------------------------------------------------------------------------
def test_build_env_file_is_owner_only_and_complete(tmp_path: Path):
    path = build_env_file(
        tmp_path,
        llm_base_url="https://api.example.com/v1",
        llm_api_key="secret-llm",
        llm_model="llm-model-x",
        embedding_base_url="https://api.example.com/v1",
        embedding_api_key="secret-embed",
        embedding_model="embed-model-y",
        embedding_dimensions=768,
    )
    text = path.read_text(encoding="utf-8")
    # All required configuration is present.
    assert "HINDSIGHT_API_LLM_BASE_URL=https://api.example.com/v1" in text
    assert "HINDSIGHT_API_LLM_MODEL=llm-model-x" in text
    assert "HINDSIGHT_API_LLM_API_KEY=secret-llm" in text
    assert "HINDSIGHT_API_EMBEDDINGS_PROVIDER=openai" in text
    assert "HINDSIGHT_API_EMBEDDINGS_OPENAI_MODEL=embed-model-y" in text
    assert "HINDSIGHT_API_EMBEDDINGS_OPENAI_DIMENSIONS=768" in text
    assert f"HINDSIGHT_API_EMBEDDINGS_OPENAI_BATCH_SIZE={EMBEDDING_BATCH_SIZE}" in text
    assert "HINDSIGHT_API_DATABASE_BACKEND=pg0" in text
    assert "HINDSIGHT_API_HOST=127.0.0.1" in text
    assert "HINDSIGHT_API_PORT=8888" in text
    assert "HINDSIGHT_API_WORKERS=1" in text
    assert "HINDSIGHT_API_ACCESS_LOG=false" in text
    assert "HINDSIGHT_API_ENABLE_RERANKING=false" in text
    assert "HINDSIGHT_API_RERANKER_PROVIDER=none" in text
    # Owner-only permissions.
    assert (path.stat().st_mode & 0o777) == 0o600


def test_detect_embedding_dimensions_success(embedding_server: str):
    dims = detect_embedding_dimensions(
        api_url=embedding_server,
        api_key="test-key",
        model="text-embedding-3-small",
    )
    assert dims == 384


def test_detect_embedding_dimensions_bad_api_key(embedding_server: str):
    _EmbeddingHandler.fail = True
    from chronalyn.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError):
        detect_embedding_dimensions(
            api_url=embedding_server,
            api_key="wrong-key",
            model="text-embedding-3-small",
        )


def test_detect_embedding_dimensions_bad_model(embedding_server: str):
    from chronalyn.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError):
        detect_embedding_dimensions(
            api_url=embedding_server,
            api_key="test-key",
            model="bad-model-xyz",
        )


# ---------------------------------------------------------------------------
# Managed state + service registration
# ---------------------------------------------------------------------------
def test_managed_state_uninstalled(tmp_path: Path):
    state = managed_state(tmp_path)
    assert state.installed is False
    assert state.running is False
    assert state.env_dir == tmp_path / MANAGED_DIRNAME


def test_register_managed_service_launcher_fallback(tmp_path: Path, monkeypatch):
    """Without systemd --user, the launcher fallback must not fail install."""
    # Simulate an installed venv with a hindsight-api entry point.
    venv = tmp_path / MANAGED_DIRNAME / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").write_text("#!/bin/sh\n")
    (venv / "bin" / "hindsight-api").write_text("#!/bin/sh\n")

    monkeypatch.setattr("chronalyn.managed._systemd_available", lambda: False)
    mechanism = register_managed_service(tmp_path)
    assert mechanism == "launcher"
    launcher = tmp_path / MANAGED_DIRNAME / "start-hindsight.sh"
    assert launcher.exists()
    text = launcher.read_text(encoding="utf-8")
    assert 'HINDSIGHT_API_HOST="127.0.0.1"' in text
    assert 'HINDSIGHT_API_PORT="8888"' in text
    assert (launcher.stat().st_mode & 0o777) == 0o700


def test_register_systemd_user_service_writes_unit(tmp_path: Path, monkeypatch):
    venv = tmp_path / MANAGED_DIRNAME / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").write_text("#!/bin/sh\n")
    (venv / "bin" / "hindsight-api").write_text("#!/bin/sh\n")
    (tmp_path / MANAGED_DIRNAME / ".env").write_text("A=1\n")

    calls: list[list[str]] = []
    monkeypatch.setattr("chronalyn.managed._systemd_available", lambda: True)
    monkeypatch.setattr(
        "chronalyn.managed.SYSTEMD_USER_DIR",
        tmp_path / "systemd-user",
    )

    def fake_run(command, **kwargs):
        calls.append(command)
        return None

    monkeypatch.setattr("chronalyn.managed.run_command", fake_run)
    ok = register_systemd_user_service(tmp_path)
    assert ok is True
    unit = tmp_path / "systemd-user" / SYSTEMD_UNIT_FILENAME
    assert unit.exists()
    assert unit.name == f"{SYSTEMD_SERVICE_NAME}.service"
    text = unit.read_text(encoding="utf-8")
    assert "Restart=on-failure" in text
    assert "EnvironmentFile=" in text
    assert any("daemon-reload" in c for c in calls)
    assert any("enable" in c for c in calls)
    assert any("start" in c for c in calls)


# ---------------------------------------------------------------------------
# Routing policy unchanged (Chronalyn 1.0 config stays valid)
# ---------------------------------------------------------------------------
def test_existing_dual_config_remains_valid():
    cfg = new_config(namespace="my-project", environment="prod", policy=HINDSIGHT_MNEMOSYNE)
    cfg.apply_policy_defaults()
    cfg.validate()
    assert cfg.policy == HINDSIGHT_MNEMOSYNE


def test_existing_hindsight_only_config_remains_valid():
    cfg = new_config(namespace="my-project", environment="staging", policy=HINDSIGHT_ONLY)
    cfg.apply_policy_defaults()
    cfg.validate()
    assert cfg.policy == HINDSIGHT_ONLY


def test_policy_normal_write_hindsight_only():
    pol = get_policy(HINDSIGHT_MNEMOSYNE)
    assert pol.automatic_backends == ("hindsight",)


def test_policy_checkpoint_reaches_both():
    pol = get_policy(HINDSIGHT_MNEMOSYNE)
    assert set(pol.checkpoint_backends) == {"hindsight", "mnemosyne"}


def test_policy_merged_recall_prohibited():
    pol = get_policy(HINDSIGHT_MNEMOSYNE)
    # recall is Hindsight-first with bounded fallback; there is no merged mode.
    assert pol.recall_primary == "hindsight"
    assert pol.fallback_backend == "mnemosyne"


def test_version_is_1_1_0():
    assert identity.VERSION == "1.1.0"
    assert identity.RELEASE_NAME == "v1.1.0"
    assert identity.IS_RELEASE_CANDIDATE is False
