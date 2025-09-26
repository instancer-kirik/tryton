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

# Add cache busting for Python files
RUN echo "Cache bust: $(date)" > /app/cache_bust.txt

# Copy script files and make them executable
COPY --chown=app:app health_check.py /app/health_check.py
COPY --chown=app:app entrypoint.sh /app/entrypoint.sh
COPY --chown=app:app wsgi.py /app/wsgi.py
COPY --chown=app:app start_server.sh /app/start_server.sh

RUN chmod +x /app/health_check.py /app/entrypoint.sh /app/start_server.sh /app/init_database.py && \
    chown app:app /app/health_check.py /app/entrypoint.sh /app/wsgi.py /app/start_server.sh /app/init_database.py

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
CMD ["/app/start_server.sh"]
