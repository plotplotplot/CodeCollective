# AI Entrypoint

Start here: `/ai.entrypoint.json`

## Rules For AI Assistants

1. Treat `/data/category_maps/lenses.json` as the primary taxonomy entrypoint.
2. Treat `/data/category_maps/community_sectors.json` as a subset of Lenses.
3. Keep `/data/category_maps/index.json` `default_map` set to `lenses`.
4. Keep `/calendar.html` `window.CALENDAR_DEFAULT_CATEGORY_MAP` set to `lenses`.
5. Keep fallback maps in `/js/calendar.js` in sync with taxonomy files.
6. Preserve dedicated colors for each Lenses category.

## Lenses Hierarchy

- `lenses`: Community, Education, Health, Arts & Culture, Housing, Public Safety, Environment, Economy
- `community_sectors` subset: Community, Education, Health, Arts & Culture, Housing, Public Safety, Environment

The only intentional difference is `Economy`, which exists in `lenses` and not in `community_sectors`.
