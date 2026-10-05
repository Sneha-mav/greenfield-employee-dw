"""Run all ETL stored procedures to load staging -> OLTP -> OLAP.

Usage: python scripts/run_etl.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db_manager import DatabaseConnection

db = DatabaseConnection()

steps = [
    ("sp_load_dim_department",              None),
    ("sp_load_dim_project",                 None),
    ("sp_load_dim_employee",                (None,)),
    ("sp_load_fact_performance_reviews",    None),
]

for name, args in steps:
    print(f"Running {name}...", flush=True)
    if args:
        db.call_procedure(name, args)
    else:
        db.call_procedure(name)
    print(f"  Done.", flush=True)

print("All ETL procedures complete.")
