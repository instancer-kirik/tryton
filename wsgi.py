import os
import sys
import json
import time

# Simple WSGI application for debugging
def simple_health_check(environ, start_response):
    response_data = {
        'status': 'healthy',
        'timestamp': time.time(),
        'path': environ.get('PATH_INFO', ''),
        'method': environ.get('REQUEST_METHOD', 'GET'),
        'message': 'Simple health check working'
    }

    response_body = json.dumps(response_data).encode('utf-8')

    status = '200 OK'
    headers = [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(response_body)))
    ]

    start_response(status, headers)
    return [response_body]

def application(environ, start_response):
    path = environ.get('PATH_INFO', '')

    if path == '/health':
        return simple_health_check(environ, start_response)
    elif path == '/':
        # Simple root response
        response_body = b'Tryton is starting up...'
        status = '200 OK'
        headers = [
            ('Content-Type', 'text/plain'),
            ('Content-Length', str(len(response_body)))
        ]
        start_response(status, headers)
        return [response_body]
    else:
        # Try to load Tryton for other paths
        try:
            from trytond.config import config
            from trytond.wsgi import app as tryton_app

            config_file = os.environ.get('TRYTON_CONFIG', '/app/railway-trytond.conf')
            if os.path.exists(config_file):
                config.update_etc(config_file)

            return tryton_app(environ, start_response)
        except Exception as e:
            # Return error info
            error_body = f'Tryton not ready: {str(e)}'.encode('utf-8')
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
    print(f"Starting server on port {port}...")
    server.serve_forever()
