import json
import re
from datetime import datetime, timedelta

from app.services.audit_service import log_audit
from app.services.otp_service import create_otp_session
from app.utils.database import db_transaction, get_db_cursor
from app.utils.security import hash_password, verify_password
from app.utils.validators import validate_email, validate_password
from flask import current_app, flash, session


def strong_password(password: str) -> bool:
    """
    Check if password meets strength requirements.
    """
    if len(password) < 8:
        return False

    if not re.search(r"[A-Z]", password):
        return False

    if not re.search(r"[a-z]", password):
        return False

    if not re.search(r"\d", password):
        return False

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False

    return True


def register_user(username, email, password, role="user"):
    """Register a new user"""
    # Validate inputs
    if not validate_email(email):
        return False, None, "Invalid email format"

    is_valid, message = validate_password(password)
    if not is_valid:
        return False, None, message

    # Check if user already exists
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT user_id FROM Users WHERE username = ? OR email = ?",
            (username, email),
        )
        if cursor.fetchone():
            return False, None, "Username or email already exists"

        # PASSWORD STRENGTH CHECK — RIGHT HERE
        if not strong_password(password):

            return (
                False,
                None,
                "Password must be 8+ chars, include uppercase, lowercase, number & symbol.",
            )

    # Create user and user limits in a single transaction
    password_hash = hash_password(password)
    with db_transaction() as cursor:
        cursor.execute(
            """
            INSERT INTO Users (username, email, password_hash, role)
            OUTPUT INSERTED.user_id
            VALUES (?, ?, ?, ?)
            """,
            (username, email, password_hash, role),
        )
        user_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO UserLimits (user_id, daily_limit, monthly_limit, last_reset_date)
            VALUES (?, ?, ?, CAST(GETDATE() AS DATE))
            """,
            user_id,
            current_app.config["DEFAULT_DAILY_LIMIT"],
            current_app.config["DEFAULT_MONTHLY_LIMIT"],
        )

    # Commit has happened at this point; now log audit **outside** the transaction
    try:
        log_audit(
            user_id,
            "USER_REGISTERED",
            "User",
            user_id,
            {"username": username, "email": email, "role": role},
        )
    except Exception as e:
        current_app.logger.warning(f"Audit log failed for user {user_id}: {e}")
    return True, user_id, "User registered successfully"


def check_account_lockout(user_id):
    """Check if user account is locked"""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT account_locked_until
            FROM Users
            WHERE user_id = ?
        """,
            user_id,
        )

        result = cursor.fetchone()
        if result and result[0]:
            lockout_until = result[0]
            if datetime.utcnow() < lockout_until:
                remaining = (lockout_until - datetime.utcnow()).total_seconds()
                return True, remaining
            else:
                # Lockout expired, reset it
                with get_db_cursor(commit=True) as update_cursor:
                    update_cursor.execute(
                        """
                        UPDATE Users
                        SET account_locked_until = NULL, failed_login_attempts = 0
                        WHERE user_id = ?
                    """,
                        user_id,
                    )

    return False, 0


def handle_failed_login(user_id):
    """Handle a failed login attempt"""
    max_attempts = current_app.config["MAX_LOGIN_ATTEMPTS"]
    lockout_duration = current_app.config["ACCOUNT_LOCKOUT_DURATION"]

    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            UPDATE Users
            SET failed_login_attempts = failed_login_attempts + 1
            WHERE user_id = ?
        """,
            user_id,
        )

        cursor.execute(
            """
            SELECT failed_login_attempts
            FROM Users
            WHERE user_id = ?
        """,
            user_id,
        )

        attempts = cursor.fetchone()[0]

        if attempts >= max_attempts:
            lockout_until = datetime.utcnow() + timedelta(seconds=lockout_duration)
            cursor.execute(
                """
                UPDATE Users
                SET account_locked_until = ?
                WHERE user_id = ?
            """,
                lockout_until,
                user_id,
            )

            log_audit(
                user_id,
                "ACCOUNT_LOCKED",
                "User",
                user_id,
                {"reason": "max_login_attempts", "attempts": attempts},
            )

            return True, lockout_duration

    return False, 0


def handle_successful_login(user_id):
    """Handle a successful login"""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            UPDATE Users
            SET failed_login_attempts = 0,
                account_locked_until = NULL,
                last_login = GETDATE()
            WHERE user_id = ?
        """,
            user_id,
        )

    log_audit(user_id, "LOGIN_SUCCESS", "User", user_id, {})


def authenticate_user(username, password):
    """Authenticate a user with username and password"""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT user_id, password_hash, role
            FROM Users
            WHERE username = ? OR email = ?
        """,
            username,
            username,
        )

        result = cursor.fetchone()
        if not result:
            return False, None, None, "Invalid username or password"

        user_id, password_hash, role = result

        # Check account lockout
        is_locked, remaining = check_account_lockout(user_id)
        if is_locked:
            return (
                False,
                None,
                None,
                f"Account is locked. Try again in {int(remaining/60)} minutes.",
            )

        # Verify password
        if not verify_password(password, password_hash):
            handle_failed_login(user_id)
            return False, None, None, "Invalid username or password"

        # Successful authentication
        handle_successful_login(user_id)
        return True, user_id, role, "Authentication successful"


def get_user_by_id(user_id):
    """Get user information by ID"""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT user_id, username, email, role, created_at, last_login
            FROM Users
            WHERE user_id = ?
        """,
            user_id,
        )

        result = cursor.fetchone()
        if not result:
            return None

        return {
            "user_id": result[0],
            "username": result[1],
            "email": result[2],
            "role": result[3],
            "created_at": result[4].isoformat() if result[4] else None,
            "last_login": result[5].isoformat() if result[5] else None,
        }
