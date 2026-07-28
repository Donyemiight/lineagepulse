#!/usr/bin/env bash
# Bootstrap a fresh local DataHub with the nyc-taxi sample dataset.
#
# This is the path used by the demo runbook and the smoke test. It is
# idempotent: if DataHub is already running, it just verifies the
# connection and loads the dataset if it isn't loaded yet.

set -euo pipefail

echo "→ Checking prerequisites"
for cmd in docker python3 curl; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "✗ $cmd is not installed. Please install it first."
    exit 1
  fi
done

echo "→ Spinning up DataHub (this can take 3–5 minutes on first run)"
datahub docker quickstart || true

echo "→ Waiting for GMS to come up on :8080"
for i in {1..60}; do
  if curl -sf http://localhost:8080/health >/dev/null 2>&1; then
    echo "✓ DataHub GMS is up"
    break
  fi
  sleep 5
done

echo "→ Loading nyc-taxi sample (has planted freshness issues — perfect demo)"
datahub datapack load nyc-taxi || true

echo
echo "✓ Done. Open http://localhost:9002 to browse the catalog."
echo "  GMS endpoint: http://localhost:8080"
echo "  Get a token at Settings → Access Tokens → Generate"
