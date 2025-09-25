# Multi-stage Dockerfile for Tryton ERP on Railway
# Optimized for DivvyQueue integration

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libpq5 \
    libxml2-dev \
    libxml2 \
    libxslt1-dev \
    libxslt1.1 \
    libldap2-dev \
    libsasl2-dev \
    libsasl2-2 \
    libssl-dev \
    python3-dev \
    build-essential \
    git \
    curl \
    ca-certificates \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create app user and directories
RUN useradd -m -d /app -s /bin/bash -u 1000 app && \
    mkdir -p /app/uploads /app/logs /app/attachments /app/backups && \
    chown -R app:app /app

# Set working directory
WORKDIR /app

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip setuptools wheel

# Install Tryton core and modules
RUN pip install --no-cache-dir \
    "trytond>=6.0.0,<6.1" \
    "proteus>=6.0.0,<6.1" \
    psycopg2-binary \
    gunicorn \
    redis \
    python-dotenv \
    bcrypt \
    pytz \
    python-dateutil \
    lxml \
    relatorio \
    python-sql \
    werkzeug \
    "passlib[argon2]" \
    requests \
    python-stdnum

# Install Tryton modules for DivvyQueue
RUN pip install --no-cache-dir \
    "trytond-party>=6.0.0,<6.1" \
    "trytond-product>=6.0.0,<6.1" \
    "trytond-sale>=6.0.0,<6.1" \
    "trytond-purchase>=6.0.0,<6.1" \
    "trytond-account>=6.0.0,<6.1" \
    "trytond-stock>=6.0.0,<6.1" \
    "trytond-project>=6.0.0,<6.1" \
    "trytond-company>=6.0.0,<6.1" \
    "trytond-currency>=6.0.0,<6.1" \
    "trytond-country>=6.0.0,<6.1"

# Copy application code and configuration
COPY --chown=app:app . .
COPY --chown=app:app railway-trytond.conf /app/railway-trytond.conf

# Create health check script
RUN cat > /app/health_check.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
import json
import time

try:
    from trytond.config import config
    config_file = os.environ.get('TRYTON_CONFIG', '/app/railway-trytond.conf')
    if os.path.exists(config_file):
        config.update_etc(config_file)

    response = {
        'status': 'healthy',
        'timestamp': time.time(),
        'database': os.environ.get('DATABASE_NAME', 'divvyqueue_prod'),
        'version': '6.0'
    }
    print(json.dumps(response))
    sys.exit(0)
except Exception as e:
    response = {
        'status': 'unhealthy',
        'error': str(e),
        'timestamp': time.time()
    }
    print(json.dumps(response))
    sys.exit(1)
EOF

# Create entrypoint script
RUN cat > /app/entrypoint.sh << 'EOF'
#!/bin/bash
set -e

export PYTHONPATH="/app:${PYTHONPATH}"
export TRYTOND_CONFIG="${TRYTON_CONFIG:-/app/railway-trytond.conf}"

# Create required directories
mkdir -p /app/uploads /app/logs /app/attachments

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

echo "Starting Tryton server..."
exec "$@"
EOF

# Create WSGI application
RUN cat > /app/wsgi.py << 'EOF'
import os
import sys
import json
import time
from trytond.config import config
from trytond.wsgi import app as tryton_app
from werkzeug.wrappers import Request, Response

config_file = os.environ.get('TRYTON_CONFIG', '/app/railway-trytond.conf')
if os.path.exists(config_file):
    config.update_etc(config_file)

def health_check_app(environ, start_response):
    try:
        response_data = {
            'status': 'healthy',
            'timestamp': time.time(),
            'database': os.environ.get('DATABASE_NAME', 'divvyqueue_prod'),
            'version': '6.0'
        }
        response = Response(
            json.dumps(response_data),
            mimetype='application/json',
            status=200
        )
    except Exception as e:
        response_data = {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }
        response = Response(
            json.dumps(response_data),
            mimetype='application/json',
            status=503
        )
    return response(environ, start_response)

def application(environ, start_response):
    request = Request(environ)
    if request.path == '/health':
        return health_check_app(environ, start_response)
    else:
        return tryton_app(environ, start_response)
EOF

# Make scripts executable
RUN chmod +x /app/health_check.py /app/entrypoint.sh && \
    chown app:app /app/health_check.py /app/entrypoint.sh /app/wsgi.py

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TRYTON_CONFIG=/app/railway-trytond.conf

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD python3 /app/health_check.py || exit 1

# Switch to app user
USER app

# Set entrypoint and command
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "--max-requests", "1000", "--access-logfile", "-", "--error-logfile", "-", "wsgi:application"]
