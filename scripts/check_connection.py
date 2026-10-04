"""python scripts/check_connection.py  -> verifies credentials and MySQL version."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from src.config import get_engine

with get_engine().connect() as conn:
    version = conn.execute(text("SELECT VERSION()")).scalar()
    db = conn.execute(text("SELECT DATABASE()")).scalar()
print(f"Connected. MySQL {version}, database '{db}'")
if int(version.split(".")[0]) < 8:
    print("WARNING: MySQL 8.0+ is required (CTEs, window functions).")