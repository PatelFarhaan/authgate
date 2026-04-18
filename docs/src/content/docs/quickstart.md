---
title: Quick Start
description: Get AuthGate running locally in under 5 minutes.
---

AuthGate is a ~50MB container. The fastest path is the zero-config docker-compose shipped at the repo root.

## One-command deploy

```bash
curl -O https://raw.githubusercontent.com/gatesuite/authgate/main/docker-compose.yml
docker compose up -d
```

Open **http://localhost:8000/login** — you'll see the branded login page.

**That's it.** No config files to create, no repo to clone. Postgres is bundled in the same stack. The published `ghcr.io/gatesuite/authgate:latest` image is used.

## Enabling OAuth providers

Out of the box the login page shows "no providers configured" — you need to add credentials for at least one of GitHub, Google, or GitLab. Set them as env vars before `docker compose up`:

```bash
export GITHUB_CLIENT_ID=your_github_client_id
export GITHUB_CLIENT_SECRET=your_github_client_secret

export GOOGLE_CLIENT_ID=your_google_client_id
export GOOGLE_CLIENT_SECRET=your_google_client_secret

export GITLAB_CLIENT_ID=your_gitlab_client_id
export GITLAB_CLIENT_SECRET=your_gitlab_client_secret

docker compose up -d
```

See [OAuth Providers](/authgate/providers/) for step-by-step instructions to get credentials from each provider.

## Pinning a version

By default the compose uses `ghcr.io/gatesuite/authgate:latest`. To pin to a specific release:

```bash
export AUTHGATE_VERSION=2.0.0
docker compose up -d
```

See the [GitHub Releases page](https://github.com/gatesuite/authgate/releases) for available versions.

## For contributors: build from source

If you're iterating on AuthGate's code, use the contributor-facing compose at `deployments/docker-compose/` which builds from the local `Dockerfile`:

```bash
git clone https://github.com/gatesuite/authgate.git
cd authgate

# 1. Create your local credentials file
cp .env.example .env
# Edit .env — set SECRET_KEY, ADMIN_SECRET_KEY, OAuth credentials

# 2. Create your authgate.yaml (mounted into the container)
cp authgate.example.yaml authgate.yaml
# Edit authgate.yaml — set baseUrl, OAuth redirectPaths to match your registered callbacks

# 3. Start the stack
cd deployments/docker-compose
docker compose up -d --build
```

The compose reads credentials from `.env` and mounts `authgate.yaml` from the repo root — edit either file and restart without rebuilding.

## Without Docker

Prerequisites: Python 3.12+, PostgreSQL running somewhere.

```bash
pip install -r requirements.txt

cp authgate.example.yaml authgate.yaml
# Edit authgate.yaml with your database URL, secret key, and OAuth credentials

# Set secrets as env vars (referenced via $VAR in authgate.yaml)
export SECRET_KEY=$(openssl rand -hex 32)
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/authgate
export GITHUB_CLIENT_ID=your_client_id
export GITHUB_CLIENT_SECRET=your_client_secret

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Next steps

- [Configuration](/authgate/configuration/) — full YAML config reference
- [OAuth Providers](/authgate/providers/) — get client IDs/secrets from GitHub, Google, GitLab
- [Integration Guide](/authgate/integration/) — wire AuthGate into your app's login flow
- [API Reference](/authgate/api-reference/) — `/api/verify`, `/api/userinfo`, JWKS
