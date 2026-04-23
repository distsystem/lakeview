#!/usr/bin/env bash
# One-shot Lakeview dev stack: Polaris + backend (uvicorn) + frontend (vite).
# All three share fate — any one dying or a Ctrl+C tears the rest down.

set -euo pipefail
cd "$(dirname "$0")/.."

bash scripts/polaris_up.sh &
POLARIS_PID=$!

echo "==> waiting for Polaris health on :8182"
for _ in $(seq 1 300); do
  curl -sf http://localhost:8182/q/health >/dev/null 2>&1 && break
  kill -0 "$POLARIS_PID" 2>/dev/null || { echo "polaris_up crashed"; exit 1; }
  sleep 1
done
curl -sf http://localhost:8182/q/health >/dev/null || {
  echo "Polaris did not become healthy in time"; exit 1;
}

uvicorn lakeview.app:app --host 0.0.0.0 --port 8766 --reload &
UVICORN_PID=$!

( cd frontend && exec bun run dev ) &
FRONTEND_PID=$!

cleanup() {
  echo
  echo "==> stopping stack"
  kill "$FRONTEND_PID" 2>/dev/null || true
  kill "$UVICORN_PID"  2>/dev/null || true
  kill "$POLARIS_PID"  2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

cat <<EOF

==> stack up
    polaris    http://localhost:8181  (mgmt :8182)
    backend    http://localhost:8766
    frontend   http://localhost:5173

    Ctrl+C stops everything.
EOF

# Exit as soon as any component dies so we can clean the rest.
wait -n
