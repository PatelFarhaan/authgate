async def test_health_returns_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "AuthGate Test"
    assert "version" in body


async def test_jwks_returns_rsa_key(client):
    resp = await client.get("/.well-known/jwks.json")
    assert resp.status_code == 200
    jwks = resp.json()
    assert "keys" in jwks
    assert len(jwks["keys"]) == 1
    key = jwks["keys"][0]
    assert key["kty"] == "RSA"
    assert key["alg"] == "RS256"
    assert key["use"] == "sig"
    assert "n" in key and "e" in key and "kid" in key


async def test_jwks_endpoint_serves_consumable_key(client, active_user_token):
    """Contract test: external JWKS consumers (e.g. apps verifying AuthGate
    tokens via /.well-known/jwks.json) must be able to (a) parse the served
    key, (b) match its kid to the kid embedded in tokens AuthGate issues, and
    (c) verify those tokens against the JWKS-derived public key."""
    import base64
    import re

    import jwt

    jwks = (await client.get("/.well-known/jwks.json")).json()
    key = jwks["keys"][0]

    assert key["alg"] == "RS256"
    assert key["kty"] == "RSA"
    assert key["use"] == "sig"
    assert key["kid"]

    # n and e must be unpadded base64url (RFC 7518 §6.3.1).
    b64url = re.compile(r"^[A-Za-z0-9_-]+$")
    for field in ("n", "e"):
        assert b64url.match(key[field]), f"{field} is not base64url"
        # Must be decodable with urlsafe_b64decode after re-padding.
        padded = key[field] + "=" * (-len(key[field]) % 4)
        base64.urlsafe_b64decode(padded)

    # kid in JWKS must match the kid header of issued tokens.
    header = jwt.get_unverified_header(active_user_token)
    assert header["kid"] == key["kid"]

    # A real issued token verifies against the JWKS-derived public key.
    public_key = jwt.PyJWK(key).key
    decoded = jwt.decode(
        active_user_token, public_key, algorithms=["RS256"], issuer="authgate"
    )
    assert decoded["sub"]
