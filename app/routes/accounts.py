from app.routes.auth import login_required
from app.services.audit_service import log_audit
from app.utils.account_generator import generate_unique_account_number
from app.utils.database import db_transaction, get_db_cursor
from app.utils.validators import sanitize_input
from flask import Blueprint, jsonify, request, session

bp = Blueprint("accounts", __name__)


@bp.route("", methods=["GET"])
@login_required
def get_accounts():
    """Get all accounts for current user"""
    user_id = session.get("user_id")
    role = session.get("role")

    with get_db_cursor() as cursor:
        if role == "admin":
            # Admin can see all accounts
            cursor.execute(
                """
                SELECT account_id, user_id, account_number, account_type, balance, created_at, is_active
                FROM BankAccounts
                ORDER BY created_at DESC
            """
            )
        else:
            # Regular users see only their accounts
            cursor.execute(
                """
                SELECT account_id, user_id, account_number, account_type, balance, created_at, is_active
                FROM BankAccounts
                WHERE user_id = ?
                ORDER BY created_at DESC
            """,
                user_id,
            )

        accounts = []
        for row in cursor.fetchall():
            accounts.append(
                {
                    "account_id": row[0],
                    "user_id": row[1],
                    "account_number": row[2],
                    "account_type": row[3],
                    "balance": float(row[4]),
                    "created_at": row[5].isoformat() if row[5] else None,
                    "is_active": bool(row[6]),
                }
            )

    return jsonify(accounts), 200


@bp.route("", methods=["POST"])
@login_required
def create_account():
    """Create a new bank account"""
    user_id = session.get("user_id")
    data = request.get_json() or {}

    account_type = sanitize_input(data.get("account_type", "checking"))

    try:
        account_number = generate_unique_account_number()

        with db_transaction() as cursor:
            cursor.execute(
                """
                INSERT INTO BankAccounts (user_id, account_number, account_type, balance)
                OUTPUT INSERTED.account_id
                VALUES (?, ?, ?, 0.00)
            """,
                user_id,
                account_number,
                account_type,
            )

            account_id = cursor.fetchone()[0]

            log_audit(
                user_id,
                "ACCOUNT_CREATED",
                "BankAccount",
                account_id,
                {"account_number": account_number, "account_type": account_type},
            )

        return (
            jsonify(
                {
                    "message": "Account created successfully",
                    "account_id": account_id,
                    "account_number": account_number,
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": f"Failed to create account: {str(e)}"}), 500


@bp.route("/<int:account_id>", methods=["GET"])
@login_required
def get_account(account_id):
    """Get a specific account"""
    user_id = session.get("user_id")
    role = session.get("role")

    with get_db_cursor() as cursor:
        if role == "admin":
            cursor.execute(
                """
                SELECT account_id, user_id, account_number, account_type, balance, created_at, is_active
                FROM BankAccounts
                WHERE account_id = ?
            """,
                account_id,
            )
        else:
            cursor.execute(
                """
                SELECT account_id, user_id, account_number, account_type, balance, created_at, is_active
                FROM BankAccounts
                WHERE account_id = ? AND user_id = ?
            """,
                account_id,
                user_id,
            )

        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "Account not found"}), 404

        return (
            jsonify(
                {
                    "account_id": result[0],
                    "user_id": result[1],
                    "account_number": result[2],
                    "account_type": result[3],
                    "balance": float(result[4]),
                    "created_at": result[5].isoformat() if result[5] else None,
                    "is_active": bool(result[6]),
                }
            ),
            200,
        )


@bp.route("/<int:account_id>/deposit", methods=["POST"])
@login_required
def deposit_to_account(account_id):
    """Deposit money to an account"""
    user_id = session.get("user_id")
    role = session.get("role")
    data = request.get_json() or {}

    amount = data.get("amount")
    description = sanitize_input(data.get("description", "Deposit"))

    if not amount:
        return jsonify({"error": "Amount is required"}), 400

    # Validate amount
    from app.utils.validators import validate_amount

    is_valid, amount_decimal, error = validate_amount(amount)
    if not is_valid:
        return jsonify({"error": error}), 400

    # Verify account ownership (or admin)
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT user_id FROM BankAccounts WHERE account_id = ? AND is_active = 1",
            account_id,
        )
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "Account not found"}), 404

        if role != "admin" and result[0] != user_id:
            return jsonify({"error": "Unauthorized"}), 403

    try:
        with db_transaction() as cursor:
            # Credit the account
            cursor.execute(
                """
                UPDATE BankAccounts
                SET balance = balance + ?
                WHERE account_id = ?
                """,
                amount_decimal,
                account_id,
            )

            # Create transaction record
            cursor.execute(
                """
                INSERT INTO Transactions (to_account_id, amount, transaction_type, status, description)
                OUTPUT INSERTED.transaction_id
                VALUES (?, ?, 'deposit', 'completed', ?)
                """,
                account_id,
                amount_decimal,
                description,
            )

            transaction_id = cursor.fetchone()[0]

            log_audit(
                user_id,
                "DEPOSIT",
                "Transaction",
                transaction_id,
                {"account_id": account_id, "amount": float(amount_decimal)},
            )

        return (
            jsonify(
                {"message": "Deposit successful", "transaction_id": transaction_id}
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Deposit failed: {str(e)}"}), 500


@bp.route("/<int:account_id>/balance", methods=["GET"])
@login_required
def get_balance(account_id):
    """Get account balance"""
    user_id = session.get("user_id")
    role = session.get("role")

    with get_db_cursor() as cursor:
        if role == "admin":
            cursor.execute(
                """
                SELECT balance
                FROM BankAccounts
                WHERE account_id = ?
            """,
                account_id,
            )
        else:
            cursor.execute(
                """
                SELECT balance
                FROM BankAccounts
                WHERE account_id = ? AND user_id = ?
            """,
                account_id,
                user_id,
            )

        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "Account not found"}), 404

        return jsonify({"balance": float(result[0])}), 200
