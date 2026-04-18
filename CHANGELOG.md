# Changelog

## [3.0.1](https://github.com/gatesuite/authgate/compare/v3.0.0...v3.0.1) (2026-04-18)


### Bug Fixes

* CI test environment and pre-commit YAML exclusion for Helm templates ([bdd74cd](https://github.com/gatesuite/authgate/commit/bdd74cd07afe879ac2e71f82bb8808e0a996feb2))

## [3.0.0](https://github.com/gatesuite/authgate/compare/v2.1.0...v3.0.0) (2026-04-18)


### ⚠ BREAKING CHANGES

* Admin panel enforces a minimum SECRET_KEY length of 64 characters (RFC 7518, HS256). Deployments with a short key will see the admin container refuse to start:

### Features

* add admin panel with user management UI ([f29ed4b](https://github.com/gatesuite/authgate/commit/f29ed4b9453055ed947ec168bf1ce435f7887732))

## [2.1.0](https://github.com/gatesuite/authgate/compare/v2.0.0...v2.1.0) (2026-04-16)


### Features

* **docs:** add Starlight docs site with GitHub-style theme and ([8df22aa](https://github.com/gatesuite/authgate/commit/8df22aa2d908ee31b81468ddb98a32380248bf94))
* **docs:** add Starlight documentation site ([8122c5c](https://github.com/gatesuite/authgate/commit/8122c5c7c298a0eda8d5d872f30594058223b179))
* **docs:** add Starlight documentation site ([8df22aa](https://github.com/gatesuite/authgate/commit/8df22aa2d908ee31b81468ddb98a32380248bf94))
* **docs:** add Starlight documentation site with GitHub-style theme ([a83d758](https://github.com/gatesuite/authgate/commit/a83d7580814afe7659c22f0e983ec7fb0ec3e963))


### Bug Fixes

* theme live reload, test infrastructure, and make app-up ([b434366](https://github.com/gatesuite/authgate/commit/b434366f91a5918307ca2bca07ba0eca35e19aa7))

## [2.0.0](https://github.com/PatelFarhaan/authgate/compare/v1.0.9...v2.0.0) (2026-04-13)


### ⚠ BREAKING CHANGES

* add is_active flag to disable user login  Adds is_active boolean to users table (default true). Enforced in  the OAuth callback, /api/verify, and /api/userinfo — disabled users  cannot log in and active JWTs are invalidated.  BREAKING CHANGE: existing deployments must run  ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;  before upgrading.
* remove deprecated provider columns, return providers list  Deletes User.provider and User.provider_id columns and switches  UserInfo to return providers: list[str] sourced from the UserProvider  relationship, sorted most-recently-linked first.  BREAKING CHANGE: UserInfo.provider (string) replaced with UserInfo.providers (list[str]).  API consumers must update their parsing. Existing user.provider and user.provider_id  columns in the users table are now unused — safe to drop.

### Features

* add is_active flag to disable user login  Adds is_active boolean to users table (default true). Enforced in  the OAuth callback, /api/verify, and /api/userinfo — disabled users  cannot log in and active JWTs are invalidated.  BREAKING CHANGE: existing deployments must run  ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;  before upgrading. ([90c146a](https://github.com/PatelFarhaan/authgate/commit/90c146a880a367e2df7cee36d4d61991ba382539))
* **api:** add user account disabling feature ([ef1bfba](https://github.com/PatelFarhaan/authgate/commit/ef1bfba94481693f8cc1340b77b5686d001fe6af))
* redesign login page with shield logo, light/dark themes, and screenshots ([ee6cf0c](https://github.com/PatelFarhaan/authgate/commit/ee6cf0cd3c72a350fbf5337449354904a1dd88e3))
* remove deprecated provider columns, return providers list  Deletes User.provider and User.provider_id columns and switches  UserInfo to return providers: list[str] sourced from the UserProvider  relationship, sorted most-recently-linked first.  BREAKING CHANGE: UserInfo.provider (string) replaced with UserInfo.providers (list[str]).  API consumers must update their parsing. Existing user.provider and user.provider_id  columns in the users table are now unused — safe to drop. ([44559be](https://github.com/PatelFarhaan/authgate/commit/44559be701f8574ad990adfb8404c75e771c439c))
* update login page styles and enhance configuration for accent color ([ef4b318](https://github.com/PatelFarhaan/authgate/commit/ef4b31873e6e98a0d6ca5eb1d9c1cb217dfa3a93))
