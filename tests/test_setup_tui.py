from pathlib import Path

from hermes_memory_router.setup_tui import (
    DualSetupApp,
    DualSetupState,
    MenuLayout,
    explain_dual_mode,
    menu_key_action,
    wrap_lines,
)


def test_menu_supports_numbers_space_enter_and_arrows():
    assert menu_key_action(ord("2"), 3, 0) == ("activate", 1)
    assert menu_key_action(ord(" "), 3, 2) == ("activate", 2)
    assert menu_key_action(10, 3, 1) == ("activate", 1)
    assert menu_key_action(259, 3, 0) == ("move", 2)
    assert menu_key_action(258, 3, 2) == ("move", 0)
    assert menu_key_action(ord("b"), 3, 1) == ("back", 1)
    assert menu_key_action(ord("q"), 3, 1) == ("quit", 1)


def test_mouse_hit_testing_is_bounded():
    layout = MenuLayout(((0, 5, 6), (1, 8, 10)))
    assert layout.item_at(5, 20, left=4, right=60) == 0
    assert layout.item_at(9, 20, left=4, right=60) == 1
    assert layout.item_at(7, 20, left=4, right=60) is None
    assert layout.item_at(9, 70, left=4, right=60) is None


def test_dual_explanation_is_strict():
    text = "\n".join(explain_dual_mode())
    assert "HINDSIGHT only" in text
    assert "HINDSIGHT + MNEMOSYNE" in text
    assert "MERGED RECALL -> prohibited" in text


def test_url_validation():
    state = DualSetupState(Path("/tmp/test"))
    app = DualSetupApp(state)
    assert app._validate_url("http://127.0.0.1:8888") is None
    assert app._validate_url("https://api.example.test", require_https=True) is None
    assert "HTTPS" in app._validate_url("http://api.example.test", require_https=True)
    assert app._validate_url("ftp://example.test") is not None


def test_wrapping_preserves_blank_lines():
    assert wrap_lines("one\n\ntwo", 20) == ["one", "", "two"]


def test_acknowledgements_explain_local_and_remote_transmission():
    from hermes_memory_router.setup_tui import acknowledgement_items

    local = DualSetupState(Path("/tmp/local"), hindsight_api_url="http://127.0.0.1:8888")
    remote = DualSetupState(
        Path("/tmp/remote"),
        hindsight_api_url="https://memory.example.test",
    )
    assert "local to this host" in acknowledgement_items(local)[3]
    assert "off-device" in acknowledgement_items(remote)[3]


def test_dual_setup_state_defaults_to_lightweight_hermes():
    state = DualSetupState(Path("/tmp/test"))
    assert state.with_browser is False
