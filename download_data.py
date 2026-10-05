"""Download the real, bounded OBIS subset used in the proof of concept."""
from pathlib import Path
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
BASE = 'https://api.obis.org/v3/'
QUERY = {
    'scientificname': 'Actinopterygii',
    'geometry': 'POLYGON ((122 9, 125 9, 125 12, 122 12, 122 9))',
    'fields': 'id,occurrenceID,dataset_id,datasetName,scientificName,species,speciesid,genus,family,class,decimalLatitude,decimalLongitude,year,minimumDepthInMeters,maximumDepthInMeters,marine,absence,dropped,flags,license,rightsHolder,accessRights,basisOfRecord,coordinateUncertaintyInMeters',
}


def get_json(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                return json.load(response)
        except Exception as error:
            print(f'Request retry {attempt + 1}: {type(error).__name__}: {error}', flush=True)
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def main():
    rows, after, reported_total = [], '-1', None
    checkpoint = DATA / 'download_checkpoint.json'
    if checkpoint.exists():
        saved = json.loads(checkpoint.read_text(encoding='utf-8'))
        # The first checkpoint format predates its query field; it was generated
        # by this same downloader for this fixed pilot query.
        if saved.get('query', QUERY) == QUERY:
            rows, after, reported_total = saved['rows'], saved['after'], saved['total']
            print(f'Resuming matching download at {len(rows):,} records.', flush=True)
    while True:
        params = dict(QUERY, after=after, size=10000)
        if after != '-1':
            params['total'] = 'false'
        page = get_json(BASE + 'occurrence?' + urllib.parse.urlencode(params))
        if page.get('total') is not None:
            reported_total = page['total']
        batch = page.get('results', [])
        if not batch:
            break
        new_after = batch[-1]['id']
        if new_after == after:
            raise RuntimeError('Pagination cursor did not advance.')
        rows.extend(batch)
        after = new_after
        checkpoint.write_text(json.dumps({'query': QUERY, 'rows': rows, 'after': after, 'total': reported_total}), encoding='utf-8')
        print(f'Downloaded {len(rows):,} / {reported_total:,} records', flush=True)
    if len({row['id'] for row in rows}) != len(rows):
        raise RuntimeError('Duplicate OBIS IDs in paginated download.')
    if reported_total is not None and len(rows) != reported_total:
        raise RuntimeError('Fetched count does not match API count; investigate before analysis.')
    (DATA / 'obis_visayas_raw.json').write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    provenance = {
        'source': 'Ocean Biodiversity Information System (OBIS)',
        'endpoint': BASE + 'occurrence', 'query': QUERY,
        'query_example_url': BASE + 'occurrence?' + urllib.parse.urlencode(dict(QUERY, size=10000, after='-1')),
        'retrieved_utc': datetime.now(timezone.utc).isoformat(),
        'reported_total': reported_total, 'downloaded_records': len(rows),
        'pagination': 'Sequential pages; after = last OBIS record id; exhausted to empty page.',
        'scope': 'Visayas-region rectangle, 122–125 E and 9–12 N; not an official administrative or maritime boundary.',
        'taxonomy': 'Actinopterygii (ray-finned fish), not all fish; marine flag enforced during cleaning.',
    }
    (DATA / 'provenance.json').write_text(json.dumps(provenance, indent=2, ensure_ascii=False), encoding='utf-8')
    # Retain provider attribution and original record-level rights in the raw snapshot.
    ids = sorted({r['dataset_id'] for r in rows if r.get('dataset_id')})
    metadata = []
    for dataset_id in ids:
        print(f'Fetching provider metadata: {dataset_id}', flush=True)
        metadata.append({'dataset_id': dataset_id, 'metadata': get_json(BASE + 'dataset/' + dataset_id)})
    (DATA / 'dataset_metadata.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
    countries = get_json('https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_0_countries.geojson')
    philippines = {'type': 'FeatureCollection', 'features': [f for f in countries['features'] if f['properties'].get('ADMIN') == 'Philippines']}
    assert philippines['features'], 'Philippine map geometry not found.'
    (DATA / 'philippines_outline.geojson').write_text(json.dumps(philippines), encoding='utf-8')
    checkpoint.unlink(missing_ok=True)
    print(f'Complete: {len(rows):,} records from {len(ids)} contributing datasets.', flush=True)


if __name__ == '__main__':
    main()
