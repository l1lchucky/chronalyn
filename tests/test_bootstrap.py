from __future__ import annotations

import json
import os

import pytest

from chronalyn.bootstrap import (
    HermesRuntime,
    find_hermes_runtime,
    install_plugin_entry,
    install_router_into_runtime,
    sha256_file,
    validate_hermes_installer,
    write_hindsight_profile_config,
    write_secret_env,
)
from chronalyn.exceptions import ConfigurationError


def test_sha256_file(tmp_path):
    path = tmp_path / "value"
    path.write_bytes(b"abc")
    assert sha256_file(path) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_validate_hermes_installer_identity(tmp_path):
    valid = tmp_path / "install.sh"
    body = (
        "#!/bin/bash\n"
        "# Hermes Agent Installer\n"
        "REPO=https://github.com/NousResearch/hermes-agent.git\n"
        "HERMES_HOME=$HOME/.hermes\n" + "# padding\n" * 2000
    )
    valid.write_text(body)
    validate_hermes_installer(valid)

    invalid = tmp_path / "invalid.sh"
    invalid.write_text("#!/bin/bash\necho wrong\n")
    with pytest.raises(ConfigurationError):
        validate_hermes_installer(invalid)


def test_find_hermes_runtime_from_shebang(tmp_path, monkeypatch):
    if os.name == "nt":
        pytest.skip("POSIX shebang executable discovery is not available on Windows")
    python = tmp_path / "venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\n")
    python.chmod(0o755)
    hermes = tmp_path / "bin/hermes"
    hermes.parent.mkdir()
    hermes.write_text(f"#!{python}\n")
    hermes.chmod(0o755)
    monkeypatch.setenv("PATH", str(hermes.parent))
    runtime = find_hermes_runtime(tmp_path / "home")
    assert runtime is not None
    assert runtime.python == str(python.resolve())
    assert runtime.command == str(hermes.resolve())


def test_secret_env_updates_without_duplicate_and_is_private(tmp_path):
    home = tmp_path / "hermes"
    path = write_secret_env(home, {"HINDSIGHT_API_KEY": "first"})
    write_secret_env(home, {"HINDSIGHT_API_KEY": "second", "OTHER": "x"})
    lines = path.read_text().splitlines()
    assert lines.count("HINDSIGHT_API_KEY=second") == 1
    assert "OTHER=x" in lines
    if os.name == "posix":
        assert path.stat().st_mode & 0o077 == 0


def test_hindsight_profile_config_is_strict_external_or_cloud(tmp_path):
    path = write_hindsight_profile_config(
        tmp_path,
        mode="local_external",
        api_url="http://127.0.0.1:8888",
        bank_id="project-staging",
    )
    payload = json.loads(path.read_text())
    assert payload["mode"] == "local_external"
    assert payload["bank_id"] == "project-staging"
    with pytest.raises(ConfigurationError):
        write_hindsight_profile_config(
            tmp_path,
            mode="local_embedded",
            api_url="http://127.0.0.1:8888",
            bank_id="x",
        )


def test_runtime_install_commands_are_explicit(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)

    class Probe:
        returncode = 0

    monkeypatch.setattr("chronalyn.bootstrap.run_command", fake_run)
    monkeypatch.setattr("chronalyn.bootstrap.subprocess.run", lambda *a, **k: Probe())
    runtime = HermesRuntime("/bin/hermes", "/venv/bin/python", "/venv")
    install_router_into_runtime(
        runtime,
        package_source="/tmp/router.whl",
        dual=True,
    )
    assert calls[0][:4] == ["/venv/bin/python", "-m", "pip", "install"]
    assert "mnemosyne-memory>=3.15,<4" in calls[0]

    install_plugin_entry(runtime, hermes_home=tmp_path)
    assert "install-plugin" in calls[1]
    assert str(tmp_path) in calls[1]


def test_link_router_command_is_safe(tmp_path):
    if os.name == "nt":
        pytest.skip("Windows symlink creation requires an optional OS privilege")
    from chronalyn import identity
    from chronalyn.bootstrap import link_router_command

    runtime_bin = tmp_path / "runtime/bin"
    runtime_bin.mkdir(parents=True)
    source = runtime_bin / identity.CLI_COMMAND
    source.write_text("#!/bin/sh\n")
    source.chmod(0o755)
    command_dir = tmp_path / "commands"
    command_dir.mkdir()
    hermes = command_dir / "hermes"
    hermes.write_text("#!/bin/sh\n")
    hermes.chmod(0o755)
    runtime = HermesRuntime(str(hermes), str(runtime_bin / "python"), str(tmp_path / "runtime"))
    destination = link_router_command(runtime)
    assert destination.name == identity.CLI_COMMAND
    assert destination.is_symlink()
    assert destination.resolve() == source.resolve()

    destination.unlink()
    destination.write_text("do not replace")
    with pytest.raises(ConfigurationError, match="Refusing"):
        link_router_command(runtime)


def test_link_router_command_can_link_the_deprecated_alias(tmp_path):
    """The old command name stays available for existing installations."""
    if os.name == "nt":
        pytest.skip("Windows symlink creation requires an optional OS privilege")
    from chronalyn import identity
    from chronalyn.bootstrap import link_router_command

    runtime_bin = tmp_path / "runtime/bin"
    runtime_bin.mkdir(parents=True)
    legacy = runtime_bin / identity.LEGACY_CLI_COMMAND
    legacy.write_text("#!/bin/sh\n")
    legacy.chmod(0o755)
    command_dir = tmp_path / "commands"
    command_dir.mkdir()
    hermes = command_dir / "hermes"
    hermes.write_text("#!/bin/sh\n")
    hermes.chmod(0o755)
    runtime = HermesRuntime(str(hermes), str(runtime_bin / "python"), str(tmp_path / "runtime"))

    destination = link_router_command(runtime, command_name=identity.LEGACY_CLI_COMMAND)

    assert destination.name == identity.LEGACY_CLI_COMMAND
    assert destination.resolve() == legacy.resolve()


def test_runtime_install_falls_back_to_uv(monkeypatch, tmp_path):
    calls = []

    class Probe:
        returncode = 1

    uv = tmp_path / "bin/uv"
    uv.parent.mkdir()
    uv.write_text("#!/bin/sh\n")
    uv.chmod(0o755)
    monkeypatch.setattr("chronalyn.bootstrap.subprocess.run", lambda *a, **k: Probe())
    monkeypatch.setattr(
        "chronalyn.bootstrap.shutil.which",
        lambda name: str(uv) if name == "uv" else None,
    )
    monkeypatch.setattr(
        "chronalyn.bootstrap.run_command",
        lambda command, **kwargs: calls.append(command),
    )
    runtime = HermesRuntime("/bin/hermes", "/venv/bin/python", "/venv")
    install_router_into_runtime(
        runtime,
        package_source="/tmp/router.whl",
        dual=True,
        hermes_home=tmp_path,
    )
    assert calls[0][:5] == [str(uv), "pip", "install", "--python", "/venv/bin/python"]


def test_secret_env_rejects_newlines_and_invalid_names(tmp_path):
    with pytest.raises(ConfigurationError, match="control character"):
        write_secret_env(tmp_path, {"HINDSIGHT_API_KEY": "bad\nvalue"})
    with pytest.raises(ConfigurationError, match="variable name"):
        write_secret_env(tmp_path, {"bad-key": "value"})


def test_official_hermes_install_is_noninteractive_and_lightweight_by_default(
    monkeypatch, tmp_path
):
    from chronalyn.bootstrap import install_official_hermes

    installer = tmp_path / "install.sh"
    installer.write_text(
        "#!/bin/bash\n# Hermes Agent Installer\n"
        "REPO=https://github.com/NousResearch/hermes-agent.git\n"
        "HERMES_HOME=$HOME/.hermes\n" + "# padding\n" * 2000
    )
    installer.chmod(0o700)
    commands = []
    runtime = HermesRuntime("/tmp/hermes", "/tmp/python", "/tmp")
    monkeypatch.setattr(
        "chronalyn.bootstrap.run_command",
        lambda command, **kwargs: commands.append(command),
    )
    monkeypatch.setattr(
        "chronalyn.bootstrap.find_hermes_runtime",
        lambda home: runtime,
    )
    assert install_official_hermes(tmp_path, installer=installer) == runtime
    command = commands[0]
    assert "--skip-setup" in command
    assert "--non-interactive" in command
    assert "--skip-browser" in command


def test_official_hermes_install_can_include_browser(monkeypatch, tmp_path):
    from chronalyn.bootstrap import install_official_hermes

    installer = tmp_path / "install.sh"
    installer.write_text(
        "#!/bin/bash\n# Hermes Agent Installer\n"
        "REPO=https://github.com/NousResearch/hermes-agent.git\n"
        "HERMES_HOME=$HOME/.hermes\n" + "# padding\n" * 2000
    )
    installer.chmod(0o700)
    commands = []
    runtime = HermesRuntime("/tmp/hermes", "/tmp/python", "/tmp")
    monkeypatch.setattr(
        "chronalyn.bootstrap.run_command",
        lambda command, **kwargs: commands.append(command),
    )
    monkeypatch.setattr(
        "chronalyn.bootstrap.find_hermes_runtime",
        lambda home: runtime,
    )
    install_official_hermes(tmp_path, installer=installer, with_browser=True)
    assert "--skip-browser" not in commands[0]


def test_find_hermes_runtime_supports_dot_venv(tmp_path, monkeypatch):
    home = tmp_path / "profile"
    python = home / "hermes-agent/.venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\n")
    python.chmod(0o755)
    hermes = home / "bin/hermes"
    hermes.parent.mkdir(parents=True)
    hermes.write_text("hermes launcher placeholder\n")
    hermes.chmod(0o755)
    monkeypatch.setenv("PATH", "")
    monkeypatch.delenv("HERMES_PYTHON", raising=False)
    runtime = find_hermes_runtime(home)
    assert runtime is not None
    assert runtime.command == str(hermes.resolve())
    assert runtime.python == str(python.resolve())


def test_verify_router_runs_inside_hermes_runtime(monkeypatch, tmp_path):
    from chronalyn.bootstrap import verify_router_in_runtime

    captured = {}

    class Result:
        returncode = 0
        stdout = '{"backends": {"hindsight": {"ok": true}}}'
        stderr = ""

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["env"] = kwargs["env"]
        return Result()

    monkeypatch.setattr("chronalyn.bootstrap.subprocess.run", fake_run)
    runtime = HermesRuntime("/bin/hermes", "/venv/bin/python", "/venv")
    payload = verify_router_in_runtime(runtime, hermes_home=tmp_path)
    assert payload["backends"]["hindsight"]["ok"] is True
    assert captured["command"][0] == "/venv/bin/python"
    assert captured["command"][-1] == "status"
    assert captured["env"]["HERMES_HOME"] == str(tmp_path)


def test_hindsight_profile_update_preserves_advanced_settings(tmp_path):
    path = tmp_path / "hindsight/config.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "mode": "cloud",
                "apiUrl": "https://old.example",
                "bankId": "old-bank",
                "retain_tags": ["keep-me"],
                "observation_scopes": "per_tag",
                "recall_budget": "high",
            }
        )
    )
    write_hindsight_profile_config(
        tmp_path,
        mode="local_external",
        api_url="https://new.internal",
        bank_id="new-bank",
    )
    payload = json.loads(path.read_text())
    assert payload["mode"] == "local_external"
    assert payload["api_url"] == "https://new.internal"
    assert payload["bank_id"] == "new-bank"
    assert payload["retain_tags"] == ["keep-me"]
    assert payload["observation_scopes"] == "per_tag"
    assert payload["recall_budget"] == "high"
