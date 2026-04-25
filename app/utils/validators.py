import re
from decimal import Decimal, InvalidOperation

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    return True, "Password is valid"

def validate_amount(amount):
    """Validate and parse amount"""
    try:
        amount_decimal = Decimal(str(amount))
        if amount_decimal <= 0:
            return False, None, "Amount must be greater than zero"
        if amount_decimal.as_tuple().exponent < -2:
            return False, None, "Amount cannot have more than 2 decimal places"
        return True, amount_decimal, None
    except (InvalidOperation, ValueError):
        return False, None, "Invalid amount format"

def sanitize_input(text):
    """Basic input sanitization"""
    if not isinstance(text, str):
        return str(text)
    # Remove potentially dangerous characters
    return text.strip()
