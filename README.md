# GeoInsight — Web-GIS Store Locator

> A production-grade spatial store locator built with **React**, **FastAPI**, and **PostGIS** — featuring real-time routing (walk / bike / car), convex hull spatial analysis, and 2 000+ real Islamabad POIs from OpenStreetMap.

---

## Live Demo

| Service | URL |
|---|---|
| Frontend | _Deploy to Vercel — see [DEPLOYMENT.md](./DEPLOYMENT.md)_ |
| Backend API | _Deploy to Render — see [DEPLOYMENT.md](./DEPLOYMENT.md)_ |
| API Docs | `http://localhost:8000/docs` (local) |

---

## Screenshots

> Drop a pin → category-filtered markers appear → click any for real-road directions.

---

## Tech Stack

```
┌─────────────────────────────────────────────────────┐
│  Browser                                            │
│  React 19 + react-leaflet 5 + Leaflet 1.9           │
│  Vite 8 (dev server / production bundler)           │
└────────────────────┬────────────────────────────────┘
                     │ HTTP / REST (JSON + GeoJSON)
┌────────────────────▼────────────────────────────────┐
│  FastAPI (Python 3.12)                              │
│  uvicorn  ·  psycopg2  ·  python-dotenv             │
└────────────────────┬────────────────────────────────┘
                     │ SQL (parameterised, PostGIS)
┌────────────────────▼────────────────────────────────┐
│  PostgreSQL 16 + PostGIS 3.6                        │
│  geography(Point,4326) + GIST index                 │
└─────────────────────────────────────────────────────┘
                     │ Routing
┌────────────────────▼────────────────────────────────┐
│  OSRM (OpenStreetMap Routing Machine)               │
│  foot  ·  bike  ·  driving  — free, no API key     │
└─────────────────────────────────────────────────────┘
```

---

## Spatial Features

| Feature | PostGIS Function | Description |
|---|---|---|
| Radius search | `ST_DWithin` | Find stores within N km using index-aware geography query |
| Distance ranking | `ST_Distance` | Returns exact metres, orders results nearest-first |
| Convex Hull | `ST_ConvexHull(ST_Collect())` | Bounding polygon around all matched stores |
| Walk time | `ceil(distance_m / 83.33)` | Straight-line estimate at 5 km/h |
| Category filter | `category = ANY(%s)` | Multi-select SQL array parameter |

---

## Project Structure

```
GIS Store Locator/
├── .env                        # DATABASE_URL (never committed)
├── .gitignore
├── DEPLOYMENT.md               # Step-by-step deployment guide
├── README.md
│
├── data/
│   └── stores.csv              # 2 026 real Islamabad POIs (OSM)
│
├── backend/
│   ├── main.py                 # FastAPI app — /health, /stores/nearby
│   ├── db.py                   # Connection pool (SimpleConnectionPool)
│   ├── ingest.py               # CSV → PostGIS ingestion pipeline
│   ├── fetch_overpass.py       # Fetch real OSM data from Overpass API
│   ├── verify_routing.py       # OSRM routing quality checks
│   ├── stress_test_api.py      # Module 2 API contract tests
│   ├── stress_test_module4.py  # Module 4 category/hull/walktime tests
│   ├── requirements.txt        # pip dependencies
│   └── venv/                   # (gitignored)
│
└── frontend/
    ├── index.html
    ├── vite.config.js          # React plugin + dev-server proxy
    ├── package.json
    └── src/
        ├── main.jsx            # React entry + leaflet CSS import
        ├── index.css           # Dark design system
        └── App.jsx             # Full application component
```

---

## Local Setup

### Prerequisites

| Tool | Minimum Version |
|---|---|
| Python | 3.12 |
| Node.js | 18 |
| PostgreSQL | 14 |
| PostGIS extension | 3.x |

### 1 — Database

```sql
-- Run in psql as superuser
CREATE DATABASE geoinsight;
\c geoinsight
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create the stores table
CREATE TABLE IF NOT EXISTS stores (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    geom        geography(Point, 4326) NOT NULL,
    category    TEXT NOT NULL DEFAULT 'other'
);
CREATE INDEX IF NOT EXISTS stores_geom_idx ON stores USING GIST(geom);
```

### 2 — Environment

```bash
# Copy the example and fill in your values
cp .env.example .env
```

`.env` format:
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/geoinsight
```

> If your PostgreSQL runs on a non-default port (e.g. 5433), update the URL accordingly.

### 3 — Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

**Fetch real data and ingest:**
```bash
# Fetch 2 000+ real Islamabad POIs from OpenStreetMap
python fetch_overpass.py

# Ingest into PostGIS
python ingest.py --truncate

# Start API server
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 4 — Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

---

## API Reference

### `GET /health`

Liveness check.

**Response:**
```json
{ "status": "ok", "db": "connected" }
```

---

### `GET /stores/nearby`

Spatial proximity search. All computation is performed in PostGIS.

**Parameters:**

| Name | Type | Required | Constraints | Description |
|---|---|---|---|---|
| `lat` | float | ✅ | `[-90, 90]` | Search centre latitude |
| `lng` | float | ✅ | `[-180, 180]` | Search centre longitude |
| `radius_km` | float | ✅ | `(0, 100]` | Search radius in kilometres |
| `category` | string | ❌ | comma-separated | Filter by category e.g. `bank,hospital` |

**Response — GeoJSON FeatureCollection:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [73.0371, 33.7295] },
      "properties": {
        "id": 42,
        "name": "Faisal Mosque",
        "category": "mosque",
        "distance_m": 0.0,
        "walk_time_min": 0
      }
    }
  ],
  "hull": {
    "type": "Polygon",
    "coordinates": [[[73.03, 33.72], ...]]
  }
}
```

**Validation errors return HTTP 422.**

---

## Running Tests

```bash
cd backend

# Requires uvicorn running on port 8000
python stress_test_api.py        # Module 2: API contract (9 tests)
python stress_test_module4.py    # Module 4: category/hull/walktime (20 tests)
python verify_routing.py         # OSRM routing quality (21 tests)
```

---

## Routing

Routes are fetched client-side from free OSRM servers — **no API key required**.

| Mode | Server | Profile | Typical Speed |
|---|---|---|---|
| 🚶 Walk | `routing.openstreetmap.de` | foot | ~4.5 km/h |
| 🚲 Bike | `routing.openstreetmap.de` | bike | ~14 km/h |
| 🚗 Car | `router.project-osrm.org` | driving | ~40 km/h |

Routes use the **OpenStreetMap road network** — they follow actual mapped roads, not straight lines. Verified: road distance is always ≥ crow-flies distance.

> **Note:** Routing accuracy depends on OSM data quality for the region. Islamabad's main road network is well-mapped. Remote or newly built areas may have incomplete coverage.

---

## Categories

| Category | Emoji | OSM Tag |
|---|---|---|
| pharmacy | 💊 | `amenity=pharmacy` |
| hospital | 🏥 | `amenity=hospital`, `amenity=clinic` |
| restaurant | 🍽️ | `amenity=restaurant`, `amenity=fast_food` |
| cafe | ☕ | `amenity=cafe` |
| bank | 🏦 | `amenity=bank` |
| mosque | 🕌 | `amenity=place_of_worship` + `religion=muslim` |
| supermarket | 🛒 | `shop=supermarket`, `shop=mall` |
| school | 🎓 | `amenity=school` |
| fuel | ⛽ | `amenity=fuel` |

---

## Deployment

See **[DEPLOYMENT.md](./DEPLOYMENT.md)** for step-by-step instructions to deploy free on:
- **Frontend** → Vercel
- **Backend** → Render
- **Database** → Neon.tech (PostgreSQL + PostGIS, always-on free tier)

---

## Interview Talking Points

| Question | Answer |
|---|---|
| Why `geography` type not `geometry`? | `geography` uses an earth-curvature model. `ST_DWithin` on geography returns accurate metres, critical for real-world proximity search. |
| Why GIST index? | PostGIS spatial queries use R-tree indexes (GIST) for bounding-box pre-filtering before exact geometry tests — O(log n) vs O(n). |
| Why PostGIS for convex hull instead of client-side? | Server-side aggregation (`ST_ConvexHull(ST_Collect())`) means only one GeoJSON polygon crosses the wire, not all coordinates. |
| OSRM vs Google Maps? | OSRM is open-source, uses OSM data, and has no API key or cost. Production apps would use Google Maps/Mapbox for verified road data and traffic. |
| Why CTE in the nearby query? | The CTE materialises the filtered result set once, so `ST_ConvexHull(ST_Collect())` can aggregate over it without a second full-table scan. |

---

## License

MIT — see [LICENSE](./LICENSE)
