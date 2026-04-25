import os

from config import config
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect

# Initialize extensions
limiter = Limiter(
    key_func=get_remote_address, default_limits=["1000 per hour", "100 per minute"]
)
mail = Mail()
csrf = CSRFProtect()

# config.py (development)
# WTF_CSRF_ENABLED = False


def create_app(config_name=None):
    """Application factory"""
    app = Flask(__name__)

    # Load configuration
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config[config_name])

    # Initialize extensions with app
    csrf.init_app(app)

    # Initialize extensions
    limiter.init_app(app)

    # Make limiter available to routes
    app.limiter = limiter
    CORS(
        app,
        origins=app.config["CORS_ORIGINS"],
        supports_credentials=app.config["CORS_SUPPORTS_CREDENTIALS"],
    )
    mail.init_app(app)
    

    # Disable CSRF for API routes
    @app.before_request
    def disable_csrf_for_api():
        from flask import request

        if request.path.startswith("/api/"):
            if request.endpoint:
                csrf.exempt(request.endpoint)

    # Register blueprints
    from app.routes import accounts, admin, auth, dashboard, transactions, transfers

    app.register_blueprint(auth.bp, url_prefix="/api/auth")
    app.register_blueprint(accounts.bp, url_prefix="/api/accounts")
    app.register_blueprint(transfers.bp, url_prefix="/api/transfers")
    app.register_blueprint(transactions.bp, url_prefix="/api/transactions")
    app.register_blueprint(admin.bp, url_prefix="/api/admin")
    app.register_blueprint(dashboard.bp, url_prefix="/api/dashboard")

    # **THEN exempt all API blueprints from CSRF**
    csrf.exempt(auth.bp)
    csrf.exempt(accounts.bp)
    csrf.exempt(transfers.bp)
    csrf.exempt(transactions.bp)
    csrf.exempt(admin.bp)
    csrf.exempt(dashboard.bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        return {"error": "Internal server error"}, 500

    @app.route("/")
    def home():
        return {"status": "API running"}

    return app
