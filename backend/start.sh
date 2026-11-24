#!/bin/sh
# Start the Glean API (GLEAN_ROLE=api, default) or the arq worker (GLEAN_ROLE=worker).
# Any failure exits non-zero so Railway's ON_FAILURE restart policy restarts it.
set -eu
: "${DATABASE_URL:?DATABASE_URL is required}"
: "${REDIS_URL:?REDIS_URL is required}"
: "${SECRET_KEY:?SECRET_KEY is required}"
export VECTOR_BACKEND="${VECTOR_BACKEND:-pgvector}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export DEBUG="${DEBUG:-false}"
# Logs go to Railway's log view only (no log volume needed).
unset LOG_FILE || true
# Keep native thread pools at the service's CPU count, not the host's.
cpus=1
if [ -r /sys/fs/cgroup/cpu.max ]; then
  read -r quota period < /sys/fs/cgroup/cpu.max || true
  if [ "${quota:-max}" != "max" ] && [ -n "${period:-}" ]; then
    cpus=$(( (quota + period - 1) / period ))
  else
    cpus=2
  fi
fi
[ "$cpus" -lt 1 ] && cpus=1
[ "$cpus" -gt 4 ] && cpus=4
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-$cpus}" OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-$cpus}"

case "${GLEAN_ROLE:-api}" in
  api)
    python /opt/glean/bootstrap.py
    exec uvicorn glean_api.main:app --host :: --port "${PORT:-8000}" \
      --proxy-headers --forwarded-allow-ips '*' --no-server-header
    ;;
  worker)
    python /opt/glean/bootstrap.py --wait-only
    exec arq glean_worker.main.WorkerSettings
    ;;
  *)
    echo "Unknown GLEAN_ROLE '${GLEAN_ROLE}' (use api or worker)" >&2
    exit 64
    ;;
esac
