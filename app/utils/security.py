import bcrypt
import secrets
import string

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def generate_secure_random_string(length=16):
    """Generate a secure random string"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_account_number():
    """Generate a random 10-16 digit account number"""
    # Generate 12-digit account number
    return ''.join(secrets.choice(string.digits) for _ in range(12))
