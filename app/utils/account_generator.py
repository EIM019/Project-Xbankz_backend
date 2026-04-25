from app.utils.security import generate_account_number
from app.utils.database import get_db_cursor

def generate_unique_account_number():
    """Generate a unique account number"""
    max_attempts = 10
    for _ in range(max_attempts):
        account_number = generate_account_number()
        # Check if account number already exists
        with get_db_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM BankAccounts WHERE account_number = ?", account_number)
            if cursor.fetchone()[0] == 0:
                return account_number
    raise Exception("Failed to generate unique account number")
