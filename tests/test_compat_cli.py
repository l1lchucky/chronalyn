"""The deprecated `hermes-memory-router` console command.

It must keep working for existing installations, warn clearly on stderr, and
delegate to Chronalyn without changing behaviour or exit codes.
"""

from __future__ import annotations

import pytest

from chronalyn import compat_cli, identity
from chronalyn.compat_cli import main as compat_main


def test_warns_on_stderr_and_delegates(tmp_path, capsys) -> None:
    exit_code = compat_main(
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

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "deprecated" in captured.err.lower()
    # The warning must name the replacement command.
    assert identity.CLI_COMMAND in captured.err
    # The real work still happened.
    assert (tmp_path / identity.STATE_DIRNAME / identity.CONFIG_FILENAME).exists()


def test_warning_goes_to_stderr_not_stdout(tmp_path, capsys) -> None:
    """--json consumers parse stdout; the warning must not corrupt it."""
    import json

    exit_code = compat_main(
        [
            "--hermes-home",
            str(tmp_path),
            "--json",
            "init",
            "--namespace",
            "project",
            "--environment",
            "staging",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "deprecated" not in captured.out.lower()
    # stdout must remain machine-readable.
    assert json.loads(captured.out)["policy"] == "hindsight-only"


def test_propagates_failure_exit_code(tmp_path, capsys) -> None:
    """A delegated failure must not be masked by the alias."""
    exit_code = compat_main(["--hermes-home", str(tmp_path), "validate"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "deprecated" in captured.err.lower()


def test_version_flag_reports_chronalyn(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        compat_main(["--version"])

    assert excinfo.value.code == 0
    assert identity.BRAND in capsys.readouterr().out


def test_deprecation_notice_names_both_commands() -> None:
    notice = identity.DEPRECATION_NOTICE
    assert identity.LEGACY_CLI_COMMAND in notice
    assert identity.CLI_COMMAND in notice


def test_forwards_argv_verbatim_to_the_canonical_cli(monkeypatch, capsys) -> None:
    argv = ["--hermes-home", "/tmp/chronalyn", "validate", "--json"]
    received: list[list[str] | None] = []
    monkeypatch.setattr(
        compat_cli,
        "chronalyn_main",
        lambda delegated: received.append(delegated) or 17,
    )

    assert compat_cli.main(argv) == 17
    assert received == [argv]
    assert capsys.readouterr().out == ""
