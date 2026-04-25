import re
from functools import wraps

import pyodbc
from app.services.audit_service import log_audit
from app.services.auth_service import authenticate_user, get_user_by_id, register_user
from app.services.otp_service import create_otp_session, verify_otp
from app.utils.validators import validate_email, validate_password
from flask import Blueprint, jsonify, request, session

bp = Blueprint("auth", __name__)


def login_required(f):
    """Decorator to require authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Decorator to require admin role"""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)

    return decorated_function


@bp.route("/register", methods=["POST"])
def register():
    """User registration endpoint"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not username or not email or not password:
        return jsonify({"error": "Username, email, and password are required"}), 400

    success, user_id, message = register_user(username, email, password, role="user")

    if success:
        return jsonify({"message": message, "user_id": user_id}), 201
    else:
        return jsonify({"error": message}), 400


@bp.route("/login", methods=["POST"])
def login():
    """User login endpoint"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    success, user_id, role, message = authenticate_user(username, password)

    if not success:

        return jsonify({"error": message}), 401

    # Generate OTP
    try:
        otp_code = create_otp_session(user_id)
        # In production, send OTP via email
        # For now, we'll return it in response (remove in production)
        return (
            jsonify(
                {
                    "message": "OTP sent to your email",
                    "otp_code": otp_code,  # Remove this in production
                    "requires_otp": True,
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": f"Failed to send OTP: {str(e)}"}), 500


@bp.route("/verify-otp", methods=["POST"])
def verify_otp_endpoint():
    """OTP verification endpoint"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = data.get("username", "").strip()
    otp_code = data.get("otp_code", "").strip()

    if not username or not otp_code:
        return jsonify({"error": "Username and OTP code are required"}), 400

    # Get user_id from username
    from app.utils.database import get_db_cursor

    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT user_id, role FROM Users WHERE username = ? OR email = ?",
            username,
            username,
        )
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "User not found"}), 404
        user_id, role = result

    # Verify OTP
    success, message = verify_otp(user_id, otp_code)

    if not success:
        return jsonify({"error": message}), 401

    # Create session
    session["user_id"] = user_id
    session["username"] = username
    session["role"] = role
    session.permanent = True

    log_audit(user_id, "LOGIN_COMPLETE", "User", user_id, {})

    return (
        jsonify(
            {
                "message": "Login successful",
                "user": {"user_id": user_id, "username": username, "role": role},
            }
        ),
        200,
    )


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """User logout endpoint"""
    user_id = session.get("user_id")
    log_audit(user_id, "LOGOUT", "User", user_id, {})

    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200


@bp.route("/me", methods=["GET"])
@login_required
def get_current_user():
    """Get current authenticated user"""
    user_id = session.get("user_id")
    user = get_user_by_id(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user), 200
