import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_cors import CORS
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
from dotenv import load_dotenv

load_dotenv()


# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
migrate = Migrate()
jwt = JWTManager()
mail = Mail()
cors = CORS()

FRONTEND_URL = os.environ.get("FRONTEND_URL")
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # Example: 500 MB limit

    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    mail.init_app(app)
    
    # Configure 
    # CORS(app)

    cors.init_app(app, resources={
        r"/*": {
            "origins": [
                "http://localhost:5173",  # Default React dev server
                "http://localhost:5174",  # Default React dev server
                "http://127.0.0.1:3000",  # Alternative local address
                  # Your future production frontend
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
              # If using cookies/auth
        }
    })
    
    # Register blueprints
    from routes.auth_routes import auth_bp
    from routes.user_routes import user_bp
    from routes.course_routes import course_bp
    from routes.admin_routes import admin_bp
    from routes.payment_routes import payment_bp
    from routes.file_routes import file_bp
    from routes.notification_routes import notification_bp
    from routes.certificate_routes import certificate_bp
    from routes.live_session_routes import live_session_bp
    from routes.helper_routes import helper_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(user_bp, url_prefix='/api/v1/users')
    app.register_blueprint(course_bp, url_prefix='/api/v1/courses')
    app.register_blueprint(admin_bp, url_prefix='/api/v1/admin')
    app.register_blueprint(payment_bp, url_prefix='/api/v1/payments')
    app.register_blueprint(file_bp, url_prefix='/api/v1/files')
    app.register_blueprint(notification_bp, url_prefix='/api/v1/notifications')
    app.register_blueprint(certificate_bp, url_prefix='/api/v1/certificates')
    app.register_blueprint(live_session_bp, url_prefix='/api/v1/live-sessions')
    app.register_blueprint(helper_bp,url_prefix='/api/v1/helper/')
    # Create tables
    with app.app_context():
        import models  # noqa: F401
        db.create_all()
    
    # JWT token blacklist handling
    from models import TokenBlacklist
    
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        token_jti = jwt_payload['jti']
        token = TokenBlacklist.query.filter_by(jti=token_jti).first()
        return token is not None
    
    # Root endpoint
    @app.route('/')
    def root():
        return {
            'message': 'AI First Academy API',
            'version': '1.0',
            'status': 'running',
            'endpoints': {
                'api': '/api/v1/',
                'auth': '/api/v1/auth',
                'users': '/api/v1/users',
                'courses': '/api/v1/courses',
                'admin': '/api/v1/admin',
                'payments': '/api/v1/payments',
                'files': '/api/v1/files',
                'notifications': '/api/v1/notifications',
                'certificates': '/api/v1/certificates',
                'live-sessions': '/api/v1/live-sessions'
            }
        }
    
    # API root endpoint
    @app.route('/api/v1/')
    def api_root():
        return {
            'message': 'AI First Academy API',
            'version': '1.0',
            'endpoints': {
                'auth': '/api/v1/auth',
                'users': '/api/v1/users',
                'courses': '/api/v1/courses',
                'admin': '/api/v1/admin',
                'payments': '/api/v1/payments',
                'files': '/api/v1/files',
                'notifications': '/api/v1/notifications',
                'certificates': '/api/v1/certificates',
                'live-sessions': '/api/v1/live-sessions'
            }
        }
    
    return app
