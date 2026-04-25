from flask import current_app
from app.utils.database import get_db_cursor, db_transaction
from datetime import datetime, date

def reset_daily_limits_if_needed(user_id):
    """Reset daily limits if a new day has started"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT last_reset_date, daily_used
            FROM UserLimits
            WHERE user_id = ?
        """, user_id)
        
        result = cursor.fetchone()
        if not result:
            return
        
        last_reset_date, daily_used = result
        today = date.today()
        
        if last_reset_date != today:
            with get_db_cursor(commit=True) as update_cursor:
                update_cursor.execute("""
                    UPDATE UserLimits
                    SET daily_used = 0,
                        last_reset_date = CAST(GETDATE() AS DATE)
                    WHERE user_id = ?
                """, user_id)

def reset_monthly_limits_if_needed(user_id):
    """Reset monthly limits if a new month has started"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT last_reset_date, monthly_used
            FROM UserLimits
            WHERE user_id = ?
        """, user_id)
        
        result = cursor.fetchone()
        if not result:
            return
        
        last_reset_date, monthly_used = result
        today = date.today()
        
        # Check if we're in a new month
        if last_reset_date.month != today.month or last_reset_date.year != today.year:
            with get_db_cursor(commit=True) as update_cursor:
                update_cursor.execute("""
                    UPDATE UserLimits
                    SET monthly_used = 0,
                        last_reset_date = CAST(GETDATE() AS DATE)
                    WHERE user_id = ?
                """, user_id)

def check_transfer_limits(user_id, amount):
    """Check if transfer is within daily and monthly limits"""
    reset_daily_limits_if_needed(user_id)
    reset_monthly_limits_if_needed(user_id)
    
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT daily_limit, daily_used, monthly_limit, monthly_used
            FROM UserLimits
            WHERE user_id = ?
        """, user_id)
        
        result = cursor.fetchone()
        if not result:
            return False, "User limits not found"
        
        daily_limit, daily_used, monthly_limit, monthly_used = result
        
        if daily_used + amount > daily_limit:
            return False, f"Transfer exceeds daily limit. Available: ${daily_limit - daily_used:.2f}"
        
        if monthly_used + amount > monthly_limit:
            return False, f"Transfer exceeds monthly limit. Available: ${monthly_limit - monthly_used:.2f}"
        
        return True, None

def update_transfer_limits(user_id, amount):
    """Update daily and monthly used amounts after a transfer"""
    with db_transaction() as cursor:
        cursor.execute("""
            UPDATE UserLimits
            SET daily_used = daily_used + ?,
                monthly_used = monthly_used + ?
            WHERE user_id = ?
        """, amount, amount, user_id)
