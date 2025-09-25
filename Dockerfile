# Multi-stage Dockerfile for Tryton ERP on Railway
# Optimized for DivvyQueue integration

# Stage 1: Builder
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    libldap2-dev \
    libsasl2-dev \
    libssl-dev \
    python3-dev \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --upgrade pip setuptools wheel

# Copy requirements and install dependencies
WORKDIR /build

# Install Tryton core
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

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    libxml2 \
    libxslt1.1 \
    libldap-2.5-0 \
    libsasl2-2 \
    libssl3 \
    postgresql-client \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app user and directories
RUN useradd -m -d /app -s /bin/bash -u 1000 app && \
    mkdir -p /app/uploads /app/logs /app/attachments /app/backups && \
    chown -R app:app /app

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=app:app . .

# Copy configuration files
COPY --chown=app:app railway-trytond.conf /app/railway-trytond.conf

# Create health check script
COPY --chown=app:app <<'EOF' /app/health_check.py
#!/usr/bin/env python3
"""Health check script for Railway deployment."""
import os
import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            try:
                # Basic health check - verify Tryton can start
                from trytond.pool import Pool
                from trytond.config import config

                # Load configuration
                config_file = os.environ.get('TRYTON_CONFIG', '/app/railway-trytond.conf')
                if os.path.exists(config_file):
                    config.update_etc(config_file)

                # Check database connection
                database_name = os.environ.get('DATABASE_NAME', 'divvyqueue_prod')

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()

                response = {
                    'status': 'healthy',
                    'timestamp': time.time(),
                    'database': database_name,
                    'version': '6.0'
                }

                self.wfile.write(json.dumps(response).encode())

            except Exception as e:
                self.send_response(503)
                self.send_header('Content-type', 'application/json')
                self.end_headers()

                response = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': time.time()
                }

                self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default logging
        pass

if __name__ == '__main__':
    try:
        # Test health check
        from trytond.pool import Pool
        print("Health check: OK")
        sys.exit(0)
    except Exception as e:
        print(f"Health check: FAILED - {e}")
        sys.exit(1)
EOF

# Create entrypoint script
COPY --chown=app:app <<'EOF' /app/entrypoint.sh
#!/bin/bash
set -e

# Environment setup
export PYTHONPATH="/app:${PYTHONPATH}"
export TRYTOND_CONFIG="${TRYTON_CONFIG:-/app/railway-trytond.conf}"

# Create required directories
mkdir -p /app/uploads /app/logs /app/attachments

# Database initialization function
init_database() {
    echo "Initializing Tryton database..."

    # Wait for database to be ready
    echo "Waiting for database connection..."
    python3 -c "
import os
import time
import psycopg2
from urllib.parse import urlparse

db_url = os.environ.get('DATABASE_URL')
if db_url:
    parsed = urlparse(db_url)
    for i in range(30):
        try:
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password
            )
            conn.close()
            print('Database connection successful')
            break
        except:
            print(f'Waiting for database... ({i+1}/30)')
            time.sleep(2)
    else:
        raise Exception('Database connection failed')
"

    # Check if database needs initialization
    DATABASE_NAME="${DATABASE_NAME:-divvyqueue_prod}"

    echo "Checking if database is initialized..."
    if ! python3 -c "
from trytond.pool import Pool
from trytond.config import config
import os

config.update_etc('${TRYTOND_CONFIG}')
try:
    pool = Pool('${DATABASE_NAME}')
    print('Database already initialized')
except:
    print('Database needs initialization')
    exit(1)
"; then
        echo "Initializing database with core modules..."
        trytond-admin -c "${TRYTOND_CONFIG}" -d "${DATABASE_NAME}" --all --password

        echo "Setting up admin user..."
        if [ -n "${ADMIN_EMAIL}" ] && [ -n "${TRYTON_ADMIN_PASSWORD}" ]; then
            python3 -c "
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.config import config

config.update_etc('${TRYTOND_CONFIG}')
pool = Pool('${DATABASE_NAME}')
pool.init()

with Transaction().start('${DATABASE_NAME}', 1, context={}):
    User = pool.get('res.user')
    admin = User.search([('login', '=', 'admin')])[0]
    admin.email = '${ADMIN_EMAIL}'
    admin.save()
    print(f'Admin user configured with email: ${ADMIN_EMAIL}')
"
        fi

        echo "Database initialization complete"
    fi
}

# Function to start health check server
start_health_server() {
    echo "Starting health check server..."
    python3 -c "
import os
from http.server import HTTPServer
from health_check import HealthHandler
import threading

def run_health_server():
    server = HTTPServer(('0.0.0.0', 8080), HealthHandler)
    server.serve_forever()

thread = threading.Thread(target=run_health_server, daemon=True)
thread.start()
print('Health check server started on port 8080')
" &
}

# Main execution
echo "Starting Tryton for DivvyQueue..."
echo "Configuration: ${TRYTOND_CONFIG}"
echo "Database: ${DATABASE_NAME:-divvyqueue_prod}"
echo "Port: ${PORT:-8000}"

# Initialize database if needed
if [ "${SKIP_DB_INIT}" != "true" ]; then
    init_database
fi

# Start health check server
start_health_server

# Execute the main command
echo "Starting Tryton server..."
exec "$@"
EOF

# Make scripts executable
RUN chmod +x /app/health_check.py /app/entrypoint.sh

# Create WSGI application
COPY --chown=app:app <<'EOF' /app/wsgi.py
"""WSGI application for Railway deployment."""
import os
import sys
from trytond.config import config
from trytond.wsgi import app as application

# Load configuration
config_file = os.environ.get('TRYTON_CONFIG', '/app/railway-trytond.conf')
if os.path.exists(config_file):
    config.update_etc(config_file)

# Add health check endpoint
from trytond.protocols.dispatcher import create
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Response
import json
import time

def health_check(environ, start_response):
    """Health check endpoint for Railway."""
    try:
        from trytond.pool import Pool
        database_name = os.environ.get('DATABASE_NAME', 'divvyqueue_prod')

        response_data = {
            'status': 'healthy',
            'timestamp': time.time(),
            'database': database_name,
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

# Wrap the original application with health check
original_app = application

def app_with_health(environ, start_response):
    """WSGI application with health check."""
    path = environ.get('PATH_INFO', '')

    if path == '/health':
        return health_check(environ, start_response)
    else:
        return original_app(environ, start_response)

application = app_with_health

if __name__ == "__main__":
    from werkzeug.serving import run_simple
    port = int(os.environ.get('PORT', 8000))
    run_simple('0.0.0.0', port, application, use_reloader=False)
EOF

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TRYTON_CONFIG=/app/railway-trytond.conf \
    TZ=UTC

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python3 /app/health_check.py || exit 1

# Switch to app user
USER app

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command for Railway
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "--keepalive", "2", "--max-requests", "1000", "--access-logfile", "-", "--error-logfile", "-", "wsgi:application"]
