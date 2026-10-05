"""
Flask Application Factory
Creates and configures the Flask web application.
"""

import os
import logging
from typing import Optional
from flask import Flask
from flask_cors import CORS

from config import config_manager, secrets_manager
from config.settings import Settings

# Import routes
from .routes import main_routes, api_routes

logger = logging.getLogger(__name__)


def create_app(config: Optional[Settings] = None) -> Flask:
    """
    Create and configure the Flask application.
    
    Args:
        config: Configuration settings (defaults to global config)
        
    Returns:
        Configured Flask application
    """
    
    # Use provided config or load from global
    if config is None:
        config = config_manager.get()
    
    # Create Flask app
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
        template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
    )
    
    # Configure app
    app.config.update(
        SECRET_KEY=config.web.secret_key or "change-me-in-production",
        SESSION_COOKIE_NAME="ffgc_session",
        PERMANENT_SESSION_LIFETIME=config.web.session_timeout,
        JSON_SORT_KEYS=False,
        JSONIFY_PRETTYPRINT_REGULAR=False,
    )
    
    # Enable CORS
    CORS(
        app,
        origins=config.web.cors_origins,
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )
    
    # Register blueprints
    app.register_blueprint(main_routes)
    app.register_blueprint(api_routes, url_prefix=config.web.api_prefix)
    
    # Configure logging
    if not app.debug:
        # Set up Flask logger
        flask_logger = logging.getLogger("flask.app")
        flask_logger.setLevel(config.logging.level.value)
        
        # Add handler if not already configured
        if not flask_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ))
            flask_logger.addHandler(handler)
    
    # Add context processor for template variables
    @app.context_processor
    def inject_global_variables():
        """Inject global variables into templates."""
        return {
            "app_name": config.app_name,
            "version": config.version,
            "environment": config.environment,
            "api_prefix": config.web.api_prefix,
        }
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        from flask import jsonify, render_template
        
        if os.environ.get("FLASK_ENV") == "development":
            return render_template("404.html"), 404
        
        return jsonify({
            "error": "Not Found",
            "message": "The requested resource was not found",
            "status": 404,
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        from flask import jsonify
        
        logger.error(f"Internal server error: {error}")
        
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "status": 500,
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle uncaught exceptions."""
        from flask import jsonify
        
        logger.error(f"Uncaught exception: {error}", exc_info=True)
        
        return jsonify({
            "error": "Internal Server Error",
            "message": str(error),
            "status": 500,
        }), 500
    
    return app


# Global app instance (for convenience)
_app = None


def get_app() -> Flask:
    """Get the global Flask application instance."""
    global _app
    if _app is None:
        _app = create_app()
    return _app
