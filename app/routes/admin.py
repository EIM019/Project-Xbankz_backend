from app.utils.database import get_db_cursor
from flask import Blueprint, jsonify, request, session

from .auth import admin_required

bp = Blueprint("admin", __name__)


@bp.route("/users", methods=["GET"])
@admin_required
def get_all_users():
    """Get all users (admin only)"""
    limit = request.args.get("limit", type=int, default=100)
    offset = request.args.get("offset", type=int, default=0)

    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT user_id, username, email, role, created_at, last_login, failed_login_attempts, account_locked_until
            FROM Users
            ORDER BY created_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """,
            offset,
            limit,
        )

        users = []
        for row in cursor.fetchall():
            users.append(
                {
                    "user_id": row[0],
                    "username": row[1],
                    "email": row[2],
                    "role": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "last_login": row[5].isoformat() if row[5] else None,
                    "failed_login_attempts": row[6],
                    "account_locked_until": row[7].isoformat() if row[7] else None,
                }
            )

    return jsonify(users), 200


@bp.route("/transactions", methods=["GET"])
@admin_required
def get_all_transactions():
    """Get all transactions (admin only)"""
    limit = request.args.get("limit", type=int, default=100)
    offset = request.args.get("offset", type=int, default=0)
    status = request.args.get("status")

    with get_db_cursor() as cursor:
        if status:
            cursor.execute(
                """
                SELECT t.transaction_id, t.from_account_id, t.to_account_id, t.amount,
                       t.transaction_type, t.status, t.description, t.fraud_flags,
                       t.created_at, t.approved_by, t.approved_at
                FROM Transactions t
                WHERE t.status = ?
                ORDER BY t.created_at DESC
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """,
                status,
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


@bp.route("/flagged-transactions", methods=["GET"])
@admin_required
def get_flagged_transactions():
    """Get all flagged transactions (admin only)"""
    limit = request.args.get("limit", type=int, default=100)
    offset = request.args.get("offset", type=int, default=0)

    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT t.transaction_id, t.from_account_id, t.to_account_id, t.amount,
                   t.transaction_type, t.status, t.description, t.fraud_flags,
                   t.created_at, t.approved_by, t.approved_at
            FROM Transactions t
            WHERE t.status = 'flagged' OR t.fraud_flags IS NOT NULL
            ORDER BY t.created_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """,
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
