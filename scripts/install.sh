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

"$hermes_python" -m chronalyn.cli \
  --hermes-home "$hermes_home" --no-animation install-plugin

hermes_command="$(command -v hermes 2>/dev/null || true)"
# Link both the new command and the deprecated alias when they exist.
for command_name in chronalyn hermes-memory-router; do
  router_entry="$(dirname "$hermes_python")/$command_name"
  if [ -n "$hermes_command" ] && [ -x "$router_entry" ]; then
    destination="$(dirname "$hermes_command")/$command_name"
    if [ ! -e "$destination" ] || [ -L "$destination" ]; then
      ln -sfn "$router_entry" "$destination"
    fi
  fi
done

echo "Installed Chronalyn into: $hermes_python"
echo "Provider entry: $hermes_home/plugins/chronalyn"
echo "Compatibility entry: $hermes_home/plugins/hermes_memory_router"
echo
echo "Next:"
echo "  chronalyn setup"
