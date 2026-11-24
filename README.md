[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/new/template/glean?utm_medium=integration&utm_source=button&utm_campaign=glean)

# Glean on Railway

One-click Railway template for [Glean](https://github.com/LeslieLeung/glean) **v0.3.0** (AGPL-3.0), a self-hosted RSS reader and personal knowledge base: feeds, full-text extraction, folders, tags, bookmarks, notes, read-later, an admin dashboard and an MCP server.

## What it deploys

| Service | Source | What it does |
| --- | --- | --- |
| **Web** | `web/` (`ghcr.io/leslieleung/glean-web:0.3.0@sha256:668f741f…`) | Reader UI on a public URL; nginx proxies `/api` and `/mcp` to Backend |
| **Admin** | `admin/` (`ghcr.io/leslieleung/glean-admin:0.3.0@sha256:3f93f74c…`) | Admin dashboard on its own public URL |
| **Backend** | `backend/` (built from Glean commit `3a0c39dc`, tag `v0.3.0`) | FastAPI API; runs migrations and the first-boot account setup |
| **Worker** | `backend/` with `GLEAN_ROLE=worker` | arq worker: feed fetches every 15 minutes, full-text extraction, cleanup |
| **Postgres** | `pgvector/pgvector:0.8.7-pg16@sha256:484e8380…` | Database with pgvector, on a volume |
| **Redis** | `redis:8.4.8-alpine@sha256:ff72f74e…` | Job queue, password-protected, private network only |

Why the backend is built here instead of using `ghcr.io/leslieleung/glean-backend:0.3.0`: that image is 4.3 GB (CUDA PyTorch for the optional local embedding model), over Railway's 4 GB image limit on Free and Trial plans. `backend/Dockerfile` installs exactly upstream's locked dependencies (`uv.lock`) minus `torch` and `sentence-transformers` and what only they pull in, giving a ~0.7 GB image. Embeddings still work through any OpenAI-compatible API (Admin > Embeddings).

Other changes from upstream's compose file, all in this repo:

- First boot creates the admin (`ADMIN_USERNAME` / generated `ADMIN_PASSWORD`) and your reader account (`GLEAN_USER_EMAIL` / generated `GLEAN_USER_PASSWORD`), then turns open sign-up off. Upstream's default `admin` / `Admin123!` is never used. Later boots never touch accounts.
- Migrations run under a PostgreSQL advisory lock (overlapping Railway deploys can't run them twice); the worker waits for the schema.
- Logs go to stdout only (no log volume), and per-statement SQL logging is turned down so Railway's log rate limit isn't hit.
- The API listens dual-stack on `PORT`; nginx re-resolves the backend's private DNS name and sizes its workers to the service's CPUs.
- Any startup failure exits non-zero, so Railway's on-failure restart policy restarts it.

## Variables

| Service | Variable | Default | Notes |
| --- | --- | --- | --- |
| Backend | `GLEAN_USER_EMAIL` | *(you enter it)* | Email for your reader login |
| Backend | `GLEAN_USER_PASSWORD` | `${{secret(20)}}` | Reader password, see the Variables tab |
| Backend | `ADMIN_USERNAME` | `admin` | Admin dashboard login |
| Backend | `ADMIN_PASSWORD` | `${{secret(24)}}` | Admin dashboard password |
| Backend | `SECRET_KEY` | `${{secret(64)}}` | JWT signing key |
| Backend | `DATABASE_URL`, `REDIS_URL`, `MCP_*` | references | Wired to Postgres, Redis and the Web domain |
| Postgres | `POSTGRES_PASSWORD` | `${{secret(32)}}` | Database password |
| Redis | `REDIS_PASSWORD` | `${{secret(32)}}` | Queue password |

Changing `ADMIN_PASSWORD` or `GLEAN_USER_PASSWORD` after the first boot does not change the accounts; change passwords in the apps.

## Resources

Tested with every service limited to 0.5 GB RAM / 1 vCPU: Backend ~210 MB and Worker ~250 MB after fetching feeds, so the stack runs on Railway's Free and Trial plans.

## Updates

Railway sends an "update available" notice to every project deployed from this template when `main` changes. Each update bumps the pinned Glean release (commit and image digests) and gets an entry in [CHANGELOG.md](CHANGELOG.md), breaking changes first. Upstream marks Glean as still in development, so back up Postgres before applying an update.
