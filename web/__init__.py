"""
Web module for Free Fire Guest Account Checker
Contains both Flask and FastAPI applications
"""

from __future__ import annotations

__all__ = [
    "app",
    "app_fastapi",
    "routes",
    "models",
    "run_flask",
    "run_fastapi"
]

from .app import app, run_flask
from .app_fastapi import app as app_fastapi, run_fastapi
from . import routes, models
