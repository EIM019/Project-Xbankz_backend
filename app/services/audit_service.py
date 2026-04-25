from flask import request
from app.utils.database import get_db_cursor
import json
from datetime import datetime

def log_audit(user_id, action, resource_type=None, resource_id=None, details=None):
    """Log an audit event"""
    try:
        ip_address = request.remote_addr if request else None
        details_json = json.dumps(details) if details else None
        
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
                INSERT INTO AuditLog (user_id, action, resource_type, resource_id, details, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
            """, user_id, action, resource_type, resource_id, details_json, ip_address)
    except Exception as e:
        # Don't fail the main operation if audit logging fails
        print(f"Audit logging error: {str(e)}")
