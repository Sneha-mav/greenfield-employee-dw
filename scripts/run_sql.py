"""Run .sql files against whichever DB the .env points to (local or hosted).

    python scripts/run_sql.py sql/01_staging_ddl.sql sql/02_oltp_ddl.sql

Supports DELIMITER blocks, so the same runner works for stored procedures later.
Avoid trailing '-- comments' after a statement's semicolon.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import get_engine


def split_statements(sql: str) -> list[str]:
    delimiter, buf, stmts = ";", [], []
    for line in sql.splitlines():
        s = line.strip()
        if s.upper().startswith("DELIMITER "):
            delimiter = s.split(None, 1)[1]
            continue
        if s.startswith("--"):
            continue
        buf.append(line)
        if s.endswith(delimiter):
            stmt = "\n".join(buf).strip()
            stmt = stmt[: -len(delimiter)].strip()
            if stmt:
                stmts.append(stmt)
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        stmts.append(tail)
    return stmts


def main(files: list[str]) -> None:
    if not files:
        sys.exit(__doc__)
    raw = get_engine().raw_connection()  # raw cursor: no %-formatting surprises
    try:
        cur = raw.cursor()
        for f in files:
            stmts = split_statements(Path(f).read_text(encoding="utf-8"))
            print(f"--> {f} ({len(stmts)} statements)")
            for stmt in stmts:
                cur.execute(stmt)
            raw.commit()
        print("Done.")
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


if __name__ == "__main__":
    main(sys.argv[1:])
