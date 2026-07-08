# REQUIREMENTS.md — GeoInsight: Web-GIS Store Locator

**Version:** 1.0  
**Status:** Awaiting approval  
**Scope:** Solo build, local-only, 4–6 calendar days

---

## 1. Purpose & Context

GeoInsight is a web application that lets a user drop a pin on a map, set a search radius, and retrieve all stores within that radius ranked by real-world distance — with all spatial computation performed inside PostgreSQL/PostGIS, not in JavaScript. The project exists for one purpose: to make every geospatial claim on a CV truthful and defensible before a job interview closes. The scope is therefore fixed at the minimum feature set that exercises the full required skill stack (ReactJS, Leaflet, PostGIS spatial functions, GeoJSON, raw spatial data transformation) with no additions that do not serve that goal. The hard constraint is that the project must be complete, public, and demonstrable within 4–6 days from the start of work.

---

## 2. Scope

### In Scope

| #   | Feature                                                               |
| --- | --------------------------------------------------------------------- |
| 1   | CSV → PostGIS ingestion pipeline (raw spatial data transformation)    |
| 2   | `geography(Point, 4326)` column + GIST spatial index                  |
| 3   | FastAPI endpoint returning a GeoJSON `FeatureCollection`              |
| 4   | Leaflet map rendered in React via `react-leaflet`                     |
| 5   | Click-to-drop-pin and browser Geolocation API for search center       |
| 6   | Radius slider (1–20 km) driving a live spatial query                  |
| 7   | Distance-ranked markers with name + distance popups                   |
| 8   | Visual search-radius circle on the map                                |
| 9   | README with map screenshot, PostGIS SQL snippet, architecture summary |
| 10  | 60-second Loom demo video                                             |

### Out of Scope

| Feature                            | Reason excluded                                                     |
| ---------------------------------- | ------------------------------------------------------------------- |
| Authentication / user accounts     | Not required for demo; adds build time with zero CV value           |
| Docker / containerisation          | Unnecessary for local demo; adds setup risk                         |
| Cloud deployment                   | Out of time budget; local demo is sufficient for interview          |
| QGIS                               | Desktop GIS tool — not part of this stack                           |
| CesiumJS (3D globe)                | Stretch only; do not build until core ships                         |
| Mapbox base layer toggle           | Stretch only; do not build until core ships                         |
| Multi-user / concurrent sessions   | Single-user local demo is the entire target                         |
| Database migrations tooling        | Manual SQL scripts are sufficient for this scope                    |
| Unit / integration test suite      | Out of time budget for a 6-day build                                |
| Caching layer (Redis, etc.)        | Not needed at demo scale                                            |
| Any library not in the fixed stack | Stack is frozen: React, react-leaflet, FastAPI, PostgreSQL, PostGIS |

> **Assumption:** "Local-only" means the app runs on `localhost` and is demonstrated via screen recording. No public URL is required for the interview deliverable beyond the GitHub repo.

---

## 3. Functional Requirements

| ID    | Requirement                                                                                                                                                                                              | Acceptance Test                                                                                                                                  |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| FR-1  | **Data ingestion:** A Python script must read a CSV file with columns `name,lat,lng` and insert each row into the `stores` table as a `geography` point using `ST_MakePoint(lng, lat)`.                  | Running the script against a valid CSV produces the correct row count in the database; `SELECT COUNT(*) FROM stores` matches the CSV line count. |
| FR-2  | **Spatial storage:** Every inserted store must be stored in a `geography(Point, 4326)` column, not as raw float columns.                                                                                 | `\d stores` shows the `geom` column type as `geography(Point,4326)`.                                                                             |
| FR-3  | **Spatial index:** A GIST index must exist on the `geom` column before any API queries are run.                                                                                                          | `\d stores` shows a GIST index on `geom`; `EXPLAIN` on the nearby query shows index use (not Seq Scan) at scale.                                 |
| FR-4  | **Nearby endpoint:** The API must expose `GET /stores/nearby?lat=&lng=&radius_km=` and return all stores within `radius_km` of the given coordinates.                                                    | A request with valid params returns HTTP 200 and a valid GeoJSON `FeatureCollection`; results are confined to stores within the stated radius.   |
| FR-5  | **PostGIS spatial filter:** The radius filter must be implemented with `ST_DWithin` in the database query, not by fetching all rows and filtering in Python.                                             | The SQL executed (visible in FastAPI logs or `EXPLAIN ANALYZE`) uses `ST_DWithin`.                                                               |
| FR-6  | **Distance ranking:** Results must be ordered by `ST_Distance` ascending (nearest first).                                                                                                                | The `distance_m` property in each Feature increases monotonically through the returned array.                                                    |
| FR-7  | **GeoJSON output:** The endpoint response must be a valid GeoJSON `FeatureCollection` where each Feature's `geometry` is a `Point` produced by `ST_AsGeoJSON`.                                           | Response parses without error as valid GeoJSON; geometry coordinates match the stored lat/lng.                                                   |
| FR-8  | **Map render:** The frontend must display a Leaflet map centred on Islamabad on load, with an OpenStreetMap tile layer.                                                                                  | The map is visible in the browser with no API key required.                                                                                      |
| FR-9  | **Pin drop:** A user must be able to click anywhere on the map to set the search centre; the selected point must be visually distinguished from store markers.                                           | Clicking the map places a distinct marker; subsequent searches use that point.                                                                   |
| FR-10 | **Geolocation:** A "Use my location" button must request the browser Geolocation API and set the search centre to the returned coordinates.                                                              | Clicking the button, granting permission, and triggering a search uses the device's coordinates.                                                 |
| FR-11 | **Radius control:** A slider must allow the user to select a search radius between 1 km and 20 km in 1 km increments.                                                                                    | Moving the slider updates the displayed radius value and triggers a new API call.                                                                |
| FR-12 | **Search circle:** A circle of the chosen radius must be drawn on the map centred on the search pin.                                                                                                     | The circle redraws correctly when the pin or radius changes.                                                                                     |
| FR-13 | **Store markers + popups:** Each returned store must render as a map marker; clicking it must show a popup with the store name and formatted distance (e.g., "1.2 km away").                             | Clicking a marker shows the correct name and distance for that store.                                                                            |
| FR-14 | **Input validation:** The API must return HTTP 422 if `lat`, `lng`, or `radius_km` are missing, non-numeric, or out of plausible range (`lat` ∈ [−90, 90], `lng` ∈ [−180, 180], `radius_km` ∈ (0, 100]). | Requests with missing or out-of-range params return 422, not 500.                                                                                |

---

## 4. Non-Functional Requirements

| ID    | Requirement                                                                                                                                                                                                                |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| NFR-1 | **CRS correctness:** All coordinates must use EPSG:4326 (WGS84), the standard for GPS lat/lng. No other CRS is used or accepted.                                                                                           |
| NFR-2 | **`geography` type:** The `geom` column must use the PostGIS `geography` type (not `geometry`) so that `ST_Distance` and `ST_DWithin` return and accept metres on the Earth's surface without requiring manual projection. |
| NFR-3 | **Spatial index:** A GIST index on `geom` is required before the first API query runs, enabling index-accelerated bounding-box pre-filtering by `ST_DWithin`.                                                              |
| NFR-4 | **GeoJSON as API contract:** All spatial data crossing the API boundary must be formatted as GeoJSON, produced server-side by `ST_AsGeoJSON`. The frontend must not construct geometry strings manually.                   |
| NFR-5 | **Spatial computation in the database:** Distance filtering and ranking must be performed entirely in PostGIS SQL. No row-level distance arithmetic is permitted in Python or JavaScript.                                  |
| NFR-6 | **Basic input validation:** All three query parameters are validated server-side before the SQL query is constructed (see FR-14).                                                                                          |
| NFR-7 | **Local-only performance target:** Queries against ≤ 500 store rows must return in < 500 ms on a developer laptop. No optimisation beyond the GIST index is required.                                                      |

---

## 5. Data Model

### 5.1 `stores` Table

```sql
CREATE TABLE stores (
    id   SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    geom geography(Point, 4326)  -- WGS84 lat/lng; geography type ensures metric distance
);

CREATE INDEX stores_geom_idx ON stores USING GIST (geom);
```

**Column notes:**
- `geom` uses `geography`, not `geometry`. This is intentional: `geography` operates on a spherical model of the Earth and returns distances in metres without a manual projection step.
- `4326` is the EPSG code for WGS84 — the coordinate reference system used by GPS and all standard lat/lng data.
- The GIST index enables `ST_DWithin` to use bounding-box pre-filtering instead of scanning every row.

### 5.2 Input CSV Format

The ingestion script expects a UTF-8 CSV with a header row and the following columns, in order:

```
name,lat,lng
```

| Column | Type   | Constraints   | Example         |
| ------ | ------ | ------------- | --------------- |
| `name` | string | Non-empty     | `City Pharmacy` |
| `lat`  | float  | ∈ [−90, 90]   | `33.7215`       |
| `lng`  | float  | ∈ [−180, 180] | `73.0433`       |

> **No other columns are required.** Additional columns in the CSV are silently ignored by the ingestion script.

---

## 6. API Contract

### Endpoint

```
GET /stores/nearby
```

### Query Parameters

| Parameter   | Type  | Required | Validation    | Example   |
| ----------- | ----- | -------- | ------------- | --------- |
| `lat`       | float | Yes      | ∈ [−90, 90]   | `33.6844` |
| `lng`       | float | Yes      | ∈ [−180, 180] | `73.0479` |
| `radius_km` | float | Yes      | ∈ (0, 100]    | `5`       |

### Success Response — HTTP 200

A valid GeoJSON `FeatureCollection`. Features are ordered nearest-first.

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [73.0512, 33.6901]
      },
      "properties": {
        "id": 42,
        "name": "City Pharmacy",
        "distance_m": 847.3
      }
    }
  ]
}
```

### Error Response — HTTP 422

```json
{
  "detail": "radius_km must be between 0 and 100"
}
```

### Notes
- `coordinates` in GeoJSON are always `[longitude, latitude]` — this is the GeoJSON spec, not a convention to be argued with.
- `distance_m` is in metres, as returned by `ST_Distance` on `geography` columns. The frontend converts to kilometres for display.
- An empty radius returns `{ "type": "FeatureCollection", "features": [] }`, not a 404.

---

## 7. Core PostGIS Query

This is the heart of the project. Know every word of it.

```sql
SELECT
    id,
    name,
    ST_AsGeoJSON(geom)::json          AS geometry,
    ST_Distance(
        geom,
        ST_MakePoint(:lng, :lat)::geography
    )                                  AS distance_m
FROM stores
WHERE ST_DWithin(
    geom,
    ST_MakePoint(:lng, :lat)::geography,
    :radius_m          -- ST_DWithin on geography takes metres
)
ORDER BY distance_m;
```

### Why each function is used

| Function                            | Role                                                                                                                                                                                                                                                                                              |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ST_MakePoint(:lng, :lat)`          | Constructs a point from the user's coordinates. **Argument order is `(longitude, latitude)` — the single most common beginner mistake in PostGIS.**                                                                                                                                               |
| `::geography`                       | Casts the point to the `geography` type so all distance calculations use metres on the Earth's surface, not unitless Cartesian coordinates.                                                                                                                                                       |
| `ST_DWithin(geom, point, radius_m)` | **Filters** rows to those within `radius_m` metres of the search point. This is index-accelerated: PostGIS uses the GIST index to pre-filter with a bounding box before checking exact distance. This is the correct function for radius search — do not use `ST_Distance` in the `WHERE` clause. |
| `ST_Distance(geom, point)`          | **Measures** the exact geodesic distance in metres between each store and the search point. Used only for ranking (`ORDER BY`), not for filtering.                                                                                                                                                |
| `ST_AsGeoJSON(geom)`                | Serialises the stored `geography` point into a GeoJSON geometry string, which is then cast to `::json` so FastAPI embeds it as a nested object, not an escaped string.                                                                                                                            |

> **Critical gotcha — `(longitude, latitude)` argument order:** `ST_MakePoint` takes `(x, y)` = `(longitude, latitude)`. Swapping them is syntactically valid and produces wrong results silently. Always write `ST_MakePoint(lng, lat)`.

> **`radius_m` conversion:** The API accepts `radius_km` from the client. The Python layer converts to metres (`radius_km * 1000`) before passing `:radius_m` to the query. `ST_DWithin` on `geography` columns works in metres.

---

## 8. Module / Milestone Breakdown

### Module 0 — Environment Setup
**Goal:** PostGIS is running locally and you can execute one spatial query by hand.

**Tasks:**
1. Install PostgreSQL and the PostGIS extension.
2. Create the project database: `CREATE DATABASE geoinsight;`
3. Enable PostGIS: `CREATE EXTENSION postgis;`
4. Verify: `SELECT PostGIS_Version();` returns a version string.
5. Run the sanity-check distance query between Islamabad and Lahore (see project brief) and confirm it returns ~270,000 metres.
6. Create a Python virtualenv; install `fastapi`, `uvicorn`, `psycopg2-binary`, `python-dotenv`.

**Done when:** `SELECT PostGIS_Version();` succeeds AND the Islamabad–Lahore distance query returns a result you can explain in one sentence.

**Estimate:** ½ day.

---

### Module 1 — Data Ingestion (Raw CSV → PostGIS)
**Goal:** A real CSV of named places is loaded into a PostGIS table with a spatial index. This satisfies the "independently transform raw spatial data" requirement.

**Tasks:**
1. Obtain or create a CSV of ≥ 50 real places in Islamabad with `name,lat,lng` columns. Real coordinates are required.
2. Create the `stores` table (see §5.1 schema).
3. Create the GIST index on `geom`.
4. Write `ingest.py`: read the CSV, insert each row using `ST_MakePoint(lng, lat)::geography`.
5. Run the script. Verify row count. Spot-check 2–3 coordinates in a GIS viewer or by eyeballing the values.

**Done when:** `SELECT COUNT(*) FROM stores` equals the CSV row count AND `SELECT name, ST_AsText(geom) FROM stores LIMIT 3` shows plausible Islamabad coordinates.

**Estimate:** 1 day (including sourcing data).

---

### Module 2 — Spatial API
**Goal:** A FastAPI endpoint executes the PostGIS query and returns a valid GeoJSON `FeatureCollection`.

**Tasks:**
1. Scaffold FastAPI app with a database connection via `psycopg2`.
2. Implement `GET /stores/nearby` with query-param validation (FR-14).
3. Execute the core PostGIS query (§7).
4. Convert results to a `FeatureCollection` dict and return as JSON.
5. Test with `curl` or the FastAPI docs UI (`/docs`): confirm valid GeoJSON is returned, features are ordered nearest-first, and an out-of-range param returns 422.

**Done when:** `curl "http://localhost:8000/stores/nearby?lat=33.6844&lng=73.0479&radius_km=5"` returns a valid GeoJSON `FeatureCollection` with results ordered by `distance_m`.

**Estimate:** 1 day.

---

### Module 3 — Leaflet Frontend
**Goal:** A React app renders the map, calls the API, and displays ranked results with popups.

**Tasks:**
1. Scaffold a React app (`create-react-app` or Vite). Install `react-leaflet` and `leaflet`.
2. Render `<MapContainer>` centred on Islamabad with an OpenStreetMap tile layer.
3. Add a click handler: clicking the map sets the search-centre state to the clicked `LatLng`.
4. Add a "Use my location" button that calls `navigator.geolocation.getCurrentPosition`.
5. Add a radius slider (1–20 km, step 1).
6. On pin-set or slider-change, call `/stores/nearby`, parse the GeoJSON response, and render `<Marker>` components for each feature.
7. Render a `<Circle>` at the search centre with the selected radius.
8. Add `<Popup>` to each marker showing `name` and `(distance_m / 1000).toFixed(1) + " km away"`.
9. Visually distinguish the search-centre marker from store markers (different icon or colour).

**Done when:** The full interaction loop works: drop pin → move slider → markers update → circle redraws → popups show correct names and distances.

**Estimate:** 1–1.5 days.

---

### Module 4 — Polish & Deliverable
**Goal:** The repo is public, professional, and persuasive to a recruiter and interviewer in under 60 seconds.

**Tasks:**
1. Write `README.md`:
   - Lead with a screenshot of the running map (markers visible, radius circle drawn).
   - Include the full PostGIS SQL from §7, syntax-highlighted, in a code block.
   - Write a 3-sentence architecture summary: CSV → PostGIS (geography/4326) → spatial query (ST_DWithin + ST_Distance) → GeoJSON → Leaflet.
   - Include setup instructions (clone, create DB, run ingestion, start API, start frontend).
2. Record a 60-second Loom demo: load the map, drop a pin, move the slider, show markers appearing and popups opening.
3. Push the repo public. Confirm the Loom link is in the README.
4. Update CV: replace the placeholder with the real GitHub URL.

**Done when:** A stranger can open the GitHub repo, understand what it does from the README in 30 seconds, and watch the demo video.

**Estimate:** ½–1 day.

---

### Total Estimate

| Module    | Task                 | Estimate     |
| --------- | -------------------- | ------------ |
| 0         | Environment          | ½ day        |
| 1         | Data + Ingestion     | 1 day        |
| 2         | Spatial API          | 1 day        |
| 3         | Leaflet Frontend     | 1–1.5 days   |
| 4         | Polish + Deliverable | ½–1 day      |
| **Total** |                      | **4–5 days** |

> One day of buffer is available within the 6-day window for debugging. Do not use it for stretch features until all modules are done and the demo video is recorded.

---

## 9. Definition of Done

The project is complete when all of the following are true:

1. **Public GitHub repo** exists with a `README.md` that: (a) leads with at least one screenshot showing a Leaflet map with store markers and a search-radius circle; (b) contains the full PostGIS SQL query from §7 in a syntax-highlighted code block; (c) contains a 3-sentence architecture summary covering the ingestion pipeline, the spatial query, and the GeoJSON → Leaflet path; and (d) contains a working link to the Loom demo video.
2. **All 14 functional requirements** (FR-1 through FR-14) pass their stated acceptance tests.
3. **60-second Loom demo** is recorded, publicly accessible, and shows: the map loading, a pin being dropped, the radius slider being moved, markers updating in real time, and a popup opening with name + distance.
4. **The CV line** for GeoInsight links to the live public repo URL.

---

## 10. Interview-Defensibility Notes

These are the exact concepts an interviewer at a GIS-oriented role is likely to probe. One sentence each — say them out loud before the interview.

| Concept                                    | What to say if asked                                                                                                                                                                                                                                                                                                                           |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`geography` vs `geometry`**              | "`geometry` works in flat, unitless Cartesian space — fine for city-scale data in a projected CRS, but it breaks for distance across large areas. I used `geography` because it operates on a spherical model of the Earth and returns distances in real metres without me having to manually reproject the data."                             |
| **EPSG:4326 / CRS**                        | "EPSG:4326 is WGS84 — the coordinate reference system your phone's GPS uses. All my data is in 4326, which is the safe default for lat/lng from any standard source. Using the wrong CRS silently corrupts your distances."                                                                                                                    |
| **GIST index**                             | "Spatial data can't use a B-tree index because distance isn't a linear order. A GIST index works by storing bounding boxes in a tree, so `ST_DWithin` can eliminate most of the table with a bounding-box check before it does the expensive exact-distance calculation. Without it, every query scans every row."                             |
| **`ST_DWithin` vs `ST_Distance`**          | "`ST_DWithin` is the right function for radius filtering because it's index-aware — PostGIS can use the GIST index to skip rows cheaply before computing exact distance. `ST_Distance` computes the precise geodesic distance but doesn't benefit from the index in a `WHERE` clause. I use `ST_DWithin` to filter and `ST_Distance` to rank." |
| **`(longitude, latitude)` argument order** | "`ST_MakePoint` follows the mathematical `(x, y)` convention, which is `(longitude, latitude)` — the opposite of how most people say it. Getting this wrong produces points in the wrong hemisphere and is syntactically valid, so PostGIS won't warn you. I know to always write `ST_MakePoint(lng, lat)`."                                   |
| **`ST_AsGeoJSON`**                         | "Rather than building GeoJSON strings manually in Python, I let PostGIS serialise the geometry with `ST_AsGeoJSON`. This guarantees the output is spec-compliant and keeps all spatial logic inside the database where it belongs."                                                                                                            |
| **Why PostGIS, not JavaScript?**           | "JavaScript haversine calculations in the API layer require loading every candidate row from the database, doing math in Python, and then filtering. PostGIS filters in the database using a spatial index, so only the results cross the network. It's faster, architecturally cleaner, and it's what the role's JD specifically asked for."  |

---

*End of REQUIREMENTS.md — v1.0. Awaiting your review and approval before implementation planning begins.*