import psycopg2
from psycopg2 import pool
import sys
from .config import settings

# Create a connection pool
# This pool will be used by our worker to get connections
try:
    db_pool = psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=5,  # Max 5 connections, adjust as needed
        dsn=settings.DATABASE_URL
    )
    print("Database connection pool created successfully.")

except (Exception, psycopg2.DatabaseError) as error:
    print(f"Error while creating connection pool: {error}")
    sys.exit(1)

def get_db_connection():
    """
    Get a connection from the pool.
    """
    try:
        return db_pool.getconn()
    except Exception as error:
        print(f"Error getting connection from pool: {error}")
        return None

def release_db_connection(conn):
    """
    Release a connection back to the pool.
    """
    if conn:
        db_pool.putconn(conn)

def close_db_pool():
    """
    Close all connections in the pool (on app shutdown).
    """
    db_pool.closeall()