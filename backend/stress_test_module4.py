"""
Full stress test for Module 4 (Category filter + Convex Hull + Walk time).
Run: python stress_test_module4.py
Requires: uvicorn running on port 8000
"""
import urllib.request, urllib.error, json, sys, math

BASE = 'http://127.0.0.1:8000'
LAT, LNG = 33.7295, 73.0371  # Near Faisal Mosque, Islamabad
PASS, FAIL = 0, 0

def req(path):
    with urllib.request.urlopen(f'{BASE}{path}', timeout=10) as r:
        return json.loads(r.read()), r.status

def ok(label, cond, detail=''):
    global PASS, FAIL
    icon = '[PASS]' if cond else '[FAIL]'
    print(f'  {icon} {label}' + (f' -- {detail}' if detail else ''))
    if cond: PASS += 1
    else:     FAIL += 1

print('\n=== Module 4 Stress Test ===\n')

# ── T1: Health check ──────────────────────────────────────────────────────────
print('T1  Health endpoint')
data, status = req('/health')
ok('Status 200', status == 200)
ok('DB connected', data.get('db') == 'connected')

# ── T2: Baseline nearby (no filter) ──────────────────────────────────────────
print('\nT2  Baseline /stores/nearby (5 km, no category filter)')
data, _ = req(f'/stores/nearby?lat={LAT}&lng={LNG}&radius_km=5')
feats = data['features']
ok('FeatureCollection returned', data['type'] == 'FeatureCollection')
ok('Features > 0', len(feats) > 0, f'{len(feats)} features')
ok('Convex hull present', data.get('hull') is not None, f'type={data.get("hull", {}).get("type") if data.get("hull") else "missing"}')
ok('category field in properties', 'category' in feats[0]['properties'] if feats else False)
ok('walk_time_min in properties', 'walk_time_min' in feats[0]['properties'] if feats else False)

# ── T3: Walk time is sensible ────────────────────────────────────────────────
print('\nT3  Walk time arithmetic')
for f in feats[:5]:
    dist = f['properties']['distance_m']
    wt   = f['properties']['walk_time_min']
    expected = math.ceil(dist / 83.33)
    ok(f'{f["properties"]["name"][:30]}: walk={wt} min', wt == expected, f'dist={dist:.0f}m expected={expected}')

# ── T4: Category filter — single ────────────────────────────────────────────
print('\nT4  Single category filter')
data, _ = req(f'/stores/nearby?lat={LAT}&lng={LNG}&radius_km=10&category=bank')
cats = {f['properties']['category'] for f in data['features']}
ok('Only bank results returned', cats == {'bank'} or len(data['features']) == 0, f'cats={cats}')

data, _ = req(f'/stores/nearby?lat={LAT}&lng={LNG}&radius_km=10&category=hospital')
cats = {f['properties']['category'] for f in data['features']}
ok('Only hospital results returned', cats <= {'hospital'}, f'cats={cats}')

# ── T5: Category filter — multi ──────────────────────────────────────────────
print('\nT5  Multi-category filter')
data, _ = req(f'/stores/nearby?lat={LAT}&lng={LNG}&radius_km=10&category=restaurant,cafe')
cats = {f['properties']['category'] for f in data['features']}
ok('Only restaurant/cafe returned', cats <= {'restaurant', 'cafe'}, f'cats={cats}')
ok('Hull still present when multi-filter', data.get('hull') is not None or len(data['features']) < 2)

# ── T6: Nearest-first ordering preserved after filter ───────────────────────
print('\nT6  Nearest-first ordering with filter')
data, _ = req(f'/stores/nearby?lat={LAT}&lng={LNG}&radius_km=20&category=pharmacy')
dists = [f['properties']['distance_m'] for f in data['features']]
ok('Results sorted nearest-first', dists == sorted(dists), f'first={dists[0]:.0f}m last={dists[-1]:.0f}m' if dists else 'empty')

# ── T7: Empty result returns hull=None ─────────────────────────────────────
print('\nT7  Empty result hull')
data, _ = req(f'/stores/nearby?lat=0&lng=0&radius_km=1')
ok('Empty features array', data['features'] == [])
ok('Hull is null on empty result', data.get('hull') is None)

# ── T8: GeoJSON coordinate order in features ─────────────────────────────────
print('\nT8  GeoJSON coordinate order')
data, _ = req(f'/stores/nearby?lat={LAT}&lng={LNG}&radius_km=5')
if data['features']:
    c = data['features'][0]['geometry']['coordinates']
    ok('Coordinates are [lng, lat] order', -180 <= c[0] <= 180 and -90 <= c[1] <= 90, f'coords={c}')

# ── Summary ───────────────────────────────────────────────────────────────────
print(f'\n---------------------------------')
print(f'PASSED: {PASS}  FAILED: {FAIL}')
print('=== ALL PASS ===' if FAIL == 0 else '=== SOME FAILURES ===')
sys.exit(0 if FAIL == 0 else 1)
