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
    """Health check endpoint for Railway with security validation"""

    # Basic security checks
    security_status = {
        'config_file_exists': os.path.exists('/app/railway-trytond.conf'),
        'config_file_secure': False,
        'admin_password_set': bool(os.environ.get('ADMIN_PASSWORD')),
        'secret_key_set': bool(os.environ.get('SECRET_KEY')),
        'database_url_set': bool(os.environ.get('DATABASE_URL')),
        'cors_secure': False
    }

    # Check config file permissions
    if security_status['config_file_exists']:
        try:
            stat_info = os.stat('/app/railway-trytond.conf')
            security_status['config_file_secure'] = (stat_info.st_mode & 0o777) == 0o600
        except:
            pass

    # Check CORS security
    cors_origins = os.environ.get('CORS_ORIGINS', '')
    security_status['cors_secure'] = cors_origins and '*' not in cors_origins

    # Overall security score
    security_checks = [
        security_status['config_file_exists'],
        security_status['config_file_secure'],
        security_status['admin_password_set'],
        security_status['secret_key_set'],
        security_status['database_url_set'],
        security_status['cors_secure']
    ]
    security_score = sum(security_checks) / len(security_checks) * 100

    response_data = {
        'status': 'healthy' if tryton_app else 'unhealthy',
        'timestamp': time.time(),
        'path': environ.get('PATH_INFO', ''),
        'method': environ.get('REQUEST_METHOD', 'GET'),
        'tryton_loaded': tryton_app is not None,
        'wsgi_version': WSGI_VERSION,
        'message': 'Tryton ready' if tryton_app else 'Tryton failed to load',
        'security': {
            'score': round(security_score, 1),
            'status': 'secure' if security_score >= 80 else 'needs_attention',
            'checks_passed': sum(security_checks),
            'total_checks': len(security_checks)
        },
        'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'unknown')
    }

    # Include detailed security info for admin health checks (via query parameter)
    if environ.get('QUERY_STRING') == 'security=detailed':
        response_data['security']['details'] = security_status

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

def database_diagnostics(environ, start_response):
    """Database diagnostics endpoint to help troubleshoot issues"""
    try:
        import psycopg2
        from urllib.parse import urlparse

        diagnostics = {
            'timestamp': time.time(),
            'environment': {},
            'database': {},
            'tryton': {},
            'permissions': {}
        }

        # Environment check
        diagnostics['environment'] = {
            'DATABASE_URL': bool(os.environ.get('DATABASE_URL')),
            'DATABASE_NAME': os.environ.get('DATABASE_NAME', 'Not set'),
            'TRYTON_CONFIG': os.environ.get('TRYTON_CONFIG', 'Not set'),
            'config_file_exists': os.path.exists(os.environ.get('TRYTON_CONFIG', '/app/railway-trytond.conf'))
        }

        # Database connectivity test
        try:
            db_url = os.environ.get('DATABASE_URL')
            if db_url:
                conn = psycopg2.connect(db_url)
                cursor = conn.cursor()

                # Check basic connectivity
                cursor.execute("SELECT version();")
                pg_version = cursor.fetchone()[0]
                diagnostics['database']['postgresql_version'] = pg_version
                diagnostics['database']['connection'] = 'SUCCESS'

                # Check if database has Tryton tables
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name LIKE 'ir_%'
                    LIMIT 5;
                """)
                tables = [row[0] for row in cursor.fetchall()]
                diagnostics['database']['tryton_tables'] = tables
                diagnostics['database']['has_tryton_schema'] = len(tables) > 0

                # Check for users table specifically
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = 'res_user'
                    );
                """)
                has_users_table = cursor.fetchone()[0]
                diagnostics['database']['has_users_table'] = has_users_table

                if has_users_table:
                    cursor.execute("SELECT COUNT(*) FROM res_user;")
                    user_count = cursor.fetchone()[0]
                    diagnostics['database']['user_count'] = user_count

                conn.close()
            else:
                diagnostics['database']['connection'] = 'FAILED - No DATABASE_URL'
        except Exception as e:
            diagnostics['database']['connection'] = f'FAILED - {str(e)}'

        # Tryton configuration test
        try:
            from trytond.config import config
            config_file = os.environ.get('TRYTON_CONFIG', '/app/railway-trytond.conf')
            if os.path.exists(config_file):
                config.update_etc(config_file)
                diagnostics['tryton']['config_loaded'] = True
                diagnostics['tryton']['database_uri'] = config.get('database', 'uri', default='Not set')
            else:
                diagnostics['tryton']['config_loaded'] = False
        except Exception as e:
            diagnostics['tryton']['config_error'] = str(e)

        # Tryton pool test
        try:
            from trytond.pool import Pool
            database_name = os.environ.get('DATABASE_NAME', 'divvyqueue_prod')
            pool = Pool(database_name)
            diagnostics['tryton']['pool_created'] = True

            try:
                pool.init()
                diagnostics['tryton']['pool_initialized'] = True

                # Try to access a basic model
                with pool.transaction().start(database_name, 1, context={}):
                    User = pool.get('res.user')
                    users = User.search([])
                    diagnostics['tryton']['user_model_accessible'] = True
                    diagnostics['tryton']['users_found'] = len(users)

            except Exception as e:
                diagnostics['tryton']['pool_init_error'] = str(e)

        except Exception as e:
            diagnostics['tryton']['pool_error'] = str(e)

        response_body = json.dumps(diagnostics, indent=2).encode('utf-8')
        status = '200 OK'
        headers = add_cors_headers([
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(response_body)))
        ])
        start_response(status, headers)
        return [response_body]

    except Exception as e:
        error_data = {'error': 'Diagnostics failed', 'message': str(e)}
        error_body = json.dumps(error_data).encode('utf-8')
        status = '500 Internal Server Error'
        headers = add_cors_headers([
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(error_body)))
        ])
        start_response(status, headers)
        return [error_body]

def security_validation_endpoint(environ, start_response):
    """Security validation endpoint for Railway administration"""

    # Only allow GET and POST methods
    method = environ.get('REQUEST_METHOD', 'GET')
    if method not in ['GET', 'POST']:
        response_data = {'error': 'Method not allowed'}
        response_body = json.dumps(response_data).encode('utf-8')
        headers = [('Content-Type', 'application/json')]
        headers = add_cors_headers(headers)
        start_response('405 Method Not Allowed', headers)
        return [response_body]

    try:
        # Run security validation
        import subprocess
        import tempfile

        validation_results = {
            'timestamp': time.time(),
            'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'unknown'),
            'validation_passed': False,
            'errors': [],
            'warnings': [],
            'info': []
        }

        # Run environment validation script
        try:
            result = subprocess.run(
                ['python3', 'validate_env.py'],
                capture_output=True,
                text=True,
                timeout=30,
                cwd='/app'
            )

            if result.returncode == 0:
                validation_results['validation_passed'] = True
                validation_results['info'].append('Environment validation passed')
            else:
                validation_results['errors'].append('Environment validation failed')

            # Parse output for detailed results
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if '❌ ERROR:' in line:
                    validation_results['errors'].append(line.replace('❌ ERROR: ', ''))
                elif '⚠️  WARNING:' in line:
                    validation_results['warnings'].append(line.replace('⚠️  WARNING: ', ''))
                elif '✅ SUCCESS:' in line:
                    validation_results['info'].append(line.replace('✅ SUCCESS: ', ''))

        except subprocess.TimeoutExpired:
            validation_results['errors'].append('Validation script timed out')
        except Exception as e:
            validation_results['errors'].append(f'Validation script error: {str(e)}')

        # Additional security checks
        config_file = '/app/railway-trytond.conf'
        if os.path.exists(config_file):
            try:
                stat_info = os.stat(config_file)
                perms = stat_info.st_mode & 0o777
                if perms == 0o600:
                    validation_results['info'].append('Configuration file has secure permissions (600)')
                else:
                    validation_results['warnings'].append(f'Configuration file permissions: {oct(perms)} (should be 600)')
            except Exception as e:
                validation_results['errors'].append(f'Cannot check config file permissions: {str(e)}')
        else:
            validation_results['errors'].append('Configuration file not found')

        # Check environment variables without exposing values
        required_vars = ['DATABASE_URL', 'ADMIN_PASSWORD', 'SECRET_KEY']
        for var in required_vars:
            if os.environ.get(var):
                validation_results['info'].append(f'{var} is configured')
            else:
                validation_results['errors'].append(f'{var} is not set')

        # Check CORS configuration
        cors_origins = os.environ.get('CORS_ORIGINS', '')
        if cors_origins:
            if '*' in cors_origins:
                validation_results['errors'].append('CORS_ORIGINS contains wildcard (*) - security risk')
            else:
                validation_results['info'].append('CORS_ORIGINS is securely configured')
        else:
            validation_results['warnings'].append('CORS_ORIGINS not set')

        # Overall status
        validation_results['overall_status'] = (
            'secure' if validation_results['validation_passed'] and not validation_results['errors']
            else 'needs_attention' if validation_results['warnings'] and not validation_results['errors']
            else 'insecure'
        )

        response_body = json.dumps(validation_results, indent=2).encode('utf-8')
        status = '200 OK' if validation_results['validation_passed'] else '400 Bad Request'
        headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(response_body)))
        ]
        headers = add_cors_headers(headers)

        start_response(status, headers)
        return [response_body]

    except Exception as e:
        error_response = {
            'error': 'Security validation failed',
            'message': str(e),
            'timestamp': time.time()
        }
        response_body = json.dumps(error_response).encode('utf-8')
        headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(response_body)))
        ]
        headers = add_cors_headers(headers)

        start_response('500 Internal Server Error', headers)
        return [response_body]

def init_database_endpoint(environ, start_response):
    """Database initialization endpoint with robust error handling"""
    try:
        from trytond.pool import Pool
        from trytond.config import config
        from trytond.modules import get_module_list
        import subprocess

        config_file = os.environ.get('TRYTON_CONFIG', '/app/railway-trytond.conf')
        database_name = os.environ.get('DATABASE_NAME', 'divvyqueue_prod')

        if os.path.exists(config_file):
            config.update_etc(config_file)

        response_data = {
            'status': 'initializing',
            'database': database_name,
            'steps': []
        }

        # Step 1: Check if database is already initialized
        try:
            pool = Pool(database_name)
            pool.init()
            with pool.transaction().start(database_name, 1, context={}):
                User = pool.get('res.user')
                users = User.search([])
                response_data.update({
                    'status': 'already_initialized',
                    'message': f'Database already initialized with {len(users)} users',
                    'steps': ['Database check: Already initialized']
                })
        except Exception as check_error:
            response_data['steps'].append(f'Database check: Not initialized - {str(check_error)}')

            # Step 2: Initialize database with core modules
            try:
                response_data['steps'].append('Starting database initialization...')

                # Create database structure
                cmd = [
                    'trytond-admin',
                    '-c', config_file,
                    '-d', database_name,
                    '--all'
                ]

                response_data['steps'].append(f'Running: {" ".join(cmd)}')
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

                if result.returncode == 0:
                    response_data['steps'].append('Database structure created successfully')

                    # Step 3: Set admin password if provided
                    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin')
                    try:
                        cmd_password = [
                            'trytond-admin',
                            '-c', config_file,
                            '-d', database_name,
                            '--password'
                        ]

                        response_data['steps'].append('Setting admin password...')
                        result_password = subprocess.run(
                            cmd_password,
                            input=admin_password,
                            text=True,
                            capture_output=True,
                            timeout=60
                        )

                        if result_password.returncode == 0:
                            response_data['steps'].append('Admin password set successfully')
                        else:
                            response_data['steps'].append(f'Password setting failed: {result_password.stderr}')

                    except Exception as pwd_error:
                        response_data['steps'].append(f'Password setting error: {str(pwd_error)}')

                    # Step 4: Verify initialization
                    try:
                        pool = Pool(database_name)
                        pool.init()
                        with pool.transaction().start(database_name, 1, context={}):
                            User = pool.get('res.user')
                            users = User.search([])
                            response_data.update({
                                'status': 'success',
                                'message': f'Database initialized successfully with {len(users)} users',
                            })
                            response_data['steps'].append(f'Verification: Found {len(users)} users')
                    except Exception as verify_error:
                        response_data.update({
                            'status': 'partial_success',
                            'message': f'Database created but verification failed: {str(verify_error)}'
                        })
                        response_data['steps'].append(f'Verification failed: {str(verify_error)}')

                else:
                    response_data.update({
                        'status': 'failed',
                        'message': f'Database initialization failed: {result.stderr}'
                    })
                    response_data['steps'].append(f'Initialization failed: {result.stderr}')
                    if result.stdout:
                        response_data['steps'].append(f'STDOUT: {result.stdout}')

            except subprocess.TimeoutExpired:
                response_data.update({
                    'status': 'timeout',
                    'message': 'Database initialization timed out after 10 minutes'
                })
                response_data['steps'].append('ERROR: Initialization timeout')

            except Exception as init_error:
                response_data.update({
                    'status': 'error',
                    'message': f'Initialization error: {str(init_error)}'
                })
                response_data['steps'].append(f'Initialization error: {str(init_error)}')

        response_body = json.dumps(response_data, indent=2).encode('utf-8')
        status = '200 OK'
        headers = add_cors_headers([
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(response_body)))
        ])
        start_response(status, headers)
        return [response_body]

    except Exception as e:
        error_data = {
            'status': 'error',
            'message': f'Endpoint error: {str(e)}',
            'steps': [f'Critical error: {str(e)}']
        }
        error_body = json.dumps(error_data, indent=2).encode('utf-8')
        status = '500 Internal Server Error'
        headers = add_cors_headers([
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(error_body)))
        ])
        start_response(status, headers)
        return [error_body]

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

    # Security validation endpoint
    if path == '/security-check':
        return security_validation_endpoint(environ, start_response)

    # Database initialization endpoint
    if path == '/init-database' and method == 'POST':
        return init_database_endpoint(environ, start_response)

    # Database diagnostics endpoint
    if path == '/db-diagnostics':
        return database_diagnostics(environ, start_response)

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
