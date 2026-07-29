import psycopg

conn = psycopg.connect("postgresql://rubato:rubato@localhost:5432/rubato")
result = conn.execute("SELECT 1;").fetchone()
print(result)
conn.close()