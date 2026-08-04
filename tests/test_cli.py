import json

from chronalyn.cli import main
from chronalyn.compatibility import profile_fingerprint
from chronalyn.store import RouterStore


def test_cli_init_validate_and_plugin_lifecycle(tmp_path, capsys):
    assert (
        main(
            [
                "--hermes-home",
                str(tmp_path),
                "init",
                "--namespace",
                "project",
                "--environment",
                "staging",
            ]
        )
        == 0
    )
    assert (tmp_path / "memory-router/config.json").exists()

    assert main(["--hermes-home", str(tmp_path), "validate"]) == 0
    assert '"namespace": "project"' in capsys.readouterr().out

    assert main(["--hermes-home", str(tmp_path), "install-plugin"]) == 0
    # Hermes discovers user providers at $HERMES_HOME/plugins/<provider-id>/.
    plugin = tmp_path / "plugins" / "chronalyn"
    assert (plugin / "__init__.py").exists()
    assert (plugin / "plugin.yaml").exists()

    assert main(["--hermes-home", str(tmp_path), "uninstall-plugin"]) == 0
    assert not plugin.exists()
    # Uninstalling the plugin entry must never remove router configuration.
    assert (tmp_path / "memory-router/config.json").exists()


def test_cli_init_refuses_overwrite(tmp_path):
    args = [
        "--hermes-home",
        str(tmp_path),
        "init",
        "--namespace",
        "project",
        "--environment",
        "staging",
    ]
    assert main(args) == 0
    assert main(args) == 2
    assert main([*args, "--force"]) == 0


def test_cli_db_info_check_backup_verify_and_vacuum(tmp_path, capsys):
    assert (
        main(
            [
                "--hermes-home",
                str(tmp_path),
                "init",
                "--namespace",
                "project",
                "--environment",
                "staging",
            ]
        )
        == 0
    )
    capsys.readouterr()
    store = RouterStore(
        tmp_path / "memory-router/router.db",
        namespace="project",
        environment="staging",
        profile_fingerprint=profile_fingerprint(tmp_path),
        strict_binding=True,
    )
    store.close()

    assert main(["--hermes-home", str(tmp_path), "--json", "db", "info"]) == 0
    assert json.loads(capsys.readouterr().out)["schema_version"] == 2
    assert main(["--hermes-home", str(tmp_path), "--json", "db", "check"]) == 0
    assert json.loads(capsys.readouterr().out)["integrity"] == "ok"

    backup = tmp_path / "backups/router.sqlite"
    assert (
        main(
            [
                "--hermes-home",
                str(tmp_path),
                "--json",
                "db",
                "backup",
                "--output",
                str(backup),
            ]
        )
        == 0
    )
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["sha256"]
    assert (
        main(
            [
                "--hermes-home",
                str(tmp_path),
                "--json",
                "db",
                "verify-backup",
                "--path",
                str(backup),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["ok"] is True

    assert main(["--hermes-home", str(tmp_path), "db", "vacuum"]) == 2
    capsys.readouterr()
    assert main(["--hermes-home", str(tmp_path), "--json", "db", "vacuum", "--yes"]) == 0
    assert json.loads(capsys.readouterr().out)["vacuumed"] is True


def test_cli_db_check_integrity_failure_exit_code(tmp_path, capsys):
    assert (
        main(
            [
                "--hermes-home",
                str(tmp_path),
                "init",
                "--namespace",
                "project",
                "--environment",
                "staging",
            ]
        )
        == 0
    )
    capsys.readouterr()
    path = tmp_path / "memory-router/router.db"
    path.write_bytes(b"broken")

    assert main(["--hermes-home", str(tmp_path), "--json", "db", "check"]) == 3
    assert json.loads(capsys.readouterr().out)["ok"] is False
