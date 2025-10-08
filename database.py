import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import os

class Database:
    """PostgreSQL database connection and operations"""

    def __init__(self):
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_password = os.environ.get('DB_PASSWORD', '')

        self.config = {
            'database': os.environ.get('DB_NAME', 'attendance_db'),
            'user': os.environ.get('DB_USER', 'postgres')
        }

        # Only add host/port if not using Unix socket
        if not db_host.startswith('/'):
            self.config['host'] = db_host
            self.config['port'] = os.environ.get('DB_PORT', '5432')
        else:
            self.config['host'] = db_host

        # Only add password if it's provided
        if db_password:
            self.config['password'] = db_password

    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = psycopg2.connect(**self.config)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def fetch_one(self, query, params=None):
        """Fetch single row"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()
                return dict(result) if result else None

    def fetch_all(self, query, params=None):
        """Fetch all rows"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]

    def execute(self, query, params=None):
        """Execute query (INSERT, UPDATE, DELETE)"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                # For INSERT with RETURNING
                if query.strip().upper().startswith('INSERT') and 'RETURNING' in query.upper():
                    result = cursor.fetchone()
                    return result[0] if result else None
                return cursor.rowcount

    def execute_many(self, query, params_list):
        """Execute batch operations"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                return cursor.rowcount


# Global database instance
db = Database()
