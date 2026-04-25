"""
Helper script to create .env file for backend configuration
"""
import os

env_content = """# Flask Configuration
SECRET_KEY=xbankz-dev-secret-key-change-in-production-2024
FLASK_ENV=development

# Database Configuration
# Update this with your SQL Server connection details
# For Windows Authentication (recommended for local dev):
DATABASE_CONNECTION_STRING=DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=xBankz;Trusted_Connection=yes;

# Alternative: SQL Server Authentication
# DATABASE_CONNECTION_STRING=DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=xBankz;UID=your_username;PWD=your_password;

# CORS Configuration
CORS_ORIGINS=http://localhost:5173

# Mail Configuration (Optional - for OTP emails)
# For Gmail, you'll need an App Password: https://support.google.com/accounts/answer/185833
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com

# Security
SESSION_COOKIE_SECURE=False
"""

env_path = os.path.join(os.path.dirname(__file__), '.env')

if os.path.exists(env_path):
    print(f".env file already exists at {env_path}")
    print("Skipping .env file creation. Delete it first if you want to recreate.")
    exit(0)

with open(env_path, 'w') as f:
    f.write(env_content)

print(f"[OK] Created .env file at {env_path}")
print("\n[IMPORTANT] Please update the DATABASE_CONNECTION_STRING in .env with your SQL Server details!")
print("   If using Windows Authentication, the default should work if SQL Server is on localhost.")
