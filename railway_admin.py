#!/usr/bin/env python3
"""
Railway Administration Script for Tryton
This script provides administrative functions for Railway-deployed Tryton instances,
including security validation, health checks, and maintenance tasks.
"""

import os
import sys
import json
import time
import subprocess
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any

class RailwayAdmin:
    def __init__(self):
        self.app_url = self._get_app_url()
        self.environment = os.environ.get('RAILWAY_ENVIRONMENT', 'unknown')
        self.verbose = False

    def _get_app_url(self) -> str:
        """Determine the application URL"""
        # Try Railway-provided URL first
        railway_url = os.environ.get('RAILWAY_STATIC_URL')
        if railway_url:
            return f"https://{railway_url}"

        # Fall back to localhost if running locally
        port = os.environ.get('PORT', '8000')
        return f"http://localhost:{port}"

    def _print(self, message: str, level: str = 'INFO'):
        """Print formatted message"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
        prefix_map = {
            'INFO': '📋',
            'SUCCESS': '✅',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'DEBUG': '🔍'
        }
        prefix = prefix_map.get(level, '📋')
        print(f"[{timestamp}] {prefix} {message}")

    def _run_command(self, command: List[str], timeout: int = 60) -> Dict[str, Any]:
        """Run shell command and return result"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd='/app' if os.path.exists('/app') else '.'
            )

            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': ' '.join(command)
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': f'Command timed out after {timeout} seconds',
                'command': ' '.join(command)
            }
        except Exception as e:
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'command': ' '.join(command)
            }

    def _make_request(self, endpoint: str, method: str = 'GET') -> Optional[Dict]:
        """Make HTTP request to application"""
        try:
            url = f"{self.app_url}{endpoint}"
            response = requests.request(method, url, timeout=30)

            if response.headers.get('content-type', '').startswith('application/json'):
                return {
                    'success': response.status_code < 400,
                    'status_code': response.status_code,
                    'data': response.json()
                }
            else:
                return {
                    'success': response.status_code < 400,
                    'status_code': response.status_code,
                    'data': {'message': response.text[:500]}
                }

        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'status_code': 0,
                'data': {'error': str(e)}
            }

    def health_check(self) -> bool:
        """Perform comprehensive health check"""
        self._print("🏥 Starting Health Check", 'INFO')

        # 1. Basic health endpoint
        self._print("Checking health endpoint...", 'INFO')
        health_response = self._make_request('/health')

        if not health_response or not health_response['success']:
            self._print("Health endpoint failed", 'ERROR')
            return False

        health_data = health_response['data']
        self._print(f"Health Status: {health_data.get('status', 'unknown')}", 'SUCCESS')

        # 2. Security status from health check
        security_info = health_data.get('security', {})
        if security_info:
            score = security_info.get('score', 0)
            if score >= 80:
                self._print(f"Security Score: {score}/100", 'SUCCESS')
            else:
                self._print(f"Security Score: {score}/100 - Needs attention", 'WARNING')

        # 3. Database connectivity
        if health_data.get('tryton_loaded'):
            self._print("Tryton application loaded successfully", 'SUCCESS')
        else:
            self._print("Tryton application failed to load", 'ERROR')
            return False

        return True

    def security_validation(self) -> bool:
        """Run comprehensive security validation"""
        self._print("🔒 Starting Security Validation", 'INFO')

        # 1. Run local validation script
        self._print("Running environment validation...", 'INFO')
        if os.path.exists('validate_env.py'):
            result = self._run_command(['python3', 'validate_env.py'])
            if result['success']:
                self._print("Environment validation passed", 'SUCCESS')
            else:
                self._print("Environment validation failed", 'ERROR')
                if self.verbose:
                    self._print(f"Error: {result['stderr']}", 'ERROR')
                return False
        else:
            self._print("validate_env.py not found, checking via endpoint", 'WARNING')

        # 2. Check security endpoint
        self._print("Checking security endpoint...", 'INFO')
        security_response = self._make_request('/security-check')

        if not security_response:
            self._print("Could not connect to security endpoint", 'ERROR')
            return False

        if not security_response['success']:
            self._print("Security validation endpoint failed", 'ERROR')
            return False

        security_data = security_response['data']
        status = security_data.get('overall_status', 'unknown')

        if status == 'secure':
            self._print("Security validation passed", 'SUCCESS')
            return True
        elif status == 'needs_attention':
            self._print("Security validation passed with warnings", 'WARNING')
            warnings = security_data.get('warnings', [])
            for warning in warnings:
                self._print(f"Warning: {warning}", 'WARNING')
            return True
        else:
            self._print("Security validation failed", 'ERROR')
            errors = security_data.get('errors', [])
            for error in errors:
                self._print(f"Error: {error}", 'ERROR')
            return False

    def database_diagnostics(self) -> bool:
        """Check database status and performance"""
        self._print("🗄️  Starting Database Diagnostics", 'INFO')

        db_response = self._make_request('/db-diagnostics')

        if not db_response or not db_response['success']:
            self._print("Database diagnostics failed", 'ERROR')
            return False

        db_data = db_response['data']

        # Connection status
        if db_data.get('connection_status') == 'connected':
            self._print("Database connection: OK", 'SUCCESS')
        else:
            self._print("Database connection: FAILED", 'ERROR')
            return False

        # Database info
        db_info = db_data.get('database_info', {})
        if db_info:
            self._print(f"Database: {db_info.get('name', 'unknown')}", 'INFO')
            self._print(f"Version: {db_info.get('version', 'unknown')}", 'INFO')

        # Performance metrics
        performance = db_data.get('performance', {})
        if performance:
            query_time = performance.get('query_time', 0)
            if query_time < 1.0:
                self._print(f"Query performance: {query_time:.3f}s", 'SUCCESS')
            else:
                self._print(f"Query performance: {query_time:.3f}s (slow)", 'WARNING')

        return True

    def configuration_check(self) -> bool:
        """Check configuration files and permissions"""
        self._print("⚙️  Checking Configuration", 'INFO')

        config_file = '/app/railway-trytond.conf'

        # Check if config file exists
        if not os.path.exists(config_file):
            self._print("Configuration file not found", 'ERROR')
            return False

        self._print("Configuration file exists", 'SUCCESS')

        # Check file permissions
        try:
            stat_info = os.stat(config_file)
            perms = stat_info.st_mode & 0o777
            if perms == 0o600:
                self._print("Configuration file permissions: secure (600)", 'SUCCESS')
            else:
                self._print(f"Configuration file permissions: {oct(perms)} (should be 600)", 'WARNING')
        except Exception as e:
            self._print(f"Could not check file permissions: {e}", 'WARNING')

        # Check environment variables (without exposing values)
        required_vars = ['DATABASE_URL', 'ADMIN_PASSWORD', 'SECRET_KEY', 'FRONTEND_URL']
        missing_vars = []

        for var in required_vars:
            if os.environ.get(var):
                self._print(f"Environment variable {var}: set", 'SUCCESS')
            else:
                missing_vars.append(var)
                self._print(f"Environment variable {var}: missing", 'ERROR')

        return len(missing_vars) == 0

    def maintenance_tasks(self) -> bool:
        """Run maintenance tasks"""
        self._print("🔧 Running Maintenance Tasks", 'INFO')

        success = True

        # 1. Clean up old log files (if any)
        log_dirs = ['/app/logs', '/tmp']
        for log_dir in log_dirs:
            if os.path.exists(log_dir):
                try:
                    # Remove log files older than 7 days
                    result = self._run_command([
                        'find', log_dir, '-name', '*.log',
                        '-type', 'f', '-mtime', '+7', '-delete'
                    ])
                    if result['success']:
                        self._print(f"Cleaned old log files from {log_dir}", 'SUCCESS')
                    else:
                        self._print(f"Could not clean log files from {log_dir}", 'WARNING')
                except Exception as e:
                    self._print(f"Error cleaning {log_dir}: {e}", 'WARNING')

        # 2. Check disk space
        try:
            result = self._run_command(['df', '-h', '/app'])
            if result['success']:
                self._print("Disk space check completed", 'SUCCESS')
                if self.verbose:
                    self._print(result['stdout'], 'DEBUG')
            else:
                self._print("Could not check disk space", 'WARNING')
        except Exception as e:
            self._print(f"Disk space check failed: {e}", 'WARNING')

        # 3. Memory usage
        try:
            result = self._run_command(['free', '-h'])
            if result['success']:
                self._print("Memory check completed", 'SUCCESS')
                if self.verbose:
                    self._print(result['stdout'], 'DEBUG')
        except Exception as e:
            self._print(f"Memory check failed: {e}", 'WARNING')

        return success

    def full_diagnostic(self) -> bool:
        """Run complete diagnostic suite"""
        self._print("🚀 Starting Full Diagnostic Suite", 'INFO')
        self._print(f"Environment: {self.environment}", 'INFO')
        self._print(f"Application URL: {self.app_url}", 'INFO')

        results = {
            'health_check': self.health_check(),
            'security_validation': self.security_validation(),
            'database_diagnostics': self.database_diagnostics(),
            'configuration_check': self.configuration_check(),
            'maintenance_tasks': self.maintenance_tasks()
        }

        # Summary
        self._print("📊 Diagnostic Summary", 'INFO')
        passed = sum(results.values())
        total = len(results)

        for test_name, result in results.items():
            status = "PASS" if result else "FAIL"
            level = "SUCCESS" if result else "ERROR"
            self._print(f"{test_name}: {status}", level)

        overall_status = passed == total
        if overall_status:
            self._print(f"Overall Status: HEALTHY ({passed}/{total})", 'SUCCESS')
        else:
            self._print(f"Overall Status: NEEDS ATTENTION ({passed}/{total})", 'WARNING')

        return overall_status

def main():
    """Main CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description='Railway Tryton Administration Tool')
    parser.add_argument('command', choices=[
        'health', 'security', 'database', 'config', 'maintenance', 'full'
    ], help='Command to run')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--url', help='Override application URL')

    args = parser.parse_args()

    admin = RailwayAdmin()
    admin.verbose = args.verbose

    if args.url:
        admin.app_url = args.url

    # Command mapping
    commands = {
        'health': admin.health_check,
        'security': admin.security_validation,
        'database': admin.database_diagnostics,
        'config': admin.configuration_check,
        'maintenance': admin.maintenance_tasks,
        'full': admin.full_diagnostic
    }

    try:
        success = commands[args.command]()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        admin._print("Operation cancelled by user", 'WARNING')
        sys.exit(130)
    except Exception as e:
        admin._print(f"Unexpected error: {e}", 'ERROR')
        if args.verbose:
            import traceback
            admin._print(traceback.format_exc(), 'DEBUG')
        sys.exit(1)

if __name__ == '__main__':
    main()
