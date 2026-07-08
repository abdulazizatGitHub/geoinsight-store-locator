"""
main.py — GeoInsight FastAPI application.

Endpoints:
    GET /health                    → {"status": "ok"}
    GET /stores/nearby             → GeoJSON FeatureCollection
        ?lat=<float>               latitude of search centre  [-90, 90]
        ?lng=<float>               longitude of search centre [-180, 180]
        ?radius_km=<float>         search radius in km        (0, 100]

All spatial computation is performed in PostGIS (ST_DWithin, ST_Distance).
No row-level distance arithmetic is performed in Python.
"""

import json
from contextlib import contextmanager
from typing import Generator

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import db

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title='GeoInsight Store Locator API',
    description='Spatial store search powered by PostGIS',
    version='1.0.0',
)

# CORS — allow all origins for local demo (React dev server on a different port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['GET'],
    allow_headers=['*'],
)


# ── DB helper ─────────────────────────────────────────────────────────────────
@contextmanager
def get_cursor() -> Generator:
    """Context manager: borrow a connection, yield a cursor, auto-return."""
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.rollback()          # read-only endpoint; rollback keeps conn clean
    finally:
        db.put_conn(conn)


# ── Core PostGIS query ────────────────────────────────────────────────────────
NEARBY_SQL = """
    WITH results AS (
        SELECT
            id,
            name,
            category,
            geom,
            ST_Distance(
                geom,
                ST_MakePoint(%(lng)s, %(lat)s)::geography
            ) AS distance_m
        FROM stores
        WHERE ST_DWithin(
            geom,
            ST_MakePoint(%(lng)s, %(lat)s)::geography,
            %(radius_m)s
        )
        {category_clause}
    )
    SELECT
        id,
        name,
        category,
        ST_AsGeoJSON(geom) AS geometry,
        distance_m,
        (SELECT ST_AsGeoJSON(ST_ConvexHull(ST_Collect(geom::geometry))) FROM results) AS hull_geojson
    FROM results
    ORDER BY distance_m;
"""


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get('/health')
def health() -> dict:
    """Liveness check — confirms API and DB connection are alive."""
    try:
        with get_cursor() as cur:
            cur.execute('SELECT 1;')
        return {'status': 'ok', 'db': 'connected'}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f'DB unavailable: {exc}')


@app.get('/stores/nearby')
def stores_nearby(
    lat: float = Query(..., ge=-90,   le=90,   description='Search centre latitude'),
    lng: float = Query(..., ge=-180,  le=180,  description='Search centre longitude'),
    radius_km: float = Query(..., gt=0, le=100, description='Search radius in kilometres'),
    category: str = Query(None, description='Filter by category (comma-separated)')
) -> JSONResponse:
    """
    Return all stores within radius_km of (lat, lng), ordered nearest-first.
    Response is a valid GeoJSON FeatureCollection with an optional hull_geojson.
    """
    import math

    radius_m = radius_km * 1000  # ST_DWithin on geography accepts metres
    params = {'lat': lat, 'lng': lng, 'radius_m': radius_m}

    category_clause = ""
    if category:
        cats = [c.strip() for c in category.split(',') if c.strip()]
        if cats:
            category_clause = "AND category = ANY(%(cats)s)"
            params['cats'] = cats

    sql = NEARBY_SQL.format(category_clause=category_clause)

    with get_cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    features = []
    hull_geojson = None

    for store_id, name, cat, geom_text, distance_m, hull_text in rows:
        geometry = json.loads(geom_text)
        
        # Grab hull from first row (it's the same for all rows due to CTE)
        if hull_geojson is None and hull_text:
            hull_geojson = json.loads(hull_text)

        # Walking speed ~5km/h -> 83.33 m/min
        walk_time_min = math.ceil(distance_m / 83.33)

        features.append({
            'type': 'Feature',
            'geometry': geometry,
            'properties': {
                'id': store_id,
                'name': name,
                'category': cat,
                'distance_m': round(distance_m, 2),
                'walk_time_min': walk_time_min
            },
        })

    feature_collection = {
        'type': 'FeatureCollection',
        'features': features,
        'hull': hull_geojson
    }

    return JSONResponse(content=feature_collection)
