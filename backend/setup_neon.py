import os
import psycopg2

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not set")
    exit(1)

print("Connecting to Neon...")
conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor()

print("Creating PostGIS extension...")
cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

print("Creating stores table...")
cur.execute("""
CREATE TABLE IF NOT EXISTS stores (
    id       SERIAL PRIMARY KEY,
    name     TEXT NOT NULL,
    geom     geography(Point, 4326) NOT NULL,
    category TEXT NOT NULL DEFAULT 'other'
);
""")

print("Creating spatial index...")
cur.execute("CREATE INDEX IF NOT EXISTS stores_geom_idx ON stores USING GIST(geom);")

print("Done setting up schema on Neon.")
cur.close()
conn.close()
