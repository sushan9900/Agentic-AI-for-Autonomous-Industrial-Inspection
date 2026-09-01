import httpx
import json

def inspect():
    c = httpx.Client(timeout=15.0, headers={'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    doi = '10.17632/kcyn4nhv2c.1'
    print('=== 1. DataCite Check ===')
    try:
        r = c.get(f'https://api.datacite.org/dois/{doi}')
        print('DataCite Status:', r.status_code)
        if r.status_code == 200:
            attrs = r.json().get('data', {}).get('attributes', {})
            print('Title:', attrs.get('titles'))
            print('Creators:', attrs.get('creators'))
            print('License:', attrs.get('rightsList'))
            print('URL:', attrs.get('url'))
    except Exception as e:
        print('DataCite error:', e)

    print('\n=== 2. Mendeley Files Check ===')
    try:
        r2 = c.get('https://data.mendeley.com/api/datasets/kcyn4nhv2c/files')
        print('Mendeley API Status:', r2.status_code)
        if r2.status_code == 200:
            files = r2.json()
            print(f'Files found: {len(files)}')
            print(json.dumps(files, indent=2))
    except Exception as e:
        print('Mendeley API error:', e)

if __name__ == '__main__':
    inspect()
