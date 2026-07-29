import psycopg

from app.config import POSTGRES_DSN


def check_indexed_chunks():
    conn = psycopg.connect(POSTGRES_DSN)
    cur = conn.cursor()

    cur.execute(
        "SELECT strategy, count(*) FROM policy_chunks GROUP BY strategy;"
    )
    print("--- Chunk counts by strategy ---")
    for strategy, count in cur.fetchall():
        print(f"{strategy}: {count}")

    cur.execute(
        "SELECT source, strategy, chunk_index, left(text, 60) FROM policy_chunks ORDER BY source, strategy, chunk_index;"
    )
    print("\n--- Sample rows ---")
    for source, strategy, chunk_index, preview in cur.fetchall():
        print(f"[{source} / {strategy} / {chunk_index}] {preview}...")

    cur.close()
    conn.close()


if __name__ == "__main__":
    check_indexed_chunks()