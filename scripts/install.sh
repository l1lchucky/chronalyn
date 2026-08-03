#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python -m pip install "$repo_dir"
hermes-memory-router install-plugin

echo
echo "Installed the Python package and Hermes plugin entry."
echo "Create configuration:"
echo "  hermes-memory-router init --namespace my-project --environment staging"
echo "Then activate:"
echo "  hermes config set memory.provider hermes_memory_router"
