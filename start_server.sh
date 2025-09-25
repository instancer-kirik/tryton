#!/bin/bash
set -e

echo "=== Starting Tryton Server ==="
echo "PORT: ${PORT:-8000}"
echo "WORKERS: ${WORKERS:-1}"

# Use Railway's PORT or default to 8000
export SERVER_PORT="${PORT:-8000}"

# Start gunicorn with dynamic port
exec gunicorn \
    --bind "0.0.0.0:${SERVER_PORT}" \
    --workers "${WORKERS:-1}" \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    wsgi:application
