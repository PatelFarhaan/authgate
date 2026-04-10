# AuthGate

**Lightweight, customizable OAuth login service for your apps.**

> Plug-and-play authentication gateway — deploy as a sidecar, add OAuth to any app in minutes.

<p align="center">
  <img src="./docs/images/login-light.png" alt="AuthGate Login — Light Mode" width="46%" />
  &nbsp;&nbsp;&nbsp;&nbsp;
  <img src="./docs/images/login-dark.png" alt="AuthGate Login — Dark Mode" width="46%" />
</p>

<p align="center">
  <img src="./excalidraw/architecture.svg" alt="AuthGate Architecture" />
</p>

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

### AuthGate vs Dex

A common question — both handle OAuth, but they solve different problems:

| | **AuthGate** | **Dex** |
|---|---|---|
| **What it is** | Plug-and-play OAuth login service with user DB | OIDC identity federation/proxy layer |
| **Login UI** | Full branded login page with theme, logo, colors | Minimal built-in, expects upstream to handle it |
| **User storage** | PostgreSQL — stores email, name, avatar, provider links | Stateless — no user database, passes tokens through |
| **JWT** | Custom RS256 JWTs with configurable claims and expiry | Standard OIDC ID tokens |
| **Theming** | Configurable via YAML config + custom Jinja2 templates, light/dark support | No theming — provides an OIDC interface only |
| **Config** | YAML config file with `$VAR` env var references | YAML config file with connector definitions |
| **Use case** | "I need a drop-in auth service with a branded login page" | "I need one OIDC endpoint that federates multiple identity sources" |
| **Complexity** | Simple — single container, `docker compose up` | More complex — designed for Kubernetes/enterprise identity |
| **Image size** | ~50MB | ~30MB |

**When to use AuthGate:** You want a complete auth solution — branded login page, user management, JWT issuance — without writing any auth code. Deploy as a sidecar next to your app.

**When to use Dex:** You need to federate multiple identity sources (LDAP, SAML, GitHub, Google) into a single OIDC interface for apps that already speak OIDC. Dex is a connector, not a complete auth service.

---

## Features

- **OAuth Providers** — GitHub, Google, GitLab (enable any combination)
- **Beautiful Login UI** — dark theme, glassmorphism, fully brandable via YAML config
- **JWT (RS256)** — asymmetric keys, auto-generated, JWKS endpoint for downstream verification
- **PostgreSQL** — async, production-ready user storage
- **Fully Customizable** — app name, logo, colors, tagline, theme — all from a single YAML config
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

cp authgate.example.yaml authgate.yaml
# Edit authgate.yaml — add at least one OAuth connector with client ID + secret

cd deployments/docker-compose
docker compose up -d
```

Open **http://localhost:8000/login** and you'll see the branded login page.

### Without Docker

```bash
# Prerequisites: Python 3.12+, PostgreSQL
pip install -r requirements.txt

# Create config
cp authgate.example.yaml authgate.yaml
# Edit authgate.yaml with your database URL, secret key, and OAuth credentials

# Set secrets as env vars (referenced via $VAR in authgate.yaml)
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/authgate
export GITHUB_CLIENT_ID=your_client_id
export GITHUB_CLIENT_SECRET=your_client_secret

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Configuration

All configuration is done via a YAML config file — similar to how [Dex](https://dexidp.io/) handles configuration.

On startup, AuthGate loads `authgate.yaml` from the working directory (or the path set by the `AUTHGATE_CONFIG` env var). If the file is not found, AuthGate exits with an error.

**Keep secrets out of the config file.** Use `$VAR` syntax to reference environment variables — store actual secret values in Kubernetes Secrets, `.env` files, or your platform's secret manager.

### Full YAML config reference

```yaml
# authgate.yaml

# ---------------------------------------------------------------------------
# Branding & appearance
# ---------------------------------------------------------------------------
app:
  name: MyApp                                      # Displayed on the login page
  logoUrl: ""                                      # URL to an external logo image
  logoPath: ""                                     # Local file path; served at /static/logo
  tagline: Secure authentication for your apps     # Subtitle on the login page
  accentColor: "#6366f1"                           # Primary accent color (hex)
  defaultTheme: light                              # light | dark | auto
  customLoginTemplate: ""                          # Path to a custom Jinja2 login template

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
server:
  host: 0.0.0.0
  port: 8000
  baseUrl: ""                     # Public URL (e.g. https://auth.example.com)
  secretKey: $SECRET_KEY          # Read from SECRET_KEY env var

  allowedRedirects:               # Glob patterns for valid redirect URLs
    - http://localhost:3000/*
    - https://app.example.com/*

  corsOrigins:                    # Allowed CORS origins
    - http://localhost:3000
    - https://app.example.com

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
database:
  url: $DATABASE_URL              # Async PostgreSQL URI from env var

# ---------------------------------------------------------------------------
# JWT & cookies
# ---------------------------------------------------------------------------
jwt:
  expiryHours: 24                 # Token lifetime in hours
  keysDir: ./keys                 # Directory for the RS256 key pair
  cookieName: authgate_token      # Name of the auth cookie
  cookieDomain: ""                # e.g. .example.com for cross-subdomain
  cookieSecure: false             # Set true in production (HTTPS)

# ---------------------------------------------------------------------------
# OAuth connectors
# ---------------------------------------------------------------------------
connectors:
  - type: github
    id: github
    name: GitHub
    config:
      clientID: $GITHUB_CLIENT_ID
      clientSecret: $GITHUB_CLIENT_SECRET
      redirectPath: /auth/github/callback

  - type: google
    id: google
    name: Google
    config:
      clientID: $GOOGLE_CLIENT_ID
      clientSecret: $GOOGLE_CLIENT_SECRET
      redirectPath: /auth/google/callback

  - type: gitlab
    id: gitlab
    name: GitLab
    config:
      clientID: $GITLAB_CLIENT_ID
      clientSecret: $GITLAB_CLIENT_SECRET
      redirectPath: /auth/gitlab/callback
      baseUrl: https://gitlab.com
```

### Custom Login Template

You can replace the built-in login page with your own branded HTML by setting `app.customLoginTemplate` in your config:

```yaml
app:
  customLoginTemplate: /etc/authgate/login.html
```

Custom templates are rendered with Jinja2 and receive the following context variables:

| Variable | Type | Description |
|----------|------|-------------|
| `app_name` | str | From `app.name` |
| `app_logo_url` | str | From `app.logoUrl` (or `/static/logo` if `app.logoPath` is set) |
| `app_tagline` | str | From `app.tagline` |
| `accent_color` | str | From `app.accentColor` |
| `theme` | str | `light`, `dark`, or empty (auto) — see below |
| `providers` | list | OAuth providers `[{id, name, color, url}]` |
| `error` | str | Error code from `?error=` query param |
| `authenticated` | str | Set when redirected back after success |

#### Light & Dark Theme Support

The `theme` variable lets your custom template render in light or dark mode. The value comes from (in order of priority):

1. `?theme=light` or `?theme=dark` query param (set by the client app)
2. `app.defaultTheme` from your config (`light`, `dark`, or `auto`)
3. Empty string when `auto` — let the template handle it via JS / `prefers-color-scheme`

**Example custom template** with theme support:

```html
<!DOCTYPE html>
<html lang="en"{% if theme %} data-theme="{{ theme }}"{% endif %}>
<head>
    {% if not theme %}
    <script>
        if (window.matchMedia("(prefers-color-scheme:dark)").matches) {
            document.documentElement.setAttribute("data-theme", "dark");
        }
    </script>
    {% endif %}
    <style>
        :root {
            --bg: #ffffff;
            --text: #333333;
            --accent: {{ accent_color }};
        }
        [data-theme="dark"] {
            --bg: #0d1117;
            --text: #e6edf3;
        }
        body {
            background: var(--bg);
            color: var(--text);
        }
    </style>
</head>
<body>
    <h1>Sign in to {{ app_name }}</h1>
    {% for provider in providers %}
        <a href="{{ provider.url }}">Continue with {{ provider.name }}</a>
    {% endfor %}
</body>
</html>
```

**Client apps** that want to sync their own theme preference can append `?theme=light` or `?theme=dark` to the AuthGate login URL:

```javascript
// In your client app:
const theme = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
window.location.href = `https://auth.example.com/login?redirect_url=${redirectUrl}&theme=${theme}`;
```

Apps that don't care about theming can omit the param — AuthGate falls back to `app.defaultTheme` from the config.

### Kubernetes: ConfigMap + Secret

For Kubernetes deployments, put the config in a ConfigMap and secrets in a Secret. The `$VAR` syntax bridges them:

**Secret** (actual credentials):

```bash
kubectl create secret generic authgate-secrets \
  --from-literal=SECRET_KEY="$(openssl rand -base64 32)" \
  --from-literal=DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/authgate" \
  --from-literal=GITHUB_CLIENT_ID="your-client-id" \
  --from-literal=GITHUB_CLIENT_SECRET="your-client-secret"
```

**ConfigMap** (YAML config referencing secrets via `$VAR`):

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: authgate-config
data:
  authgate.yaml: |
    app:
      name: MyApp
      accentColor: "#6366f1"
    server:
      secretKey: $SECRET_KEY
      allowedRedirects:
        - https://app.example.com/*
      corsOrigins:
        - https://app.example.com
    database:
      url: $DATABASE_URL
    jwt:
      cookieSecure: true
    connectors:
      - type: github
        id: github
        name: GitHub
        config:
          clientID: $GITHUB_CLIENT_ID
          clientSecret: $GITHUB_CLIENT_SECRET
          redirectPath: /auth/github/callback
```

**Deployment** (mount both):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: authgate
spec:
  template:
    spec:
      containers:
        - name: authgate
          image: ghcr.io/farhaan/authgate:latest
          env:
            - name: AUTHGATE_CONFIG
              value: /etc/authgate/authgate.yaml
          envFrom:
            - secretRef:
                name: authgate-secrets
          volumeMounts:
            - name: config
              mountPath: /etc/authgate
              readOnly: true
      volumes:
        - name: config
          configMap:
            name: authgate-config
```

The config file reads `$SECRET_KEY`, `$DATABASE_URL`, etc. from the environment variables injected by the Secret.

---

## OAuth Provider Setup

### GitHub

1. Go to **Settings > Developer settings > OAuth Apps > New OAuth App**
2. Set **Homepage URL** to your AuthGate URL (e.g., `http://localhost:8000`)
3. Set **Authorization callback URL** to `{BASE_URL}{GITHUB_REDIRECT_PATH}` (e.g. `http://localhost:8000/auth/github/callback`)
4. Add the Client ID and Client Secret to your `authgate.yaml` connector config (use `$VAR` syntax to reference env vars)

### Google

1. Go to **Google Cloud Console > APIs & Services > Credentials**
2. Create an **OAuth 2.0 Client ID** (Web application)
3. Add **Authorized redirect URI**: `{BASE_URL}{GOOGLE_REDIRECT_PATH}` (e.g. `http://localhost:8000/auth/google/callback`)
4. Add the Client ID and Client Secret to your `authgate.yaml` connector config (use `$VAR` syntax to reference env vars)

### GitLab

1. Go to **User Settings > Applications**
2. Set **Redirect URI** to `{BASE_URL}{GITLAB_REDIRECT_PATH}` (e.g. `http://localhost:8000/auth/gitlab/callback`)
3. Select scope: `read_user`
4. Add the Application ID and Secret to your `authgate.yaml` connector config (use `$VAR` syntax to reference env vars)

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
| `{PROVIDER_REDIRECT_PATH}` | GET | OAuth callback — path set per connector in config |
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

> **Tip:** For a cleaner setup, use an `authgate.yaml` config file with `$VAR` references
> mounted via ConfigMap + Secret. See [Configuration (YAML)](#configuration-yaml) above
> for a complete Kubernetes example with ConfigMap, Secret, and Deployment manifests.

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
│   ├── config.py             # YAML config loader
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
├── authgate.example.yaml     # Configuration reference
├── authgate.example.yaml     # YAML configuration reference
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
