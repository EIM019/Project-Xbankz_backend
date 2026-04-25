from app.services.transfer_service import (
    approve_interbank_transfer,
    create_interbank_transfer,
    process_internal_transfer,
    reject_interbank_transfer,
)
from app.utils.validators import sanitize_input, validate_amount
from flask import Blueprint, jsonify, request, session

from .auth import admin_required, login_required

bp = Blueprint("transfers", __name__)


@bp.route("/internal", methods=["POST"])
@login_required
def internal_transfer():
    """Process an internal transfer"""
    user_id = session.get("user_id")
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    from_account_id = data.get("from_account_id")
    to_account_id = data.get("to_account_id")
    amount = data.get("amount")
    description = sanitize_input(data.get("description", ""))

    if not from_account_id or not to_account_id or not amount:
        return (
            jsonify(
                {"error": "from_account_id, to_account_id, and amount are required"}
            ),
            400,
        )

    # Validate amount
    is_valid, amount_decimal, error = validate_amount(amount)
    if not is_valid:
        return jsonify({"error": error}), 400

    # Verify account ownership
    from app.utils.database import get_db_cursor

    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT user_id FROM BankAccounts WHERE account_id = ?", from_account_id
        )
        result = cursor.fetchone()
        if not result or result[0] != user_id:
            return jsonify({"error": "Invalid source account"}), 403

    success, message, transaction_id = process_internal_transfer(
        from_account_id, to_account_id, amount_decimal, description, user_id
    )

    if success:
        return jsonify({"message": message, "transaction_id": transaction_id}), 200
    else:
        return jsonify({"error": message}), 400


@bp.route("/interbank", methods=["POST"])
@login_required
def interbank_transfer():
    """Create an interbank transfer"""
    user_id = session.get("user_id")
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    from_account_id = data.get("from_account_id")
    to_account_number = data.get("to_account_number", "").strip()
    amount = data.get("amount")
    description = sanitize_input(data.get("description", ""))

    if not from_account_id or not to_account_number or not amount:
        return (
            jsonify(
                {"error": "from_account_id, to_account_number, and amount are required"}
            ),
            400,
        )

    # Validate amount
    is_valid, amount_decimal, error = validate_amount(amount)
    if not is_valid:
        return jsonify({"error": error}), 400

    # Verify account ownership
    from app.utils.database import get_db_cursor

    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT user_id FROM BankAccounts WHERE account_id = ?", from_account_id
        )
        result = cursor.fetchone()
        if not result or result[0] != user_id:
            return jsonify({"error": "Invalid source account"}), 403

    success, message, transaction_id = create_interbank_transfer(
        from_account_id, to_account_number, amount_decimal, description, user_id
    )

    if success:
        return jsonify({"message": message, "transaction_id": transaction_id}), 201
    else:
        return jsonify({"error": message}), 400


@bp.route("/<int:transaction_id>/approve", methods=["POST"])
@admin_required
def approve_transfer(transaction_id):
    """Approve an interbank transfer (admin only)"""
    admin_user_id = session.get("user_id")
    data = request.get_json() or {}

    # For interbank transfers, we need a destination account ID
    # In a real system, this would be validated against external bank records
    to_account_id = data.get("to_account_id")

    success, message = approve_interbank_transfer(
        transaction_id, admin_user_id, to_account_id
    )

    if success:
        return jsonify({"message": message}), 200
    else:
        return jsonify({"error": message}), 400


@bp.route("/<int:transaction_id>/reject", methods=["POST"])
@admin_required
def reject_transfer(transaction_id):
    """Reject an interbank transfer (admin only)"""
    admin_user_id = session.get("user_id")

    success, message = reject_interbank_transfer(transaction_id, admin_user_id)

    if success:
        return jsonify({"message": message}), 200
    else:
        return jsonify({"error": message}), 400
