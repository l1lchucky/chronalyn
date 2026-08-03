#!/usr/bin/env bash
set -euo pipefail

hermes memory off || true
hermes-memory-router uninstall-plugin || true
python -m pip uninstall -y hermes-memory-router || true

echo "Removed the plugin entry and Python package."
echo "Router state, Mnemosyne data, and Hindsight data were preserved."
