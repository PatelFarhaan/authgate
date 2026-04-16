"""
E2E tests for /api/verify and /api/userinfo.
"""

# ---------------------------------------------------------------------------
# /api/verify
# ---------------------------------------------------------------------------


async def test_verify_no_token_returns_invalid(client):
    resp = await client.get("/api/verify")
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    assert body["user"] is None


async def test_verify_garbage_token_returns_invalid(client):
    resp = await client.get(
        "/api/verify",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code == 200
    assert resp.json()["valid"] is False


async def test_verify_valid_token_via_bearer_header(
    client, active_user, active_user_token
):
    resp = await client.get(
        "/api/verify",
        headers={"Authorization": f"Bearer {active_user_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    user = body["user"]
    assert user["email"] == active_user.email
    assert user["name"] == active_user.name
    assert user["id"] == active_user.id
    assert "github" in user["providers"]


async def test_verify_valid_token_via_cookie(client, active_user, active_user_token):
    resp = await client.get(
        "/api/verify",
        headers={"Cookie": f"authgate_token={active_user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


async def test_verify_inactive_user_returns_invalid(client, inactive_user_token):
    resp = await client.get(
        "/api/verify",
        headers={"Authorization": f"Bearer {inactive_user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["valid"] is False


async def test_verify_response_includes_full_user_shape(
    client, active_user, active_user_token
):
    resp = await client.get(
        "/api/verify",
        headers={"Authorization": f"Bearer {active_user_token}"},
    )
    user = resp.json()["user"]
    assert "id" in user
    assert "email" in user
    assert "name" in user
    assert "avatar_url" in user
    assert "providers" in user
    assert "created_at" in user
    assert "last_login_at" in user


# ---------------------------------------------------------------------------
# /api/userinfo
# ---------------------------------------------------------------------------


async def test_userinfo_no_token_returns_401(client):
    resp = await client.get("/api/userinfo")
    assert resp.status_code == 401


async def test_userinfo_invalid_token_returns_401(client):
    resp = await client.get(
        "/api/userinfo",
        headers={"Authorization": "Bearer garbage"},
    )
    assert resp.status_code == 401


async def test_userinfo_valid_token_returns_user(
    client, active_user, active_user_token
):
    resp = await client.get(
        "/api/userinfo",
        headers={"Authorization": f"Bearer {active_user_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == active_user.email
    assert body["name"] == active_user.name
    assert "github" in body["providers"]


async def test_userinfo_via_cookie(client, active_user, active_user_token):
    resp = await client.get(
        "/api/userinfo",
        headers={"Cookie": f"authgate_token={active_user_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == active_user.email


async def test_userinfo_inactive_user_returns_401(client, inactive_user_token):
    resp = await client.get(
        "/api/userinfo",
        headers={"Authorization": f"Bearer {inactive_user_token}"},
    )
    assert resp.status_code == 401
