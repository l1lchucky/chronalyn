#!/usr/bin/env bash
set -euo pipefail

hermes_home="${HERMES_HOME:-$HOME/.hermes}"
marker="HMR-SMOKE-$(date +%s)"

hermes-memory-router validate >/dev/null
hermes-memory-router status
printf 'Marker for interactive Hermes test: %s\n' "$marker"

cat <<EOF
In Hermes, run:
1. memory_router_checkpoint with marker $marker and verified evidence.
2. memory_router_recall for $marker.
3. memory_router_status.
4. memory_router_forget using the returned record ID.
5. memory_router_retry if any delivery failed.
EOF
