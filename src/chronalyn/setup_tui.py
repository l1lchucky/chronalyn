from __future__ import annotations

import queue
import re
import shutil
import sys
import textwrap
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import identity
from .bootstrap import (
    OFFICIAL_HERMES_INSTALLER,
    DownloadReceipt,
    HermesRuntime,
    download_https,
    find_hermes_runtime,
    install_official_hermes,
    install_plugin_entry,
    install_router_into_runtime,
    link_router_command,
    make_temp_dir,
    verify_router_in_runtime,
    write_hindsight_profile_config,
    write_secret_env,
)
from .compatibility import (
    backup_configuration,
    discover,
    is_local_endpoint,
    restore_backup,
    set_active_provider_with_hermes,
)
from .config import new_config, write_config
from .exceptions import ConfigurationError
from .policy import HINDSIGHT_MNEMOSYNE

# Screen banner. Distinct from identity.BRAND, which is the product name.
BRAND = "CHRONALYN"
SUBTITLE = "STRICT HINDSIGHT + MNEMOSYNE SETUP"
MIN_WIDTH = 72
MIN_HEIGHT = 22

PACMAN_FRAMES = (
    "C  * * * *",
    "<  * * *  ",
    "C    * *  ",
    "<      *  ",
)

KEY_HELP = "ARROWS move  1-9 choose  SPACE select  ENTER continue  MOUSE click  B back  Q quit"
_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")


@dataclass(frozen=True)
class MenuItem:
    title: str
    description: str = ""
    enabled: bool = True


@dataclass
class DualSetupState:
    hermes_home: Path
    package_source: str = ""
    namespace: str = "my-project"
    environment: str = "staging"
    hindsight_mode: str = "local_external"
    hindsight_api_url: str = "http://127.0.0.1:8888"
    hindsight_bank_id: str = "my-project-staging"
    hindsight_api_key: str = ""
    cloud_approved: bool = False
    with_browser: bool = False
    acknowledgements: set[int] = field(default_factory=set)
    runtime: HermesRuntime | None = None
    discovery: object | None = None
    installer_receipt: DownloadReceipt | None = None
    backup_path: Path | None = None
    status: dict[str, object] = field(default_factory=dict)
    launched_from_hermes: bool = False


@dataclass(frozen=True)
class MenuLayout:
    rows: tuple[tuple[int, int, int], ...]
    # Each tuple: (item_index, first_y, last_y)

    def item_at(self, y: int, x: int, *, left: int, right: int) -> int | None:
        if x < left or x > right:
            return None
        for index, first, last in self.rows:
            if first <= y <= last:
                return index
        return None


def menu_key_action(key: int, item_count: int, selected: int) -> tuple[str, int]:
    """Translate a key press into a menu action.

    This stays separate from curses so the controls are easy to test.
    """

    if item_count <= 0:
        return "none", 0
    if key in (ord("q"), ord("Q"), 27):
        return "quit", selected
    if key in (ord("b"), ord("B")):
        return "back", selected
    if key in (10, 13, ord(" ")):
        return "activate", selected
    if ord("1") <= key <= ord("9"):
        index = key - ord("1")
        if index < item_count:
            return "activate", index
        return "none", selected
    # Common curses values: KEY_UP=259, KEY_DOWN=258, KEY_LEFT=260, KEY_RIGHT=261.
    if key in (259, 260, ord("k"), ord("K")):
        return "move", (selected - 1) % item_count
    if key in (258, 261, ord("j"), ord("J"), 9):
        return "move", (selected + 1) % item_count
    return "none", selected


def wrap_lines(text: str, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        if not paragraph:
            lines.append("")
            continue
        lines.extend(
            textwrap.wrap(
                paragraph,
                width=max(10, width),
                replace_whitespace=False,
                drop_whitespace=True,
            )
            or [""]
        )
    return lines


def explain_dual_mode() -> tuple[str, ...]:
    return (
        "NORMAL TURN   -> HINDSIGHT only",
        "CHECKPOINT    -> HINDSIGHT + MNEMOSYNE",
        "FAILOVER      -> bounded MNEMOSYNE checkpoints",
        "MERGED RECALL -> prohibited",
    )


def acknowledgement_items(state: DualSetupState) -> tuple[str, ...]:
    remote = bool(state.hindsight_api_url) and not is_local_endpoint(state.hindsight_api_url)
    transmission = (
        "Sanitized memory is sent off-device to the displayed Hindsight endpoint; "
        "raw tool messages remain disabled."
        if remote
        else "The selected Hindsight endpoint is local to this host; raw tool messages "
        "remain disabled."
    )
    return (
        "Hindsight is the only automatic memory authority.",
        "Mnemosyne receives verified checkpoints, not every turn.",
        "Existing Hindsight memories are preserved; no migration runs.",
        transmission,
    )


class SetupCancelled(ConfigurationError):
    pass


class DualSetupApp:
    def __init__(self, state: DualSetupState, *, mouse: bool = True) -> None:
        self.state = state
        self.mouse_requested = mouse
        self.curses: Any = None
        self.stdscr: Any = None
        self.frame = 0
        self.log_lines: list[str] = []
        self.log_path: Path | None = None
        self._temp_dir: Path | None = None

    # ------------------------------------------------------------------
    # Public entry
    # ------------------------------------------------------------------
    def run(self) -> int:
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ConfigurationError(
                "The Dual Memory Router setup UI requires an interactive terminal. "
                "Use the documented adopt/provider CLI commands for automation."
            )
        try:
            import curses
        except ImportError as exc:  # pragma: no cover - platform boundary
            raise ConfigurationError(
                "Python curses support is unavailable. Use Linux, macOS, or WSL, "
                "or use the non-interactive CLI setup commands."
            ) from exc
        self.curses = curses
        return curses.wrapper(self._main)

    # ------------------------------------------------------------------
    # Rendering primitives
    # ------------------------------------------------------------------
    def _safe_add(self, y: int, x: int, text: str, attr: int = 0) -> None:
        assert self.stdscr is not None
        height, width = self.stdscr.getmaxyx()
        if y < 0 or y >= height or x >= width:
            return
        clipped = text[: max(0, width - x - 1)]
        try:
            self.stdscr.addstr(y, x, clipped, attr)
        except self.curses.error:
            pass

    def _draw_chrome(self, step: str, *, footer: str = KEY_HELP) -> tuple[int, int]:
        assert self.stdscr is not None
        curses = self.curses
        self.stdscr.erase()
        height, width = self.stdscr.getmaxyx()
        if height < MIN_HEIGHT or width < MIN_WIDTH:
            message = f"Terminal too small: {width}x{height}; need {MIN_WIDTH}x{MIN_HEIGHT}"
            self._safe_add(max(0, height // 2), max(0, (width - len(message)) // 2), message)
            self._safe_add(max(0, height // 2 + 2), 2, "Resize the terminal, then press any key.")
            self.stdscr.refresh()
            self.stdscr.getch()
            return self._draw_chrome(step, footer=footer)

        top = f" {BRAND} // {SUBTITLE} "
        self._safe_add(0, 0, "─" * (width - 1), curses.A_DIM)
        self._safe_add(1, 2, top, curses.A_BOLD)
        right = f" {step} "
        self._safe_add(1, max(2, width - len(right) - 3), right, curses.A_REVERSE)
        self._safe_add(2, 0, "─" * (width - 1), curses.A_DIM)

        frame = PACMAN_FRAMES[self.frame % len(PACMAN_FRAMES)]
        self.frame += 1
        self._safe_add(height - 3, 2, frame, curses.A_BOLD)
        self._safe_add(height - 2, 0, "─" * (width - 1), curses.A_DIM)
        self._safe_add(height - 1, 2, footer, curses.A_DIM)
        return height, width

    def _draw_title(self, y: int, title: str, body: str = "") -> int:
        assert self.stdscr is not None
        _, width = self.stdscr.getmaxyx()
        self._safe_add(y, 4, title, self.curses.A_BOLD)
        y += 2
        for line in wrap_lines(body, width - 10):
            self._safe_add(y, 4, line)
            y += 1
        return y

    def _set_cursor(self, visible: bool) -> None:
        try:
            self.curses.curs_set(1 if visible else 0)
        except (self.curses.error, AttributeError):
            pass

    def _wait_key(self, timeout_ms: int = 120) -> int:
        assert self.stdscr is not None
        self.stdscr.timeout(timeout_ms)
        key = self.stdscr.getch()
        self.stdscr.timeout(-1)
        return int(key)

    def _enable_mouse(self) -> None:
        if not self.mouse_requested:
            return
        try:
            self.curses.mousemask(self.curses.ALL_MOUSE_EVENTS)
            self.curses.mouseinterval(120)
            # xterm mouse reporting; harmless when unsupported.
            sys.stdout.write("\x1b[?1000h\x1b[?1006h")
            sys.stdout.flush()
        except Exception:
            self.mouse_requested = False

    def _disable_mouse(self) -> None:
        if self.mouse_requested:
            try:
                sys.stdout.write("\x1b[?1000l\x1b[?1006l")
                sys.stdout.flush()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Widgets
    # ------------------------------------------------------------------
    def _menu(
        self,
        step: str,
        title: str,
        body: str,
        items: Sequence[MenuItem],
        *,
        default: int = 0,
        allow_back: bool = True,
    ) -> int:
        assert self.stdscr is not None
        selected = max(0, min(default, len(items) - 1))
        while True:
            height, width = self._draw_chrome(step)
            y = self._draw_title(4, title, body)
            y += 1
            rows: list[tuple[int, int, int]] = []
            for index, item in enumerate(items):
                attr = self.curses.A_REVERSE if index == selected else 0
                if not item.enabled:
                    attr |= self.curses.A_DIM
                marker = ">" if index == selected else " "
                line = f" {index + 1}. {marker} {item.title} "
                self._safe_add(y, 6, line, attr)
                first = y
                y += 1
                if item.description:
                    for wrapped in wrap_lines(item.description, width - 18):
                        self._safe_add(y, 12, wrapped, self.curses.A_DIM)
                        y += 1
                rows.append((index, first, y - 1))
                y += 1
            layout = MenuLayout(tuple(rows))
            self.stdscr.refresh()
            key = self._wait_key()
            if key == -1:
                continue
            if key == self.curses.KEY_MOUSE and self.mouse_requested:
                try:
                    _id, x, mouse_y, _z, state = self.curses.getmouse()
                except self.curses.error:
                    continue
                clicked_index = layout.item_at(mouse_y, x, left=4, right=width - 4)
                if clicked_index is not None:
                    selected = clicked_index
                    if state & (
                        self.curses.BUTTON1_CLICKED
                        | self.curses.BUTTON1_DOUBLE_CLICKED
                        | self.curses.BUTTON1_RELEASED
                    ):
                        if items[selected].enabled:
                            return selected
                continue
            action, candidate = menu_key_action(key, len(items), selected)
            if action == "quit":
                raise SetupCancelled("Setup cancelled; no changes were applied")
            if action == "back":
                if allow_back:
                    return -1
                continue
            if action == "move":
                selected = candidate
                continue
            if action == "activate":
                selected = candidate
                if items[selected].enabled:
                    return selected

    def _acknowledgements(self) -> bool:
        items = acknowledgement_items(self.state)
        selected = 0
        while True:
            height, width = self._draw_chrome("5 / 7  TRUST & PRIVACY")
            y = self._draw_title(
                4,
                "Review the strict policy",
                "Toggle every statement with SPACE or a mouse click. The installer "
                "will not continue until the data flow is understood.",
            )
            y += 1
            rows: list[tuple[int, int, int]] = []
            for index, text in enumerate(items):
                checked = index in self.state.acknowledgements
                box = "[x]" if checked else "[ ]"
                attr = self.curses.A_REVERSE if index == selected else 0
                self._safe_add(y, 6, f" {index + 1}. {box} {text} ", attr)
                rows.append((index, y, y))
                y += 2
            ready = len(self.state.acknowledgements) == len(items)
            status = "ENTER continue" if ready else "Check all four statements to continue"
            self._safe_add(
                height - 5, 4, status, self.curses.A_BOLD if ready else self.curses.A_DIM
            )
            self.stdscr.refresh()
            key = self._wait_key()
            if key == -1:
                continue
            if key == self.curses.KEY_MOUSE and self.mouse_requested:
                try:
                    _id, x, mouse_y, _z, event = self.curses.getmouse()
                except self.curses.error:
                    continue
                clicked_index = MenuLayout(tuple(rows)).item_at(mouse_y, x, left=4, right=width - 4)
                if clicked_index is not None and event & (
                    self.curses.BUTTON1_CLICKED
                    | self.curses.BUTTON1_RELEASED
                    | self.curses.BUTTON1_DOUBLE_CLICKED
                ):
                    selected = clicked_index
                    self._toggle_ack(clicked_index)
                continue
            if ord("1") <= key <= ord("4"):
                selected = key - ord("1")
                self._toggle_ack(selected)
            elif key in (259, 260, ord("k"), ord("K")):
                selected = (selected - 1) % len(items)
            elif key in (258, 261, ord("j"), ord("J"), 9):
                selected = (selected + 1) % len(items)
            elif key == ord(" "):
                self._toggle_ack(selected)
            elif key in (10, 13) and ready:
                return True
            elif key in (ord("b"), ord("B")):
                return False
            elif key in (ord("q"), ord("Q"), 27):
                raise SetupCancelled("Setup cancelled; no changes were applied")

    def _toggle_ack(self, index: int) -> None:
        if index in self.state.acknowledgements:
            self.state.acknowledgements.remove(index)
        else:
            self.state.acknowledgements.add(index)

    def _text_input(
        self,
        step: str,
        title: str,
        prompt: str,
        default: str,
        *,
        secret: bool = False,
        validator: Callable[[str], str | None] | None = None,
    ) -> str | None:
        assert self.stdscr is not None
        value = default
        cursor = len(value)
        error = ""
        self._set_cursor(True)
        while True:
            height, width = self._draw_chrome(step)
            y = self._draw_title(4, title, prompt)
            y += 2
            display = "*" * len(value) if secret else value
            field_width = max(20, width - 14)
            visible = display[max(0, cursor - field_width + 1) :]
            self._safe_add(y, 6, " " * field_width, self.curses.A_REVERSE)
            self._safe_add(y, 6, visible, self.curses.A_REVERSE)
            self._safe_add(y + 2, 6, "ENTER save   ESC back   CTRL+U clear", self.curses.A_DIM)
            if error:
                self._safe_add(y + 4, 6, error, self.curses.A_BOLD)
            self.stdscr.move(y, min(width - 2, 6 + len(visible)))
            self.stdscr.refresh()
            key = self.stdscr.get_wch()
            if isinstance(key, str):
                if key in ("\n", "\r"):
                    candidate = value.strip()
                    message = validator(candidate) if validator else None
                    if message:
                        error = message
                        continue
                    self._set_cursor(False)
                    return candidate
                if key in ("\x1b",):
                    self._set_cursor(False)
                    return None
                if key in ("\x15",):
                    value = ""
                    cursor = 0
                    continue
                if key in ("\x7f", "\b"):
                    if cursor > 0:
                        value = value[: cursor - 1] + value[cursor:]
                        cursor -= 1
                    continue
                if key.isprintable() and len(value) < 512:
                    value = value[:cursor] + key + value[cursor:]
                    cursor += len(key)
                    error = ""
            else:
                if key == self.curses.KEY_LEFT:
                    cursor = max(0, cursor - 1)
                elif key == self.curses.KEY_RIGHT:
                    cursor = min(len(value), cursor + 1)
                elif key == self.curses.KEY_HOME:
                    cursor = 0
                elif key == self.curses.KEY_END:
                    cursor = len(value)
                elif key in (self.curses.KEY_BACKSPACE, 127):
                    if cursor > 0:
                        value = value[: cursor - 1] + value[cursor:]
                        cursor -= 1

    def _show_info(
        self,
        step: str,
        title: str,
        lines: Sequence[str],
        *,
        continue_label: str = "ENTER continue",
        allow_back: bool = True,
    ) -> bool:
        while True:
            height, width = self._draw_chrome(step)
            y = self._draw_title(4, title)
            y += 1
            for raw in lines:
                for line in wrap_lines(raw, width - 10):
                    if y >= height - 5:
                        break
                    self._safe_add(y, 4, line)
                    y += 1
            self._safe_add(height - 5, 4, continue_label, self.curses.A_BOLD)
            self.stdscr.refresh()
            key = self._wait_key()
            if key == -1:
                continue
            if key == self.curses.KEY_MOUSE and self.mouse_requested:
                try:
                    _id, mouse_x, mouse_y, _z, event = self.curses.getmouse()
                except self.curses.error:
                    continue
                if mouse_y >= height - 6 and event & (
                    self.curses.BUTTON1_CLICKED
                    | self.curses.BUTTON1_RELEASED
                    | self.curses.BUTTON1_DOUBLE_CLICKED
                ):
                    return True
                continue
            if key in (10, 13, ord(" ")):
                return True
            if allow_back and key in (ord("b"), ord("B")):
                return False
            if key in (ord("q"), ord("Q"), 27):
                raise SetupCancelled("Setup cancelled; no changes were applied")

    # ------------------------------------------------------------------
    # Progress/log screen
    # ------------------------------------------------------------------
    def _run_task(
        self, step: str, title: str, task: Callable[[Callable[[str], None]], None]
    ) -> None:
        events: queue.Queue[tuple[str, object]] = queue.Queue()
        logs: list[str] = []

        def emit(line: str) -> None:
            clean = line.replace("\r", "").rstrip()
            if not clean:
                return
            events.put(("log", clean))
            if self.log_path:
                with self.log_path.open("a", encoding="utf-8") as handle:
                    handle.write(clean + "\n")

        def worker() -> None:
            try:
                task(emit)
            except BaseException as exc:
                events.put(("error", exc))
            else:
                events.put(("done", None))

        thread = threading.Thread(target=worker, daemon=True, name="hmr-dual-setup")
        thread.start()
        done = False
        error: BaseException | None = None
        while not done:
            while True:
                try:
                    kind, payload = events.get_nowait()
                except queue.Empty:
                    break
                if kind == "log":
                    logs.append(str(payload))
                    logs[:] = logs[-200:]
                elif kind == "error":
                    error = (
                        payload
                        if isinstance(payload, BaseException)
                        else RuntimeError(str(payload))
                    )
                    done = True
                elif kind == "done":
                    done = True
            height, width = self._draw_chrome(
                step,
                footer="Setup is running; output is logged. Do not close the terminal.",
            )
            y = self._draw_title(
                4, title, "The Pac-Man line advances while the current operation is active."
            )
            y += 1
            available = max(4, height - y - 5)
            for line in logs[-available:]:
                self._safe_add(y, 4, line, self.curses.A_DIM)
                y += 1
            self.stdscr.refresh()
            self._wait_key(100)
        thread.join(timeout=1)
        if error:
            raise error

    # ------------------------------------------------------------------
    # Flow
    # ------------------------------------------------------------------
    def _main(self, stdscr: Any) -> int:
        self.stdscr = stdscr
        curses = self.curses
        self._set_cursor(False)
        stdscr.keypad(True)
        self._enable_mouse()
        self._temp_dir = make_temp_dir("hmr-dual-setup-")
        logs = self.state.hermes_home / "memory-router" / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        try:
            logs.chmod(0o700)
        except OSError:
            pass
        self.log_path = logs / f"setup-{int(time.time())}.log"
        self.log_path.touch(mode=0o600, exist_ok=False)

        try:
            self._welcome()
            self._scan_and_ensure_hermes()
            self._identity()
            self._hindsight()
            if not self._acknowledgements():
                self._hindsight()
                if not self._acknowledgements():
                    raise SetupCancelled("Setup cancelled; no changes were applied")
            self._review()
            self._apply()
            self._complete()
            return 0
        finally:
            self._disable_mouse()
            if self._temp_dir:
                shutil.rmtree(self._temp_dir, ignore_errors=True)

    def _welcome(self) -> None:
        lines = [
            "One Hermes memory provider. Two deliberately different roles.",
            "",
            *explain_dual_mode(),
            "",
            "The router never activates itself merely because a package exists. It does not "
            "copy old Hindsight memories, merge both recall sets, patch Hermes, or expose both "
            "providers' full administrative tool inventories.",
            "",
            "This interface is monochrome and dependency-free. Mouse support is enabled where "
            "the terminal exposes it; number keys, arrows, SPACE, and ENTER always work.",
        ]
        self._show_info("1 / 7  INTRO", "Understand dual mode", lines, allow_back=False)

    def _scan_and_ensure_hermes(self) -> None:
        self.state.discovery = discover(self.state.hermes_home)
        self.state.runtime = find_hermes_runtime(self.state.hermes_home)
        if self.state.runtime:
            lines = [
                "Hermes runtime detected.",
                f"Command: {self.state.runtime.command}",
                f"Python:  {self.state.runtime.python}",
                "The installer will not reinstall or replace Hermes.",
            ]
            self._show_info("2 / 7  SYSTEM", "Hermes detected", lines, allow_back=False)
            return

        choice = self._menu(
            "2 / 7  SYSTEM",
            "Hermes is not installed",
            "The router can install Hermes through Nous Research's official HTTPS "
            "installer. The default skips Playwright and Chromium to keep the first "
            "install small. Choose browser automation only when you need browser tools. "
            "The upstream script is saved to an owner-only temporary file, checked for "
            "expected identity markers, hashed, shown for review, and then executed.",
            (
                MenuItem(
                    "Install lightweight Hermes",
                    "Skips Playwright and Chromium. Browser tools can be added later.",
                ),
                MenuItem(
                    "Install Hermes with browser automation",
                    "Includes the upstream browser-tool dependencies.",
                ),
                MenuItem("Exit without changes", "Install Hermes yourself and rerun setup."),
            ),
            default=1 if self.state.with_browser else 0,
            allow_back=False,
        )
        if choice == 2:
            raise SetupCancelled("Hermes installation was declined; no changes were applied")
        self.state.with_browser = choice == 1

        assert self._temp_dir is not None
        installer = self._temp_dir / "hermes-install.sh"

        def download_task(log: Callable[[str], None]) -> None:
            log(f"Downloading: {OFFICIAL_HERMES_INSTALLER}")
            receipt = download_https(
                OFFICIAL_HERMES_INSTALLER,
                installer,
                max_bytes=2_000_000,
            )
            from .bootstrap import validate_hermes_installer

            validate_hermes_installer(installer)
            self.state.installer_receipt = receipt
            log(f"SHA-256: {receipt.sha256}")
            log(f"Bytes: {receipt.bytes}")

        self._run_task("2 / 7  SYSTEM", "Download official Hermes installer", download_task)
        receipt = self.state.installer_receipt
        assert receipt is not None
        approved = self._show_info(
            "2 / 7  SYSTEM",
            "Approve the official Hermes installer",
            (
                f"Source:  {receipt.url}",
                f"SHA-256: {receipt.sha256}",
                f"Size:    {receipt.bytes} bytes",
                "",
                "Browser automation: "
                + ("included" if self.state.with_browser else "not included"),
                "",
                "The Dual Memory Router bootstrap never invokes sudo. The upstream Hermes "
                "installer may request OS-package privileges on some systems; its output is "
                "captured in the setup log. Press ENTER to run it or B to cancel.",
            ),
            continue_label="ENTER run official installer   B cancel",
            allow_back=True,
        )
        if not approved:
            raise SetupCancelled("Hermes installation was not approved")

        def install_task(log: Callable[[str], None]) -> None:
            self.state.runtime = install_official_hermes(
                self.state.hermes_home,
                installer=installer,
                with_browser=self.state.with_browser,
                log=log,
            )
            log("Hermes runtime located successfully")

        self._run_task("2 / 7  SYSTEM", "Install Hermes Agent", install_task)

    def _identity(self) -> None:
        while True:
            namespace = self._text_input(
                "3 / 7  IDENTITY",
                "Project namespace",
                "A stable project boundary used in the router database and both bank names.",
                self.state.namespace,
                validator=self._validate_name,
            )
            if namespace is None:
                continue
            self.state.namespace = namespace
            environment = self._text_input(
                "3 / 7  IDENTITY",
                "Environment",
                "Use a physical deployment boundary such as staging or production.",
                self.state.environment,
                validator=self._validate_name,
            )
            if environment is None:
                continue
            self.state.environment = environment
            self.state.hindsight_bank_id = f"{namespace}-{environment}"
            return

    def _hindsight(self) -> None:
        state = discover(self.state.hermes_home)
        detected = bool(state.hindsight_api_url and state.hindsight_bank_id)
        items = [
            MenuItem(
                "Reuse detected Hindsight connection",
                (
                    f"{state.hindsight_api_url} / bank {state.hindsight_bank_id}"
                    if detected
                    else "No complete existing Hindsight connection was detected."
                ),
                enabled=detected,
            ),
            MenuItem(
                "Connect to self-hosted Hindsight",
                "Use an already-running external Hindsight API. The router does not manage its process.",
            ),
            MenuItem(
                "Connect to Hindsight Cloud",
                "Sanitized automatic memory leaves this machine over HTTPS; raw tool messages stay disabled.",
            ),
        ]
        default = 0 if detected else 1
        choice = self._menu(
            "4 / 7  HINDSIGHT",
            "Choose the Hindsight authority",
            "Hindsight is always the only automatic retention, recall, and reflection backend. "
            "Mnemosyne remains a verified-checkpoint ledger.",
            items,
            default=default,
        )
        if choice == -1:
            return self._identity()
        if choice == 0:
            self.state.hindsight_api_url = str(state.hindsight_api_url)
            self.state.hindsight_bank_id = str(state.hindsight_bank_id)
            self.state.hindsight_mode = (
                state.hindsight_mode
                if state.hindsight_mode in {"cloud", "local_external"}
                else ("cloud" if state.hindsight_is_cloud else "local_external")
            )
            return
        if choice == 1:
            self.state.hindsight_mode = "local_external"
            url = self._text_input(
                "4 / 7  HINDSIGHT",
                "Self-hosted Hindsight API",
                "Enter the external API URL. The router does not manage the "
                "embedded Hindsight process.",
                self.state.hindsight_api_url or "http://127.0.0.1:8888",
                validator=self._validate_url,
            )
            if url is None:
                return self._hindsight()
            self.state.hindsight_api_url = url
            key = self._text_input(
                "4 / 7  HINDSIGHT",
                "Self-hosted API key (optional)",
                "Leave blank when the API has no authentication. A supplied key is masked "
                "and stored only in $HERMES_HOME/.env with owner-only permissions.",
                self.state.hindsight_api_key,
                secret=True,
            )
            if key is None:
                return self._hindsight()
            self.state.hindsight_api_key = key
        else:
            self.state.hindsight_mode = "cloud"
            url = self._text_input(
                "4 / 7  HINDSIGHT",
                "Hindsight Cloud API",
                "Confirm the HTTPS endpoint. Cloud activation requires explicit acknowledgement.",
                "https://api.hindsight.vectorize.io",
                validator=lambda value: self._validate_url(value, require_https=True),
            )
            if url is None:
                return self._hindsight()
            self.state.hindsight_api_url = url
            key = self._text_input(
                "4 / 7  HINDSIGHT",
                "Hindsight API key",
                "The key is masked and written only to $HERMES_HOME/.env with owner-only permissions.",
                "",
                secret=True,
                validator=lambda value: None if value else "An API key is required for cloud mode.",
            )
            if key is None:
                return self._hindsight()
            self.state.hindsight_api_key = key
            self.state.cloud_approved = True

        bank = self._text_input(
            "4 / 7  HINDSIGHT",
            "Hindsight bank",
            "Use a bank name unique to this project and environment.",
            self.state.hindsight_bank_id,
            validator=self._validate_name,
        )
        if bank is None:
            return self._hindsight()
        self.state.hindsight_bank_id = bank

    @staticmethod
    def _validate_name(value: str) -> str | None:
        if _NAME_RE.fullmatch(value):
            return None
        return "Use letters, numbers, dot, dash, or underscore."

    @staticmethod
    def _validate_url(value: str, require_https: bool = False) -> str | None:
        if require_https and not value.startswith("https://"):
            return "Cloud mode requires an HTTPS endpoint."
        if not value.startswith(("http://", "https://")):
            return "Enter an http:// or https:// URL."
        return None

    def _review(self) -> None:
        mode = (
            "Hindsight Cloud" if self.state.hindsight_mode == "cloud" else "self-hosted Hindsight"
        )
        lines = [
            f"Hermes home:       {self.state.hermes_home}",
            f"Namespace:         {self.state.namespace}",
            f"Environment:       {self.state.environment}",
            f"Primary:           {mode}",
            f"Hindsight API:     {self.state.hindsight_api_url}",
            f"Hindsight bank:    {self.state.hindsight_bank_id}",
            f"Mnemosyne bank:    {self.state.namespace}-{self.state.environment}-checkpoints",
            "",
            *explain_dual_mode(),
            "",
            "Actions:",
            "  1. Install router and bounded Mnemosyne dependency into Hermes' own Python.",
            "  2. Install one Hermes memory-provider entry.",
            "  3. Back up Hermes, Hindsight, router, and secret configuration.",
            "  4. Write strict profile-scoped configuration.",
            "  5. Verify both backends before activating the router.",
            "  6. Activate chronalyn as the sole external provider.",
            "",
            "No historical memory migration. No telemetry. No raw tool-message retention. No core patching.",
        ]
        confirmed = self._show_info(
            "6 / 7  REVIEW",
            "Review the complete installation plan",
            lines,
            continue_label="ENTER install dual mode   B revise",
            allow_back=True,
        )
        if not confirmed:
            self.state.acknowledgements.clear()
            self._hindsight()
            if not self._acknowledgements():
                raise SetupCancelled("Setup cancelled; no changes were applied")
            return self._review()

    def _apply(self) -> None:
        assert self.state.runtime is not None
        runtime = self.state.runtime
        backup: Path | None = None

        def apply_task(log: Callable[[str], None]) -> None:
            nonlocal backup
            log("Installing the router in Hermes' Python environment")
            install_router_into_runtime(
                runtime,
                package_source=self.state.package_source,
                dual=True,
                hermes_home=self.state.hermes_home,
                log=log,
            )
            log("Creating rollback backup before plugin or configuration changes")
            backup = backup_configuration(
                self.state.hermes_home,
                reason=f"{identity.BRAND} {identity.RELEASE_NAME} guided setup",
            )
            self.state.backup_path = backup
            try:
                log("Installing the Hermes memory-provider entry")
                install_plugin_entry(
                    runtime,
                    hermes_home=self.state.hermes_home,
                    log=log,
                )
                write_hindsight_profile_config(
                    self.state.hermes_home,
                    mode=self.state.hindsight_mode,
                    api_url=self.state.hindsight_api_url,
                    bank_id=self.state.hindsight_bank_id,
                )
                if self.state.hindsight_api_key:
                    write_secret_env(
                        self.state.hermes_home,
                        {"HINDSIGHT_API_KEY": self.state.hindsight_api_key},
                    )
                    # The gateway will load $HERMES_HOME/.env on restart. The
                    # setup process also needs the key for its pre-activation
                    # health check without echoing it into logs.
                    import os

                    os.environ["HINDSIGHT_API_KEY"] = self.state.hindsight_api_key

                config = new_config(
                    namespace=self.state.namespace,
                    environment=self.state.environment,
                    policy=HINDSIGHT_MNEMOSYNE,
                )
                config.hindsight.api_url = self.state.hindsight_api_url
                config.hindsight.bank_id = self.state.hindsight_bank_id
                config.hindsight.tags = [
                    f"project:{self.state.namespace}",
                    f"environment:{self.state.environment}",
                ]
                config.mnemosyne.bank = (
                    f"{self.state.namespace}-{self.state.environment}-checkpoints"
                )
                config.redaction.mode = (
                    "reject" if self.state.environment.lower() == "production" else "redact"
                )
                config.apply_policy_defaults()
                config.validate()
                write_config(
                    self.state.hermes_home / "memory-router" / "config.json",
                    config,
                )

                log("Verifying Hindsight and Mnemosyne inside Hermes' Python runtime")
                self.state.status = verify_router_in_runtime(
                    runtime,
                    hermes_home=self.state.hermes_home,
                )
                backend_payload = self.state.status.get("backends", {})
                backends = backend_payload if isinstance(backend_payload, dict) else {}
                unhealthy = [
                    name
                    for name, payload in backends.items()
                    if isinstance(payload, dict) and not bool(payload.get("ok"))
                ]
                if unhealthy:
                    raise ConfigurationError("Backend verification failed: " + ", ".join(unhealthy))

                log(f"Activating {identity.PROVIDER_ID} as the sole external provider")
                set_active_provider_with_hermes(identity.PROVIDER_ID, self.state.hermes_home)
                final = discover(self.state.hermes_home)
                if final.active_providers != (identity.PROVIDER_ID,):
                    raise ConfigurationError(
                        f"Hermes did not activate {identity.PROVIDER_ID} as the sole "
                        "external memory provider"
                    )
                command_link = link_router_command(runtime)
                log(f"{identity.BRAND} command linked at {command_link}")
                log("Strict dual mode activated")
            except BaseException:
                if backup is not None:
                    log("Setup failed; restoring the pre-change configuration")
                    restore_backup(self.state.hermes_home, backup)
                raise

        self._run_task("7 / 7  INSTALL", "Install and verify strict dual mode", apply_task)

    def _complete(self) -> None:
        backup = str(self.state.backup_path or "not created")
        log_path = str(self.log_path or "")
        lines = [
            "STRICT DUAL MODE IS ACTIVE",
            "",
            "Hindsight:  automatic memory / recall / reflect",
            "Mnemosyne:  verified checkpoints / bounded fallback",
            f"Backup:     {backup}",
            f"Setup log:  {log_path}",
            "",
            "Next checks:",
            "  hermes setup            # configure model/gateway if this was a fresh Hermes install",
            "  hermes memory status",
        ]
        if not self.state.launched_from_hermes:
            lines.append(f"  {identity.CLI_COMMAND} status")
        lines.extend(
            [
                "  ./scripts/live-smoke-test.sh",
                "",
                "Rollback never deletes memory data:",
                f"  {identity.CLI_COMMAND} rollback --yes",
            ]
        )
        self._show_info(
            "COMPLETE",
            f"{identity.BRAND} {identity.RELEASE_NAME} is ready",
            lines,
            continue_label="ENTER exit setup",
            allow_back=False,
        )


def run_dual_setup(
    *,
    hermes_home: Path,
    package_source: str = "",
    mouse: bool = True,
    with_browser: bool = False,
    launched_from_hermes: bool = False,
) -> int:
    state = DualSetupState(
        hermes_home=hermes_home.expanduser(),
        package_source=package_source,
        with_browser=with_browser,
        launched_from_hermes=launched_from_hermes,
    )
    return DualSetupApp(state, mouse=mouse).run()
