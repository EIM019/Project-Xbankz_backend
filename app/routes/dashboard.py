from datetime import datetime, timedelta

from app.utils.database import get_db_cursor
from flask import Blueprint, jsonify, session

from .auth import login_required

bp = Blueprint("dashboard", __name__)


@bp.route("/stats", methods=["GET"])
@login_required
def get_dashboard_stats():
    """Get dashboard statistics"""
    user_id = session.get("user_id")
    role = session.get("role")

    with get_db_cursor() as cursor:
        if role == "admin":
            # Admin stats
            cursor.execute("SELECT COUNT(*) FROM Users")
            total_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM BankAccounts")
            total_accounts = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM Transactions WHERE status = 'pending'")
            pending_transfers = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM Transactions WHERE status = 'flagged'")
            flagged_transactions = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT SUM(amount) FROM Transactions
                WHERE status = 'completed' AND created_at >= DATEADD(day, -30, GETDATE())
            """
            )
            monthly_volume = cursor.fetchone()[0] or 0

            return (
                jsonify(
                    {
                        "total_users": total_users,
                        "total_accounts": total_accounts,
                        "pending_transfers": pending_transfers,
                        "flagged_transactions": flagged_transactions,
                        "monthly_volume": float(monthly_volume),
                    }
                ),
                200,
            )
        else:
            # User stats
            cursor.execute(
                """
                SELECT COUNT(*), SUM(balance)
                FROM BankAccounts
                WHERE user_id = ? AND is_active = 1
            """,
                user_id,
            )
            result = cursor.fetchone()
            total_accounts = result[0]
            total_balance = float(result[1] or 0)

            cursor.execute(
                """
                SELECT COUNT(*) FROM Transactions t
                INNER JOIN BankAccounts ba ON (t.from_account_id = ba.account_id OR t.to_account_id = ba.account_id)
                WHERE ba.user_id = ? AND t.created_at >= DATEADD(day, -30, GETDATE())
            """,
                user_id,
            )
            monthly_transactions = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT daily_limit, daily_used, monthly_limit, monthly_used
                FROM UserLimits
                WHERE user_id = ?
            """,
                user_id,
            )
            limits_result = cursor.fetchone()
            if limits_result:
                daily_limit = float(limits_result[0])
                daily_used = float(limits_result[1])
                monthly_limit = float(limits_result[2])
                monthly_used = float(limits_result[3])
            else:
                daily_limit = daily_used = monthly_limit = monthly_used = 0

            return (
                jsonify(
                    {
                        "total_accounts": total_accounts,
                        "total_balance": total_balance,
                        "monthly_transactions": monthly_transactions,
                        "daily_limit": daily_limit,
                        "daily_used": daily_used,
                        "daily_remaining": daily_limit - daily_used,
                        "monthly_limit": monthly_limit,
                        "monthly_used": monthly_used,
                        "monthly_remaining": monthly_limit - monthly_used,
                    }
                ),
                200,
            )
