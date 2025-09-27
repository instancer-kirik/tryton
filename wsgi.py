import os
import sys
import json
import time
from wsgiref.util import FileWrapper

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

def add_cors_headers(headers):
    """Add CORS headers to allow cross-origin requests"""
    cors_headers = [
        ('Access-Control-Allow-Origin', '*'),
        ('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'),
        ('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With'),
        ('Access-Control-Max-Age', '86400'),
    ]
    return headers + cors_headers

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
    headers = add_cors_headers(headers)

    start_response(status, headers)
    return [response_body]

def serve_static_file(file_path, environ, start_response):
    """Serve static files for SAO web client"""
    try:
        if not os.path.exists(file_path):
            status = '404 Not Found'
            headers = [('Content-Type', 'text/plain')]
            start_response(status, headers)
            return [b'File not found']

        # Determine content type
        content_type = 'text/html'
        if file_path.endswith('.js'):
            content_type = 'application/javascript'
        elif file_path.endswith('.css'):
            content_type = 'text/css'
        elif file_path.endswith('.png'):
            content_type = 'image/png'
        elif file_path.endswith('.svg'):
            content_type = 'image/svg+xml'
        elif file_path.endswith('.wav'):
            content_type = 'audio/wav'
        elif file_path.endswith('.json'):
            content_type = 'application/json'

        with open(file_path, 'rb') as f:
            file_data = f.read()

        status = '200 OK'
        headers = [
            ('Content-Type', content_type),
            ('Content-Length', str(len(file_data)))
        ]
        headers = add_cors_headers(headers)
        start_response(status, headers)
        return [file_data]

    except Exception as e:
        print(f"Error serving static file {file_path}: {e}")
        status = '500 Internal Server Error'
        headers = [('Content-Type', 'text/plain')]
        start_response(status, headers)
        return [f'Error serving file: {str(e)}'.encode('utf-8')]

def application(environ, start_response):
    """Main WSGI application"""
    path = environ.get('PATH_INFO', '').rstrip('/')
    method = environ.get('REQUEST_METHOD', 'GET')

    # Handle CORS preflight requests
    if method == 'OPTIONS':
        status = '200 OK'
        headers = add_cors_headers([('Content-Length', '0')])
        start_response(status, headers)
        return [b'']

    # Health check endpoint
    if path == '/health':
        return health_check(environ, start_response)

    # Serve SAO static files
    sao_root = '/app/sao'
    if path == '' or path == '/':
        # Serve index.html for root path
        return serve_static_file(os.path.join(sao_root, 'index.html'), environ, start_response)
    elif path.startswith('/dist/') or path.startswith('/images/') or path.startswith('/sounds/') or path.startswith('/locale/'):
        # Serve static assets
        file_path = os.path.join(sao_root, path.lstrip('/'))
        return serve_static_file(file_path, environ, start_response)

    # If Tryton loaded successfully, delegate API requests to it
    if tryton_app:
        try:
            # Wrap Tryton response to add CORS headers
            def cors_start_response(status, response_headers, exc_info=None):
                response_headers = add_cors_headers(response_headers)
                return start_response(status, response_headers, exc_info)

            return tryton_app(environ, cors_start_response)
        except Exception as e:
            # Log error but still try to handle
            print(f"Tryton app error for path {path}: {e}")
            error_body = f'Tryton error: {str(e)}'.encode('utf-8')
            status = '500 Internal Server Error'
            headers = [
                ('Content-Type', 'text/plain'),
                ('Content-Length', str(len(error_body)))
            ]
            headers = add_cors_headers(headers)
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
        headers = add_cors_headers(headers)
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
