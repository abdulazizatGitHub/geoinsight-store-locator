# Deployment Guide — GeoInsight Store Locator

Free deployment using **Neon** (database) + **Render** (backend) + **Vercel** (frontend).
No credit card required for any of these services.

---

## Architecture in Production

```
Browser
  │
  ├─► Vercel CDN          (React static bundle)
  │     │
  │     └─► Render         (FastAPI — /stores/nearby, /health)
  │               │
  │               └─► Neon.tech  (PostgreSQL 16 + PostGIS)
  │
  └─► OSRM servers        (routing — no auth, called from browser)
```

---

## Step 1 — Neon Database (PostGIS)

1. Go to [neon.tech](https://neon.tech) → **Sign up free**
2. Create a new project → name it `geoinsight`
3. In **SQL Editor**, run:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS stores (
    id       SERIAL PRIMARY KEY,
    name     TEXT NOT NULL,
    geom     geography(Point, 4326) NOT NULL,
    category TEXT NOT NULL DEFAULT 'other'
);

CREATE INDEX IF NOT EXISTS stores_geom_idx ON stores USING GIST(geom);
```

4. Copy the **Connection String** from the Neon dashboard:
   ```
   postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/geoinsight?sslmode=require
   ```

5. Ingest data from your local machine pointing at Neon:
   ```bash
   cd backend
   # Temporarily set DATABASE_URL to the Neon connection string
   $env:DATABASE_URL="postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/geoinsight?sslmode=require"
   python ingest.py --truncate
   ```

---

## Step 2 — Render Backend

### 2a — Create a Web Service

1. Go to [render.com](https://render.com) → Sign up with GitHub
2. **New → Web Service**
3. Connect your GitHub repo
4. Configure:

| Setting | Value |
|---|---|
| Root Directory | `backend` |
| Runtime | `Python 3.12` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | `Free` |

### 2b — Environment Variables

In Render → your service → **Environment**, add:

| Key | Value |
|---|---|
| `DATABASE_URL` | Neon connection string (with `?sslmode=require`) |
| `PYTHON_VERSION` | `3.12.0` |

### 2c — CORS Update

Before deploying, update `main.py` to allow your Vercel domain:

```python
# In backend/main.py — replace the existing CORSMiddleware block
ALLOWED_ORIGINS = [
    "http://localhost:5173",               # local dev
    "https://your-app.vercel.app",        # production — update this
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)
```

> You can use `allow_origins=["*"]` for a portfolio demo — just don't do this for production apps that handle sensitive data.

### 2d — Note on Free Tier Sleep

Render's free tier **spins down after 15 minutes of inactivity**. First request after sleep takes ~30 seconds.

To keep it warm for a demo:
- Use [UptimeRobot](https://uptimerobot.com) (free) to ping `https://your-backend.onrender.com/health` every 14 minutes.

---

## Step 3 — Vercel Frontend

### 3a — Update API URL for Production

In `frontend/vite.config.js`, the proxy only works in development. For production, the frontend needs to call the Render backend directly.

Create `frontend/.env.production`:
```
VITE_API_BASE=https://your-backend.onrender.com
```

Create `frontend/.env.development`:
```
VITE_API_BASE=
```
_(empty = use Vite proxy to localhost:8000)_

Update `frontend/src/App.jsx` — change the fetch URL:
```javascript
// Replace:
const url = `/stores/nearby?lat=...`

// With:
const BASE = import.meta.env.VITE_API_BASE || ''
const url = `${BASE}/stores/nearby?lat=...`
```

### 3b — Deploy to Vercel

1. Go to [vercel.com](https://vercel.com) → Sign up with GitHub
2. **New Project** → Import your repo
3. Configure:

| Setting | Value |
|---|---|
| Framework Preset | `Vite` |
| Root Directory | `frontend` |
| Build Command | `npm run build` |
| Output Directory | `dist` |

4. Add environment variable:
   - `VITE_API_BASE` = `https://your-backend.onrender.com`

5. Deploy — Vercel gives you a URL like `https://geoinsight.vercel.app`

### 3c — Update Render CORS

Go back to Render → add your Vercel URL to `ALLOWED_ORIGINS` in `main.py` and redeploy.

---

## Step 4 — Verify Deployment

```bash
# Health check
curl https://your-backend.onrender.com/health
# Expected: {"status":"ok","db":"connected"}

# Spatial query
curl "https://your-backend.onrender.com/stores/nearby?lat=33.7295&lng=73.0371&radius_km=2"
# Expected: GeoJSON FeatureCollection with features array
```

---

## Alternative: Railway (All-in-One)

Railway is simpler — deploys all three services from one dashboard with automatic GitHub CI/CD.

1. [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Add a **PostgreSQL** plugin → run PostGIS setup SQL
3. Add a **Python** service for the backend
4. Add a **Static Site** service for the frontend
5. Railway automatically sets `DATABASE_URL` as an environment variable

Free tier: **$5/month credit** — enough for a portfolio project with low traffic.

---

## CI/CD — GitHub Actions

See [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for the automated pipeline that runs on every push:

- ✅ Python dependency install
- ✅ Backend stress tests (mocked DB)  
- ✅ Frontend production build (catches bundle errors)
- ✅ OSRM routing quality check

Render and Vercel both offer **automatic deploys on `git push`** — just connect your GitHub repo in their dashboards.

---

## Environment Variables Reference

| Variable | Where Used | Description |
|---|---|---|
| `DATABASE_URL` | Backend `.env` + Render | Full PostgreSQL connection string |
| `VITE_API_BASE` | Frontend `.env.production` | Backend URL (empty in dev — uses Vite proxy) |

---

## Security Checklist for Production

- [ ] `.env` is in `.gitignore` ✅
- [ ] No secrets in frontend code (VITE_ vars are public by design — never put DB credentials there)
- [ ] CORS restricted to your actual frontend domain
- [ ] Parameterised SQL everywhere (no f-string queries) ✅
- [ ] Input validation via FastAPI Query constraints ✅
- [ ] HTTPS enforced by Render/Vercel automatically ✅
- [ ] Database credentials only in environment variables, never in source code ✅
