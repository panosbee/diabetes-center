"""
Config package περιέχει τις ρυθμίσεις της εφαρμογής.
"""

from .config import (
    JWT_SECRET_KEY,
    UPLOAD_FOLDER,
    ALLOWED_EXTENSIONS,
    MAX_CONTENT_LENGTH,
    DEEPSEEK_API_KEY,
    DEEPSEEK_API_URL,
    MONGO_URI,
    DATABASE_NAME,
    TESSERACT_CMD
)

__all__ = [
    'JWT_SECRET_KEY',
    'UPLOAD_FOLDER',
    'ALLOWED_EXTENSIONS',
    'MAX_CONTENT_LENGTH',
    'DEEPSEEK_API_KEY',
    'DEEPSEEK_API_URL',
    'MONGO_URI',
    'DATABASE_NAME',
    'TESSERACT_CMD'
] 