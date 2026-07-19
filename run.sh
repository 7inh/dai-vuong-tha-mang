#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
PORT="${PORT:-8080}"

echo "Serving at http://localhost:${PORT}"
exec python3 -m http.server "$PORT"
