import secrets
import string
from datetime import datetime, timedelta, timezone

from app.services.audit_service import log_audit
from app.utils.database import db_transaction, get_db_cursor
from flask import current_app


def generate_otp():
    """Generate a 6-digit OTP"""
    return "".join(secrets.choice(string.digits) for _ in range(6))


def create_otp_session(user_id):
    """Create a new OTP session for a user"""
    otp_code = generate_otp()
    expiry_minutes = current_app.config["OTP_EXPIRY_MINUTES"]
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)

    with db_transaction() as cursor:
        # Invalidate any existing unused OTPs for this user
        cursor.execute(
            """
            UPDATE OTPSessions 
            SET used = 1 
            WHERE user_id = ? AND used = 0 AND expires_at > GETDATE()
        """,
            user_id,
        )

        # Create new OTP session
        cursor.execute(
            """
            INSERT INTO OTPSessions (user_id, otp_code, expires_at)
            VALUES (?, ?, ?)
        """,
            user_id,
            otp_code,
            expires_at,
        )

        log_audit(
            user_id, "OTP_GENERATED", "OTPSession", None, {"action": "otp_created"}
        )

    return otp_code


def verify_otp(user_id, otp_code):
    """Verify an OTP code for a user"""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            SELECT otp_id, expires_at, used
            FROM OTPSessions
            WHERE user_id = ? AND otp_code = ?
            ORDER BY created_at DESC
        """,
            user_id,
            otp_code,
        )

        result = cursor.fetchone()

        if not result:
            log_audit(
                user_id,
                "OTP_VERIFICATION_FAILED",
                "OTPSession",
                None,
                {"reason": "invalid_code"},
            )
            return False, "Invalid OTP code"

        otp_id, expires_at, used = result

        if used:
            log_audit(
                user_id,
                "OTP_VERIFICATION_FAILED",
                "OTPSession",
                None,
                {"reason": "already_used"},
            )
            return False, "OTP code has already been used"

        # ✅ Convert expires_at to timezone-aware in UTC if it's naive
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expires_at:
            log_audit(
                user_id,
                "OTP_VERIFICATION_FAILED",
                "OTPSession",
                None,
                {"reason": "expired"},
            )
            return False, "OTP code has expired"

        # Mark OTP as used
        cursor.execute(
            """
            UPDATE OTPSessions
            SET used = 1
            WHERE otp_id = ?
        """,
            otp_id,
        )

        log_audit(
            user_id, "OTP_VERIFIED", "OTPSession", otp_id, {"action": "otp_verified"}
        )
        return True, "OTP verified successfully"
