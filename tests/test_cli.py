from pathlib import Path

import pytest

from hermes_memory_router.cli import main


def test_cli_init_validate_and_plugin_lifecycle(tmp_path, capsys):
    assert main([
        "--hermes-home", str(tmp_path),
        "init", "--namespace", "project", "--environment", "staging",
    ]) == 0
    assert (tmp_path / "memory-router/config.json").exists()

    assert main(["--hermes-home", str(tmp_path), "validate"]) == 0
    assert '"namespace": "project"' in capsys.readouterr().out

    assert main(["--hermes-home", str(tmp_path), "install-plugin"]) == 0
    plugin = tmp_path / "plugins/memory/hermes_memory_router"
    assert (plugin / "__init__.py").exists()
    assert (plugin / "plugin.yaml").exists()

    assert main(["--hermes-home", str(tmp_path), "uninstall-plugin"]) == 0
    assert not plugin.exists()


def test_cli_init_refuses_overwrite(tmp_path):
    args = [
        "--hermes-home", str(tmp_path),
        "init", "--namespace", "project", "--environment", "staging",
    ]
    assert main(args) == 0
    with pytest.raises(SystemExit, match="already exists"):
        main(args)
    assert main(args + ["--force"]) == 0
