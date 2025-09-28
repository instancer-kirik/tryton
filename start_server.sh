#!/bin/bash
set -e

echo "=== Starting Tryton Server ==="
echo "PORT: ${PORT:-8000}"
echo "WORKERS: ${WORKERS:-1}"

# Use Railway's PORT or default to 8000
export SERVER_PORT="${PORT:-8000}"

# Create dynamic configuration with proper DATABASE_URL
echo "=== Creating Dynamic Configuration ==="
python3 create_config.py || {
    echo "✗ Failed to create configuration"
    exit 1
}

# Check and initialize database if needed
echo "=== Checking Database Status ==="
if python3 -c "
import os
from trytond.pool import Pool
from trytond.config import config

try:
    config_file = os.environ.get('TRYTON_CONFIG', '/app/railway-trytond.conf')
    if os.path.exists(config_file):
        config.update_etc(config_file)

    database_name = os.environ.get('DATABASE_NAME', 'divvyqueue_prod')
    pool = Pool(database_name)
    pool.init()

    with pool.transaction().start(database_name, 1, context={}):
        User = pool.get('res.user')
        users = User.search([])
        print(f'Database initialized with {len(users)} users')
except Exception as e:
    print(f'Database not initialized: {e}')
    exit(1)
"; then
    echo "✓ Database already initialized"
else
    echo "⚠ Database needs initialization - running setup..."
    python3 init_database.py || echo "⚠ Database initialization script failed, continuing anyway..."
fi

# Start gunicorn with dynamic port
exec gunicorn \
    --bind "0.0.0.0:${SERVER_PORT}" \
    --workers "${WORKERS:-1}" \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    wsgi:application
