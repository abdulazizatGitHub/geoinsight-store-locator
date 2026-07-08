"""
stress_test_api.py — Module 2 full stress test suite.
Run with: python stress_test_api.py
Server must be running at http://127.0.0.1:8000
"""

import urllib.request
import json
import sys

BASE = 'http://127.0.0.1:8000'
passed = 0
failed = 0


def check(label, url, expect_status, extra=None):
    global passed, failed
    try:
        req = urllib.request.urlopen(url, timeout=5)
        status = req.status
        body = json.loads(req.read())
    except urllib.error.HTTPError as e:
        status = e.code
        body = json.loads(e.read())
    except Exception as e:
        print(f'  FAIL [{label}]: {e}')
        failed += 1
        return None

    ok = (status == expect_status)
    if extra:
        ok = ok and extra(body)

    symbol = 'PASS' if ok else 'FAIL'
    if ok:
        passed += 1
    else:
        failed += 1
    print(f'  {symbol} [{label}] HTTP {status} (expected {expect_status})')
    return body


print('=== Module 2 Stress Tests ===\n')

# ── Test 1: Health endpoint ───────────────────────────────────────────────────
print('[1] Health endpoint')
check('GET /health', f'{BASE}/health', 200,
      lambda b: b.get('status') == 'ok')

# ── Test 2: Valid nearby query ────────────────────────────────────────────────
print('\n[2] Valid nearby query (Faisal Mosque, 2km)')
url = f'{BASE}/stores/nearby?lat=33.7295&lng=73.0371&radius_km=2'
body = check('GET /stores/nearby valid', url, 200,
             lambda b: b.get('type') == 'FeatureCollection')

if body and body.get('features'):
    feats = body['features']
    dists = [f['properties']['distance_m'] for f in feats]
    monotonic = all(dists[i] <= dists[i + 1] for i in range(len(dists) - 1))

    first_name = feats[0]['properties']['name']
    first_dist = feats[0]['properties']['distance_m']
    last_name  = feats[-1]['properties']['name']
    last_dist  = feats[-1]['properties']['distance_m']
    geom       = feats[0]['geometry']
    coords     = geom.get('coordinates', [])

    print(f'       Features returned : {len(feats)}')
    print(f'       First             : {first_name} @ {first_dist}m')
    print(f'       Last              : {last_name} @ {last_dist}m')
    print(f'       Ordered nearest-first : {"PASS" if monotonic else "FAIL - NOT MONOTONIC"}')
    print(f'       geometry is dict  : {"PASS" if isinstance(geom, dict) else "FAIL - got " + type(geom).__name__}')
    print(f'       geometry.type     : {geom.get("type")} (must be Point)')
    print(f'       coordinates       : {coords} (lng~73, lat~33)')

# ── Test 3: Empty result set ──────────────────────────────────────────────────
print('\n[3] Valid query with no results (ocean, 0,0)')
url2 = f'{BASE}/stores/nearby?lat=0.0&lng=0.0&radius_km=1'
body2 = check('empty result set', url2, 200,
              lambda b: b.get('type') == 'FeatureCollection' and b.get('features') == [])
if body2 is not None:
    print(f'       features=[]       : {"PASS" if body2["features"] == [] else "FAIL"}')

# ── Test 4: Missing parameter → 422 ──────────────────────────────────────────
print('\n[4] Missing lat -> 422')
check('missing lat', f'{BASE}/stores/nearby?lng=73.0&radius_km=5', 422)

# ── Test 5: lat out of range → 422 ───────────────────────────────────────────
print('\n[5] lat=999 -> 422')
check('lat out of range', f'{BASE}/stores/nearby?lat=999&lng=73.0&radius_km=5', 422)

# ── Test 6: radius_km = 0 → 422 ──────────────────────────────────────────────
print('\n[6] radius_km=0 -> 422')
check('radius zero', f'{BASE}/stores/nearby?lat=33.7&lng=73.0&radius_km=0', 422)

# ── Test 7: radius_km > 100 → 422 ────────────────────────────────────────────
print('\n[7] radius_km=101 -> 422')
check('radius over max', f'{BASE}/stores/nearby?lat=33.7&lng=73.0&radius_km=101', 422)

# ── Test 8: Large radius → many results ──────────────────────────────────────
print('\n[8] Large radius 20km - expect all 79 rows')
body3 = check('large radius', f'{BASE}/stores/nearby?lat=33.7&lng=73.0&radius_km=20', 200)
if body3:
    count = len(body3['features'])
    print(f'       Features returned : {count} (expected ~79)')

# ── Test 9: GeoJSON coordinates are [lng, lat] order ─────────────────────────
print('\n[9] GeoJSON coordinate order [lng, lat]')
url9 = f'{BASE}/stores/nearby?lat=33.7295&lng=73.0371&radius_km=0.1'
body9 = check('coord order check', url9, 200)
if body9 and body9.get('features'):
    feat = body9['features'][0]
    coords = feat['geometry']['coordinates']
    lng_ok = 72.0 < coords[0] < 74.0   # longitude first
    lat_ok = 33.0 < coords[1] < 34.0   # latitude second
    print(f'       coords[0] (lng) = {coords[0]:.4f} in [72,74]: {"PASS" if lng_ok else "FAIL"}')
    print(f'       coords[1] (lat) = {coords[1]:.4f} in [33,34]: {"PASS" if lat_ok else "FAIL"}')

# ── Summary ───────────────────────────────────────────────────────────────────
print(f'\n=== Results: {passed} passed, {failed} failed ===')
if failed > 0:
    sys.exit(1)
else:
    print('=== Module 2 COMPLETE: All tests PASSED ===')
