from __future__ import annotations

import os
import sys
import threading
from contextlib import AbstractContextManager
from types import TracebackType
from typing import TextIO

#: Environment variables that suppress the animation. ``HMR_NO_ANIMATION`` is the
#: pre-rename name and is still honoured so existing scripts keep working.
ANIMATION_DISABLE_ENV_VARS = ("CHRONALYN_NO_ANIMATION", "HMR_NO_ANIMATION")
_TRUTHY = frozenset({"1", "true", "yes"})


def _animation_disabled_by_env() -> bool:
    return any(
        os.environ.get(name, "").strip().lower() in _TRUTHY for name in ANIMATION_DISABLE_ENV_VARS
    )


class PacmanLoader(AbstractContextManager["PacmanLoader"]):
    """Small dependency-free Pac-Man loading indicator.

    It stays quiet for redirected output, CI, JSON mode, tests, and when
    CHRONALYN_NO_ANIMATION=1 (or the legacy HMR_NO_ANIMATION=1) is set.
    """

    _frames = (
        "ᗧ * * *",
        "ᗣ   * *",
        "ᗧ     *",
        "ᗣ      ",
    )

    def __init__(
        self,
        label: str,
        *,
        stream: TextIO | None = None,
        enabled: bool | None = None,
        interval: float = 0.12,
    ) -> None:
        self.label = label
        self.stream = stream or sys.stderr
        self.interval = interval
        automatic = bool(
            getattr(self.stream, "isatty", lambda: False)()
            and not os.environ.get("CI")
            and not _animation_disabled_by_env()
            and os.environ.get("TERM", "") != "dumb"
        )
        self.enabled = automatic if enabled is None else enabled
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> PacmanLoader:
        if self.enabled:
            self._thread = threading.Thread(target=self._animate, daemon=True)
            self._thread.start()
        return self

    def _animate(self) -> None:
        index = 0
        while not self._stop.is_set():
            frame = self._frames[index % len(self._frames)]
            self.stream.write(chr(13) + f"\x1b[2K{frame}  {self.label}")
            self.stream.flush()
            index += 1
            if self._stop.wait(self.interval):
                break

    def stop(self, final: str | None = None) -> None:
        if not self.enabled:
            return
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        self.stream.write("\r\x1b[2K")
        if final:
            self.stream.write(final + "\n")
        self.stream.flush()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()
        return None
