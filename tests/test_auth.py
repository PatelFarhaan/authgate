"""
E2E tests for /auth/{provider} start and OAuth callback flows.

External HTTP calls (GitHub token + user APIs) are intercepted by respx
so no real OAuth credentials are needed.
"""

import httpx
import respx

from app.jwt_handler import jwt_handler

GITHUB_CALLBACK = "/auth/github/callback"


def _state(redirect_url: str = "") -> str:
    return jwt_handler.create_state_token(redirect_url, "github")


# ---------------------------------------------------------------------------
# Auth start — /auth/{provider}
# ---------------------------------------------------------------------------


async def test_auth_start_unknown_provider_redirects_error(client):
    resp = await client.get("/auth/nonexistent", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "invalid_provider" in resp.headers["location"]


async def test_auth_start_github_redirects_to_authorize_url(client):
    resp = await client.get("/auth/github", follow_redirects=False)
    assert resp.status_code in (302, 307)
    loc = resp.headers["location"]
    assert "github.com/login/oauth/authorize" in loc
    assert "state=" in loc
    assert "client_id=test-github-client-id" in loc


async def test_auth_start_blocked_redirect_url(client):
    resp = await client.get(
        "/auth/github?redirect_url=http://evil.com/steal",
        follow_redirects=False,
    )
    assert resp.status_code in (302, 307)
    assert "invalid_redirect" in resp.headers["location"]


async def test_auth_start_allowed_redirect_url_forwarded_in_state(client):
    resp = await client.get(
        "/auth/github?redirect_url=http://localhost:3000/callback",
        follow_redirects=False,
    )
    assert resp.status_code in (302, 307)
    loc = resp.headers["location"]
    assert "github.com/login/oauth/authorize" in loc
    assert "state=" in loc


# ---------------------------------------------------------------------------
# OAuth callback — error / malformed input
# ---------------------------------------------------------------------------


async def test_callback_missing_code_and_state(client):
    resp = await client.get(GITHUB_CALLBACK, follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "missing_params" in resp.headers["location"]


async def test_callback_missing_code_only(client):
    resp = await client.get(
        GITHUB_CALLBACK,
        params={"state": _state()},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 307)
    assert "missing_params" in resp.headers["location"]


async def test_callback_invalid_state_token(client):
    resp = await client.get(
        GITHUB_CALLBACK,
        params={"code": "some-code", "state": "not-a-valid-jwt"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 307)
    assert "invalid_state" in resp.headers["location"]


async def test_callback_provider_error_passthrough(client):
    """Provider returns an error param — forwarded to login page."""
    resp = await client.get(
        GITHUB_CALLBACK,
        params={"error": "access_denied", "state": _state()},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 307)
    assert "access_denied" in resp.headers["location"]


# ---------------------------------------------------------------------------
# OAuth callback — happy paths (provider calls mocked with respx)
# ---------------------------------------------------------------------------


async def test_callback_new_user_gets_token_cookie_and_new_user_flag(client):
    state = _state("http://localhost:3000/callback")

    with respx.mock:
        respx.post("https://github.com/login/oauth/access_token").mock(
            return_value=httpx.Response(200, json={"access_token": "gh-test-token"})
        )
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": 99001,
                    "email": "newuser@example.com",
                    "name": "New User",
                    "avatar_url": "https://avatars.githubusercontent.com/u/99001",
                },
            )
        )

        resp = await client.get(
            GITHUB_CALLBACK,
            params={"code": "test-code", "state": state},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    loc = resp.headers["location"]
    assert "token=" in loc
    assert "new_user=true" in loc
    assert "authgate_token" in resp.cookies


async def test_callback_existing_user_no_new_user_flag(client, active_user):
    state = _state("http://localhost:3000/callback")

    with respx.mock:
        respx.post("https://github.com/login/oauth/access_token").mock(
            return_value=httpx.Response(200, json={"access_token": "gh-test-token"})
        )
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": 1001,
                    "email": active_user.email,
                    "name": active_user.name,
                    "avatar_url": active_user.avatar_url,
                },
            )
        )

        resp = await client.get(
            GITHUB_CALLBACK,
            params={"code": "test-code", "state": state},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    loc = resp.headers["location"]
    assert "token=" in loc
    assert "new_user=true" not in loc


async def test_callback_disabled_user_blocked(client, inactive_user):
    state = _state()

    with respx.mock:
        respx.post("https://github.com/login/oauth/access_token").mock(
            return_value=httpx.Response(200, json={"access_token": "gh-test-token"})
        )
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": 2001,
                    "email": inactive_user.email,
                    "name": inactive_user.name,
                    "avatar_url": "",
                },
            )
        )

        resp = await client.get(
            GITHUB_CALLBACK,
            params={"code": "test-code", "state": state},
            follow_redirects=False,
        )

    assert resp.status_code in (302, 307)
    assert "account_disabled" in resp.headers["location"]


async def test_callback_no_email_blocked(client):
    state = _state()

    with respx.mock:
        respx.post("https://github.com/login/oauth/access_token").mock(
            return_value=httpx.Response(200, json={"access_token": "gh-test-token"})
        )
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": 99002,
                    "email": None,
                    "name": "No Email User",
                    "avatar_url": "",
                },
            )
        )
        # GitHub falls back to the emails endpoint when email is null
        respx.get("https://api.github.com/user/emails").mock(
            return_value=httpx.Response(200, json=[])
        )

        resp = await client.get(
            GITHUB_CALLBACK,
            params={"code": "test-code", "state": state},
            follow_redirects=False,
        )

    assert resp.status_code in (302, 307)
    assert "no_email" in resp.headers["location"]


async def test_callback_provider_http_failure_returns_error(client):
    state = _state()

    with respx.mock:
        respx.post("https://github.com/login/oauth/access_token").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        resp = await client.get(
            GITHUB_CALLBACK,
            params={"code": "test-code", "state": state},
            follow_redirects=False,
        )

    assert resp.status_code in (302, 307)
    assert "provider_error" in resp.headers["location"]


async def test_callback_no_redirect_url_shows_authenticated_page(client):
    """When no redirect_url in state, user is sent to /login?authenticated=true."""
    state = _state("")  # no redirect URL

    with respx.mock:
        respx.post("https://github.com/login/oauth/access_token").mock(
            return_value=httpx.Response(200, json={"access_token": "gh-test-token"})
        )
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": 99003,
                    "email": "noredirect@example.com",
                    "name": "No Redirect User",
                    "avatar_url": "",
                },
            )
        )

        resp = await client.get(
            GITHUB_CALLBACK,
            params={"code": "test-code", "state": state},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    assert "authenticated=true" in resp.headers["location"]
