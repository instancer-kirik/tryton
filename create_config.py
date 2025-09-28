#!/usr/bin/env python3
"""
Dynamic Tryton Configuration Creator for Railway
This script creates a proper tryton.conf file at runtime using environment variables.
"""

import os
import sys

def create_tryton_config():
    """Create Tryton configuration file with Railway environment variables"""

    # Get environment variables
    database_url = os.environ.get('DATABASE_URL')
    database_name = os.environ.get('DATABASE_NAME', 'divvyqueue_prod')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin')

    if not database_url:
        print("ERROR: DATABASE_URL environment variable is required")
        sys.exit(1)

    # Configuration template
    config_content = f"""# Tryton Configuration for Railway Deployment
# Generated dynamically from environment variables

[database]
# Railway PostgreSQL connection
uri = {database_url}
default_name = {database_name}

[web]
# Web server disabled - static files served by WSGI

[session]
# Session settings
timeout = 3600
super_pwd = {admin_password}

[cache]
# Simple memory cache
class = trytond.cache.MemoryCache
model = 200
record = 2000
field = 100

[jsonrpc]
# JSON-RPC API endpoint - handled by WSGI
data = /app/sao
cors = *

[password]
# Password policy
length = 8
entropy = 0.5

[logging]
# Logging configuration for Railway
keys = root,trytond,werkzeug

[logging.handlers]
keys = console

[logging.formatters]
keys = default

[logger_root]
level = INFO
handlers = console

[logger_trytond]
level = INFO
handlers = console
qualname = trytond
propagate = 0

[logger_werkzeug]
level = WARNING
handlers = console
qualname = werkzeug
propagate = 0

[handler_console]
class = StreamHandler
args = (sys.stdout,)
formatter = default

[formatter_default]
format = %(asctime)s [%(levelname)s] %(name)s: %(message)s
datefmt = %Y-%m-%d %H:%M:%S
"""

    # Write the configuration file
    config_file = '/app/railway-trytond.conf'
    try:
        with open(config_file, 'w') as f:
            f.write(config_content)

        print(f"✓ Created Tryton configuration: {config_file}")
        print(f"✓ Database URI: {database_url[:50]}...")
        print(f"✓ Database name: {database_name}")
        return True

    except Exception as e:
        print(f"✗ Failed to create configuration file: {e}")
        return False

if __name__ == '__main__':
    success = create_tryton_config()
    sys.exit(0 if success else 1)
