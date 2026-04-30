# Baltimore Vacants Data Pipeline (R2 Shards)

This pipeline pulls official Baltimore City vacant-property data and publishes sharded GeoJSON to Cloudflare R2.

Sources (Housing/Accela_DHCD MapServer):
- Layer `8`: `Vacant Lot`
- Layer `9`: `All Vacant Building Notices`

## Local refresh

```bash
python baltimore/fetch_vacants.py \
  --output baltimore/data/vacants.geojson
```

This writes:
- `baltimore/data/vacants.geojson`
- `baltimore/data/vacants.geojson.gz`

## Build shards

```bash
python baltimore/shard_vacants.py \
  --input baltimore/data/vacants.geojson \
  --output-root baltimore/data/publish \
  --prefix vacants \
  --shard-size 1000
```

Output object keys:
- `vacants/latest.json`
- `vacants/vYYYYMMDDTHHMMSSZ/manifest.json`
- `vacants/vYYYYMMDDTHHMMSSZ/shards/group=<GROUP>/page=0001.json.gz`

Groups:
- `ALL`
- `VACANT_LOT`
- `VACANT_BUILDING_NOTICE`

## Build parcel-boundary shards (for always-on boundaries)

```bash
python baltimore/build_vacants_parcels.py \
  --vacants-input baltimore/data/vacants.geojson \
  --output baltimore/data/vacants_parcels.geojson

python baltimore/shard_vacants.py \
  --input baltimore/data/vacants_parcels.geojson \
  --output-root baltimore/data/publish \
  --prefix vacants_parcels \
  --shard-size 500
```

Output object keys:
- `vacants_parcels/latest.json`
- `vacants_parcels/vYYYYMMDDTHHMMSSZ/manifest.json`
- `vacants_parcels/vYYYYMMDDTHHMMSSZ/shards/group=<GROUP>/page=0001.json.gz`

## Publish to R2

Use existing publisher:

```bash
python usa/publish_to_r2.py \
  --input-root baltimore/data/publish \
  --prefix vacants \
  --keep-versions 30
```

Required env vars:
- `R2_BUCKET`
- `R2_ENDPOINT_URL`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`

## Worker API (`cloudflare/worker.js`)

- `GET /api/vacants/meta`
- `GET /api/vacants/meta?version=vYYYYMMDDTHHMMSSZ`
- `GET /api/vacants?group=ALL&page=1`
- `GET /api/vacants?group=VACANT_LOT&page=1`
- `GET /api/vacants?group=VACANT_BUILDING_NOTICE&page=1`
- `GET /api/vacants_parcels/meta`
- `GET /api/vacants_parcels?group=ALL&page=1`
