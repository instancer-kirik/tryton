#!/usr/bin/env python3
"""
Railway Database Setup Script for Tryton
This script handles database creation and initialization for Railway PostgreSQL
"""

import os
import sys
import psycopg2
import urllib.parse
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def parse_database_url(database_url):
    """Parse DATABASE_URL and return connection components"""
    try:
        parsed = urllib.parse.urlparse(database_url)
        return {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'user': parsed.username,
            'password': parsed.password,
            'database': parsed.path.lstrip('/') if parsed.path else 'postgres'
        }
    except Exception as e:
        print(f"ERROR: Could not parse DATABASE_URL: {e}")
        return None

def connect_to_postgres(db_config, database='postgres'):
    """Connect to PostgreSQL server"""
    try:
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn
    except Exception as e:
        print(f"ERROR: Could not connect to PostgreSQL: {e}")
        return None

def database_exists(conn, database_name):
    """Check if database exists"""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (database_name,)
        )
        result = cursor.fetchone()
        cursor.close()
        return result is not None
    except Exception as e:
        print(f"ERROR: Could not check database existence: {e}")
        return False

def create_database(conn, database_name):
    """Create database if it doesn't exist"""
    try:
        cursor = conn.cursor()
        # Use identifier to safely quote database name
        cursor.execute(
            f'CREATE DATABASE "{database_name}" WITH ENCODING \'UTF8\''
        )
        cursor.close()
        print(f"✓ Created database: {database_name}")
        return True
    except Exception as e:
        print(f"ERROR: Could not create database {database_name}: {e}")
        return False

def list_databases(conn):
    """List all databases"""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname"
        )
        databases = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return databases
    except Exception as e:
        print(f"ERROR: Could not list databases: {e}")
        return []

def run_trytond_init(database_name, config_file='/app/railway-trytond.conf'):
    """Run trytond-admin to initialize the database"""
    try:
        import subprocess

        print(f"Initializing Tryton database '{database_name}'...")

        cmd = [
            'trytond-admin',
            '-c', config_file,
            '-d', database_name,
            '--all'
        ]

        print(f"Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode == 0:
            print("✓ Tryton database initialization completed successfully")
            if result.stdout:
                print("STDOUT:", result.stdout)
            return True
        else:
            print(f"✗ Tryton initialization failed with return code: {result.returncode}")
            if result.stderr:
                print("STDERR:", result.stderr)
            if result.stdout:
                print("STDOUT:", result.stdout)
            return False

    except subprocess.TimeoutExpired:
        print("✗ Tryton initialization timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"✗ Error running trytond-admin: {e}")
        return False

def main():
    """Main database setup function"""
    print("=== Railway Database Setup for Tryton ===")

    # Get environment variables
    database_url = os.environ.get('DATABASE_URL')
    target_database = os.environ.get('DATABASE_NAME', 'divvyqueue_prod')

    if not database_url:
        print("ERROR: DATABASE_URL environment variable is required")
        return False

    print(f"Target database: {target_database}")

    # Parse DATABASE_URL
    db_config = parse_database_url(database_url)
    if not db_config:
        return False

    print(f"Connecting to PostgreSQL at: {db_config['host']}:{db_config['port']}")

    # Connect to PostgreSQL server (using default 'postgres' database)
    conn = connect_to_postgres(db_config, 'postgres')
    if not conn:
        # Try connecting to the database specified in URL
        print("Trying to connect using database from URL...")
        conn = connect_to_postgres(db_config, db_config['database'])
        if not conn:
            return False

    try:
        # List existing databases
        databases = list_databases(conn)
        print(f"Existing databases: {databases}")

        # Check if target database exists
        if database_exists(conn, target_database):
            print(f"✓ Database '{target_database}' already exists")
        else:
            print(f"Database '{target_database}' does not exist, creating it...")
            if not create_database(conn, target_database):
                print("ERROR: Failed to create database")
                return False

        conn.close()

        # Now initialize the database with Tryton
        print(f"\n=== Initializing Tryton in database '{target_database}' ===")

        # Update DATABASE_NAME environment variable for trytond-admin
        os.environ['DATABASE_NAME'] = target_database

        success = run_trytond_init(target_database)

        if success:
            print(f"\n✅ Database '{target_database}' is ready for Tryton!")
            print("You can now start the Tryton server.")
            return True
        else:
            print(f"\n❌ Failed to initialize Tryton database '{target_database}'")
            return False

    except Exception as e:
        print(f"ERROR: Database setup failed: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
