"""python scripts/check_connection.py  -> verifies credentials and MySQL version."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db_manager import DatabaseConnection

db = DatabaseConnection()
row = db.fetch_one("SELECT VERSION() AS version, DATABASE() AS db_name")
version = row["version"] if row else "Unknown"
db_name = row["db_name"] if row else "Unknown"

print(f"Connected successfully! MySQL {version}, database '{db_name}'")
major_version = version.split(".")[0]
if major_version.isdigit() and int(major_version) < 8:
    print("WARNING: MySQL 8.0+ is required for CTEs and window functions.")
