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
