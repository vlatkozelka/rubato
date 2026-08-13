import os
import re
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("POSTGRES_DSN","")
if not DATABASE_URL:
    sys.exit("DATABASE_URL not found in .env")

SQL_DIR = Path(os.getenv("SQL_DIR", "../db/init"))

def sort_key(path: Path):
    match = re.match(r"^(\d+)_", path.name)
    return int(match.group(1)) if match else float("inf")

def main():
    sql_files = sorted(SQL_DIR.glob("*.sql"), key=sort_key)
    if not sql_files:
        print(f"No .sql files found in {SQL_DIR}")
        return

    with psycopg.connect(DATABASE_URL) as conn:
        try:
            with conn.cursor() as cur:
                for sql_file in sql_files:
                    print(f"Running {sql_file.name}...")
                    sql = sql_file.read_text()
                    cur.execute(sql)
            conn.commit()
            print("All migrations ran successfully.")
        except Exception as e:
            conn.rollback()
            print(f"Failed on {sql_file.name}: {e}")
            raise

if __name__ == "__main__":
    main()