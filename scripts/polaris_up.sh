#!/usr/bin/env bash
# One-shot Polaris dev: build JAR if needed, launch, wait for health, bootstrap.
# Ctrl+C stops the JVM.
#
# Env knobs:
#   POLARIS_DIR             override the apache/polaris checkout location
#   POLARIS_SKIP_FIXTURES   (default 1 here) don't regenerate S3 fixtures

set -euo pipefail
cd "$(dirname "$0")/.."

POLARIS_DIR="${POLARIS_DIR:-$(cd .. && pwd)/polaris}"
JAR="${POLARIS_DIR}/runtime/server/build/quarkus-app/quarkus-run.jar"

if ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE '[:\.]8181$'; then
  echo "ERROR: :8181 is already bound — another Polaris is running. Stop it first." >&2
  exit 1
fi

if [ ! -f "$JAR" ]; then
  echo "==> building Polaris JAR (first run only; ~2-3 min)"
  (
    cd "$POLARIS_DIR"
    ./gradlew :polaris-server:assemble :polaris-server:quarkusAppPartsBuild
  )
fi

echo "==> launching Polaris from $JAR"
java \
  -Dpolaris.bootstrap.credentials=POLARIS,root,s3cr3t \
  -jar "$JAR" &
PID=$!

cleanup() {
  echo
  echo "==> stopping Polaris ($PID)"
  kill "$PID" 2>/dev/null || true
  wait "$PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "==> waiting for health on :8182"
for _ in $(seq 1 300); do
  curl -sf http://localhost:8182/q/health >/dev/null 2>&1 && break
  kill -0 "$PID" 2>/dev/null || { echo "Polaris died during startup"; exit 1; }
  sleep 1
done
curl -sf http://localhost:8182/q/health >/dev/null || {
  echo "Polaris did not become healthy in time"; exit 1;
}

POLARIS_SKIP_FIXTURES="${POLARIS_SKIP_FIXTURES:-1}" \
  bash scripts/bootstrap_polaris.sh

echo
echo "==> Polaris ready at http://localhost:8181 — Ctrl+C to stop"
wait "$PID"
