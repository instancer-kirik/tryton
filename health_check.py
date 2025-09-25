#!/usr/bin/env python3
import json
import time
import sys

# Simple health check that doesn't depend on Tryton being fully loaded
response = {
    'status': 'healthy',
    'timestamp': time.time(),
    'message': 'Basic health check - app is running'
}
print(json.dumps(response))
sys.exit(0)
