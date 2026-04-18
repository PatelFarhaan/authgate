---
title: Admin Panel
description: Optional web UI for managing AuthGate users — enable, disable, delete, and search from a browser.
---

The admin panel is an optional companion service that gives you a web UI to manage all AuthGate users. It runs as a **separate container** alongside AuthGate, connects to the same PostgreSQL database, and requires no additional storage.

:::caution[Internal tool]
The admin panel is designed for internal use only. Do not expose it to the public internet — run it on a private network or behind a VPN/internal ingress only.
:::

## Features

- **Dashboard** — total users, active vs. disabled counts, provider breakdown, new signups this week
- **Users table** — search by name or email, filter by provider (GitHub/Google/GitLab) or status (active/disabled), paginated
- **Enable / disable** — toggles a user's `is_active` flag; disabled users cannot log in and their existing JWTs are invalidated
- **Delete** — permanently removes a user and all linked OAuth providers (cascade)

## Local development

The admin container is included in the deployment Docker Compose and starts automatically with `make app-up`.

**1. Add your admin credentials to `.env`:**

```bash
ADMIN_USERNAME=admin          # defaults to "admin" if unset
ADMIN_PASSWORD=yourpassword   # required — empty password disables login entirely
ADMIN_SECRET_KEY=             # generate with: openssl rand -hex 32
```

Generate a secret key (minimum 64 characters, i.e. 32 bytes of entropy):

```bash
echo "ADMIN_SECRET_KEY=$(openssl rand -hex 32)" >> .env
```

**2. Start the stack:**

```bash
make app-up
```

**3. Open the admin panel:**

```
http://localhost:8001
```

Tail admin logs separately:

```bash
make admin-logs
```

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | Same PostgreSQL URI used by AuthGate |
| `ADMIN_PASSWORD` | Yes | — | Password for the admin login form. Empty = login disabled |
| `ADMIN_USERNAME` | No | `admin` | Username for the admin login form |
| `ADMIN_SECRET_KEY` | Yes* | — | Signing key for admin session tokens (HS256). Minimum 64 characters. Generate with `openssl rand -hex 32`. Falls back to `SECRET_KEY` if unset |
| `COOKIE_SECURE` | No | `false` | Set `true` in production (HTTPS only) |

:::note
`DATABASE_URL` is the same value used by the main AuthGate service — the admin panel reads from the same database, it does not write schema changes.
:::

## Kubernetes / Helm

The admin panel is **disabled by default**. Enable it in your `values.yaml`:

```yaml
admin:
  enabled: true

  image:
    repository: ghcr.io/gatesuite/authgate-admin
    tag: "2.0.0"       # pin to a specific release

  # Reuse the main secret (must contain DATABASE_URL, ADMIN_USERNAME, ADMIN_PASSWORD)
  # or specify a separate secret:
  existingSecret: "authgate-secrets"

  service:
    type: ClusterIP
    port: 8001

  ingress:
    enabled: true
    host: admin-auth.internal.example.com   # internal hostname only
    className: nginx
    annotations:
      nginx.ingress.kubernetes.io/whitelist-source-range: "10.0.0.0/8"
    tls: true
    tlsSecretName: admin-auth-tls

  resources:
    requests:
      cpu: 50m
      memory: 64Mi
    limits:
      cpu: 200m
      memory: 128Mi
```

The Helm chart creates a separate `Deployment`, `Service`, and (optionally) `Ingress` for the admin panel — all prefixed with `<release>-admin`.

### Required secret keys

The secret referenced by `admin.existingSecret` (or `existingSecret` if not set separately) must contain:

| Key | Description |
|-----|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `ADMIN_USERNAME` | Admin login username |
| `ADMIN_PASSWORD` | Admin login password |
| `ADMIN_SECRET_KEY` | *(optional)* Session signing key |

```bash
kubectl create secret generic authgate-admin-secrets \
  --from-literal=DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/authgate" \
  --from-literal=ADMIN_USERNAME="admin" \
  --from-literal=ADMIN_PASSWORD="$(openssl rand -base64 24)" \
  --from-literal=ADMIN_SECRET_KEY="$(openssl rand -hex 32)"
```

## Session behaviour

- Sessions are signed JWT tokens (HS256) stored in an `admin_session` httponly cookie
- Sessions expire after **8 hours**
- The signing key defaults to `SECRET_KEY` — set `ADMIN_SECRET_KEY` to isolate admin sessions from the main app's signing key

## Security recommendations

- **Never expose port 8001 publicly** — use an internal ingress or port-forward only
- **Use HTTPS** — set `COOKIE_SECURE=true` and terminate TLS at the ingress
- **Restrict by IP** — use ingress `whitelist-source-range` annotations or a network policy
- **Rotate `ADMIN_SECRET_KEY`** — this invalidates all active admin sessions (users must re-login)
- **Strong password** — `ADMIN_PASSWORD` is the only credential; use a long random string
- **Minimum key length** — `ADMIN_SECRET_KEY` must be at least 64 characters (32 bytes of entropy per RFC 7518 for HS256); the app refuses to start if the key is too short
