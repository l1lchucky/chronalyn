#!/usr/bin/env bash
set -euo pipefail

hermes_home="${HERMES_HOME:-$HOME/.hermes}"
hermes_python=""
for candidate in \
  "$hermes_home/hermes-agent/venv/bin/python" \
  "/usr/local/lib/hermes-agent/venv/bin/python"; do
  if [ -x "$candidate" ]; then hermes_python="$candidate"; break; fi
done

hermes memory off 2>/dev/null || true
if [ -n "$hermes_python" ]; then
  "$hermes_python" -m hermes_memory_router.cli \
    --hermes-home "$hermes_home" --no-animation uninstall-plugin 2>/dev/null || true
  "$hermes_python" -m pip uninstall -y hermes-memory-router 2>/dev/null || true
fi

command_path="$(command -v hermes-memory-router 2>/dev/null || true)"
if [ -n "$command_path" ] && [ -L "$command_path" ]; then
  rm -f "$command_path"
fi

echo "Removed the router package and Hermes plugin entry."
echo "Preserved router state, Hindsight data, Mnemosyne data, backups, and logs."
