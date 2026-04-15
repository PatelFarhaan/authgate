---
title: Security
description: AuthGate's security model, defaults, and reporting vulnerabilities.
---

## Security model

AuthGate is designed to be secure by default. Key choices:

- **RS256 (asymmetric JWTs)** — the private key never leaves the auth container. Downstream apps verify tokens with the public key via JWKS, so there's no shared secret to leak.
- **CSRF protection** — OAuth state parameter uses signed, time-limited (10 min) tokens. Any tampered or replayed state is rejected at the callback.
- **HttpOnly cookies** — prevents XSS token theft. JS on the client cannot read `authgate_token`.
- **Redirect validation** — only URLs matching `server.allowedRedirects` glob patterns are accepted. Prevents open-redirect attacks.
- **Non-root container** — AuthGate runs as an unprivileged user inside Docker.
- **No password storage** — OAuth only. There's no credential database to breach.
- **User disable** — `is_active` flag blocks disabled users at the OAuth callback AND invalidates their active JWTs via `/api/verify` and `/api/userinfo`.
- **Local JWT verification via JWKS** — apps can verify tokens without calling AuthGate per request, avoiding a central point of failure.
- **Minimal data** — only email, name, avatar stored. No tracking, no analytics, no IP logs.

## Token lifecycle

| Token | Algorithm | Expiry | Signed with |
|---|---|---|---|
| User JWT | RS256 (asymmetric) | 24h (configurable via `jwt.expiryHours`) | Private key at `{JWT_KEYS_DIR}/private.pem` |
| OAuth state token | HS256 (symmetric) | 10 minutes | `SECRET_KEY` from config |

### Rotating JWT keys

To rotate keys (e.g., after suspected compromise):

1. Stop AuthGate
2. Delete or move `{JWT_KEYS_DIR}/private.pem` and `public.pem`
3. Start AuthGate — new keys are auto-generated on startup
4. **All existing JWTs become invalid** — users must re-authenticate

There's no built-in key rollover (keeping old keys valid during a transition period). If you need zero-downtime rotation, that's a feature request for a future release.

## Default credentials (development only)

The shipped `docker-compose.yml` uses a placeholder `SECRET_KEY` of `change-me-in-production-this-is-insecure`. **Override this in production.** Generate a proper secret with:

```bash
openssl rand -base64 32
```

The Postgres default credentials (`authgate:authgate`) are also insecure — they work for local dev but should be swapped for production deployments via managed Postgres (RDS, Cloud SQL, Neon, etc.) with proper credentials.

## HTTPS / production hardening

For production:

```yaml
# authgate.yaml
jwt:
  cookieSecure: true       # cookie sent over HTTPS only
```

Use TLS at the ingress layer (Nginx, ALB, Cloudflare, etc.) — terminate TLS before the AuthGate container.

Consider setting:

```yaml
jwt:
  cookieDomain: .example.com    # cross-subdomain cookie (if AuthGate + app share parent domain)
```

## Content Security Policy

AuthGate doesn't set a CSP header by default. If you serve AuthGate behind a reverse proxy, add one there. A reasonable starting policy for the login page:

```
Content-Security-Policy: default-src 'self';
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  font-src https://fonts.gstatic.com;
  img-src 'self' data: https:
```

The `'unsafe-inline'` for styles is needed because the built-in login template uses inline CSS. If you use a custom template without inline styles, you can drop it.

## Dependencies

AuthGate keeps dependencies minimal:

- `fastapi`, `uvicorn`, `sqlalchemy`, `asyncpg` — core
- `PyJWT[crypto]`, `cryptography` — JWT signing/verification
- `httpx` — async HTTP client for OAuth provider calls
- `jinja2` — login template rendering
- `pyyaml` — config parsing

Periodic dependency updates happen via release-please — check the [GitHub Releases](https://github.com/gatesuite/authgate/releases) for the changelog.

## Reporting security issues

**Please report security vulnerabilities privately.** Two options:

1. **GitHub Security Advisory** (preferred): [Open a draft advisory](https://github.com/gatesuite/authgate/security/advisories/new)
2. Email the maintainer

Do **not** open public issues or PRs for undisclosed vulnerabilities.

Acknowledgement: we'll respond within 7 days with a fix timeline. After a fix is released, we'll credit you in the security advisory and release notes unless you prefer anonymity.

## Threat model

AuthGate assumes:

- **Your network layer is trusted** — AuthGate ↔ Postgres traffic, AuthGate ↔ OAuth providers traffic, and the `/api/verify` call from apps are all assumed to be either inside a trusted network or over TLS
- **Your `SECRET_KEY` is kept secret** — leaking it allows an attacker to forge OAuth state tokens (but NOT user JWTs, which use RS256)
- **Your private key is kept secret** — leaking `private.pem` allows an attacker to forge user JWTs. Treat it like any other service credential.

AuthGate does **not** protect against:

- Compromised OAuth provider accounts (if an attacker has your GitHub account, they can sign in as you)
- Phishing (a fake login page tricking users into providing provider credentials to the attacker)
- Compromised client apps (a malicious app with a valid JWT can impersonate the user)

These are general OAuth realities, not AuthGate-specific.
