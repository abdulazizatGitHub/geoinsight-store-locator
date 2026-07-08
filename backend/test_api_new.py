import urllib.request, json
url = 'http://127.0.0.1:8000/stores/nearby?lat=33.7295&lng=73.0371&radius_km=2&category=restaurant,cafe'
print(f'Fetching: {url}')
req = urllib.request.urlopen(url)
data = json.loads(req.read())
print(f'Features: {len(data["features"])}')
print(f'Hull included: {"Yes" if data.get("hull") else "No"}')
if data["features"]:
    prop = data["features"][0]["properties"]
    print(f'First Feature: {prop["name"]} | Cat: {prop["category"]} | Walk time: {prop["walk_time_min"]} mins')
