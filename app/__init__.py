"""Core domain and auth scaffold for Paperclip baseline service."""

from .config import Settings
from .server import create_server

__all__ = ["Settings", "create_server"]
