"""
fetch_overpass.py — Fetch real Islamabad POIs from OpenStreetMap Overpass API.
Saves to data/stores.csv with columns: name,lat,lng,category

Run: python fetch_overpass.py
     python fetch_overpass.py --dry-run   (print count only, no file write)

If the network request fails, the script exits with a clear error message
and fallback instructions.
"""

import csv
import json
import os
import sys
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error

OUTPUT_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'stores.csv')

# Islamabad bounding box: south, west, north, east
BBOX = '33.55,72.80,33.80,73.20'

# Single combined Overpass query — one HTTP request, no rate limiting
COMBINED_QUERY = """
[out:json][timeout:300];
(
  nwr["amenity"="pharmacy"]({bbox});
  nwr["amenity"="hospital"]({bbox});
  nwr["amenity"="clinic"]({bbox});
  nwr["amenity"="restaurant"]({bbox});
  nwr["amenity"="cafe"]({bbox});
  nwr["amenity"="fast_food"]({bbox});
  nwr["amenity"="bank"]({bbox});
  nwr["amenity"="place_of_worship"]["religion"="muslim"]({bbox});
  nwr["shop"="supermarket"]({bbox});
  nwr["shop"="mall"]({bbox});
  nwr["amenity"="school"]({bbox});
  nwr["amenity"="fuel"]({bbox});
);
out center;
"""

OVERPASS_URL = 'https://overpass-api.de/api/interpreter'
MIN_NAME_LEN = 2


def tag_to_category(tags: dict) -> str:
    """Derive our category label from OSM tags."""
    amenity = tags.get('amenity', '')
    shop    = tags.get('shop', '')
    religion = tags.get('religion', '')

    if amenity in ('pharmacy',):                         return 'pharmacy'
    if amenity in ('hospital', 'clinic'):                return 'hospital'
    if amenity in ('restaurant', 'fast_food'):           return 'restaurant'
    if amenity == 'cafe':                                return 'cafe'
    if amenity == 'bank':                                return 'bank'
    if amenity == 'place_of_worship' and religion == 'muslim': return 'mosque'
    if amenity == 'school':                              return 'school'
    if amenity == 'fuel':                                return 'fuel'
    if shop in ('supermarket', 'mall'):                  return 'supermarket'
    return 'other'


def query_overpass(overpass_query: str) -> list[dict]:
    """POST a single query to the Overpass API."""
    data = urllib.parse.urlencode({'data': overpass_query}).encode()
    req = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={'User-Agent': 'GeoInsight-StoreLocator/1.0 (educational project)'},
    )
    with urllib.request.urlopen(req, timeout=320) as resp:
        body = json.loads(resp.read())
    return body.get('elements', [])


def clean_name(tags: dict) -> str | None:
    name = tags.get('name') or tags.get('name:en') or tags.get('brand')
    if not name or len(name.strip()) < MIN_NAME_LEN:
        return None
    return name.strip()


def fetch_all() -> list[dict]:
    """Fetch all categories in ONE Overpass request."""
    query = COMBINED_QUERY.format(bbox=BBOX)
    print('  Sending combined Overpass query (one request, all categories)...')

    try:
        elements = query_overpass(query)
    except urllib.error.URLError as e:
        print(f'NETWORK ERROR: {e}')
        raise
    except Exception as e:
        print(f'ERROR: {e}')
        raise

    print(f'  Raw elements returned: {len(elements)}')

    records = []
    seen_ids = set()

    for el in elements:
        osm_id = el.get('id')
        if osm_id in seen_ids:
            continue
        tags = el.get('tags', {})
        name = clean_name(tags)
        if not name:
            continue
            
        # Coordinates can be directly on nodes, or in 'center' for ways/relations
        if el.get('type') == 'node':
            lat = el.get('lat')
            lng = el.get('lon')
        else:
            center = el.get('center', {})
            lat = center.get('lat')
            lng = center.get('lon')
            
        if lat is None or lng is None:
            continue
            
        category = tag_to_category(tags)
        records.append({'name': name, 'lat': lat, 'lng': lng, 'category': category})
        seen_ids.add(osm_id)

    return records


def write_csv(records: list[dict], path: str) -> None:
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'lat', 'lng', 'category'])
        writer.writeheader()
        writer.writerows(records)
    print(f'\nWritten: {path}')


def run(dry_run: bool = False) -> None:
    print('Querying Overpass API — 1 combined request for all categories...')
    print(f'Bounding box: {BBOX}\n')

    try:
        records = fetch_all()
    except Exception as e:
        print(f'\nFailed to fetch data: {e}')
        print('\nFallback: run  python ingest.py  with the existing test CSV')
        print('         or retry once network is available.')
        sys.exit(1)

    print(f'\nTotal records fetched: {len(records)}')

    # Summary by category
    from collections import Counter
    counts = Counter(r['category'] for r in records)
    for cat, count in sorted(counts.items()):
        print(f'  {cat:12s}: {count}')

    if dry_run:
        print('\n[dry-run] No file written.')
        return

    if len(records) < 10:
        print('\nWARN: Very few records returned. Check bounding box or API status.')

    write_csv(records, OUTPUT_CSV)
    print(f'=== Overpass fetch COMPLETE: {len(records)} real locations ===')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    run(dry_run=args.dry_run)
