#!/usr/bin/env bash
set -euo pipefail

TMP_ENV_FILE="$(mktemp)"
trap 'rm -f "$TMP_ENV_FILE"' EXIT

cat > "$TMP_ENV_FILE" <<'EOF'
GEMINI_API_KEY: "AIzaSyCeKFNc8k8rtmN9q7KnChh_drK54pOGdhQ"
CORS_ORIGINS_RAW: "http://localhost:5173,https://rast-nu.vercel.app,https://rast.name.ng,https://www.rast.name.ng"
UNPAYWALL_EMAIL: "awun8191@gmail.com"
APP_ENV: "development"
EOF

gcloud run services update research-api \
  --env-vars-file "$TMP_ENV_FILE" \
  --region=us-central1 \
  --project=researchassistant-3446d
