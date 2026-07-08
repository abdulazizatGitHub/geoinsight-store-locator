"""
ingest.py — CSV → PostGIS ingestion pipeline
Reads data/stores.csv and inserts each row into the stores table
as a geography(Point, 4326) using ST_MakePoint(lng, lat).

Usage:
    python ingest.py
    python ingest.py --csv ../data/stores.csv   (explicit path)
    python ingest.py --truncate                  (clear table before insert)
"""

import csv
import os
import sys
import argparse
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

DATABASE_URL = os.getenv('DATABASE_URL')
DEFAULT_CSV  = os.path.join(os.path.dirname(__file__), '..', 'data', 'stores.csv')

INSERT_SQL = """
    INSERT INTO stores (name, geom, category) VALUES %s
"""

# ── Helpers ───────────────────────────────────────────────────────────────────
def validate_row(row: dict, line_num: int) -> tuple[str, float, float, str]:
    """Parse and validate a single CSV row. Raises ValueError on bad data."""
    name = row.get('name', '').strip()
    if not name:
        raise ValueError(f'Line {line_num}: empty name')

    category = row.get('category', 'other').strip()

    try:
        lat = float(row['lat'])
        lng = float(row['lng'])
    except (KeyError, ValueError):
        raise ValueError(f'Line {line_num}: lat/lng must be numeric')

    if not (-90 <= lat <= 90):
        raise ValueError(f'Line {line_num}: lat={lat} out of [-90, 90]')
    if not (-180 <= lng <= 180):
        raise ValueError(f'Line {line_num}: lng={lng} out of [-180, 180]')

    return name, lat, lng, category


def run(csv_path: str, truncate: bool = False) -> None:
    if not DATABASE_URL:
        print('ERROR: DATABASE_URL not set in .env', file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(csv_path):
        print(f'ERROR: CSV not found at {csv_path}', file=sys.stderr)
        sys.exit(1)

    # ── Read & validate CSV ────────────────────────────────────────────────────
    records: list[tuple[str, float, float, str]] = []
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # start=2 because row 1 is header
            name, lat, lng, category = validate_row(row, i)
            records.append((name, lat, lng, category))

    print(f'CSV loaded: {len(records)} valid rows from {csv_path}')

    # ── Connect & insert ───────────────────────────────────────────────────────
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                if truncate:
                    cur.execute('TRUNCATE TABLE stores RESTART IDENTITY;')
                    print('Table truncated.')

                # Prepare data for bulk insert
                insert_data = [(name, f'POINT({lng} {lat})', category) for name, lat, lng, category in records]
                
                if insert_data:
                    execute_values(cur, INSERT_SQL, insert_data, template="(%s, ST_GeogFromText(%s), %s)")
                    print(f'Inserted: {len(insert_data)} rows')

        # ── Verify ────────────────────────────────────────────────────────────
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM stores;')
            db_count = cur.fetchone()[0]
            print(f'DB row count: {db_count}')

            cur.execute(
                "SELECT name, ST_AsText(geom) FROM stores ORDER BY id LIMIT 3;"
            )
            print('\nSpot-check (first 3 rows):')
            for name, geom_text in cur.fetchall():
                safe_name = name.encode('ascii', 'replace').decode('ascii')
                print(f'  {safe_name!r:45s} -> {geom_text}')

        if db_count >= len(records):
            print('\n=== Ingestion COMPLETE ===')
        else:
            print(f'\nWARN: Expected {len(records)} rows, found {db_count}')

    finally:
        conn.close()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ingest stores CSV into PostGIS')
    parser.add_argument('--csv',      default=DEFAULT_CSV, help='Path to CSV file')
    parser.add_argument('--truncate', action='store_true',  help='Clear table before insert')
    args = parser.parse_args()

    run(csv_path=args.csv, truncate=args.truncate)
