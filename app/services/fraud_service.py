from flask import current_app
from app.utils.database import get_db_cursor
from datetime import datetime, timedelta
import json

def check_large_amount(amount):
    """Check if amount exceeds large amount threshold"""
    threshold = current_app.config['LARGE_AMOUNT_THRESHOLD']
    return amount >= threshold

def check_rapid_transfers(user_id, from_account_id):
    """Check for rapid transfer frequency"""
    window_minutes = current_app.config['RAPID_TRANSFER_WINDOW_MINUTES']
    count_threshold = current_app.config['RAPID_TRANSFER_COUNT_THRESHOLD']
    
    window_start = datetime.utcnow() - timedelta(minutes=window_minutes)
    
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*)
            FROM Transactions
            WHERE from_account_id = ?
                AND created_at >= ?
                AND status IN ('completed', 'pending')
        """, from_account_id, window_start)
        
        count = cursor.fetchone()[0]
        return count >= count_threshold

def detect_fraud(user_id, from_account_id, amount):
    """Run all fraud detection checks and return flags"""
    flags = []
    
    # Large amount check
    if check_large_amount(amount):
        flags.append({
            'type': 'large_amount',
            'severity': 'high',
            'message': f'Transfer amount ${amount:.2f} exceeds threshold'
        })
    
    # Rapid transfer check
    if check_rapid_transfers(user_id, from_account_id):
        flags.append({
            'type': 'rapid_transfers',
            'severity': 'medium',
            'message': 'Multiple transfers detected in short time window'
        })
    
    return flags

def should_flag_transaction(fraud_flags):
    """Determine if transaction should be flagged based on fraud detection"""
    if not fraud_flags:
        return False
    
    # Flag if any high severity issue
    return any(flag.get('severity') == 'high' for flag in fraud_flags)
