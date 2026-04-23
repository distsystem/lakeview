#!/usr/bin/env bash
# Seed a local Polaris instance with Lance fixtures for Lakeview dev.
#
# Flow:
#   1. Generate Lance fixtures via scripts/generate_test_data.py (S3 target)
#   2. Wait for Polaris on :8181
#   3. Exchange root credentials for an OAuth access token
#   4. Create catalog + namespace (idempotent; 409 is tolerated)
#   5. Register each fixture as a Lance generic table
#
# Assumes `pixi run -e polaris polaris-dev` is already running.
# Expects S3_BUCKET / S3_PREFIX (matching the `seed` task) and AWS_* creds
# in the environment — via direnv/.env, the same way `seed` uses them.

set -euo pipefail

POLARIS_URL=${POLARIS_URL:-http://localhost:8181}
POLARIS_MGMT_URL=${POLARIS_MGMT_URL:-http://localhost:8182}
CLIENT_ID=${POLARIS_CLIENT_ID:-root}
CLIENT_SECRET=${POLARIS_CLIENT_SECRET:-s3cr3t}
CATALOG=${POLARIS_CATALOG:-lakeview_test}
NAMESPACE=${POLARIS_NAMESPACE:-demo}

: "${S3_BUCKET:?set S3_BUCKET (same var the seed task uses)}"
: "${S3_PREFIX:?set S3_PREFIX (same var the seed task uses)}"
TARGET="s3://${S3_BUCKET}/${S3_PREFIX}"

# roleArn is required by the Polaris schema but unused in this read-only
# dev flow — Lakeview opens Lance datasets with its own AWS creds.
ROLE_ARN=${POLARIS_S3_ROLE_ARN:-arn:aws:iam::000000000000:role/dev-placeholder}
REGION=${AWS_REGION:-us-east-1}
# Optional custom S3 endpoint (Baidu BOS, MinIO, ...). Falls back to AWS.
S3_ENDPOINT=${POLARIS_S3_ENDPOINT:-${AWS_ENDPOINT_URL:-}}
STORAGE_ENDPOINT_FIELD=""
if [ -n "$S3_ENDPOINT" ]; then
  STORAGE_ENDPOINT_FIELD=",
      \"endpoint\": \"${S3_ENDPOINT}\""
fi

# --- 1. fixtures ------------------------------------------------------------
# Skip via POLARIS_SKIP_FIXTURES=1 if the target already has what you need.
# Failures here are non-fatal: Polaris registration only needs the fixture
# paths to exist at read time, not at bootstrap time.
if [ "${POLARIS_SKIP_FIXTURES:-0}" != "1" ]; then
  echo "==> generating fixtures to $TARGET"
  python scripts/generate_test_data.py --target "$TARGET" --fixture all \
    || echo "  (fixture generation reported errors; continuing)"
else
  echo "==> skipping fixture generation (POLARIS_SKIP_FIXTURES=1)"
fi

# --- 2. wait for polaris ----------------------------------------------------
echo "==> waiting for Polaris (health at $POLARIS_MGMT_URL)"
for _ in $(seq 1 60); do
  if curl -sf "$POLARIS_MGMT_URL/q/health" >/dev/null; then break; fi
  sleep 1
done
curl -sf "$POLARIS_MGMT_URL/q/health" >/dev/null || {
  echo "Polaris did not come up on $POLARIS_MGMT_URL"; exit 1;
}

# --- 3. token ---------------------------------------------------------------
echo "==> acquiring token"
TOKEN=$(curl -sf -X POST "$POLARIS_URL/api/catalog/v1/oauth/tokens" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&scope=PRINCIPAL_ROLE:ALL" \
  | python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
AUTH="Authorization: Bearer ${TOKEN}"

# tolerate 409 on create so the script is idempotent.
post_idempotent() {
  local url=$1 body=$2 label=$3
  local code
  code=$(curl -s -o /tmp/polaris-bootstrap.out -w "%{http_code}" \
    -X POST "$url" -H "$AUTH" -H 'Content-Type: application/json' -d "$body")
  case "$code" in
    200|201|204) echo "   [$label] created" ;;
    409)         echo "   [$label] already exists" ;;
    *)           echo "   [$label] HTTP $code"; cat /tmp/polaris-bootstrap.out; echo; exit 1 ;;
  esac
}

# --- 4. catalog + namespace -------------------------------------------------
echo "==> creating catalog $CATALOG"
post_idempotent "$POLARIS_URL/api/management/v1/catalogs" "$(cat <<EOF
{
  "catalog": {
    "type": "INTERNAL",
    "name": "${CATALOG}",
    "properties": { "default-base-location": "${TARGET}" },
    "storageConfigInfo": {
      "storageType": "S3",
      "allowedLocations": ["${TARGET}/"],
      "roleArn": "${ROLE_ARN}",
      "region": "${REGION}"${STORAGE_ENDPOINT_FIELD}
    }
  }
}
EOF
)" catalog

echo "==> creating namespace $NAMESPACE"
post_idempotent "$POLARIS_URL/api/catalog/v1/${CATALOG}/namespaces" \
  "{\"namespace\": [\"${NAMESPACE}\"], \"properties\": {}}" namespace

# --- 5. generic Lance tables ------------------------------------------------
echo "==> registering Lance generic tables"
for fixture in fake_runs blob_images; do
  post_idempotent \
    "$POLARIS_URL/api/catalog/polaris/v1/${CATALOG}/namespaces/${NAMESPACE}/generic-tables" \
    "{
      \"name\": \"${fixture}\",
      \"format\": \"lance\",
      \"base-location\": \"${TARGET}/${fixture}.lance\"
    }" "table:${fixture}"
done

echo
echo "==> done"
echo "  Polaris:    ${POLARIS_URL}"
echo "  Catalog:    ${CATALOG}"
echo "  Namespace:  ${NAMESPACE}"
echo "  Tables:     fake_runs, blob_images"
