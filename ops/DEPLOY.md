# Deploy

orca-validator is **co-located on the shared cyberiad droplet** for now, behind
`orca.cyberiad.ai`. It is built to be a good neighbour and to lift-and-shift to its own
droplet later without surgery.

## Bring it up

```bash
cp .env.example .env          # set API_KEY (and DATABASE_URL/REDIS_URL if not using compose)
make install                  # npm install (verifier) + pip install -e ".[dev]"
make verify-machines          # topology gate — must pass before deploy
docker compose up -d --build  # api + its OWN postgres + redis (CPU/mem limited)
docker compose exec api alembic upgrade head   # apply migrations
curl -s localhost:8085/health # {"status":"ok","checks":{"postgres":"ok","redis":"ok"}}
```

## Exposing it at orca.cyberiad.ai

`orca.cyberiad.ai` is a sibling of the existing `*.cyberiad.ai` apps (memchat/paperclip), each
of which has its **own per-domain cert** — there is no `*.cyberiad.ai` wildcard, and the builder
wildcard only covers `*.builder.cyberiad.ai`. Three steps:

1. **DNS** — add an A record `orca.cyberiad.ai → <droplet IP>` (it does not resolve yet).
2. **Cert** — `certbot certonly --webroot -w /var/www/certbot -d orca.cyberiad.ai`
   (the vhost ships the `/.well-known/acme-challenge/` location for HTTP-01).
3. **nginx** — copy `ops/nginx/orca.cyberiad.ai.conf` to `/etc/nginx/sites-enabled/orca.cyberiad.ai`,
   then `nginx -t && systemctl reload nginx`. It proxies to the **web** UI on `:3000`.

The raw API (`:8085`) stays internal — the web proxies to it server-side. If programmatic API
access is wanted publicly, give it its own subdomain/cert (e.g. `api.orca.cyberiad.ai → :8085`).

## Why it can't starve the builder (the co-location contract)

We watched a busy process starve a *shared* connection pool and 500 every login on this
droplet. This service is isolated by construction:

- **Its own Postgres + Redis** (compose services) — never the builder's instances.
- **Explicit `cpus` / `mem_limit`** on `api` (and the worker when enabled) in `docker-compose.yml`.
- **Bounded worker concurrency** (`WORKER_CONCURRENCY`) — OCR/LLM never fan out unboundedly.
- **DB engine hardening** carried from the builder's login-race postmortem:
  `pool_pre_ping=True` + `pool_timeout` (fail fast on exhaustion, never an unbounded stall).

### Load check (task §7.1)
Before trusting it under real traffic, drive `POST /documents` concurrently while watching
`docker stats` (api stays within its `cpus`/`mem_limit`) and the Postgres connection count
(`SELECT count(*) FROM pg_stat_activity`) — it must stay well under `DATABASE_POOL_SIZE +
DATABASE_MAX_OVERFLOW`, with the worker capped at `WORKER_CONCURRENCY`.

## Processing modes

- **Default (MVP):** in-process FastAPI BackgroundTasks. One `api` service, no worker needed.
- **Production:** set `USE_REDIS_QUEUE=true`; the api enqueues and a dedicated worker
  (`python -m backend.pipeline.worker`, or `make worker`) consumes with bounded concurrency.
  Add it as a second compose service behind the same image with its own `cpus`/`mem_limit`.

## Migrating to a dedicated droplet (lift-and-shift checklist)

Because the unit is already isolated, migration is mechanical:

1. Stand up the new droplet with Docker + the wildcard cert (or its own cert for `orca.cyberiad.ai`).
2. `pg_dump` the compose Postgres volume → restore on the new host (or repoint `DATABASE_URL`
   at a managed Postgres).
3. `git clone`, copy `.env`, `docker compose up -d --build`, `alembic upgrade head`.
4. Move `ops/nginx/orca.cyberiad.ai.conf` to the new host (or repoint DNS at it) and reload nginx.
5. Cut DNS for `orca.cyberiad.ai` to the new droplet; decommission the co-located stack.
