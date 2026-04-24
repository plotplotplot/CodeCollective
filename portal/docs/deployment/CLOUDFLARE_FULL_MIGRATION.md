# Cloudflare Full-Site Migration

This setup migrates `codecollective.us` from S3 static hosting to Cloudflare Workers static assets, while mounting the portal at `/p/`.

## What this serves

- Legacy site static assets from repository root
- Portal SPA at `/p/` (from `portal/web/dist`)
- API proxy at `/api/governance/*` -> `GOVERNANCE_API_ORIGIN`
- PIdP proxy at `/pidp/*` -> `https://pidp.arkavo.org/*` (prefix stripped)

## 1) Build deployable site bundle

From repo root:

```bash
./scripts/build_cloudflare_site.sh
```

This writes output to:

- `.cloudflare/site` (Worker static assets directory)

## 2) Deploy to Cloudflare (Wrangler integration)

From repo root:

```bash
npx wrangler deploy
```

Optional override:

```bash
npx wrangler deploy --var GOVERNANCE_API_ORIGIN:https://portal.arkavo.org --var PIDP_API_ORIGIN:https://pidp.arkavo.org
```

## 3) Validate before DNS cutover

Use the Worker URL from deploy output and test:

- `/` (legacy homepage)
- `/p/` (portal)
- `/p/governance`
- `/api/governance/motions`
- `/pidp/auth/me` (should return 401 without login, which is expected)

## 4) Route53 cutover

Important: Route53 cannot route by path (`/p/`). It only routes hostnames. Path behavior is handled by the Worker.

1. In Cloudflare DNS, confirm `codecollective.us` and `www.codecollective.us` records exist in the zone.
2. In Cloudflare SSL/TLS, set mode to `Full (strict)` after origin certs are ready (or keep proxied Worker-only setup).
3. In Route53 hosted zone for `codecollective.us`, replace current alias targets with Cloudflare nameservers by updating registrar delegation.
4. At your domain registrar (where `codecollective.us` is registered), change NS records to the two Cloudflare nameservers shown in Cloudflare.
5. Wait for NS propagation (typically minutes to a few hours; full global propagation can take up to 48h).
6. After propagation, verify:
   - `https://codecollective.us/`
   - `https://codecollective.us/p/`
   - `https://www.codecollective.us/p/`

## Rollback

To rollback quickly, revert registrar NS records back to previous Route53 NS values.
