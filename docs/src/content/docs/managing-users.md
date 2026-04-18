---
title: Managing Users
description: Disable users, upgrade notes, first-time signup detection, user administration.
---

## User data model

AuthGate stores minimal data per user:

| Column | Type | Purpose |
|---|---|---|
| `id` | UUID | Primary key (referenced in JWT `sub` claim) |
| `email` | string | Unique identifier across all providers |
| `name` | string | Display name from the provider |
| `avatar_url` | string | Avatar image URL |
| `created_at` | timestamp | When the user first signed up |
| `last_login_at` | timestamp | Most recent login |
| `is_active` | boolean | If `false`, user is blocked from logging in |

Plus a `user_providers` table for the one-to-many relationship of OAuth providers linked to each user (a user can sign in with both GitHub and Google and link to the same record by email).

## Disabling a user

Each user has an `is_active` boolean on the `users` table (default `true`). Set it to `false` to immediately:

- **Block future logins** at the OAuth callback — the user is redirected to `/login?error=account_disabled`
- **Invalidate active sessions** — `/api/verify` returns `{ "valid": false }` and `/api/userinfo` returns `401` for disabled users, even if their JWT hasn't expired

Toggle it via the admin panel (see [Admin Panel](/authgate/admin-panel/)) or directly in the database:

```sql
-- Disable a user
UPDATE users SET is_active = false WHERE email = 'user@example.com';

-- Re-enable
UPDATE users SET is_active = true WHERE email = 'user@example.com';
```

## Detecting first-time signups

When a user signs in for the first time, AuthGate appends `&new_user=true` to the redirect URL:

```
https://app.example.com/dashboard?token=eyJhbG...&new_user=true
```

Use this signal to trigger:
- Welcome emails
- Onboarding wizards
- Analytics events (`user_signup`)
- Default resource provisioning (e.g., creating a default workspace)

The param is absent on subsequent logins.

:::caution
`new_user=true` is a UX signal, not a cryptographic claim. It's not signed. Don't use it for security-critical logic — use it for "show the welcome banner" style UX cues only.
:::

## Viewing user data

Use the [Admin Panel](/authgate/admin-panel/) for a web UI, or query Postgres directly:

```sql
-- List all users
SELECT id, email, name, created_at, last_login_at, is_active
FROM users
ORDER BY last_login_at DESC;

-- Count users per provider
SELECT provider, COUNT(*) as user_count
FROM user_providers
GROUP BY provider;

-- Find users who haven't logged in recently
SELECT email, last_login_at
FROM users
WHERE last_login_at < NOW() - INTERVAL '90 days'
ORDER BY last_login_at;

-- Find users with multiple linked providers
SELECT u.email, ARRAY_AGG(up.provider) as providers
FROM users u
JOIN user_providers up ON u.id = up.user_id
GROUP BY u.email
HAVING COUNT(up.provider) > 1;
```

## Upgrading from pre-`is_active` versions

AuthGate creates tables via `Base.metadata.create_all`, which doesn't `ALTER` existing tables. If you're upgrading an existing deployment (pre-2.0.0), run once against your database:

```sql
ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
```

### Removing deprecated provider columns

The older `provider` and `provider_id` columns on `users` (deprecated and removed in the 2.0.0 release) can stay — they're harmless. If you want a clean schema:

```sql
ALTER TABLE users DROP COLUMN provider;
ALTER TABLE users DROP COLUMN provider_id;
```

The current data model uses the `user_providers` table for multi-provider support.

## Deleting a user

To permanently delete a user and all their linked provider identities:

```sql
DELETE FROM users WHERE email = 'user@example.com';
```

The `user_providers` table has `ON DELETE CASCADE` on its foreign key, so linked providers are cleaned up automatically.
