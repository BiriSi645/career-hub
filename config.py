import os
from secrets import token_hex
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def postgres_url(variable_name, default=None):
    """Read a PostgreSQL connection URL, including the previous URL format."""
    database_url = os.getenv(variable_name, default)
    if not database_url:
        raise RuntimeError(f"{variable_name} must be set.")

    if database_url.startswith("postgresql+psycopg://"):
        database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    if not database_url.startswith("postgresql://"):
        raise RuntimeError(
            f"{variable_name} must use PostgreSQL with the psycopg driver."
        )

    return database_url


class Config:
    ON_VERCEL = os.getenv("VERCEL") == "1" or os.getenv("VERCEL_ENV") in {"preview", "production"}
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    if len(SECRET_KEY) < 32 or SECRET_KEY == "replace-with-a-long-random-value":
        if ON_VERCEL:
            raise RuntimeError("Set a stable SECRET_KEY of at least 32 characters on Vercel.")
        SECRET_KEY = token_hex(32)
    DATABASE_URL = postgres_url("DATABASE_URL", None if ON_VERCEL else "postgresql://localhost:5432/career_hub")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = (
        ON_VERCEL or os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    )
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    RESUME_STORAGE = "blob" if ON_VERCEL else os.getenv("RESUME_STORAGE", "local")
    if RESUME_STORAGE not in {"local", "blob"}:
        raise RuntimeError("RESUME_STORAGE must be local or blob.")
    RESUME_MAX_BYTES = 4 * 1024 * 1024 if RESUME_STORAGE == "blob" else 10 * 1024 * 1024
    MAX_CONTENT_LENGTH = 4_500_000 if RESUME_STORAGE == "blob" else 10 * 1024 * 1024
    RESUME_UPLOAD_DIR = BASE_DIR / "instance" / "resumes"


