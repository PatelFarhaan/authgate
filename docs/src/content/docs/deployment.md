---
title: Deployment
description: Deploy AuthGate via Docker Compose or Kubernetes (Helm).
---

## Docker Compose (local / small deployments)

The repo ships a zero-config root `docker-compose.yml` that bundles AuthGate + PostgreSQL:

```bash
curl -O https://raw.githubusercontent.com/gatesuite/authgate/main/docker-compose.yml
docker compose up -d
```

Set OAuth credentials via env vars before `up`:

```bash
export GITHUB_CLIENT_ID=... GITHUB_CLIENT_SECRET=...
export GOOGLE_CLIENT_ID=... GOOGLE_CLIENT_SECRET=...
export GITLAB_CLIENT_ID=... GITLAB_CLIENT_SECRET=...
docker compose up -d
```

Pin a specific version:

```bash
export AUTHGATE_VERSION=2.0.0
docker compose up -d
```

## Kubernetes (Helm via OCI)

**Step 1: Create the secret** (never committed to values.yaml):

```bash
kubectl create secret generic authgate-secrets \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/authgate" \
  --from-literal=GITHUB_CLIENT_ID="your-client-id" \
  --from-literal=GITHUB_CLIENT_SECRET="your-client-secret"
```

:::tip
For a cleaner setup, use an `authgate.yaml` config file with `$VAR` references mounted via ConfigMap + Secret. See [Configuration → Kubernetes](/authgate/configuration/#kubernetes-configmap--secret) for a complete example.
:::

**Step 2: Install the chart**:

```bash
helm install authgate oci://ghcr.io/gatesuite/charts/authgate \
  --set existingSecret=authgate-secrets
```

Or use a `values.yaml` override:

```bash
helm install authgate oci://ghcr.io/gatesuite/charts/authgate -f my-values.yaml
```

To install from source instead:

```bash
git clone https://github.com/gatesuite/authgate.git
helm install authgate ./authgate/deployments/helm/authgate -f my-values.yaml
```

### Production defaults included

The Helm chart ships with sensible production defaults:

- **HPA** — 2-10 replicas, scales on CPU + memory
- **PodDisruptionBudget** — `minAvailable: 1` (zero-downtime rolling updates)
- **Topology spread constraints** — replicas distributed across nodes/zones
- **Read-only root filesystem** — container can't write outside designated volumes
- **Non-root user** — runs as unprivileged user
- **Startup / liveness / readiness probes** — Kubernetes-native health checking
- **Rolling update strategy** — no downtime during deployments

### Key Helm values

| Value | Default | Purpose |
|---|---|---|
| `image.tag` | `latest` | Image version (override for reproducibility) |
| `replicaCount` | `1` | Minimum replicas (HPA scales up from here) |
| `autoscaling.maxReplicas` | `10` | Max replicas |
| `existingSecret` | `""` | Name of the pre-created Secret with credentials |
| `ingress.enabled` | `false` | Enable Ingress (set host / TLS as needed) |
| `persistence.keys.enabled` | `true` | Persist JWT keys across pod restarts |

See the chart's `values.yaml` for the full list.

## Production checklist

Before going live:

- [ ] **Strong `SECRET_KEY`** — use `openssl rand -hex 32`, never the default
- [ ] **HTTPS only** — set `jwt.cookieSecure: true` in config
- [ ] **Correct `baseUrl`** — AuthGate needs to know its public URL for OAuth redirect construction
- [ ] **Restrictive `allowedRedirects`** — match only your actual app URLs, no wildcards like `http://*`
- [ ] **CORS origins explicit** — don't use `*`; list your app domains
- [ ] **Postgres persistent volume** — don't lose the user database to pod restarts
- [ ] **JWT keys persistent volume** — losing `keysDir` invalidates all active JWTs
- [ ] **Database backups** — standard Postgres backup strategy (pgBackRest, wal-g, cloud-native tooling)
- [ ] **OAuth app redirect URIs** — update from `localhost` to production URLs at GitHub/Google/GitLab
- [ ] **Monitoring** — scrape `/health` for liveness; optional metrics endpoint coming in future release

## Ingress example (NGINX + cert-manager)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: authgate
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt
spec:
  ingressClassName: nginx
  tls:
    - hosts: [auth.example.com]
      secretName: authgate-tls
  rules:
    - host: auth.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: authgate
                port:
                  number: 8000
```
