#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$(mktemp)"
BODY_FILE="$(mktemp)"
SERVER_PID=""

cleanup() {
  if [[ -n "${SERVER_PID}" ]] && kill -0 "${SERVER_PID}" 2>/dev/null; then
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi
  rm -f "${LOG_FILE}" "${BODY_FILE}"
}

trap cleanup EXIT

PORT="$(
  python3 - <<'PY'
import socket

with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    print(s.getsockname()[1])
PY
)"

cd "${ROOT_DIR}"
if [[ -x "${ROOT_DIR}/.venv/bin/uvicorn" ]]; then
  SERVER_CMD=("${ROOT_DIR}/.venv/bin/uvicorn")
else
  SERVER_CMD=(uv run --no-sync uvicorn)
fi

"${SERVER_CMD[@]}" main:app --host 127.0.0.1 --port "${PORT}" >"${LOG_FILE}" 2>&1 &
SERVER_PID=$!

sleep 3

if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
  echo "Server exited before health check." >&2
  cat "${LOG_FILE}" >&2
  exit 1
fi

set +e
HTTP_CODE="$(
  curl -sS -o "${BODY_FILE}" -w '%{http_code}' "http://127.0.0.1:${PORT}/health"
)"
CURL_EXIT=$?
set -e

if [[ "${CURL_EXIT}" -ne 0 ]]; then
  echo "curl failed with exit code ${CURL_EXIT}." >&2
  cat "${LOG_FILE}" >&2
  exit 1
fi

if [[ "${HTTP_CODE}" != "200" ]]; then
  echo "Unexpected /health status: ${HTTP_CODE}" >&2
  cat "${BODY_FILE}" >&2
  cat "${LOG_FILE}" >&2
  exit 1
fi

if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
  echo "Server crashed after returning /health." >&2
  cat "${LOG_FILE}" >&2
  exit 1
fi

echo "Health check passed on port ${PORT}."
