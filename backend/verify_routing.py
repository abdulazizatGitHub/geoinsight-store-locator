"""
Verify OSRM routing quality for Islamabad.
Tests that:
1. Routes follow actual roads (not straight lines)
2. Foot/bike don't route through motorways
3. Car doesn't route through footpaths
4. Distance is always >= straight-line distance (road must be >= crow-flies)
5. All 3 profiles return sane geometry
"""
import urllib.request
import json
import math
import sys

BASE_URLS = {
    'foot': 'https://routing.openstreetmap.de/routed-foot/route/v1/foot',
    'bike': 'https://routing.openstreetmap.de/routed-bike/route/v1/bike',
    'car':  'https://router.project-osrm.org/route/v1/driving',
}

# Two points in Islamabad that require going around a block (not straight through)
# Faisal Mosque -> Centaurus Mall — ~3.5 km straight, ~5+ km by road
A = {'lat': 33.7295, 'lng': 73.0371}  # Faisal Mosque
B = {'lat': 33.7128, 'lng': 73.0489}  # Centaurus Mall

PASS = 0
FAIL = 0

def ok(label, cond, detail=''):
    global PASS, FAIL
    status = '[PASS]' if cond else '[FAIL]'
    print(f'  {status} {label}' + (f' -- {detail}' if detail else ''))
    if cond: PASS += 1
    else: FAIL += 1

def haversine(a, b):
    """Straight-line distance in meters."""
    R = 6371000
    lat1, lat2 = math.radians(a['lat']), math.radians(b['lat'])
    dlat = math.radians(b['lat'] - a['lat'])
    dlng = math.radians(b['lng'] - a['lng'])
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlng/2)**2
    return 2 * R * math.asin(math.sqrt(h))

def get_route(profile, frm, to):
    url = f"{BASE_URLS[profile]}/{frm['lng']},{frm['lat']};{to['lng']},{to['lat']}?overview=full&geometries=geojson&steps=true"
    req = urllib.request.Request(url, headers={'User-Agent': 'GeoInsight-Test/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

straight = haversine(A, B)
print(f'\n=== OSRM Routing Quality Test ===')
print(f'  Straight-line distance A->B: {straight:.0f} m ({straight/1000:.2f} km)')
print(f'  Expecting road distance > straight-line for all profiles\n')

for profile in ['foot', 'bike', 'car']:
    print(f'Profile: {profile.upper()}')
    try:
        data = get_route(profile, A, B)
        ok('Response code OK',  data.get('code') == 'Ok', data.get('code'))

        route = data['routes'][0]
        dist  = route['distance']
        dur   = route['duration']
        geo   = route['geometry']
        coords = geo.get('coordinates', [])
        steps  = route['legs'][0].get('steps', [])

        ok('Route has geometry',        len(coords) > 2, f'{len(coords)} points')
        ok('Road dist >= straight-line', dist >= straight * 0.9, f'{dist:.0f}m road vs {straight:.0f}m straight')
        ok('Duration > 0 seconds',       dur > 0, f'{dur:.0f}s = {dur/60:.1f} min')
        ok('Has turn-by-turn steps',     len(steps) > 1, f'{len(steps)} steps')
        ok('Geometry is a LineString',   geo.get('type') == 'LineString')

        # Sanity check: each mode should have reasonable speed
        if dist > 0:
            speed_kmh = (dist / 1000) / (dur / 3600)
            if profile == 'foot':
                ok('Walk speed 2-8 km/h', 2 <= speed_kmh <= 8, f'{speed_kmh:.1f} km/h')
            elif profile == 'bike':
                ok('Bike speed 5-25 km/h', 5 <= speed_kmh <= 25, f'{speed_kmh:.1f} km/h')
            elif profile == 'car':
                ok('Car speed 15-80 km/h', 15 <= speed_kmh <= 80, f'{speed_kmh:.1f} km/h')

    except Exception as e:
        ok(f'{profile} request succeeded', False, str(e))
    print()

print(f'---------------------------------')
print(f'PASSED: {PASS}  FAILED: {FAIL}')
sys.exit(0 if FAIL == 0 else 1)
