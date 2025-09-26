#!/usr/bin/env python3
"""
Database Initialization Helper for Tryton on Railway
This script initializes the Tryton database if it doesn't exist yet.
"""

import os
import sys
import time
import subprocess
from pathlib import Path

def log(message):
    """Print timestamped log message"""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def check_database_connection():
    """Check if database is accessible"""
    try:
        import psycopg2
        from urllib.parse import urlparse

        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            log("ERROR: No DATABASE_URL environment variable found")
            return False

        log(f"Testing database connection...")
        conn = psycopg2.connect(db_url)
        conn.close()
        log("✓ Database connection successful")
        return True

    except Exception as e:
        log(f"✗ Database connection failed: {e}")
        return False

def is_database_initialized():
    """Check if Tryton database is already initialized"""
    try:
        from trytond.pool import Pool
        from trytond.config import config

        config_file = os.environ.get('TRYTON_CONFIG', '/app/railway-trytond.conf')
        if os.path.exists(config_file):
            config.update_etc(config_file)

        database_name = os.environ.get('DATABASE_NAME', 'divvyqueue_prod')
        log(f"Checking if database '{database_name}' is initialized...")

        # Try to access the database pool
        pool = Pool(database_name)

        # Try to access a basic table
        with pool.transaction().start(database_name, 1, context={}):
            User = pool.get('res.user')
            users = User.search([])
            log(f"✓ Database initialized with {len(users)} users")
            return True

    except Exception as e:
        log(f"Database not initialized: {e}")
        return False

def initialize_database():
    """Initialize Tryton database with core modules"""
    try:
        config_file = os.environ.get('TRYTON_CONFIG', '/app/railway-trytond.conf')
        database_name = os.environ.get('DATABASE_NAME', 'divvyqueue_prod')

        log(f"Initializing Tryton database '{database_name}'...")
        log(f"Using config file: {config_file}")

        # Run trytond-admin to initialize database
        cmd = [
            'trytond-admin',
            '-c', config_file,
            '-d', database_name,
            '--all'
        ]

        log(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            log("✓ Database initialization completed successfully")
            log("STDOUT:", result.stdout)
        else:
            log("✗ Database initialization failed")
            log("STDERR:", result.stderr)
            log("STDOUT:", result.stdout)
            return False

        # Set admin password if provided
        admin_password = os.environ.get('TRYTON_ADMIN_PASSWORD')
        if admin_password:
            log("Setting admin password...")
            cmd = [
                'trytond-admin',
                '-c', config_file,
                '-d', database_name,
                '--password'
            ]

            result = subprocess.run(
                cmd,
                input=admin_password,
                text=True,
                capture_output=True,
                timeout=60
            )

            if result.returncode == 0:
                log("✓ Admin password set successfully")
            else:
                log("⚠ Failed to set admin password")
                log("STDERR:", result.stderr)

        return True

    except subprocess.TimeoutExpired:
        log("✗ Database initialization timed out")
        return False
    except Exception as e:
        log(f"✗ Database initialization error: {e}")
        return False

def update_admin_email():
    """Update admin user email if provided"""
    try:
        admin_email = os.environ.get('ADMIN_EMAIL')
        if not admin_email:
            log("No ADMIN_EMAIL provided, skipping email update")
            return True

        from trytond.pool import Pool
        from trytond.transaction import Transaction
        from trytond.config import config

        config_file = os.environ.get('TRYTON_CONFIG', '/app/railway-trytond.conf')
        database_name = os.environ.get('DATABASE_NAME', 'divvyqueue_prod')

        if os.path.exists(config_file):
            config.update_etc(config_file)

        pool = Pool(database_name)
        pool.init()

        with Transaction().start(database_name, 1, context={}):
            User = pool.get('res.user')
            admin_users = User.search([('login', '=', 'admin')])

            if admin_users:
                admin = admin_users[0]
                admin.email = admin_email
                admin.save()
                log(f"✓ Admin email updated to: {admin_email}")
            else:
                log("⚠ Admin user not found")

        return True

    except Exception as e:
        log(f"⚠ Failed to update admin email: {e}")
        return False

def main():
    """Main initialization process"""
    log("=== Tryton Database Initialization ===")

    # Check environment
    log("Checking environment...")
    required_vars = ['DATABASE_URL', 'DATABASE_NAME', 'TRYTON_CONFIG']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        log(f"✗ Missing required environment variables: {missing_vars}")
        return False

    log("✓ All required environment variables present")

    # Check database connectivity
    if not check_database_connection():
        log("✗ Cannot connect to database - aborting")
        return False

    # Check if database is already initialized
    if is_database_initialized():
        log("✓ Database already initialized - skipping initialization")

        # Still try to update admin email
        update_admin_email()
        return True

    # Initialize database
    log("Database needs initialization...")
    if not initialize_database():
        log("✗ Database initialization failed")
        return False

    # Update admin email
    update_admin_email()

    # Verify initialization
    if is_database_initialized():
        log("✓ Database initialization verified successfully")
        log("=== Initialization Complete ===")
        return True
    else:
        log("✗ Database initialization verification failed")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
