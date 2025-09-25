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
