"""
IndexTTS FastAPI - REST API wrapper for IndexTTS2
"""

__version__ = "1.0.0"

from .api import app, get_app

__all__ = ["app", "get_app"]

