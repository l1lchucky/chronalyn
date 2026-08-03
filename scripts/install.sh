#!/usr/bin/env bash
set -euo pipefail
umask 077

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
hermes_home="${HERMES_HOME:-$HOME/.hermes}"

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
  fi
  for candidate in \
    "$hermes_home/hermes-agent/.venv/bin/python" \
    "$hermes_home/hermes-agent/venv/bin/python" \
    "/usr/local/lib/hermes-agent/.venv/bin/python" \
    "/usr/local/lib/hermes-agent/venv/bin/python"; do
    if [ -x "$candidate" ]; then printf '%s\n' "$candidate"; return 0; fi
  done
  return 1
}

hermes_python="$(find_hermes_python || true)"
if [ -z "$hermes_python" ]; then
  echo "ERROR: Hermes is not installed or its Python runtime could not be found." >&2
  echo "Use ./scripts/install-dual.sh to install Hermes and the strict dual router." >&2
  exit 2
fi

if "$hermes_python" -m pip --version >/dev/null 2>&1; then
  "$hermes_python" -m pip install --upgrade "$repo_dir"
elif [ -x "$hermes_home/bin/uv" ]; then
  "$hermes_home/bin/uv" pip install --python "$hermes_python" --upgrade "$repo_dir"
elif command -v uv >/dev/null 2>&1; then
  uv pip install --python "$hermes_python" --upgrade "$repo_dir"
else
  echo "ERROR: Hermes runtime has neither pip nor managed uv." >&2
  exit 2
fi

"$hermes_python" -m hermes_memory_router.cli \
  --hermes-home "$hermes_home" --no-animation install-plugin

hermes_command="$(command -v hermes 2>/dev/null || true)"
router_entry="$(dirname "$hermes_python")/hermes-memory-router"
if [ -n "$hermes_command" ] && [ -x "$router_entry" ]; then
  destination="$(dirname "$hermes_command")/hermes-memory-router"
  if [ ! -e "$destination" ] || [ -L "$destination" ]; then
    ln -sfn "$router_entry" "$destination"
  fi
fi

echo "Installed Hermes Memory Router into: $hermes_python"
echo "Plugin entry: $hermes_home/plugins/memory/hermes_memory_router"
echo
echo "Next:"
echo "  hermes-memory-router setup-dual"
