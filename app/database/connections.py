import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

_first_year_engine = None
_second_year_engine = None


def _build_url(prefix: str) -> str:
    user = quote_plus(os.getenv(f"{prefix}_DB_USER", ""))
    password = quote_plus(os.getenv(f"{prefix}_DB_PASSWORD", ""))
    host = os.getenv(f"{prefix}_DB_HOST", "")
    port = os.getenv(f"{prefix}_DB_PORT", "")
    name = os.getenv(f"{prefix}_DB_NAME", "")

    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def create_first_year_connection():
    global _first_year_engine

    if _first_year_engine is None:
        _first_year_engine = create_engine(_build_url("FIRST_YEAR"))

    return _first_year_engine


def create_second_year_connection():
    global _second_year_engine

    if _second_year_engine is None:
        _second_year_engine = create_engine(_build_url("SECOND_YEAR"))

    return _second_year_engine