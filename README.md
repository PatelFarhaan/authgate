# AuthGate

**Lightweight, customizable OAuth login service for your apps.**

> Plug-and-play authentication gateway — deploy as a sidecar, add OAuth to any app in minutes.

---

## Why AuthGate?

We looked at what's already out there:

| Solution | Problem |
|----------|---------|
| **Keycloak** | Heavy, complex, overkill for most apps (~500MB+ image) |
| **Authentik** | Feature-rich but heavyweight, steep learning curve |
| **Authelia** | Focused on 2FA/SSO proxy, not a login service |
| **oauth2-proxy** | No login UI, limited customization |
| **Dex** | OIDC connector only, no user management |

**AuthGate fills the gap** — a lightweight (~50MB image), fully customizable OAuth login service with a beautiful branded UI, JWT-based auth, and one-command deployment.

---

## Features

- **OAuth Providers** — GitHub, Google, GitLab (enable any combination)
- **Beautiful Login UI** — dark theme, glassmorphism, fully brandable via env vars
- **JWT (RS256)** — asymmetric keys, auto-generated, JWKS endpoint for downstream verification
- **PostgreSQL** — async, production-ready user storage
- **Fully Customizable** — app name, logo, colors, tagline — all from environment variables
- **Kubernetes-Ready** — Helm chart, ConfigMap/Secret separation, health checks
- **Docker-First** — multi-stage build, ~50MB image, docker-compose for local dev
- **Privacy-First** — only stores email, name, avatar. No passwords. No tracking.
- **Async & Fast** — built on FastAPI with full async I/O

---

## Quick Start

### Docker Compose (recommended for local dev)

```bash
git clone https://github.com/farhaan/authgate.git
cd authgate

cp .env.example .env
# Edit .env — add at least one OAuth provider's client ID + secret

cd deployments/docker-compose
docker compose up -d
```

Open **http://localhost:8000/login** and you'll see the branded login page.

### Without Docker

```bash
# Prerequisites: Python 3.12+, PostgreSQL
pip install -r requirements.txt

# Set environment variables (or create .env file)
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/authgate
export GITHUB_CLIENT_ID=your_client_id
export GITHUB_CLIENT_SECRET=your_client_secret
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Configuration

All configuration is done via environment variables (or a `.env` file).

### Branding

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `AuthGate` | Displayed on the login page |
| `APP_LOGO_URL` | _(none)_ | URL to your logo image |
| `APP_TAGLINE` | `Secure authentication for your apps` | Subtitle on login page |
| `ACCENT_COLOR` | `#6366f1` | Primary accent color (hex) |

### Server

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `change-me-in-production` | **Must change.** Used for signing state tokens |
| `BASE_URL` | *(auto-detected)* | Public URL of AuthGate (e.g. `http://localhost:8000` or `https://auth.example.com`). Used to build OAuth callback URIs. When empty, falls back to the request's base URL |
| `GITHUB_REDIRECT_PATH` | *(required if GitHub enabled)* | Callback path for GitHub OAuth (e.g. `/auth/github/callback`, `/github/redirect`, `/callback`) |
| `GOOGLE_REDIRECT_PATH` | *(required if Google enabled)* | Callback path for Google OAuth (e.g. `/auth/google/callback`, `/login/complete`) |
| `GITLAB_REDIRECT_PATH` | *(required if GitLab enabled)* | Callback path for GitLab OAuth (e.g. `/auth/gitlab/callback`) |
| `ALLOWED_REDIRECTS` | *(required)* | Comma-separated glob patterns for valid redirect URLs (e.g. `http://localhost:3000/*`) |
| `CORS_ORIGINS` | *(required)* | Comma-separated allowed CORS origins (e.g. `http://localhost:3000`) |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | *(required)* | Async PostgreSQL connection string (e.g. `postgresql+asyncpg://user:pass@host:5432/authgate`) |

### JWT

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_EXPIRY_HOURS` | `24` | Token lifetime |
| `JWT_KEYS_DIR` | `./keys` | Directory for RSA key pair (auto-generated if missing) |
| `COOKIE_NAME` | `authgate_token` | Name of the auth cookie |
| `COOKIE_DOMAIN` | _(none)_ | Cookie domain (e.g., `.example.com` for cross-subdomain) |
| `COOKIE_SECURE` | `false` | Set `true` in production (requires HTTPS) |

### OAuth Providers

Configure one or more. Only providers with both client ID and secret will appear on the login page.

| Variable | Description |
|----------|-------------|
| `GITHUB_CLIENT_ID` | GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth App client secret |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `GITLAB_CLIENT_ID` | GitLab OAuth Application ID |
| `GITLAB_CLIENT_SECRET` | GitLab OAuth Application secret |
| `GITLAB_BASE_URL` | GitLab instance URL (default: `https://gitlab.com`) |

---

## OAuth Provider Setup

### GitHub

1. Go to **Settings > Developer settings > OAuth Apps > New OAuth App**
2. Set **Homepage URL** to your AuthGate URL (e.g., `http://localhost:8000`)
3. Set **Authorization callback URL** to `{BASE_URL}{GITHUB_REDIRECT_PATH}` (e.g. `http://localhost:8000/auth/github/callback`)
4. Copy the Client ID and Client Secret into your `.env`

### Google

1. Go to **Google Cloud Console > APIs & Services > Credentials**
2. Create an **OAuth 2.0 Client ID** (Web application)
3. Add **Authorized redirect URI**: `{BASE_URL}{GOOGLE_REDIRECT_PATH}` (e.g. `http://localhost:8000/auth/google/callback`)
4. Copy the Client ID and Client Secret into your `.env`

### GitLab

1. Go to **User Settings > Applications**
2. Set **Redirect URI** to `{BASE_URL}{GITLAB_REDIRECT_PATH}` (e.g. `http://localhost:8000/auth/gitlab/callback`)
3. Select scope: `read_user`
4. Copy the Application ID and Secret into your `.env`

---

## Integration Guide

### How it works

```
┌────────-──┐     1. redirect     ┌─-──────────┐
│  Your App │ ──────────────────→ │  AuthGate  │
│           │                     │            │
│           │  4. redirect back   │  /login    │
│           │ ←────────────────── │  (branded) │
│           │    with JWT token   │            │
└─────────-─┘                     └────┬──-────┘
                                       │ 2. OAuth
                                       ↓
                                 ┌────────-───┐
                                 │  GitHub /  │
                                 │  Google /  │
                                 │  GitLab    │
                                 └─────────-──┘
                                   3. callback
```

### Step 1: Redirect unauthenticated users

When a user visits your app without a valid session, redirect them:

```
https://auth.example.com/login?redirect_url=https://app.example.com/dashboard
```

### Step 2: Receive the token

After authentication, AuthGate redirects back to your app with a JWT:

```
https://app.example.com/dashboard?token=eyJhbG...
```

AuthGate also sets an HttpOnly cookie (`authgate_token`) — useful when your app and AuthGate share a domain.

### Step 3: Verify the token

**Option A: Call the verify endpoint**

```bash
curl -H "Authorization: Bearer <token>" https://auth.example.com/api/verify
```

**Option B: Validate locally using JWKS**

```bash
curl https://auth.example.com/.well-known/jwks.json
```

Use the public key to verify the JWT signature in your app without network calls.

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/login` | GET | Branded login page (pass `?redirect_url=...`) |
| `/auth/{provider}` | GET | Start OAuth flow (`github`, `google`, `gitlab`) |
| `{PROVIDER_REDIRECT_PATH}` | GET | OAuth callback — path set via env var per provider |
| `/api/verify` | GET | Verify JWT, returns `{ valid, user }` |
| `/api/userinfo` | GET | Get authenticated user profile |
| `/.well-known/jwks.json` | GET | Public keys for JWT verification |
| `/logout` | POST | Clear auth cookie |
| `/health` | GET | Health check |

**Authentication:** Pass token as `Authorization: Bearer <token>` header or via the `authgate_token` cookie.

---

## Deployment

### Docker Compose (local dev)

```bash
cd deployments/docker-compose
docker compose up -d
```

### Kubernetes (Helm via OCI)

**Step 1: Create the secret (never stored in values.yaml)**

```bash
kubectl create secret generic authgate-secrets \
  --from-literal=SECRET_KEY="$(openssl rand -base64 32)" \
  --from-literal=DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/authgate" \
  --from-literal=GITHUB_CLIENT_ID="your-client-id" \
  --from-literal=GITHUB_CLIENT_SECRET="your-client-secret"
```

**Step 2: Install the chart**

```bash
helm install authgate oci://ghcr.io/farhaan/charts/authgate \
  --set existingSecret=authgate-secrets
```

Or use a `values.yaml` override:

```bash
helm install authgate oci://ghcr.io/farhaan/charts/authgate -f my-values.yaml
```

To install from source instead:

```bash
helm install authgate ./deployments/helm/authgate -f my-values.yaml
```

**Production defaults included:** HPA (2-10 replicas, CPU/memory scaling), PodDisruptionBudget (minAvailable: 1), topology spread, read-only root filesystem, non-root user, startup/liveness/readiness probes, zero-downtime rolling updates.

### Make Targets

| Command | Description |
|---------|-------------|
| `make dev` | Start dev server with hot-reload |
| `make run` | Start production server |
| `make docker-up` | Build and start via Docker Compose |
| `make docker-down` | Stop containers |
| `make docker-logs` | Tail container logs |
| `make clean` | Remove `__pycache__` artifacts |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (async Python) |
| Database | PostgreSQL + asyncpg + SQLAlchemy |
| Auth | JWT (RS256) + OAuth 2.0 |
| Frontend | Jinja2 + vanilla CSS |
| Container | Docker (multi-stage, ~50MB) |
| Orchestration | Helm / Docker Compose |
| CI/CD | GitHub Actions |

---

## Architecture

### Kubernetes Deployment

```mermaid
graph TB
    User["🌐 User Browser"]

    subgraph Internet
        ALB["AWS ALB / Ingress Controller"]
    end

    subgraph EKS Cluster
        subgraph Public["Public (Ingress Rules)"]
            AG_Ingress["Ingress: auth.example.com"]
            App_Ingress["Ingress: app.example.com"]
        end

        subgraph Private["Private (ClusterIP Services)"]
            AG["AuthGate<br/>ClusterIP :8000"]
            App["App Backend<br/>ClusterIP :3000"]
            PG["PostgreSQL<br/>ClusterIP :5432"]
        end
    end

    subgraph OAuth Providers
        GH["GitHub"]
        GO["Google"]
        GL["GitLab"]
    end

    User -->|"HTTPS"| ALB
    ALB --> AG_Ingress
    ALB --> App_Ingress
    AG_Ingress --> AG
    App_Ingress --> App
    AG -->|"Async"| PG
    AG <-->|"OAuth 2.0"| GH
    AG <-->|"OAuth 2.0"| GO
    AG <-->|"OAuth 2.0"| GL
    App -.->|"GET /.well-known/jwks.json<br/>(verify JWT locally)"| AG

    style AG fill:#10b981,stroke:#047857,color:#fff
    style App fill:#3b82f6,stroke:#1d4ed8,color:#fff
    style PG fill:#6366f1,stroke:#4338ca,color:#fff
    style ALB fill:#f59e0b,stroke:#d97706,color:#fff
```

### Authentication Flow

```mermaid
sequenceDiagram
    actor User
    participant App as Your App (app.example.com)
    participant AG as AuthGate (auth.example.com)
    participant OAuth as OAuth Provider
    participant DB as PostgreSQL

    User->>App: Visit app.example.com
    App->>App: Check for JWT cookie/header
    alt No valid JWT
        App-->>User: Redirect to auth.example.com/login?redirect_url=app.example.com
        User->>AG: GET /login
        AG-->>User: Render branded login page
        User->>AG: Click "Continue with GitHub"
        AG->>OAuth: Redirect to provider authorize URL
        OAuth-->>User: Show consent screen
        User->>OAuth: Approve
        OAuth->>AG: Callback with auth code
        AG->>OAuth: Exchange code for access token
        OAuth-->>AG: Return access token
        AG->>OAuth: Fetch user profile (name, email, avatar)
        OAuth-->>AG: Return profile
        AG->>DB: Create or update user record
        DB-->>AG: Confirm
        AG->>AG: Generate JWT (RS256)
        AG-->>User: Set HttpOnly cookie + redirect to app.example.com?token=xxx
    end
    User->>App: Request with JWT
    App->>App: Verify JWT using JWKS public key
    App-->>User: Serve authenticated content
```

---

## Project Structure

```
authgate/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── config.py             # Pydantic settings from env
│   ├── database.py           # Async SQLAlchemy engine
│   ├── models.py             # User model
│   ├── schemas.py            # Pydantic response schemas
│   ├── jwt_handler.py        # RS256 JWT + JWKS + state tokens
│   ├── oauth/
│   │   ├── base.py           # Abstract OAuth provider
│   │   ├── github.py         # GitHub OAuth
│   │   ├── google.py         # Google OAuth
│   │   └── gitlab.py         # GitLab OAuth
│   ├── routes/
│   │   ├── auth.py           # Login, callback, logout
│   │   ├── api.py            # Verify, userinfo endpoints
│   │   └── health.py         # Health check
│   └── templates/
│       └── login.html        # Branded login page (Jinja2)
├── deployments/
│   ├── docker-compose/       # Local dev setup
│   └── helm/authgate/        # Kubernetes Helm chart
├── .github/workflows/        # CI/CD pipeline
├── Dockerfile                # Production container
├── .env.example              # Configuration reference
└── requirements.txt
```

---

## Security

- **RS256 (asymmetric)** — private key never leaves the auth container; downstream apps verify with the public key
- **CSRF protection** — state parameter with signed, time-limited tokens
- **HttpOnly cookies** — prevents XSS token theft
- **Redirect validation** — only allows redirects to pre-approved URL patterns
- **Non-root container** — runs as unprivileged user in Docker
- **No password storage** — OAuth only, no credential database to breach

---

© 2026 AuthGate
