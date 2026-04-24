# Cloudflare + PIdP Deployment

This deploy path uses:

- `portal/web` on **Cloudflare Workers** via `wrangler deploy`
- `portal/governance-backend` on your backend host with Postgres
- hosted PIdP at **https://pidp.arkavo.org**

## 1) Configure governance backend

Set backend runtime environment:

```bash
export DATABASE_URL='postgresql://<db-user>:<db-password>@<db-host>:5432/<db-name>'
export REDIS_URL='redis://localhost:6379/0'
export PIDP_BASE_URL='https://pidp.arkavo.org'
```

Then run backend:

```bash
cd portal/governance-backend
uvicorn main:app --host 0.0.0.0 --port 8002
```

Verify:

```bash
curl -i http://127.0.0.1:8002/health
```

## 2) Build and deploy portal web with Wrangler

Install deps and build:

```bash
cd portal/web
npm install
npm run build:cf
```

Deploy, setting proxy origins for API routes:

```bash
npx wrangler deploy \
  --var GOVERNANCE_API_ORIGIN:https://<your-governance-backend-domain>
```

Notes:

- `/api/governance/*` is proxied to `GOVERNANCE_API_ORIGIN`
- `/pidp/*` is proxied to `https://pidp.arkavo.org` by default (or `PIDP_API_ORIGIN` if overridden)
- All other routes serve the SPA from `dist/` with `index.html` fallback

## 3) Frontend runtime mode

The web app uses API mode when built with:

```bash
VITE_DATA_SOURCE=api
VITE_API_BASE_URL=/api/governance
```

Because the Worker proxies `/api/governance`, this default works without hardcoding backend URLs in the frontend bundle.
