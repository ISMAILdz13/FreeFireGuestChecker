"""
Web Interface Package
Provides Flask-based web interface for the account checker.
"""

from .app import create_app, get_app
from .routes import api_router
from .models import APIResponse

__all__ = ['create_app', 'get_app', 'api_router', 'APIResponse']
