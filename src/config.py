"""Single place that knows how to reach the database.

Order of lookup:
1. st.secrets["db"] (Streamlit Cloud) — checked first
2. Environment variables / .env (local development, scripts)
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _to_bool(v) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def get_db_config() -> dict:
    # Check Streamlit secrets FIRST (Streamlit Cloud)
    # This must come before env vars because load_dotenv() sets DB_HOST=localhost
    # from .env which would otherwise take priority on Streamlit Cloud.
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "db" in st.secrets:
            s = st.secrets["db"]
            return {
                "host": s["host"],
                "port": int(s.get("port", 3306)),
                "user": s["user"],
                "password": s.get("password", ""),
                "database": s["database"],
                "ssl": _to_bool(s.get("ssl", False)),
                "ssl_ca": s.get("ssl_ca") or None,
            }
    except Exception:
        pass

    # Fall back to environment variables / .env (local development)
    if os.getenv("DB_HOST"):
        return {
            "host": os.environ["DB_HOST"],
            "port": int(os.getenv("DB_PORT", "3306")),
            "user": os.environ["DB_USER"],
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.environ["DB_NAME"],
            "ssl": _to_bool(os.getenv("DB_SSL", "false")),
            "ssl_ca": os.getenv("DB_SSL_CA") or None,
        }

    raise RuntimeError(
        "Database credentials not found. Create .env (local) or set "
        "st.secrets['db'] (Streamlit Cloud)."
    )


def get_engine() -> Engine:
    cfg = get_db_config()
    url = URL.create(
        "mysql+pymysql",
        username=cfg["user"],
        password=cfg["password"],
        host=cfg["host"],
        port=cfg["port"],
        database=cfg["database"],
    )
    connect_args: dict = {}
    if cfg["ssl"]:
        connect_args["ssl"] = {"ca": cfg["ssl_ca"]} if cfg["ssl_ca"] else {"check_hostname": False}
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800, connect_args=connect_args)


_shared_engine = None


def get_shared_engine() -> Engine:
    """Return a module-level cached SQLAlchemy engine for pd.read_sql() calls."""
    global _shared_engine
    if _shared_engine is None:
        _shared_engine = get_engine()
    return _shared_engine
