#!/usr/bin/env bash
set -euo pipefail

hermes_home="${HERMES_HOME:-$HOME/.hermes}"
hermes_python=""
for candidate in \
  "$hermes_home/hermes-agent/.venv/bin/python" \
  "$hermes_home/hermes-agent/venv/bin/python" \
  "/usr/local/lib/hermes-agent/.venv/bin/python" \
  "/usr/local/lib/hermes-agent/venv/bin/python"; do
  if [ -x "$candidate" ]; then hermes_python="$candidate"; break; fi
done

hermes memory off 2>/dev/null || true
if [ -n "$hermes_python" ]; then
  provider_removed=false
  packages_removed=false
  if "$hermes_python" -m chronalyn.cli \
    --hermes-home "$hermes_home" --no-animation uninstall-plugin; then
    provider_removed=true
  else
    echo "Could not remove Chronalyn Hermes provider entries." >&2
  fi
  # Uninstall the current distribution and the pre-rename one, if present.
  if "$hermes_python" -m pip uninstall -y chronalyn \
    && "$hermes_python" -m pip uninstall -y hermes-memory-router; then
    packages_removed=true
  else
    echo "Could not remove one or more Chronalyn distributions." >&2
  fi
  if [ "$provider_removed" = true ] && [ "$packages_removed" = true ]; then
    echo "Removed Chronalyn package and Hermes provider entries."
  else
    echo "Chronalyn removal was incomplete; package and provider entries may remain." >&2
  fi
else
  echo "Could not locate a Hermes Python environment; Chronalyn package and provider entries were not removed." >&2
fi

for command_name in chronalyn hermes-memory-router; do
  command_path="$(command -v "$command_name" 2>/dev/null || true)"
  if [ -n "$command_path" ] && [ -L "$command_path" ]; then
    rm -f "$command_path"
  fi
done

echo "Preserved router state, Hindsight data, Mnemosyne data, backups, and logs."
echo "Deleting data is a separate, explicit action; nothing was deleted here."
