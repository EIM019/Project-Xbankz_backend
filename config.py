import os
import secrets

from dotenv import load_dotenv

load_dotenv()

WTF_CSRF_ENABLED = False


class Config:
    """Base configuration"""

    SECRET_KEY = (
        os.environ.get(("FLASK_SECRET_KEY")) or "dev-secret-key-change-in-production"
    )

    # SQL Server Database
   # DATABASE_CONNECTION_STRING = (
    #    os.environ.get("DATABASE_CONNECTION_STRING")
     #   or "DRIVER={ODBC Driver 17 for SQL Server};SERVER=LAPTOP-N594MJOP;DATABASE=xBankzDb;Trusted_Connection=yes;"
    #)
     
     # PostgreSQL Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI") 

    # Session Configuration
    SESSION_COOKIE_SECURE = (
        os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true"
    )
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

    # CORS Configuration
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
    ]
    CORS_SUPPORTS_CREDENTIALS = True

    # Rate Limiting
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_DEFAULT = "200 per hour"

    # Mail Configuration
    MAIL_SERVER = os.environ.get("MAIL_SERVER") or "smtp.gmail.com"
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 587)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME") or "mokgweetsiit@gmail.com"
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD") or "qchsbnhnaauiosui"
    MAIL_DEFAULT_SENDER = MAIL_USERNAME

    # Security Settings
    MAX_LOGIN_ATTEMPTS = 5
    ACCOUNT_LOCKOUT_DURATION = 1800  # 30 minutes in seconds
    OTP_EXPIRY_MINUTES = 10
    OTP_LENGTH = 6

    # Fraud Detection Thresholds
    LARGE_AMOUNT_THRESHOLD = 5000.00
    RAPID_TRANSFER_WINDOW_MINUTES = 5
    RAPID_TRANSFER_COUNT_THRESHOLD = 3

    # Default Transfer Limits
    DEFAULT_DAILY_LIMIT = 10000.00
    DEFAULT_MONTHLY_LIMIT = 50000.00


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
