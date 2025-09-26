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

# Configure database URI from Railway environment
if [ -n "${DATABASE_URL}" ]; then
    echo "Updating Tryton config with Railway DATABASE_URL..."

    # Create a temporary config with the database URI
    sed "s|uri = postgresql://|uri = ${DATABASE_URL}|g" ${TRYTOND_CONFIG} > /tmp/trytond.conf
    export TRYTOND_CONFIG="/tmp/trytond.conf"

    echo "Database URI configured from Railway"
else
    echo "WARNING: No DATABASE_URL found"
fi

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
if [ -n "${DATABASE_URL}" ]; then
    python3 -c "
import os
import time
import psycopg2

db_url = os.environ.get('DATABASE_URL')
for i in range(30):
    try:
        conn = psycopg2.connect(db_url)
        conn.close()
        print('✓ Database connection successful')
        break
    except Exception as e:
        print(f'Waiting for database... ({i+1}/30) - {e}')
        time.sleep(2)
else:
    print('✗ Database connection failed after 1 minute')
    exit(1)
"
else
    echo "⚠ No DATABASE_URL provided - skipping database check"
fi

# Initialize database if needed
DATABASE_NAME="${DATABASE_NAME:-divvyqueue_prod}"

echo "=== Database Initialization Phase ==="
echo "Database name: ${DATABASE_NAME}"
echo "Skip DB init: ${SKIP_DB_INIT}"

echo "Running database initialization..."
if [ "${SKIP_DB_INIT}" != "true" ]; then
    python3 /app/init_database.py
    if [ $? -eq 0 ]; then
        echo "✓ Database initialization completed successfully"
    else
        echo "✗ Database initialization failed"
        exit 1
    fi
else
    echo "Skipping database initialization (SKIP_DB_INIT=true)"
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
