import { useState, useEffect, useCallback, useRef } from 'react'
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Circle,
  GeoJSON,
  useMapEvents,
} from 'react-leaflet'
import L from 'leaflet'

// ── Fix Vite + Leaflet default icon path breakage ─────────────────────────
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: new URL('leaflet/dist/images/marker-icon-2x.png', import.meta.url).href,
  iconUrl:       new URL('leaflet/dist/images/marker-icon.png',    import.meta.url).href,
  shadowUrl:     new URL('leaflet/dist/images/marker-shadow.png',  import.meta.url).href,
})

// ── Icons ──────────────────────────────────────────────────────────────────
const searchPinIcon = L.divIcon({
  className: '',
  html: `<div style="width:20px;height:20px;background:#4f8ef7;border:3px solid #fff;border-radius:50% 50% 50% 0;transform:rotate(-45deg);box-shadow:0 2px 8px rgba(0,0,0,0.5)"></div>`,
  iconSize: [20, 20], iconAnchor: [10, 18], popupAnchor: [0, -20],
})

const getStoreIcon = (category) => L.divIcon({
  className: '',
  html: `<div class="marker-${category}" style="width:14px;height:14px;border:2px solid #fff;border-radius:50%;box-shadow:0 1px 4px rgba(0,0,0,0.4)"></div>`,
  iconSize: [14, 14], iconAnchor: [7, 7], popupAnchor: [0, -10],
})

// ── Constants ──────────────────────────────────────────────────────────────
const ISLAMABAD    = { lat: 33.6844, lng: 73.0479 }
const DEFAULT_ZOOM = 12

const ALL_CATEGORIES = ['pharmacy','hospital','restaurant','cafe','bank','mosque','supermarket','school','fuel']
const CAT_EMOJIS     = { pharmacy:'💊', hospital:'🏥', restaurant:'🍽️', cafe:'☕', bank:'🏦', mosque:'🕌', supermarket:'🛒', school:'🎓', fuel:'⛽', other:'📍' }

// OSRM profiles — free, no API key
const TRAVEL_MODES = [
  { id: 'foot',   label: 'Walk',  emoji: '🚶', color: '#22c55e', speed: 5,   osrm: 'https://routing.openstreetmap.de/routed-foot/route/v1/foot'  },
  { id: 'bike',   label: 'Bike',  emoji: '🚲', color: '#f59e0b', speed: 15,  osrm: 'https://routing.openstreetmap.de/routed-bike/route/v1/bike'  },
  { id: 'car',    label: 'Car',   emoji: '🚗', color: '#4f8ef7', speed: 40,  osrm: 'https://router.project-osrm.org/route/v1/driving'            },
]

// ── Map click handler ──────────────────────────────────────────────────────
function MapClickHandler({ onMapClick }) {
  useMapEvents({ click(e) { onMapClick(e.latlng) } })
  return null
}

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

// ── Utility ────────────────────────────────────────────────────────────────
const fmtDist = (m) => m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(1)} km`
const fmtTime = (seconds) => {
  const mins = Math.round(seconds / 60)
  if (mins < 60) return `${mins} min`
  return `${Math.floor(mins / 60)}h ${mins % 60}m`
}

const CATEGORY_COLORS = {
  pharmacy: '#10b981', hospital: '#ef4444', restaurant: '#f59e0b', cafe: '#d97706',
  bank: '#3b82f6', mosque: '#8b5cf6', supermarket: '#ec4899', school: '#14b8a6', fuel: '#f43f5e', other: '#94a3b8'
}

// ── App ────────────────────────────────────────────────────────────────────
export default function App() {
  const [searchCenter, setSearchCenter] = useState(null)
  const [radiusKm, setRadiusKm]         = useState(3)
  const [stores, setStores]             = useState([])
  const [hull, setHull]                 = useState(null)
  const [activeCats, setActiveCats]     = useState([])
  const [loading, setLoading]           = useState(false)
  const [routeLoading, setRouteLoading] = useState(false)
  const [error, setError]               = useState(null)
  const [geoStatus, setGeoStatus]       = useState(null)

  // Route state
  const [selectedStore, setSelectedStore] = useState(null)  // feature
  const [travelMode, setTravelMode]       = useState('foot')
  const [routeGeo, setRouteGeo]           = useState(null)  // GeoJSON LineString
  const [routeInfo, setRouteInfo]         = useState(null)  // { distance_m, duration_s }

  const mapRef = useRef(null)

  // ── Fetch stores ──────────────────────────────────────────────────────────
  const fetchStores = useCallback(async (center, radius, categories) => {
    if (!center) return
    setLoading(true)
    setError(null)
    // Clear route when search changes
    setRouteGeo(null)
    setRouteInfo(null)
    setSelectedStore(null)
    try {
      let url = `/stores/nearby?lat=${center.lat}&lng=${center.lng}&radius_km=${radius}`
      if (categories.length > 0) url += `&category=${categories.join(',')}`
      const res = await fetch(url)
      if (!res.ok) throw new Error((await res.json()).detail || `HTTP ${res.status}`)
      const data = await res.json()
      setStores(data.features || [])
      setHull(data.hull || null)
    } catch (err) {
      setError(err.message)
      setStores([])
      setHull(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (searchCenter) fetchStores(searchCenter, radiusKm, activeCats)
  }, [searchCenter, radiusKm, activeCats, fetchStores])

  // ── Fetch route from OSRM ─────────────────────────────────────────────────
  const fetchRoute = useCallback(async (store, mode) => {
    if (!searchCenter || !store) return
    setRouteLoading(true)
    setRouteGeo(null)
    setRouteInfo(null)

    const modeConf  = TRAVEL_MODES.find(m => m.id === mode)
    const [lng2, lat2] = store.geometry.coordinates
    const coords = `${searchCenter.lng},${searchCenter.lat};${lng2},${lat2}`
    const url    = `${modeConf.osrm}/${coords}?overview=full&geometries=geojson`

    try {
      const res = await fetch(url)
      if (!res.ok) throw new Error(`Routing HTTP ${res.status}`)
      const data = await res.json()
      if (data.code !== 'Ok' || !data.routes?.[0]) throw new Error('No route found')
      const route = data.routes[0]
      setRouteGeo(route.geometry)
      setRouteInfo({ distance_m: route.distance, duration_s: route.duration })

      // Pan map to fit the route
      if (mapRef.current && route.geometry?.coordinates?.length > 0) {
        const coords = route.geometry.coordinates.map(([lng, lat]) => [lat, lng])
        mapRef.current.fitBounds(coords, { padding: [40, 40] })
      }
    } catch (err) {
      setError(`Routing: ${err.message}`)
    } finally {
      setRouteLoading(false)
    }
  }, [searchCenter])

  // Re-fetch route when travel mode changes (if a store is already selected)
  useEffect(() => {
    if (selectedStore) fetchRoute(selectedStore, travelMode)
  }, [travelMode]) // eslint-disable-line

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleMapClick = useCallback((latlng) => {
    setSearchCenter({ lat: latlng.lat, lng: latlng.lng })
    setGeoStatus(null)
    setSelectedStore(null)
    setRouteGeo(null)
    setRouteInfo(null)
  }, [])

  const handleSelectStore = useCallback((feat) => {
    setSelectedStore(feat)
    fetchRoute(feat, travelMode)
    // Pan to store
    const [lng, lat] = feat.geometry.coordinates
    if (mapRef.current) mapRef.current.flyTo([lat, lng], 15, { duration: 0.8 })
  }, [fetchRoute, travelMode])

  const handleUseMyLocation = useCallback(() => {
    if (!navigator.geolocation) { setGeoStatus({ type: 'error', msg: 'Geolocation not supported.' }); return }
    setGeoStatus({ type: 'info', msg: 'Requesting location...' })
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const center = { lat: pos.coords.latitude, lng: pos.coords.longitude }
        setSearchCenter(center)
        setGeoStatus({ type: 'success', msg: 'Location set from GPS.' })
        if (mapRef.current) mapRef.current.flyTo([center.lat, center.lng], 14, { duration: 1.2 })
      },
      (err) => {
        const msgs = { 1: 'Permission denied.', 2: 'Unavailable.', 3: 'Timed out.' }
        setGeoStatus({ type: 'error', msg: msgs[err.code] || 'Location error.' })
      },
      { timeout: 8000 }
    )
  }, [])

  const handleClear = useCallback(() => {
    setSearchCenter(null); setStores([]); setHull(null); setError(null)
    setGeoStatus(null); setSelectedStore(null); setRouteGeo(null); setRouteInfo(null)
  }, [])

  const toggleCategory = useCallback((cat) => {
    setActiveCats(prev => prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat])
  }, [])

  // ── Derived values ────────────────────────────────────────────────────────
  const nearestStore   = stores[0] ?? null
  const avgWalk        = stores.length > 0 ? Math.round(stores.reduce((a, s) => a + s.properties.walk_time_min, 0) / stores.length) : 0
  const activeMode     = TRAVEL_MODES.find(m => m.id === travelMode)
  const routeLineStyle = { color: activeMode?.color ?? '#4f8ef7', weight: 5, opacity: 0.85 }

  // Chart data
  const chartData = ALL_CATEGORIES.map(cat => ({
    name: cat,
    count: stores.filter(s => s.properties.category === cat).length
  })).filter(d => d.count > 0).sort((a, b) => b.count - a.count)

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="app-wrapper">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>Geo<span>Insight</span></h1>
          <p>PostGIS · OSRM Real-Time Routing</p>
        </div>

        {/* Controls */}
        <div className="controls">
          <div className="control-group">
            <span className="control-label">Search Radius</span>
            <div className="radius-row">
              <input type="range" min={1} max={20} step={1} value={radiusKm}
                onChange={e => setRadiusKm(Number(e.target.value))} />
              <span className="radius-badge">{radiusKm} km</span>
            </div>
          </div>
          <div className="control-group" style={{ flexDirection: 'row', gap: '8px' }}>
            <button className="btn btn-primary" onClick={handleUseMyLocation} disabled={loading}>📍 GPS</button>
            <button className="btn btn-secondary" onClick={handleClear} disabled={!searchCenter}>✕ Clear</button>
          </div>
          {geoStatus && <div className={`status-msg status-${geoStatus.type}`}>{geoStatus.msg}</div>}
          {error     && <div className="status-msg status-error">⚠ {error}</div>}
          {!searchCenter && !geoStatus && <div className="status-msg status-info">Click the map to drop a pin</div>}
        </div>

        {/* Category pills */}
        <div className="results-header" style={{ paddingBottom: '8px' }}>
          <span className="results-title">Filter by Category</span>
          {activeCats.length > 0 && (
            <button className="filter-pill active" style={{ fontSize: '0.6rem' }}
              onClick={() => setActiveCats([])}>Clear</button>
          )}
        </div>
        <div className="filters-container">
          {ALL_CATEGORIES.map(cat => (
            <button key={cat} className={`filter-pill ${activeCats.includes(cat) ? 'active' : ''}`}
              onClick={() => toggleCategory(cat)}>
              {CAT_EMOJIS[cat]} {cat}
            </button>
          ))}
        </div>

        {/* Live stats */}
        {searchCenter && (
          <div className="stats-panel">
            <div className="stat-card">
              <span className="stat-label">Found</span>
              <span className="stat-value">{stores.length}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Nearest</span>
              <span className="stat-value">{nearestStore ? fmtDist(nearestStore.properties.distance_m) : '—'}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Avg Walk</span>
              <span className="stat-value">{avgWalk ? `${avgWalk} min` : '—'}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Hull</span>
              <span className="stat-value">{hull ? 'Computed' : 'N/A'}</span>
            </div>
          </div>
        )}

        {/* Analytics Chart */}
        {searchCenter && chartData.length > 0 && (
          <div className="chart-container">
            <div className="route-title" style={{ marginBottom: '8px' }}>Category Distribution</div>
            <ResponsiveContainer width="100%" height={120}>
              <BarChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickLine={false} axisLine={false} />
                <Tooltip
                  cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                  contentStyle={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '12px' }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={CATEGORY_COLORS[entry.name] || '#94a3b8'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Route panel — shown when a store is selected */}
        {selectedStore && (
          <div className="route-panel">
            <div className="route-title">
              <span>Directions to</span>
              <button className="route-close" onClick={() => { setSelectedStore(null); setRouteGeo(null); setRouteInfo(null) }}>✕</button>
            </div>
            <div className="route-dest">{selectedStore.properties.name}</div>

            {/* Travel mode toggle */}
            <div className="mode-toggle">
              {TRAVEL_MODES.map(m => (
                <button key={m.id}
                  className={`mode-btn ${travelMode === m.id ? 'active' : ''}`}
                  style={travelMode === m.id ? { background: m.color, borderColor: m.color } : {}}
                  onClick={() => setTravelMode(m.id)}>
                  {m.emoji} {m.label}
                </button>
              ))}
            </div>

            {/* Route result */}
            {routeLoading && <div className="status-msg status-info">Calculating route…</div>}
            {routeInfo && !routeLoading && (
              <div className="route-result">
                <div className="route-stat">
                  <span className="stat-label">Road Distance</span>
                  <span className="route-val" style={{ color: activeMode.color }}>{fmtDist(routeInfo.distance_m)}</span>
                </div>
                <div className="route-stat">
                  <span className="stat-label">Travel Time</span>
                  <span className="route-val" style={{ color: activeMode.color }}>{fmtTime(routeInfo.duration_s)}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Results list */}
        <div className="results-header">
          <span className="results-title">Nearby Stores</span>
        </div>
        <div className="results-list">
          {!searchCenter ? (
            <div className="empty-state"><div className="icon">🗺️</div><p>Drop a pin to explore.</p></div>
          ) : stores.length === 0 && !loading ? (
            <div className="empty-state"><div className="icon">🔍</div><p>No stores found.<br/>Adjust filters or radius.</p></div>
          ) : (
            stores.map((feat, i) => {
              const { name, distance_m, category, walk_time_min } = feat.properties
              const isActive = selectedStore?.properties?.id === feat.properties.id
              return (
                <div key={feat.properties.id}
                  className={`result-item ${isActive ? 'result-active' : ''}`}
                  onClick={() => handleSelectStore(feat)}>
                  <span className="result-rank">{i + 1}</span>
                  <div className={`result-dot marker-${category}`} />
                  <div style={{ flex: 1 }}>
                    <div className="result-name">{name}</div>
                    <div className="result-cat">{CAT_EMOJIS[category] || '📍'} {category} · {walk_time_min} min walk</div>
                  </div>
                  <span className="result-dist">{fmtDist(distance_m)}</span>
                </div>
              )
            })
          )}
        </div>
      </aside>

      {/* ── Map ── */}
      <div className="map-container">
        {(loading || routeLoading) && (
          <div className="map-loading">
            <div className="spinner" />
            {routeLoading ? 'Calculating route…' : 'Searching…'}
          </div>
        )}

        <MapContainer center={[ISLAMABAD.lat, ISLAMABAD.lng]} zoom={DEFAULT_ZOOM}
          style={{ height: '100%', width: '100%' }} ref={mapRef}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapClickHandler onMapClick={handleMapClick} />

          {/* Search centre */}
          {searchCenter && (
            <Marker position={[searchCenter.lat, searchCenter.lng]} icon={searchPinIcon}>
              <Popup><div className="popup-name">📍 Search Origin</div></Popup>
            </Marker>
          )}

          {/* Radius ring */}
          {searchCenter && !selectedStore && (
            <Circle center={[searchCenter.lat, searchCenter.lng]} radius={radiusKm * 1000}
              pathOptions={{ color:'#4f8ef7', fillColor:'#4f8ef7', fillOpacity:0.05, weight:1.5, dashArray:'6 4' }} />
          )}

          {/* Convex hull */}
          {hull && !selectedStore && (
            <GeoJSON key={JSON.stringify(hull)} data={hull}
              style={{ color:'#f59e0b', weight:2, fillOpacity:0.08, dashArray:'8 4' }} />
          )}

          {/* Route line */}
          {routeGeo && (
            <GeoJSON key={JSON.stringify(routeGeo)} data={routeGeo} style={routeLineStyle} />
          )}

          {/* Store markers */}
          {stores.map((feat) => {
            const [lng, lat] = feat.geometry.coordinates
            const { id, name, distance_m, category, walk_time_min } = feat.properties
            return (
              <Marker key={id} position={[lat, lng]} icon={getStoreIcon(category)}
                eventHandlers={{ click: () => handleSelectStore(feat) }}>
                <Popup>
                  <div className="popup-name">{CAT_EMOJIS[category] || '📍'} {name}</div>
                  <div className="popup-dist" style={{ color:'var(--text-muted)', fontSize:'0.7rem', textTransform:'uppercase' }}>{category}</div>
                  <div className="popup-dist" style={{ marginTop:'6px' }}>📏 {fmtDist(distance_m)} · 🚶 {walk_time_min} min</div>
                  <button className="btn btn-primary" style={{ marginTop:'8px', padding:'6px 10px', fontSize:'0.75rem' }}
                    onClick={() => handleSelectStore(feat)}>
                    Get Directions
                  </button>
                </Popup>
              </Marker>
            )
          })}
        </MapContainer>
      </div>
    </div>
  )
}
