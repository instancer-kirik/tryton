#!/usr/bin/env python3
"""
Environment Variable Validation Script for Tryton Railway Deployment
This script validates all required and recommended environment variables
for a secure production deployment.
"""

import os
import re
import sys
import urllib.parse
from typing import Dict, List, Tuple, Optional


class ValidationResult:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.success: List[str] = []

    def add_error(self, message: str):
        self.errors.append(f"❌ ERROR: {message}")

    def add_warning(self, message: str):
        self.warnings.append(f"⚠️  WARNING: {message}")

    def add_info(self, message: str):
        self.info.append(f"ℹ️  INFO: {message}")

    def add_success(self, message: str):
        self.success.append(f"✅ SUCCESS: {message}")

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def print_results(self):
        """Print all validation results"""
        if self.success:
            print("\n=== VALIDATION PASSED ===")
            for msg in self.success:
                print(msg)

        if self.info:
            print("\n=== INFORMATION ===")
            for msg in self.info:
                print(msg)

        if self.warnings:
            print("\n=== WARNINGS ===")
            for msg in self.warnings:
                print(msg)

        if self.errors:
            print("\n=== ERRORS ===")
            for msg in self.errors:
                print(msg)


def validate_password_strength(password: str, name: str) -> Tuple[bool, List[str]]:
    """Validate password strength according to security best practices"""
    issues = []

    if len(password) < 12:
        issues.append(f"{name} should be at least 12 characters long")

    if not re.search(r'[A-Z]', password):
        issues.append(f"{name} should contain uppercase letters")

    if not re.search(r'[a-z]', password):
        issues.append(f"{name} should contain lowercase letters")

    if not re.search(r'[0-9]', password):
        issues.append(f"{name} should contain numbers")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        issues.append(f"{name} should contain special characters")

    # Check for common weak passwords
    weak_patterns = [
        'password', 'admin', '123456', 'qwerty', 'letmein',
        'welcome', 'monkey', 'dragon', 'secret', 'master'
    ]

    password_lower = password.lower()
    for pattern in weak_patterns:
        if pattern in password_lower:
            issues.append(f"{name} contains common weak pattern: {pattern}")

    return len(issues) == 0, issues


def validate_database_url(database_url: str) -> Tuple[bool, Dict, List[str]]:
    """Validate DATABASE_URL format and security"""
    issues = []
    db_info = {}

    try:
        parsed = urllib.parse.urlparse(database_url)

        db_info = {
            'scheme': parsed.scheme,
            'hostname': parsed.hostname,
            'port': parsed.port,
            'database': parsed.path.lstrip('/') if parsed.path else None,
            'username': parsed.username,
            'password': parsed.password
        }

        # Validate scheme
        if parsed.scheme not in ['postgresql', 'postgres']:
            issues.append(f"Database scheme should be 'postgresql' or 'postgres', got '{parsed.scheme}'")

        # Check for required components
        if not parsed.hostname:
            issues.append("Database hostname is missing")

        if not parsed.username:
            issues.append("Database username is missing")

        if not parsed.password:
            issues.append("Database password is missing")

        if not db_info['database']:
            issues.append("Database name is missing")

        # Security checks
        if parsed.hostname in ['localhost', '127.0.0.1']:
            issues.append("Database should not use localhost in production")

        # Check for SSL parameters
        query_params = urllib.parse.parse_qs(parsed.query)
        ssl_mode = query_params.get('sslmode', [''])[0]
        if not ssl_mode or ssl_mode == 'disable':
            issues.append("Database connection should use SSL (add ?sslmode=require)")

    except Exception as e:
        issues.append(f"Invalid DATABASE_URL format: {e}")
        return False, {}, issues

    return len(issues) == 0, db_info, issues


def validate_cors_origins(cors_origins: str) -> Tuple[bool, List[str]]:
    """Validate CORS origins for security"""
    issues = []

    if not cors_origins:
        issues.append("CORS_ORIGINS should not be empty")
        return False, issues

    if cors_origins.strip() == '*':
        issues.append("CORS_ORIGINS should not use wildcard (*) in production")
        return False, issues

    origins = [origin.strip() for origin in cors_origins.split(',')]

    for origin in origins:
        if origin == '*':
            issues.append("CORS_ORIGINS contains wildcard (*) - this is insecure")
        elif origin.startswith('http://') and 'localhost' not in origin:
            issues.append(f"CORS origin uses HTTP instead of HTTPS: {origin}")
        elif not origin.startswith(('http://', 'https://')):
            issues.append(f"Invalid CORS origin format: {origin}")

    return len(issues) == 0, issues


def validate_environment_variables() -> ValidationResult:
    """Validate all environment variables for Railway deployment"""
    result = ValidationResult()

    # Required environment variables
    required_vars = {
        'DATABASE_URL': 'PostgreSQL database connection string',
        'ADMIN_PASSWORD': 'Tryton administrator password',
        'SECRET_KEY': 'Application secret key for cryptographic operations',
        'FRONTEND_URL': 'URL of the DivvyQueue frontend application',
        'CORS_ORIGINS': 'Comma-separated list of allowed CORS origins'
    }

    # Recommended environment variables
    recommended_vars = {
        'DATABASE_NAME': 'Database name (defaults to divvyqueue_prod)',
        'SESSION_SECRET': 'Secret for session encryption',
        'SESSION_TIMEOUT': 'Session timeout in seconds',
        'LOG_LEVEL': 'Logging level (INFO recommended for production)',
        'ADMIN_EMAIL': 'Administrator email address',
        'EMAIL_HOST': 'SMTP server hostname for email notifications',
        'EMAIL_USER': 'SMTP username',
        'EMAIL_PASSWORD': 'SMTP password or app-specific password'
    }

    # Forbidden values in production
    forbidden_values = {
        'ADMIN_PASSWORD': ['admin', 'password', '123456', 'root', 'tryton'],
        'SECRET_KEY': ['dev', 'development', 'secret', 'key', 'changeme'],
        'LOG_LEVEL': ['DEBUG'],
        'CORS_ORIGINS': ['*']
    }

    print("=== TRYTON RAILWAY DEPLOYMENT VALIDATION ===")
    print(f"Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'unknown')}")
    print(f"Validation time: {os.popen('date -u').read().strip()}")

    # Check required variables
    print("\n--- REQUIRED ENVIRONMENT VARIABLES ---")
    missing_required = []

    for var, description in required_vars.items():
        value = os.environ.get(var)
        if not value:
            missing_required.append(var)
            result.add_error(f"{var} is required - {description}")
        else:
            result.add_success(f"{var} is set")

            # Check forbidden values
            if var in forbidden_values:
                if value.lower() in [v.lower() for v in forbidden_values[var]]:
                    result.add_error(f"{var} uses forbidden production value: {value}")

    if missing_required:
        result.add_error(f"Missing required variables: {', '.join(missing_required)}")
        return result

    # Validate specific variables
    print("\n--- SECURITY VALIDATION ---")

    # Validate admin password
    admin_password = os.environ.get('ADMIN_PASSWORD')
    if admin_password:
        is_strong, password_issues = validate_password_strength(admin_password, 'ADMIN_PASSWORD')
        if is_strong:
            result.add_success("ADMIN_PASSWORD meets security requirements")
        else:
            for issue in password_issues:
                result.add_warning(issue)

    # Validate secret key
    secret_key = os.environ.get('SECRET_KEY')
    if secret_key:
        if len(secret_key) < 32:
            result.add_warning("SECRET_KEY should be at least 32 characters long")
        elif len(secret_key) >= 50:
            result.add_success("SECRET_KEY length is excellent")
        else:
            result.add_success("SECRET_KEY length is acceptable")

    # Validate database URL
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        is_valid, db_info, db_issues = validate_database_url(database_url)
        if is_valid:
            result.add_success("DATABASE_URL format is valid")
            result.add_info(f"Database: {db_info.get('hostname', 'unknown')}:{db_info.get('port', 'default')}")
        else:
            for issue in db_issues:
                result.add_error(f"DATABASE_URL: {issue}")

    # Validate CORS origins
    cors_origins = os.environ.get('CORS_ORIGINS')
    if cors_origins:
        is_valid, cors_issues = validate_cors_origins(cors_origins)
        if is_valid:
            result.add_success("CORS_ORIGINS configuration is secure")
        else:
            for issue in cors_issues:
                result.add_error(f"CORS_ORIGINS: {issue}")

    # Check recommended variables
    print("\n--- RECOMMENDED ENVIRONMENT VARIABLES ---")
    for var, description in recommended_vars.items():
        value = os.environ.get(var)
        if value:
            result.add_success(f"{var} is configured")
        else:
            result.add_info(f"{var} not set - {description}")

    # Production-specific checks
    print("\n--- PRODUCTION READINESS ---")

    # Check log level
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    if log_level.upper() == 'DEBUG':
        result.add_error("LOG_LEVEL should not be DEBUG in production")
    elif log_level.upper() in ['INFO', 'WARNING', 'ERROR']:
        result.add_success(f"LOG_LEVEL is appropriate for production: {log_level}")

    # Check session timeout
    session_timeout = os.environ.get('SESSION_TIMEOUT')
    if session_timeout:
        try:
            timeout_seconds = int(session_timeout)
            if timeout_seconds > 7200:  # 2 hours
                result.add_warning("SESSION_TIMEOUT is very long (>2 hours), consider shorter timeout")
            elif timeout_seconds < 300:  # 5 minutes
                result.add_warning("SESSION_TIMEOUT is very short (<5 minutes), may affect user experience")
            else:
                result.add_success(f"SESSION_TIMEOUT is reasonable: {timeout_seconds} seconds")
        except ValueError:
            result.add_error("SESSION_TIMEOUT must be a valid integer (seconds)")

    # Check email configuration completeness
    email_vars = ['EMAIL_HOST', 'EMAIL_USER', 'EMAIL_PASSWORD']
    email_set = [var for var in email_vars if os.environ.get(var)]

    if len(email_set) == len(email_vars):
        result.add_success("Email configuration is complete")
    elif len(email_set) > 0:
        missing_email = [var for var in email_vars if var not in email_set]
        result.add_warning(f"Partial email configuration - missing: {', '.join(missing_email)}")
    else:
        result.add_info("Email not configured (optional but recommended for notifications)")

    return result


def main():
    """Main validation function"""
    print("🔒 Tryton Railway Deployment Security Validator")
    print("=" * 50)

    result = validate_environment_variables()
    result.print_results()

    print("\n" + "=" * 50)

    if result.has_errors():
        print("❌ VALIDATION FAILED - Please fix the errors above before deploying")
        print("\nNext steps:")
        print("1. Set missing environment variables in Railway dashboard")
        print("2. Fix security issues identified above")
        print("3. Run this validation script again")
        print("4. Review SECURITY.md for additional security guidance")
        sys.exit(1)
    else:
        print("✅ VALIDATION PASSED - Environment is ready for production deployment")
        print("\nNext steps:")
        print("1. Review any warnings and consider improvements")
        print("2. Deploy to Railway")
        print("3. Test the deployment with health checks")
        print("4. Set up monitoring and log analysis")
        sys.exit(0)


if __name__ == '__main__':
    main()
