#!/bin/bash
set -e

echo "=== Starting Tryton Server ==="
echo "Environment: ${RAILWAY_ENVIRONMENT:-development}"
echo "PORT: ${PORT:-8000}"
echo "WORKERS: ${WORKERS:-1}"
echo "Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"

# Use Railway's PORT or default to 8000
export SERVER_PORT="${PORT:-8000}"

# Validate critical environment variables without exposing them
echo "=== Environment Validation ==="
if [[ -z "$DATABASE_URL" ]]; then
    echo "✗ DATABASE_URL is not set"
    exit 1
fi

if [[ -z "$ADMIN_PASSWORD" ]]; then
    echo "✗ ADMIN_PASSWORD is not set"
    exit 1
fi

echo "✓ Required environment variables are set"

# Create dynamic configuration with proper security
echo "=== Creating Secure Configuration ==="
if python3 create_config.py; then
    echo "✓ Configuration created successfully"
else
    echo "✗ Failed to create configuration"
    exit 1
fi

# Verify configuration file exists and has proper permissions
CONFIG_FILE="/app/railway-trytond.conf"
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "✗ Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Check file permissions for security
CONFIG_PERMS=$(stat -c "%a" "$CONFIG_FILE")
if [[ "$CONFIG_PERMS" != "600" ]]; then
    echo "⚠ Configuration file permissions: $CONFIG_PERMS (should be 600)"
    chmod 600 "$CONFIG_FILE"
    echo "✓ Fixed configuration file permissions to 600"
fi

# Check database connectivity and initialization status
echo "=== Database Status Check ==="
DATABASE_NAME="${DATABASE_NAME:-divvyqueue_prod}"

# Test database connection without exposing credentials
if python3 -c "
import os
import sys
from trytond.pool import Pool
from trytond.config import config

try:
    config_file = os.environ.get('TRYTON_CONFIG', '/app/railway-trytond.conf')
    config.update_etc(config_file)

    database_name = os.environ.get('DATABASE_NAME', 'divvyqueue_prod')

    # Test basic connection
    pool = Pool(database_name)
    pool.init()

    # Check if database is properly initialized
    with pool.transaction().start(database_name, 1, readonly=True, context={}):
        User = pool.get('res.user')
        users = User.search([])

        if len(users) == 0:
            print('Database connected but not initialized')
            sys.exit(2)  # Needs initialization
        else:
            print(f'Database ready with {len(users)} users')
            sys.exit(0)  # Ready to go

except ImportError as e:
    print(f'Tryton import error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'Database connection failed: {e}')
    sys.exit(1)
"; then
    echo "✓ Database is ready"
elif [[ $? -eq 2 ]]; then
    echo "⚠ Database connected but needs initialization"
    echo "=== Initializing Database ==="

    if python3 init_database.py; then
        echo "✓ Database initialized successfully"
    else
        echo "⚠ Database initialization failed, but continuing..."
        echo "  Manual initialization may be required"
    fi
else
    echo "✗ Database connection failed"
    echo "  Please check DATABASE_URL and database availability"
    exit 1
fi

# Security check: Ensure we're not running as root
if [[ $EUID -eq 0 ]]; then
    echo "⚠ Warning: Running as root user"
    echo "  Consider running as non-root user for better security"
fi

# Clear any sensitive environment variables that might have been set during config
unset TRYTON_ADMIN_PASSWORD 2>/dev/null || true
unset TEMP_DATABASE_URL 2>/dev/null || true

# Set security-focused environment variables
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

# Configure gunicorn settings
GUNICORN_WORKERS="${WORKERS:-1}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"
GUNICORN_MAX_REQUESTS="${GUNICORN_MAX_REQUESTS:-1000}"
GUNICORN_MAX_REQUESTS_JITTER="${GUNICORN_MAX_REQUESTS_JITTER:-100}"

echo "=== Starting Gunicorn Server ==="
echo "Workers: $GUNICORN_WORKERS"
echo "Timeout: $GUNICORN_TIMEOUT seconds"
echo "Max requests per worker: $GUNICORN_MAX_REQUESTS"
echo "Binding to: 0.0.0.0:$SERVER_PORT"

# Start gunicorn with production-ready settings
exec gunicorn \
    --bind "0.0.0.0:${SERVER_PORT}" \
    --workers "$GUNICORN_WORKERS" \
    --timeout "$GUNICORN_TIMEOUT" \
    --max-requests "$GUNICORN_MAX_REQUESTS" \
    --max-requests-jitter "$GUNICORN_MAX_REQUESTS_JITTER" \
    --worker-class sync \
    --worker-connections 1000 \
    --keepalive 5 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance \
    --preload \
    wsgi:application
