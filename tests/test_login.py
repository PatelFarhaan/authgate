async def test_root_redirects_to_login(client):
    resp = await client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"].endswith("/login")


async def test_login_page_renders_html(client):
    resp = await client.get("/login")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "AuthGate" in resp.text


async def test_login_page_shows_github_provider(client):
    resp = await client.get("/login")
    assert resp.status_code == 200
    # GitHub is the only configured provider in authgate.test.yaml
    assert "github" in resp.text.lower()


async def test_login_dark_theme_param(client):
    resp = await client.get("/login?theme=dark")
    assert resp.status_code == 200
    assert "dark" in resp.text


async def test_login_light_theme_param(client):
    resp = await client.get("/login?theme=light")
    assert resp.status_code == 200
    assert "light" in resp.text


async def test_login_account_disabled_error(client):
    resp = await client.get("/login?error=account_disabled")
    assert resp.status_code == 200
    assert "disabled" in resp.text


async def test_logout_clears_cookie_and_redirects(client):
    resp = await client.get("/logout", follow_redirects=False)
    assert resp.status_code in (302, 307)
    # Cookie should be deleted (set with max-age=0 or expires in the past)
    set_cookie = resp.headers.get("set-cookie", "")
    assert "authgate_token" in set_cookie
