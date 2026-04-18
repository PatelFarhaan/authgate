"""
E2E tests for the AuthGate admin panel.

Fixtures (admin_client, admin_authed_client, admin_db) are defined in conftest.py.
"""

from sqlalchemy import select

from app.models import User, UserProvider

# ── Health / routing ──────────────────────────────────────────────────────────


async def test_health(admin_client):
    resp = await admin_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_root_redirects_to_dashboard(admin_client):
    resp = await admin_client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/dashboard"


# ── Auth ──────────────────────────────────────────────────────────────────────


async def test_login_page_renders(admin_client):
    resp = await admin_client.get("/login")
    assert resp.status_code == 200
    assert "Sign in" in resp.text
    assert "Admin" in resp.text


async def test_login_wrong_password_returns_401(admin_client):
    resp = await admin_client.post(
        "/login",
        data={"username": "admin", "password": "wrongpassword"},
        follow_redirects=False,
    )
    assert resp.status_code == 401
    assert "Invalid" in resp.text


async def test_login_empty_password_rejected(admin_client):
    resp = await admin_client.post(
        "/login",
        data={"username": "admin", "password": ""},
        follow_redirects=False,
    )
    assert resp.status_code == 401


async def test_login_success_sets_session_cookie(admin_client):
    resp = await admin_client.post(
        "/login",
        data={"username": "admin", "password": "testpassword"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "admin_session" in resp.headers.get("set-cookie", "")


async def test_logout_clears_session(admin_authed_client):
    resp = await admin_authed_client.get("/logout", follow_redirects=False)
    assert resp.status_code == 302

    # After logout the session cookie is cleared — protected routes redirect.
    resp = await admin_authed_client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]


# ── Protected route enforcement ───────────────────────────────────────────────


async def test_dashboard_requires_auth(admin_client):
    resp = await admin_client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]


async def test_users_requires_auth(admin_client):
    resp = await admin_client.get("/users", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]


async def test_invalid_session_token_redirects(admin_client):
    admin_client.cookies.set("admin_session", "not-a-valid-token")
    resp = await admin_client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]


# ── Dashboard ─────────────────────────────────────────────────────────────────


async def test_dashboard_renders(admin_authed_client):
    resp = await admin_authed_client.get("/dashboard")
    assert resp.status_code == 200
    assert "Dashboard" in resp.text
    assert "Total users" in resp.text
    assert "Active" in resp.text


async def test_dashboard_counts_users(admin_authed_client, admin_db):
    admin_db.add(User(email="count1@example.com", name="Count One"))
    admin_db.add(User(email="count2@example.com", name="Count Two", is_active=False))
    await admin_db.commit()

    resp = await admin_authed_client.get("/dashboard")
    assert resp.status_code == 200
    # Stats for total=2, active=1, disabled=1 should appear somewhere in the page
    assert "2" in resp.text
    assert "1" in resp.text


# ── Users list ────────────────────────────────────────────────────────────────


async def test_users_list_empty_state(admin_authed_client):
    resp = await admin_authed_client.get("/users")
    assert resp.status_code == 200
    assert "No users found" in resp.text


async def test_users_list_shows_user(admin_authed_client, admin_db):
    user = User(email="charlie@example.com", name="Charlie Test")
    admin_db.add(user)
    await admin_db.flush()
    admin_db.add(
        UserProvider(user_id=user.id, provider="github", provider_id="gh-charlie")
    )
    await admin_db.commit()

    resp = await admin_authed_client.get("/users")
    assert resp.status_code == 200
    assert "charlie@example.com" in resp.text
    assert "Charlie Test" in resp.text
    assert "github" in resp.text


async def test_users_search_by_email(admin_authed_client, admin_db):
    for email, name in [("dave@example.com", "Dave"), ("eve@example.com", "Eve")]:
        admin_db.add(User(email=email, name=name))
    await admin_db.commit()

    resp = await admin_authed_client.get("/users?q=dave")
    assert resp.status_code == 200
    assert "dave@example.com" in resp.text
    assert "eve@example.com" not in resp.text


async def test_users_search_by_name(admin_authed_client, admin_db):
    admin_db.add(User(email="frank@example.com", name="Frank Unique"))
    admin_db.add(User(email="grace@example.com", name="Grace Other"))
    await admin_db.commit()

    resp = await admin_authed_client.get("/users?q=Unique")
    assert "frank@example.com" in resp.text
    assert "grace@example.com" not in resp.text


async def test_users_filter_active(admin_authed_client, admin_db):
    admin_db.add(User(email="act@example.com", name="Active", is_active=True))
    admin_db.add(User(email="dis@example.com", name="Disabled", is_active=False))
    await admin_db.commit()

    resp = await admin_authed_client.get("/users?status=active")
    assert "act@example.com" in resp.text
    assert "dis@example.com" not in resp.text


async def test_users_filter_disabled(admin_authed_client, admin_db):
    admin_db.add(User(email="act2@example.com", name="Active2", is_active=True))
    admin_db.add(User(email="dis2@example.com", name="Disabled2", is_active=False))
    await admin_db.commit()

    resp = await admin_authed_client.get("/users?status=disabled")
    assert "dis2@example.com" in resp.text
    assert "act2@example.com" not in resp.text


async def test_users_filter_by_provider(admin_authed_client, admin_db):
    u1 = User(email="ghuser@example.com", name="GH User")
    u2 = User(email="gguser@example.com", name="GG User")
    admin_db.add(u1)
    admin_db.add(u2)
    await admin_db.flush()
    admin_db.add(
        UserProvider(user_id=u1.id, provider="github", provider_id="gh-filter1")
    )
    admin_db.add(
        UserProvider(user_id=u2.id, provider="google", provider_id="gg-filter1")
    )
    await admin_db.commit()

    resp = await admin_authed_client.get("/users?provider=github")
    assert "ghuser@example.com" in resp.text
    assert "gguser@example.com" not in resp.text


# ── User actions ──────────────────────────────────────────────────────────────


async def test_toggle_disables_active_user(admin_authed_client, admin_db):
    user = User(email="toggle-on@example.com", name="Toggle On", is_active=True)
    admin_db.add(user)
    await admin_db.commit()
    await admin_db.refresh(user)

    resp = await admin_authed_client.post(
        f"/users/{user.id}/toggle",
        data={"redirect_to": "/users"},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    await admin_db.refresh(user)
    assert user.is_active is False


async def test_toggle_enables_disabled_user(admin_authed_client, admin_db):
    user = User(email="toggle-off@example.com", name="Toggle Off", is_active=False)
    admin_db.add(user)
    await admin_db.commit()
    await admin_db.refresh(user)

    await admin_authed_client.post(
        f"/users/{user.id}/toggle",
        data={"redirect_to": "/users"},
        follow_redirects=False,
    )

    await admin_db.refresh(user)
    assert user.is_active is True


async def test_toggle_preserves_redirect_filters(admin_authed_client, admin_db):
    user = User(email="redirect@example.com", name="Redirect Test")
    admin_db.add(user)
    await admin_db.commit()
    await admin_db.refresh(user)

    resp = await admin_authed_client.post(
        f"/users/{user.id}/toggle",
        data={"redirect_to": "/users?status=active&q=test"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/users?status=active&q=test"


async def test_toggle_nonexistent_user_redirects_safely(admin_authed_client):
    resp = await admin_authed_client.post(
        "/users/nonexistent-id/toggle",
        data={"redirect_to": "/users"},
        follow_redirects=False,
    )
    assert resp.status_code == 302


async def test_delete_user(admin_authed_client, admin_db):
    user = User(email="deleteme@example.com", name="Delete Me")
    admin_db.add(user)
    await admin_db.commit()
    user_id = user.id

    resp = await admin_authed_client.post(
        f"/users/{user_id}/delete",
        follow_redirects=False,
    )
    assert resp.status_code == 302

    result = await admin_db.execute(select(User).where(User.id == user_id))
    assert result.scalar_one_or_none() is None


async def test_delete_user_cascades_providers(admin_authed_client, admin_db):
    user = User(email="cascade@example.com", name="Cascade Test")
    admin_db.add(user)
    await admin_db.flush()
    admin_db.add(
        UserProvider(user_id=user.id, provider="github", provider_id="gh-cascade")
    )
    await admin_db.commit()
    user_id = user.id

    await admin_authed_client.post(f"/users/{user_id}/delete", follow_redirects=False)

    result = await admin_db.execute(
        select(UserProvider).where(UserProvider.user_id == user_id)
    )
    assert result.scalars().all() == []


async def test_delete_nonexistent_user_redirects_safely(admin_authed_client):
    resp = await admin_authed_client.post(
        "/users/nonexistent-id/delete",
        follow_redirects=False,
    )
    assert resp.status_code == 302


# ── Action requires auth ──────────────────────────────────────────────────────


async def test_toggle_requires_auth(admin_client):
    resp = await admin_client.post(
        "/users/some-id/toggle",
        data={"redirect_to": "/users"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]


async def test_delete_requires_auth(admin_client):
    resp = await admin_client.post(
        "/users/some-id/delete",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]
