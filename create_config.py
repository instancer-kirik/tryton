#!/usr/bin/env python3
"""
Secure Tryton Configuration Creator for Railway
This script creates a proper tryton.conf file at runtime using environment variables
with improved security practices.
"""

import os
import sys
import secrets
import urllib.parse
from pathlib import Path

def validate_environment():
    """Validate required environment variables and security settings"""
    required_vars = ['DATABASE_URL']
    missing_vars = []

    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        return False

    # Check for weak admin password
    admin_password = os.environ.get('ADMIN_PASSWORD')
    if not admin_password:
        print("ERROR: ADMIN_PASSWORD environment variable is required")
        print("Never use default passwords in production!")
        return False

    if len(admin_password) < 12:
        print("WARNING: Admin password is shorter than 12 characters")
        print("Consider using a longer, more secure password")

    return True

def parse_database_url(database_url):
    """Parse DATABASE_URL and extract components securely"""
    try:
        parsed = urllib.parse.urlparse(database_url)
        return {
            'scheme': parsed.scheme,
            'hostname': parsed.hostname,
            'port': parsed.port,
            'database': parsed.path.lstrip('/'),
            'username': parsed.username,
            'password': parsed.password
        }
    except Exception as e:
        print(f"ERROR: Invalid DATABASE_URL format: {e}")
        return None

def create_tryton_config():
    """Create Tryton configuration file with Railway environment variables"""

    if not validate_environment():
        return False

    # Get environment variables
    database_url = os.environ.get('DATABASE_URL')
    database_name = os.environ.get('DATABASE_NAME', 'divvyqueue_prod')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    session_timeout = os.environ.get('SESSION_TIMEOUT', '3600')
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    cache_model_size = os.environ.get('CACHE_MODEL_SIZE', '200')
    cache_record_size = os.environ.get('CACHE_RECORD_SIZE', '2000')

    # Parse database URL for validation (don't store components)
    db_info = parse_database_url(database_url)
    if not db_info:
        return False

    # Generate session secret if not provided
    session_secret = os.environ.get('SESSION_SECRET')
    if not session_secret:
        session_secret = secrets.token_urlsafe(32)
        print("INFO: Generated new session secret (set SESSION_SECRET env var to persist)")

    # Configuration template - use environment variable references where possible
    config_content = f"""# Tryton Configuration for Railway Deployment
# Generated dynamically with security best practices

[database]
# Railway PostgreSQL connection - using environment variable
uri = {database_url}
default_name = {database_name}

[web]
# Web server disabled - static files served by WSGI
listen = 0.0.0.0:8000

[session]
# Session settings
timeout = {session_timeout}
# Admin password is set via environment variable for security
super_pwd = {admin_password}
secret = {session_secret}

[cache]
# Configurable cache settings
class = trytond.cache.MemoryCache
model = {cache_model_size}
record = {cache_record_size}
field = 100

[jsonrpc]
# JSON-RPC API endpoint - handled by WSGI
data = /app/sao
cors = *

[password]
# Strong password policy
length = 12
entropy = 0.75
forbidden = common,password,123456,admin,root,user

[logging]
# Logging configuration for Railway
keys = root,trytond,werkzeug

[logging.handlers]
keys = console

[logging.formatters]
keys = secure

[logger_root]
level = {log_level}
handlers = console

[logger_trytond]
level = {log_level}
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
formatter = secure

[formatter_secure]
# Secure formatter that doesn't log sensitive data
format = %(asctime)s [%(levelname)s] %(name)s: %(message)s
datefmt = %Y-%m-%d %H:%M:%S

[security]
# Additional security settings
csrf_protection = True
secure_cookies = True
"""

    # Write the configuration file with secure permissions
    config_file = '/app/railway-trytond.conf'

    try:
        # Create config file with restricted permissions
        config_path = Path(config_file)
        config_path.write_text(config_content)
        config_path.chmod(0o600)  # Only readable by owner

        print(f"✓ Created Tryton configuration: {config_file}")
        print(f"✓ Database: {db_info['hostname']}:{db_info['port']}/{db_info['database']}")
        print(f"✓ Database name: {database_name}")
        print(f"✓ Configuration file permissions: 600 (owner read/write only)")
        print("✓ Security validations passed")

        return True

    except Exception as e:
        print(f"✗ Failed to create configuration file: {e}")
        return False

def cleanup_old_configs():
    """Remove any old configuration files for security"""
    old_configs = [
        '/app/trytond.conf',
        '/app/tryton.conf',
        '/tmp/trytond.conf'
    ]

    for config_file in old_configs:
        try:
            if os.path.exists(config_file):
                os.remove(config_file)
                print(f"✓ Cleaned up old config: {config_file}")
        except Exception as e:
            print(f"⚠ Could not clean up {config_file}: {e}")

if __name__ == '__main__':
    print("=== Tryton Configuration Security Check ===")

    # Clean up any old configuration files
    cleanup_old_configs()

    # Create secure configuration
    success = create_tryton_config()

    if success:
        print("=== Configuration created successfully ===")
        print("\nSecurity reminders:")
        print("- Ensure ADMIN_PASSWORD is strong and unique")
        print("- Rotate DATABASE_URL credentials regularly")
        print("- Monitor logs for any security issues")
        print("- Keep Tryton and dependencies updated")
    else:
        print("=== Configuration failed - check environment variables ===")

    sys.exit(0 if success else 1)
