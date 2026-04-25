from datetime import datetime

from app.utils.database import get_db_cursor
from flask import Blueprint, jsonify, request, session

from .auth import login_required

bp = Blueprint("transactions", __name__)


@bp.route("", methods=["GET"])
@login_required
def get_transactions():
    """Get transaction history"""
    user_id = session.get("user_id")
    role = session.get("role")

    # Get query parameters
    account_id = request.args.get("account_id", type=int)
    limit = request.args.get("limit", type=int, default=50)
    offset = request.args.get("offset", type=int, default=0)

    with get_db_cursor() as cursor:
        if role == "admin":
            if account_id:
                cursor.execute(
                    """
                    SELECT t.transaction_id, t.from_account_id, t.to_account_id, t.amount,
                           t.transaction_type, t.status, t.description, t.fraud_flags,
                           t.created_at, t.approved_by, t.approved_at
                    FROM Transactions t
                    WHERE t.from_account_id = ? OR t.to_account_id = ?
                    ORDER BY t.created_at DESC
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """,
                    account_id,
                    account_id,
                    offset,
                    limit,
                )
            else:
                cursor.execute(
                    """
                    SELECT t.transaction_id, t.from_account_id, t.to_account_id, t.amount,
                           t.transaction_type, t.status, t.description, t.fraud_flags,
                           t.created_at, t.approved_by, t.approved_at
                    FROM Transactions t
                    ORDER BY t.created_at DESC
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """,
                    offset,
                    limit,
                )
        else:
            if account_id:
                # Verify account ownership
                cursor.execute(
                    "SELECT user_id FROM BankAccounts WHERE account_id = ?", account_id
                )
                result = cursor.fetchone()
                if not result or result[0] != user_id:
                    return jsonify({"error": "Account not found"}), 404

                cursor.execute(
                    """
                    SELECT t.transaction_id, t.from_account_id, t.to_account_id, t.amount,
                           t.transaction_type, t.status, t.description, t.fraud_flags,
                           t.created_at, t.approved_by, t.approved_at
                    FROM Transactions t
                    WHERE (t.from_account_id = ? OR t.to_account_id = ?)
                    ORDER BY t.created_at DESC
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """,
                    account_id,
                    account_id,
                    offset,
                    limit,
                )
            else:
                # Get all transactions for user's accounts
                cursor.execute(
                    """
                    SELECT t.transaction_id, t.from_account_id, t.to_account_id, t.amount,
                           t.transaction_type, t.status, t.description, t.fraud_flags,
                           t.created_at, t.approved_by, t.approved_at
                    FROM Transactions t
                    INNER JOIN BankAccounts ba ON (t.from_account_id = ba.account_id OR t.to_account_id = ba.account_id)
                    WHERE ba.user_id = ?
                    ORDER BY t.created_at DESC
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """,
                    user_id,
                    offset,
                    limit,
                )

        transactions = []
        for row in cursor.fetchall():
            transactions.append(
                {
                    "transaction_id": row[0],
                    "from_account_id": row[1],
                    "to_account_id": row[2],
                    "amount": float(row[3]),
                    "transaction_type": row[4],
                    "status": row[5],
                    "description": row[6],
                    "fraud_flags": row[7],
                    "created_at": row[8].isoformat() if row[8] else None,
                    "approved_by": row[9],
                    "approved_at": row[10].isoformat() if row[10] else None,
                }
            )

    return jsonify(transactions), 200


@bp.route("/<int:transaction_id>", methods=["GET"])
@login_required
def get_transaction(transaction_id):
    """Get a specific transaction"""
    user_id = session.get("user_id")
    role = session.get("role")

    with get_db_cursor() as cursor:
        if role == "admin":
            cursor.execute(
                """
                SELECT t.transaction_id, t.from_account_id, t.to_account_id, t.amount,
                       t.transaction_type, t.status, t.description, t.fraud_flags,
                       t.created_at, t.approved_by, t.approved_at
                FROM Transactions t
                WHERE t.transaction_id = ?
            """,
                transaction_id,
            )
        else:
            cursor.execute(
                """
                SELECT t.transaction_id, t.from_account_id, t.to_account_id, t.amount,
                       t.transaction_type, t.status, t.description, t.fraud_flags,
                       t.created_at, t.approved_by, t.approved_at
                FROM Transactions t
                INNER JOIN BankAccounts ba ON (t.from_account_id = ba.account_id OR t.to_account_id = ba.account_id)
                WHERE t.transaction_id = ? AND ba.user_id = ?
            """,
                transaction_id,
                user_id,
            )

        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "Transaction not found"}), 404

        return (
            jsonify(
                {
                    "transaction_id": result[0],
                    "from_account_id": result[1],
                    "to_account_id": result[2],
                    "amount": float(result[3]),
                    "transaction_type": result[4],
                    "status": result[5],
                    "description": result[6],
                    "fraud_flags": result[7],
                    "created_at": result[8].isoformat() if result[8] else None,
                    "approved_by": result[9],
                    "approved_at": result[10].isoformat() if result[10] else None,
                }
            ),
            200,
        )


@bp.route("/statement", methods=["GET"])
@login_required
def get_statement():
    """Get bank statement with date range filtering"""
    user_id = session.get("user_id")
    account_id = request.args.get("account_id", type=int)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not account_id:
        return jsonify({"error": "account_id is required"}), 400

    # Verify account ownership
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT user_id FROM BankAccounts WHERE account_id = ?", account_id
        )
        result = cursor.fetchone()
        if not result or result[0] != user_id:
            return jsonify({"error": "Account not found"}), 404

    # Parse dates
    try:
        start_datetime = datetime.fromisoformat(start_date) if start_date else None
        end_datetime = datetime.fromisoformat(end_date) if end_date else None
    except ValueError:
        return (
            jsonify(
                {"error": "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"}
            ),
            400,
        )

    with get_db_cursor() as cursor:
        if start_datetime and end_datetime:
            cursor.execute(
                """
                SELECT t.transaction_id, t.from_account_id, t.to_account_id, t.amount,
                       t.transaction_type, t.status, t.description, t.created_at
                FROM Transactions t
                WHERE (t.from_account_id = ? OR t.to_account_id = ?)
                    AND t.created_at >= ? AND t.created_at <= ?
                ORDER BY t.created_at DESC
            """,
                account_id,
                account_id,
                start_datetime,
                end_datetime,
            )
        elif start_datetime:
            cursor.execute(
                """
                SELECT t.transaction_id, t.from_account_id, t.to_account_id, t.amount,
                       t.transaction_type, t.status, t.description, t.created_at
                FROM Transactions t
                WHERE (t.from_account_id = ? OR t.to_account_id = ?)
                    AND t.created_at >= ?
                ORDER BY t.created_at DESC
            """,
                account_id,
                account_id,
                start_datetime,
            )
        elif end_datetime:
            cursor.execute(
                """
                SELECT t.transaction_id, t.from_account_id, t.to_account_id, t.amount,
                       t.transaction_type, t.status, t.description, t.created_at
                FROM Transactions t
                WHERE (t.from_account_id = ? OR t.to_account_id = ?)
                    AND t.created_at <= ?
                ORDER BY t.created_at DESC
            """,
                account_id,
                account_id,
                end_datetime,
            )
        else:
            cursor.execute(
                """
                SELECT t.transaction_id, t.from_account_id, t.to_account_id, t.amount,
                       t.transaction_type, t.status, t.description, t.created_at
                FROM Transactions t
                WHERE t.from_account_id = ? OR t.to_account_id = ?
                ORDER BY t.created_at DESC
            """,
                account_id,
                account_id,
            )

        transactions = []
        for row in cursor.fetchall():
            transactions.append(
                {
                    "transaction_id": row[0],
                    "from_account_id": row[1],
                    "to_account_id": row[2],
                    "amount": float(row[3]),
                    "transaction_type": row[4],
                    "status": row[5],
                    "description": row[6],
                    "created_at": row[7].isoformat() if row[7] else None,
                }
            )

    return (
        jsonify(
            {
                "account_id": account_id,
                "start_date": start_date,
                "end_date": end_date,
                "transactions": transactions,
            }
        ),
        200,
    )
