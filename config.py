"""Application configuration for the ByteBodega project."""

import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")


def _persistent_secret_key():
    """Create (once) and reuse a secret key so sessions survive restarts."""
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    key_path = os.path.join(INSTANCE_DIR, "secret_key")
    if os.path.exists(key_path):
        with open(key_path, "r", encoding="utf-8") as handle:
            existing = handle.read().strip()
            if existing:
                return existing
    generated = os.urandom(32).hex()
    with open(key_path, "w", encoding="utf-8") as handle:
        handle.write(generated)
    return generated


class Config:
    SECRET_KEY = os.environ.get("BYTEBODEGA_SECRET_KEY") or _persistent_secret_key()
    DATABASE = os.path.join(INSTANCE_DIR, "bytebodega.db")
    UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads", "products")

    # Session handling
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Store rules
    SHIPPING_FEE = 79.00
    FREE_SHIPPING_THRESHOLD = 2500.00
    ITEMS_PER_PAGE = 12

    # Uploads
    MAX_CONTENT_LENGTH = 6 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
