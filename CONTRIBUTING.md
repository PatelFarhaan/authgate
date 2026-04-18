# Contributing to AuthGate

Thanks for taking the time to contribute.

## Requirements

- Docker Desktop 4.0+
- Python 3.12+
- [pre-commit](https://pre-commit.com/) — for linting and formatting hooks

```bash
pip install pre-commit
pre-commit install
```

## Local development

```bash
# 1. Clone the repo
git clone https://github.com/gatesuite/authgate.git
cd authgate

# 2. Create your credentials file
cp .env.example .env
# Edit .env — set SECRET_KEY, ADMIN_SECRET_KEY, and OAuth credentials

# 3. Create your local config
cp authgate.example.yaml authgate.yaml
# Edit authgate.yaml — set baseUrl and OAuth redirectPaths

# 4. Start the stack (AuthGate + Admin + Postgres)
make app-up

# 5. Open the login page
open http://localhost:8000/login

# 6. Open the admin panel
open http://localhost:8001
```

## Running tests

```bash
# Run the full E2E test suite (builds test image, starts Postgres, runs pytest)
make test-run

# Tear down test containers and volumes
make test-down
```

## Pre-commit hooks

The project uses pre-commit for linting and formatting. Hooks run automatically on `git commit`. To run them manually:

```bash
pre-commit run --all-files
```

Hooks include: `black`, `isort`, `flake8`, `check-yaml`, `detect-private-key`.

## Commit messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/) — releases and the changelog are automated via [release-please](https://github.com/googleapis/release-please).

| Prefix | When to use |
|--------|-------------|
| `feat:` | New feature or behaviour |
| `fix:` | Bug fix |
| `docs:` | Documentation changes only |
| `chore:` | CI, deps, tooling — no user-facing change |
| `test:` | Adding or fixing tests |
| `refactor:` | Internal restructure, no behaviour change |

Breaking changes: add `!` after the type (`feat!:`) and include a `BREAKING CHANGE:` footer in the commit body.

## Pull requests

1. Fork the repo and create a branch off `main`.
2. Keep PRs focused — one logical change per PR.
3. Ensure `pre-commit run --all-files` and `make test-run` pass locally before pushing.
4. Fill in the PR description — what changed and why.

## Project structure

```
authgate/
├── app/                  # Main AuthGate FastAPI application
├── admin/                # Admin panel FastAPI application
├── tests/                # E2E test suite (pytest + real Postgres)
├── deployments/
│   ├── docker-compose/   # Contributor-facing compose (builds from source)
│   └── helm/authgate/    # Kubernetes Helm chart
├── docs/                 # Astro/Starlight documentation site
├── Dockerfile            # Multi-stage build (production + test)
├── authgate.example.yaml # Configuration reference
└── .env.example          # Environment variable reference
```

## Reporting issues

Use the issue templates. Include your OS, Docker version, AuthGate version, and the exact steps to reproduce.
