#!/usr/bin/env bash
set -euo pipefail
umask 077

VERSION="0.2.0-beta.1"
PY_VERSION="0.2.0b1"
TAG="v${VERSION}"
REPO="l1lchucky/hermes-memory-router"
WHEEL="hermes_memory_router-${PY_VERSION}-py3-none-any.whl"
RELEASE_BASE="https://github.com/${REPO}/releases/download/${TAG}"
CHECKSUMS="SHA256SUMS-hermes-memory-router-${VERSION}.txt"
HERMES_INSTALLER_URL="https://hermes-agent.nousresearch.com/install.sh"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
ALLOW_ROOT=false
MOUSE=true
WITH_BROWSER=false
LOCAL_WHEEL=""
KEEP_DOWNLOADS=false

usage() {
  cat <<EOF
Dual Memory Router ${VERSION} installer

Usage: $0 [options]

Options:
  --hermes-home PATH  Hermes profile directory (default: $HERMES_HOME)
  --no-mouse          Disable mouse support in the full setup interface
  --with-browser      Include Playwright/Chromium if Hermes must be installed
  --allow-root        Permit execution as root after an explicit warning
  --wheel PATH        Use a local wheel instead of downloading the release asset
  --keep-downloads    Preserve downloaded files for inspection
  -h, --help          Show this help

This bootstrap never invokes sudo, never pipes a download directly into a shell,
and never enables telemetry. It verifies the release wheel, installs the
lightweight setup interface into an owner-only temporary directory, then hands
all configuration and activation decisions to the branded monochrome UI.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --hermes-home) HERMES_HOME="$2"; shift 2 ;;
    --no-mouse) MOUSE=false; shift ;;
    --with-browser) WITH_BROWSER=true; shift ;;
    --allow-root) ALLOW_ROOT=true; shift ;;
    --wheel) LOCAL_WHEEL="$2"; shift 2 ;;
    --keep-downloads) KEEP_DOWNLOADS=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ ! -t 0 ] && [ ! -r /dev/tty ]; then
  echo "ERROR: this safety-first installer requires an interactive terminal." >&2
  exit 2
fi

TEMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t hmr-dual)"
LOG_DIR="$HERMES_HOME/memory-router/logs"
mkdir -p "$LOG_DIR"
chmod 700 "$LOG_DIR" 2>/dev/null || true
BOOT_LOG="$LOG_DIR/bootstrap-$(date +%Y%m%dT%H%M%S).log"
touch "$BOOT_LOG"
chmod 600 "$BOOT_LOG" 2>/dev/null || true

cleanup() {
  if [ "$KEEP_DOWNLOADS" = true ]; then
    printf '\nDownloads preserved at: %s\n' "$TEMP_DIR"
  else
    rm -rf "$TEMP_DIR"
  fi
}
trap cleanup EXIT INT TERM

line() { printf '%*s\n' 72 '' | tr ' ' '─'; }
header() {
  clear 2>/dev/null || true
  line
  printf '  DUAL MEMORY ROUTER // STRICT SETUP %s\n' "$VERSION"
  printf '  HINDSIGHT PRIMARY + MNEMOSYNE CHECKPOINTS\n'
  line
}

ask_yes_no() {
  local prompt="$1" answer=""
  printf '%s [y/N] ' "$prompt" > /dev/tty
  IFS= read -r answer < /dev/tty || answer=""
  case "$answer" in y|Y|yes|YES|Yes) return 0 ;; *) return 1 ;; esac
}

pacman_run() {
  local label="$1" logfile="$2"
  shift 2
  : > "$logfile"
  ( "$@" < /dev/tty > "$logfile" 2>&1 ) &
  local pid=$! frame=0
  local frames=("C  * * * *" "<  * * *  " "C    * *  " "<      *  ")
  while kill -0 "$pid" 2>/dev/null; do
    printf '\r%-16s  %s' "${frames[$frame]}" "$label" > /dev/tty
    frame=$(( (frame + 1) % 4 ))
    sleep 0.12
  done
  local status=0
  wait "$pid" || status=$?
  printf '\r%-72s\r' ' ' > /dev/tty
  cat "$logfile" >> "$BOOT_LOG"
  if [ "$status" -ne 0 ]; then
    printf 'FAILED: %s\n' "$label" >&2
    tail -n 80 "$logfile" >&2 || true
    return "$status"
  fi
  printf '[ok] %s\n' "$label"
}

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    echo "ERROR: sha256sum or shasum is required." >&2
    exit 2
  fi
}

download() {
  local url="$1" destination="$2"
  curl --proto '=https' --tlsv1.2 --fail --location --silent --show-error \
    --connect-timeout 20 --max-time 600 "$url" -o "$destination"
  chmod 600 "$destination" 2>/dev/null || true
}

find_hermes_python() {
  local command_path resolved first candidate
  command_path="$(command -v hermes 2>/dev/null || true)"
  if [ -n "$command_path" ]; then
    resolved="$(readlink -f "$command_path" 2>/dev/null || realpath "$command_path" 2>/dev/null || printf '%s' "$command_path")"
    first="$(head -n 1 "$resolved" 2>/dev/null || true)"
    case "$first" in
      '#!'*)
        candidate="${first#\#!}"
        candidate="${candidate%% *}"
        if [ -x "$candidate" ]; then printf '%s\n' "$candidate"; return 0; fi
        ;;
    esac
    candidate="$(dirname "$resolved")/python"
    if [ -x "$candidate" ]; then printf '%s\n' "$candidate"; return 0; fi
  fi
  for candidate in \
    "$HERMES_HOME/hermes-agent/.venv/bin/python" \
    "$HERMES_HOME/hermes-agent/venv/bin/python" \
    "/usr/local/lib/hermes-agent/.venv/bin/python" \
    "/usr/local/lib/hermes-agent/venv/bin/python"; do
    if [ -x "$candidate" ]; then printf '%s\n' "$candidate"; return 0; fi
  done
  return 1
}

python_is_usable() {
  "$1" - <<'PY' >/dev/null 2>&1
import curses
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
}

find_bootstrap_python() {
  local candidate
  candidate="$(find_hermes_python || true)"
  if [ -n "$candidate" ] && python_is_usable "$candidate"; then
    printf '%s\n' "$candidate"
    return 0
  fi
  for candidate in "$(command -v python3 2>/dev/null || true)" "$(command -v python 2>/dev/null || true)"; do
    if [ -n "$candidate" ] && python_is_usable "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

trusted_uv() {
  local candidate
  for candidate in \
    "$HERMES_HOME/bin/uv" \
    "$(command -v uv 2>/dev/null || true)"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

install_temporary_ui() {
  local python="$1" site="$2" wheel="$3" uv=""
  mkdir -p "$site"
  if "$python" -m pip --version >/dev/null 2>&1; then
    "$python" -m pip install --disable-pip-version-check --no-deps --target "$site" --upgrade "$wheel"
    return
  fi
  uv="$(trusted_uv || true)"
  if [ -n "$uv" ]; then
    "$uv" pip install --no-deps --target "$site" --upgrade "$wheel"
    return
  fi
  echo "A Python 3.11+ runtime was found, but neither pip nor trusted uv is available." >&2
  return 1
}

install_hermes_fallback() {
  local installer="$TEMP_DIR/hermes-install.sh"
  pacman_run "Download official Hermes installer" "$TEMP_DIR/hermes-download.log" \
    download "$HERMES_INSTALLER_URL" "$installer"

  if [ "$(wc -c < "$installer" | tr -d ' ')" -lt 10000 ] \
    || ! grep -q 'Hermes Agent Installer' "$installer" \
    || ! grep -q 'https://github.com/NousResearch/hermes-agent.git' "$installer"; then
    echo "ERROR: downloaded Hermes installer failed identity checks." >&2
    exit 2
  fi
  local hermes_sha
  hermes_sha="$(sha256_file "$installer")"
  printf '\nOfficial Hermes installer SHA-256:\n  %s\n' "$hermes_sha"
  printf 'Saved temporarily at: %s\n' "$installer"
  if ! ask_yes_no "No suitable Python 3.11+curses runtime exists. Run the official Hermes installer to obtain one?"; then
    echo "Cancelled before Hermes installation."
    exit 0
  fi
  local hermes_args=(
    bash "$installer" --skip-setup --non-interactive --hermes-home "$HERMES_HOME"
  )
  if [ "$WITH_BROWSER" != true ]; then
    hermes_args+=(--skip-browser)
  fi
  pacman_run "Install Hermes Agent" "$TEMP_DIR/hermes-install.log" \
    "${hermes_args[@]}"
}

header
cat <<EOF

  A small verified launcher prepares the full Dual Memory Router interface.
  All provider, privacy, bank, backup, and activation decisions happen inside
  the monochrome UI—not in this shell bootstrap.

  The setup policy is fixed:

    NORMAL TURN   -> HINDSIGHT only
    CHECKPOINT    -> HINDSIGHT + MNEMOSYNE
    FAILOVER      -> bounded MNEMOSYNE checkpoints
    MERGED RECALL -> prohibited

  It does NOT:
  - pipe network content directly into bash;
  - invoke sudo itself;
  - patch Hermes core;
  - migrate historical memories;
  - enable telemetry or raw tool-message retention.

  Setup log: $BOOT_LOG
EOF

if [ "$(id -u)" -eq 0 ] && [ "$ALLOW_ROOT" != true ]; then
  printf '\nRoot execution changes Hermes installation paths and increases impact.\n' >&2
  printf 'Rerun with --allow-root only after reviewing this script.\n' >&2
  exit 2
fi

if ! ask_yes_no "Continue to the verified Dual Memory Router interface?"; then
  echo "Cancelled. No changes were applied."
  exit 0
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "ERROR: curl is required for HTTPS downloads." >&2
  exit 2
fi

if [ -n "$LOCAL_WHEEL" ]; then
  ROUTER_WHEEL_PATH="$(cd "$(dirname "$LOCAL_WHEEL")" && pwd)/$(basename "$LOCAL_WHEEL")"
  [ -f "$ROUTER_WHEEL_PATH" ] || { echo "ERROR: wheel not found: $ROUTER_WHEEL_PATH" >&2; exit 2; }
  printf '[ok] Local router wheel SHA-256: %s\n' "$(sha256_file "$ROUTER_WHEEL_PATH")"
else
  ROUTER_WHEEL_PATH="$TEMP_DIR/$WHEEL"
  SUMS_PATH="$TEMP_DIR/$CHECKSUMS"
  pacman_run "Download release checksums" "$TEMP_DIR/checksums-download.log" \
    download "$RELEASE_BASE/$CHECKSUMS" "$SUMS_PATH"
  pacman_run "Download router wheel" "$TEMP_DIR/wheel-download.log" \
    download "$RELEASE_BASE/$WHEEL" "$ROUTER_WHEEL_PATH"
  EXPECTED="$(awk -v file="$WHEEL" '$2 == file {print $1}' "$SUMS_PATH")"
  ACTUAL="$(sha256_file "$ROUTER_WHEEL_PATH")"
  if [ -z "$EXPECTED" ] || [ "$EXPECTED" != "$ACTUAL" ]; then
    echo "ERROR: router wheel checksum verification failed." >&2
    printf 'Expected: %s\nActual:   %s\n' "${EXPECTED:-missing}" "$ACTUAL" >&2
    exit 2
  fi
  printf '[ok] Router wheel SHA-256 verified: %s\n' "$ACTUAL"
  if command -v gh >/dev/null 2>&1; then
    if gh attestation verify "$ROUTER_WHEEL_PATH" --repo "$REPO" >> "$BOOT_LOG" 2>&1; then
      echo '[ok] GitHub build provenance attestation verified'
    else
      echo '[warn] GitHub attestation verification was unavailable or failed; checksum remains verified'
    fi
  else
    echo '[info] GitHub CLI not installed; provenance check skipped, checksum verified'
  fi
fi

BOOTSTRAP_PYTHON="$(find_bootstrap_python || true)"
if [ -z "$BOOTSTRAP_PYTHON" ]; then
  # A curses UI cannot run without Python. This is the only fallback path that
  # installs Hermes before the branded interface starts.
  install_hermes_fallback
  BOOTSTRAP_PYTHON="$(find_bootstrap_python || true)"
fi
if [ -z "$BOOTSTRAP_PYTHON" ]; then
  echo "ERROR: Python 3.11+ with curses is required to launch the setup interface." >&2
  exit 2
fi

SETUP_SITE="$TEMP_DIR/setup-site"
pacman_run "Prepare lightweight setup interface" "$TEMP_DIR/setup-ui-install.log" \
  install_temporary_ui "$BOOTSTRAP_PYTHON" "$SETUP_SITE" "$ROUTER_WHEEL_PATH"

TUI_ARGS=(
  "$BOOTSTRAP_PYTHON" -m hermes_memory_router.cli
  --hermes-home "$HERMES_HOME"
  setup-dual --package-source "$ROUTER_WHEEL_PATH"
)
if [ "$MOUSE" != true ]; then TUI_ARGS+=(--no-mouse); fi
if [ "$WITH_BROWSER" = true ]; then TUI_ARGS+=(--with-browser); fi

printf '\nLaunching the full Dual Memory Router interface...\n'
(
  cd "$TEMP_DIR"
  PYTHONPATH="$SETUP_SITE" PYTHONNOUSERSITE=1 PYTHONSAFEPATH=1 \
    "${TUI_ARGS[@]}" < /dev/tty > /dev/tty 2> /dev/tty
)
