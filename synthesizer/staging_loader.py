"""StagingLoader: bulk-loads the synthesized CSVs into the stg_* tables (truncate + reload)."""
import logging
import os
import time
from pathlib import Path

import mysql.connector
import pandas as pd
from dotenv import load_dotenv
from mysql.connector import Error

logger = logging.getLogger(__name__)

# csv file name -> staging table (names follow sql/01_staging_ddl.sql and the data dictionary)
TABLE_MAP = {
    "employees_synth.csv": "stg_employee",
    "employee_history.csv": "stg_employee_history",
    "projects.csv": "stg_project",
    "assignments.csv": "stg_assignment",
    "reviews.csv": "stg_review",
}


class StagingLoader:
    def __init__(self, csv_dir="data/synthesized", database=None, chunk_size=20_000):
        load_dotenv()
        self._csv_dir = Path(csv_dir)
        self._database = database or os.getenv("DB_NAME")
        if not self._database:
            raise ValueError("DB_NAME is not set - add DB_NAME=<your database> to .env")
        self._chunk_size = chunk_size
        self._conn = None

    # ---------- connection ----------
    def _connect(self):
        try:
            self._conn = mysql.connector.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "3306")),
                user=os.getenv("DB_USER", "root"),
                password=os.getenv("DB_PASSWORD", ""),
                database=self._database,
                autocommit=False,
            )
        except Error as exc:
            logger.error("Could not connect to MySQL: %s", exc)
            raise

    # ---------- loading ----------
    def load_all(self):
        self._connect()
        totals = {}
        try:
            for csv_name, table in TABLE_MAP.items():
                totals[table] = self._load_table(csv_name, table)
            self._conn.commit()
        except (Error, FileNotFoundError):
            self._conn.rollback()
            logger.exception("Staging load failed, rolled back")
            raise
        finally:
            self._conn.close()
        return totals

    def _load_table(self, csv_name, table):
        path = self._csv_dir / csv_name
        if not path.exists():
            raise FileNotFoundError(f"{path} not found - run python -m synthesizer.run_synthesis first")
        start = time.time()
        cur = self._conn.cursor()
        cur.execute(f"TRUNCATE TABLE {table}")
        loaded = 0
        for chunk in pd.read_csv(path, chunksize=self._chunk_size):
            cols = ", ".join(chunk.columns)
            marks = ", ".join(["%s"] * len(chunk.columns))
            sql = f"INSERT INTO {table} ({cols}) VALUES ({marks})"
            rows = chunk.astype(object).where(chunk.notna(), None)   # NaN -> NULL
            cur.executemany(sql, rows.values.tolist())
            loaded += len(chunk)
        cur.close()
        logger.info("%-22s %8d rows in %.1fs", table, loaded, time.time() - start)
        return loaded


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(StagingLoader().load_all())