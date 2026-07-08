import csv, sys

path = '../data/stores.csv'
errors = []
rows = []

with open(path, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader, start=1):
        name = row.get('name', '').strip()
        if not name:
            errors.append(f'Row {i}: empty name')
        try:
            lat = float(row['lat'])
            lng = float(row['lng'])
            if not (-90 <= lat <= 90):
                errors.append(f'Row {i}: lat out of range: {lat}')
            if not (-180 <= lng <= 180):
                errors.append(f'Row {i}: lng out of range: {lng}')
            # Rough Islamabad bounding box
            if not (33.55 <= lat <= 33.80):
                errors.append(f'Row {i} [{name}]: lat not Islamabad: {lat}')
            if not (72.85 <= lng <= 73.20):
                errors.append(f'Row {i} [{name}]: lng not Islamabad: {lng}')
        except (ValueError, KeyError) as e:
            errors.append(f'Row {i}: parse error: {e}')
        rows.append(row)

print(f'Total rows: {len(rows)}')
if errors:
    print('ERRORS FOUND:')
    for err in errors:
        print(f'  {err}')
    sys.exit(1)
else:
    print('All rows valid - coordinates within Islamabad bounds')
    print('CSV stress test PASSED')
