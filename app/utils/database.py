import logging
from contextlib import contextmanager

import pyodbc
from flask import current_app

logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection"""
    try:
        conn = pyodbc.connect(current_app.config["DATABASE_CONNECTION_STRING"])
        print("Database connected!")
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        print("Database connection failed!")
        raise


@contextmanager
def get_db_cursor(commit=False):
    """Context manager for database cursor with optional commit"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database transaction error: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()


@contextmanager
def db_transaction():
    """Context manager for database transactions"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Transaction error: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()
