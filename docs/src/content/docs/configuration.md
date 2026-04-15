---
title: Configuration
description: Configure AuthGate via YAML with environment variable references.
---

All configuration is done via a YAML config file — similar to how [Dex](https://dexidp.io/) handles configuration.

On startup, AuthGate loads `authgate.yaml` from the working directory (or the path set by the `AUTHGATE_CONFIG` env var). If the file is not found, AuthGate exits with an error.

:::note
**Keep secrets out of the config file.** Use `$VAR` syntax to reference environment variables — store actual secret values in Kubernetes Secrets, `.env` files, or your platform's secret manager.
:::

## Full YAML reference

```yaml
# authgate.yaml

# ───────────────────────────────────────────────────────────────
# Branding & appearance
# ───────────────────────────────────────────────────────────────
app:
  name: MyApp                                      # Displayed on the login page
  logoUrl: ""                                      # URL to an external logo image
  logoPath: ""                                     # Local file path; served at /static/logo
  tagline: Secure authentication for your apps     # Subtitle on the login page
  accentColor: "#0060F0"                           # Primary accent color (hex)
  defaultTheme: light                              # light | dark | auto
  customLoginTemplate: ""                          # Path to a custom Jinja2 login template

# ───────────────────────────────────────────────────────────────
# Server
# ───────────────────────────────────────────────────────────────
server:
  host: 0.0.0.0
  port: 8000
  baseUrl: ""                                      # Public URL (e.g. https://auth.example.com)
  secretKey: $SECRET_KEY                           # Read from SECRET_KEY env var

  allowedRedirects:                                # Glob patterns for valid redirect URLs
    - http://localhost:3000/*
    - https://app.example.com/*

  corsOrigins:                                     # Allowed CORS origins
    - http://localhost:3000
    - https://app.example.com

# ───────────────────────────────────────────────────────────────
# Database
# ───────────────────────────────────────────────────────────────
database:
  url: $DATABASE_URL                               # Async PostgreSQL URI from env var

# ───────────────────────────────────────────────────────────────
# JWT & cookies
# ───────────────────────────────────────────────────────────────
jwt:
  expiryHours: 24
  keysDir: ./keys                                  # Directory for the RS256 key pair
  cookieName: authgate_token
  cookieDomain: ""                                 # e.g. .example.com for cross-subdomain
  cookieSecure: false                              # Set true in production (HTTPS)

# ───────────────────────────────────────────────────────────────
# OAuth connectors
# ───────────────────────────────────────────────────────────────
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

## Custom login template

You can replace the built-in login page with your own branded HTML by setting `app.customLoginTemplate` in your config:

```yaml
app:
  customLoginTemplate: /etc/authgate/login.html
```

Custom templates are rendered with Jinja2 and receive these context variables:

| Variable | Type | Description |
|----------|------|-------------|
| `app_name` | str | From `app.name` |
| `app_logo_url` | str | From `app.logoUrl` (or `/static/logo` if `app.logoPath` is set) |
| `app_tagline` | str | From `app.tagline` |
| `accent_color` | str | From `app.accentColor` |
| `theme` | str | `light`, `dark`, or empty (auto) |
| `providers` | list | OAuth providers: `[{id, name, color, url}]` |
| `error` | str | Error code from `?error=` query param |
| `authenticated` | str | Set when redirected back after success |

### Light & dark themes

The `theme` variable lets your template render in light or dark mode. The value comes from (in order of priority):

1. `?theme=light` or `?theme=dark` query param (set by the client app)
2. `app.defaultTheme` from your config (`light`, `dark`, or `auto`)
3. Empty string when `auto` — let the template handle it via JS / `prefers-color-scheme`

Example custom template with theme support:

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
        body { background: var(--bg); color: var(--text); }
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

Client apps that want to sync their own theme preference can append `?theme=light` or `?theme=dark` to the AuthGate login URL:

```javascript
const theme = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
window.location.href = `https://auth.example.com/login?redirect_url=${redirectUrl}&theme=${theme}`;
```

## Kubernetes: ConfigMap + Secret

For Kubernetes deployments, put the config in a ConfigMap and secrets in a Secret. The `$VAR` syntax bridges them.

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
      accentColor: "#0060F0"
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
          image: ghcr.io/gatesuite/authgate:latest
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
