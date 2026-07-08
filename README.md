# GeoInsight — Web-GIS Store Locator

> A production-grade spatial store locator built with **React 19**, **FastAPI**, and **PostGIS** — featuring a professional landing page, real-time multi-modal routing (walk / bike / car via OSRM), live Recharts analytics, convex hull spatial analysis, and **2,500+ real Islamabad POIs** from OpenStreetMap. Fully responsive across desktop, tablet, and mobile.

---

## Live Demo

| Service | URL |
|---|---|
| 🌐 Frontend | [geoinsight-store-locator.vercel.app](https://geoinsight-store-locator.vercel.app) |
| ⚙️ Backend API | [geoinsight-store-locator.onrender.com](https://geoinsight-store-locator.onrender.com) |
| 📖 API Docs | `https://geoinsight-store-locator.onrender.com/docs` |

> **Note:** The Render backend is on a free tier and may take ~30 seconds to wake up on first request. Use [UptimeRobot](https://uptimerobot.com) to keep it warm.

---

## Features

- 🗺️ **Professional Landing Page** — Dark-themed hero with glassmorphism feature cards
- 📍 **PostGIS Radius Search** — `ST_DWithin` with GIST index for sub-millisecond spatial queries
- 📊 **Live Recharts Analytics** — Category distribution bar chart updates in real-time with search results
- 🛣️ **Multi-Modal Routing** — Walk, Bike, Car via free OSRM (no API key); real road geometry
- 🔷 **Convex Hull Overlay** — `ST_ConvexHull(ST_Collect())` bounding polygon on all matched results
- 🧩 **Category Filters** — 9 categories (pharmacy, hospital, restaurant, cafe, bank, mosque, supermarket, school, fuel)
- 📱 **Fully Responsive** — Desktop sidebar, tablet (260px sidebar), mobile bottom-sheet drawer with FAB
- 🔒 **Secure** — CORS restricted to Vercel origin, parameterised SQL, secrets via env vars only

---

## Tech Stack

```
┌─────────────────────────────────────────────────────┐
│  Browser                                            │
│  React 19 + react-leaflet 5 + Leaflet 1.9           │
│  Recharts (analytics) · lucide-react (icons)        │
│  react-router-dom (Landing → Map routing)           │
│  Vite 8 (dev server / production bundler)           │
└────────────────────┬────────────────────────────────┘
                     │ HTTP / REST (JSON + GeoJSON)
┌────────────────────▼────────────────────────────────┐
│  FastAPI (Python 3.12)                              │
│  uvicorn  ·  psycopg2  ·  python-dotenv             │
└────────────────────┬────────────────────────────────┘
                     │ SQL (parameterised, PostGIS)
┌────────────────────▼────────────────────────────────┐
│  PostgreSQL 16 + PostGIS 3.x                        │
│  geography(Point,4326) + GIST index                 │
│  Hosted on Neon.tech (serverless, free tier)        │
└─────────────────────────────────────────────────────┘
                     │ Routing (client-side)
┌────────────────────▼────────────────────────────────┐
│  OSRM (OpenStreetMap Routing Machine)               │
│  foot · bike · driving  — free, no API key          │
└─────────────────────────────────────────────────────┘
```

---

## Spatial Features

| Feature | PostGIS Function | Description |
|---|---|---|
| Radius search | `ST_DWithin` | Index-aware geography query — finds stores within N km |
| Distance ranking | `ST_Distance` | Returns exact metres, orders results nearest-first |
| Convex Hull | `ST_ConvexHull(ST_Collect())` | Bounding polygon around all matched stores |
| Walk time estimate | `ceil(distance_m / 83.33)` | Straight-line estimate at 5 km/h |
| Category filter | `category = ANY(%s)` | Multi-select SQL array parameter |
| Building footprints | `nwr` + `out center` | Overpass `nwr` query captures nodes, ways & relations |

---

## Project Structure

```
GIS Store Locator/
├── .env                        # DATABASE_URL (never committed)
├── .gitignore
├── DEPLOYMENT.md               # Step-by-step deployment guide
├── README.md
│
├── .github/
│   └── workflows/
│       └── ci.yml              # CI/CD: test → build → deploy (Render + Vercel)
│
├── data/
│   └── stores.csv              # 2,500 real Islamabad POIs (OSM)
│
├── backend/
│   ├── main.py                 # FastAPI app — /health, /stores/nearby
│   ├── db.py                   # Connection pool (SimpleConnectionPool)
│   ├── ingest.py               # CSV → PostGIS bulk ingestion (execute_values)
│   ├── fetch_overpass.py       # Fetch real OSM data (nwr query, out center)
│   ├── setup_neon.py           # One-shot remote DB schema initialiser
│   ├── verify_routing.py       # OSRM routing quality checks (21 tests)
│   ├── stress_test_api.py      # API contract tests
│   ├── stress_test_module4.py  # Category/hull/walktime tests
│   └── requirements.txt
│
└── frontend/
    ├── index.html              # favicon.svg + SEO meta tags
    ├── public/
    │   └── favicon.svg         # Custom gradient map-pin icon
    ├── vite.config.js          # React plugin + dev-server proxy
    ├── package.json
    └── src/
        ├── main.jsx            # React entry + leaflet CSS import
        ├── index.css           # Dark design system + responsive breakpoints
        ├── App.jsx             # Router (Landing → MapDashboard)
        └── pages/
            ├── Landing.jsx     # Professional hero landing page
            └── MapDashboard.jsx # Full spatial app + bottom sheet for mobile
```

---

## Local Setup

### Prerequisites

| Tool | Minimum Version |
|---|---|
| Python | 3.12 |
| Node.js | 20 |
| PostgreSQL | 14 |
| PostGIS extension | 3.x |

### 1 — Database

```sql
-- Run in psql as superuser
CREATE DATABASE geoinsight;
\c geoinsight
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS stores (
    id       SERIAL PRIMARY KEY,
    name     TEXT NOT NULL,
    geom     geography(Point, 4326) NOT NULL,
    category TEXT NOT NULL DEFAULT 'other'
);
CREATE INDEX IF NOT EXISTS stores_geom_idx ON stores USING GIST(geom);
```

### 2 — Environment

```bash
cp .env.example .env
```

`.env` format:
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/geoinsight
```

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
# Fetch 2,500 real Islamabad POIs from OpenStreetMap (nodes + buildings)
python fetch_overpass.py

# Ingest into PostGIS using bulk execute_values
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

**Environment variable (production only):**
```
VITE_API_BASE=https://your-backend.onrender.com
```
Leave empty for local development (Vite proxy handles it automatically).

---

## API Reference

### `GET /health`

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
| `category` | string | ❌ | comma-separated | Filter e.g. `bank,hospital` |

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
        "distance_m": 312.4,
        "walk_time_min": 4
      }
    }
  ],
  "hull": { "type": "Polygon", "coordinates": [[[73.03, 33.72], ...]] }
}
```

---

## CI/CD Pipeline

GitHub Actions (`.github/workflows/ci.yml`) runs on every push to `main`:

1. **`backend-test`** — Installs Python 3.12, runs schema setup, checks imports
2. **`frontend-build`** — Installs Node 20, runs `npm ci` + `npm run build`
3. **`deploy`** (only on `main`, after both pass):
   - Triggers Render deploy hook → redeploys backend
   - Runs `amondnet/vercel-action` → redeploys frontend

**Required GitHub Secrets:**

| Secret | Where to get it |
|---|---|
| `RENDER_DEPLOY_HOOK` | Render → Service → Settings → Deploy Hook |
| `VERCEL_TOKEN` | Vercel → Account Settings → Tokens |
| `VERCEL_ORG_ID` | Vercel → Project Settings |
| `VERCEL_PROJECT_ID` | Vercel → Project Settings |

---

## Routing

Routes are fetched client-side from free OSRM servers — **no API key required**.

| Mode | OSRM Server | Typical Speed |
|---|---|---|
| 🚶 Walk | `routing.openstreetmap.de/routed-foot` | ~5 km/h |
| 🚲 Bike | `routing.openstreetmap.de/routed-bike` | ~15 km/h |
| 🚗 Car | `router.project-osrm.org/driving` | ~40 km/h |

> Routes follow actual OSM road network. Walk/bike routes avoid highways tagged `foot=no` / `bicycle=no`, which is why they can be longer than car routes near major roads — this is **correct GIS behaviour**, not a bug.

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

## Responsive Design

| Breakpoint | Layout |
|---|---|
| `> 900px` (Desktop) | Fixed 320px sidebar + full map |
| `641–900px` (Tablet) | Narrowed 260px sidebar + map |
| `≤ 640px` (Mobile) | Full-screen map + slide-up bottom sheet + floating FAB |

---

## Deployment

See **[DEPLOYMENT.md](./DEPLOYMENT.md)** for step-by-step instructions:
- **Database** → Neon.tech (PostgreSQL + PostGIS, serverless free tier)
- **Backend** → Render (free web service)
- **Frontend** → Vercel (free hobby plan)

---

## Interview Talking Points

| Question | Answer |
|---|---|
| Why `geography` type not `geometry`? | `geography` uses earth-curvature model. `ST_DWithin` returns accurate metres, critical for real-world proximity. |
| Why GIST index? | PostGIS spatial queries use R-tree (GIST) for bounding-box pre-filtering — O(log n) vs O(n). |
| Why `nwr` in Overpass? | `node` misses buildings mapped as polygons. `nwr` + `out center` captures nodes, ways and relations and returns the centroid. |
| Why PostGIS convex hull? | Server-side `ST_ConvexHull(ST_Collect())` sends one polygon over the wire, not all coordinates. |
| Why CTE in nearby query? | Materialises the filtered result once so `ST_ConvexHull` aggregates over it without a second full-table scan. |
| OSRM vs Google Maps? | OSRM is open-source, uses OSM data, no API cost. Walk/bike routes correctly avoid highways — real GIS routing behaviour. |
| Why `execute_values` for ingest? | Single batch insert of 2,500 rows is ~50× faster than individual `execute()` calls over a remote Neon connection. |

---

## License

MIT — see [LICENSE](./LICENSE)
