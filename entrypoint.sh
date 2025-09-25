#!/bin/bash
set -e

echo "=== Tryton Entrypoint Starting ==="
echo "Environment variables:"
echo "  PORT: ${PORT}"
echo "  DATABASE_URL: ${DATABASE_URL:0:30}..."
echo "  DATABASE_NAME: ${DATABASE_NAME}"
echo "  ADMIN_EMAIL: ${ADMIN_EMAIL}"
echo "  TRYTON_CONFIG: ${TRYTON_CONFIG}"

export PYTHONPATH="/app:${PYTHONPATH}"
export TRYTOND_CONFIG="${TRYTON_CONFIG:-/app/railway-trytond.conf}"

echo "PYTHONPATH: ${PYTHONPATH}"
echo "TRYTOND_CONFIG: ${TRYTOND_CONFIG}"

# Create required directories
echo "Creating directories..."
mkdir -p /app/uploads /app/logs /app/attachments

# Check if config file exists
if [ -f "${TRYTOND_CONFIG}" ]; then
    echo "Config file found: ${TRYTOND_CONFIG}"
else
    echo "WARNING: Config file not found: ${TRYTOND_CONFIG}"
fi

# Wait for database
echo "Waiting for database connection..."
python3 -c "
import os
import time
import psycopg2
from urllib.parse import urlparse

db_url = os.environ.get('DATABASE_URL')
if db_url:
    parsed = urlparse(db_url)
    for i in range(60):
        try:
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:] if parsed.path else 'postgres',
                user=parsed.username,
                password=parsed.password
            )
            conn.close()
            print('Database connection successful')
            break
        except Exception as e:
            print(f'Waiting for database... ({i+1}/60)')
            time.sleep(2)
    else:
        print('Database connection failed after 2 minutes')
        exit(1)
"

# Initialize database if needed
DATABASE_NAME="${DATABASE_NAME:-divvyqueue_prod}"

echo "=== Database Initialization Phase ==="
echo "Database name: ${DATABASE_NAME}"
echo "Skip DB init: ${SKIP_DB_INIT}"

echo "Checking database initialization..."
if [ "${SKIP_DB_INIT}" != "true" ]; then
    if ! python3 -c "
from trytond.pool import Pool
from trytond.config import config
config.update_etc('${TRYTOND_CONFIG}')
try:
    pool = Pool('${DATABASE_NAME}')
    print('Database already initialized')
except:
    print('Database needs initialization')
    exit(1)
" 2>/dev/null; then
        echo "Initializing database..."
        trytond-admin -c "${TRYTOND_CONFIG}" -d "${DATABASE_NAME}" --all

        if [ -n "${TRYTON_ADMIN_PASSWORD}" ]; then
            echo "${TRYTON_ADMIN_PASSWORD}" | trytond-admin -c "${TRYTOND_CONFIG}" -d "${DATABASE_NAME}" --password
        fi

        echo "Database initialization complete"
    fi
fi

echo "=== Starting Tryton Server ==="
echo "Command to execute: $@"
echo "Current working directory: $(pwd)"
echo "Python version: $(python3 --version)"
echo "Gunicorn version: $(gunicorn --version 2>/dev/null || echo 'gunicorn not found')"

# Test if wsgi module can be imported
echo "Testing WSGI module import..."
python3 -c "
try:
    import wsgi
    print('✓ WSGI module imported successfully')
except Exception as e:
    print(f'✗ WSGI module import failed: {e}')
"

exec "$@"
