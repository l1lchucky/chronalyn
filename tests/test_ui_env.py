"""Animation suppression env vars, new name plus legacy compatibility."""

from __future__ import annotations

import io

import pytest

from chronalyn.ui import ANIMATION_DISABLE_ENV_VARS, PacmanLoader


class _Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("CI", "TERM", *ANIMATION_DISABLE_ENV_VARS):
        monkeypatch.delenv(name, raising=False)


def test_enabled_on_a_tty_by_default() -> None:
    assert PacmanLoader("work", stream=_Tty()).enabled is True


@pytest.mark.parametrize("name", sorted(ANIMATION_DISABLE_ENV_VARS))
@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes"])
def test_either_env_var_disables_animation(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)
    assert PacmanLoader("work", stream=_Tty()).enabled is False


def test_legacy_variable_is_still_honoured() -> None:
    """Existing scripts set HMR_NO_ANIMATION; that must keep working."""
    assert "HMR_NO_ANIMATION" in ANIMATION_DISABLE_ENV_VARS
    assert "CHRONALYN_NO_ANIMATION" in ANIMATION_DISABLE_ENV_VARS


def test_unset_and_empty_values_do_not_disable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHRONALYN_NO_ANIMATION", "")
    assert PacmanLoader("work", stream=_Tty()).enabled is True


def test_ci_and_dumb_terminal_disable_animation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI", "1")
    assert PacmanLoader("work", stream=_Tty()).enabled is False
    monkeypatch.delenv("CI")
    monkeypatch.setenv("TERM", "dumb")
    assert PacmanLoader("work", stream=_Tty()).enabled is False


def test_non_tty_stream_stays_quiet() -> None:
    assert PacmanLoader("work", stream=io.StringIO()).enabled is False
