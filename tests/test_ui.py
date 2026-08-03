from __future__ import annotations

import io
import time

from hermes_memory_router.ui import PacmanLoader


class TTY(io.StringIO):
    def isatty(self):
        return True


class Pipe(io.StringIO):
    def isatty(self):
        return False


def test_animation_is_silent_for_redirected_output():
    stream = Pipe()
    with PacmanLoader("loading", stream=stream):
        time.sleep(0.02)
    assert stream.getvalue() == ""


def test_animation_renders_pacman_on_tty():
    stream = TTY()
    with PacmanLoader("loading", stream=stream, enabled=True, interval=0.005):
        time.sleep(0.02)
    output = stream.getvalue()
    assert "loading" in output
    assert "*" in output
    assert "ᗧ" in output or "ᗣ" in output
