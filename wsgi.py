import os
import sys
import json
import time

# Version identifier to verify deployment
WSGI_VERSION = "v2.0-20250926"
print(f"Loading WSGI application version: {WSGI_VERSION}")

# Load Tryton configuration once at startup
def load_tryton():
    """Load and configure Tryton application"""
    try:
        print(f"=== Loading Tryton Application {WSGI_VERSION} ===")
        from trytond.config import config
        from trytond.wsgi import app as tryton_app

        config_file = os.environ.get('TRYTON_CONFIG', '/app/railway-trytond.conf')
        print(f"Config file: {config_file}")

        if os.path.exists(config_file):
            config.update_etc(config_file)
            print(f"✓ Loaded Tryton config from: {config_file}")
        else:
            print(f"✗ Warning: Config file not found: {config_file}")

        # Test database connection
        try:
            from trytond.pool import Pool
            database_name = os.environ.get('DATABASE_NAME', 'divvyqueue_prod')
            print(f"Testing database connection to: {database_name}")

            # Try to get the pool (this will fail if DB not initialized)
            pool = Pool(database_name)
            print(f"✓ Database pool created successfully")

        except Exception as db_e:
            print(f"⚠ Database not ready: {db_e}")
            print("This is normal on first run - database may need initialization")

        print("✓ Tryton WSGI app loaded successfully")
        return tryton_app

    except Exception as e:
        print(f"✗ Failed to load Tryton: {e}")
        import traceback
        traceback.print_exc()
        return None

# Load Tryton app at module level
tryton_app = load_tryton()

def health_check(environ, start_response):
    """Health check endpoint for Railway"""
    response_data = {
        'status': 'healthy' if tryton_app else 'unhealthy',
        'timestamp': time.time(),
        'path': environ.get('PATH_INFO', ''),
        'method': environ.get('REQUEST_METHOD', 'GET'),
        'tryton_loaded': tryton_app is not None,
        'wsgi_version': WSGI_VERSION,
        'message': 'Tryton ready' if tryton_app else 'Tryton failed to load'
    }

    response_body = json.dumps(response_data).encode('utf-8')
    status = '200 OK' if tryton_app else '503 Service Unavailable'
    headers = [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(response_body)))
    ]

    start_response(status, headers)
    return [response_body]

def application(environ, start_response):
    """Main WSGI application"""
    path = environ.get('PATH_INFO', '')

    # Health check endpoint
    if path == '/health':
        return health_check(environ, start_response)

    # If Tryton loaded successfully, delegate everything else to it
    if tryton_app:
        try:
            return tryton_app(environ, start_response)
        except Exception as e:
            # Log error but still try to handle
            print(f"Tryton app error for path {path}: {e}")
            error_body = f'Tryton error: {str(e)}'.encode('utf-8')
            status = '500 Internal Server Error'
            headers = [
                ('Content-Type', 'text/plain'),
                ('Content-Length', str(len(error_body)))
            ]
            start_response(status, headers)
            return [error_body]
    else:
        # Tryton failed to load - return error
        error_body = b'Tryton failed to initialize. Check logs for details.'
        status = '503 Service Unavailable'
        headers = [
            ('Content-Type', 'text/plain'),
            ('Content-Length', str(len(error_body)))
        ]
        start_response(status, headers)
        return [error_body]

if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    port = int(os.environ.get('PORT', 8000))
    server = make_server('0.0.0.0', port, application)
    print(f"=== Starting WSGI Server on port {port} ===")
    if tryton_app:
        print("✓ Tryton loaded successfully - ready to serve web interface")
    else:
        print("✗ Tryton failed to load - check logs above")
    server.serve_forever()
