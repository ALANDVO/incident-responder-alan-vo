"""Authentication and authorization tests.

Covers the two contract-required security cases:
  * unauthenticated rejection on a data endpoint
  * role denial for an over-privileged attempt
The auth here is local JWT (Keycloak/OIDC is a tracked roadmap item).
"""
import pytest

from tests.conftest import bearer


@pytest.mark.anyio
async def test_register_returns_user_without_password(client):
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "password": "Password123!",
            "full_name": "Admin User",
            "role": "admin",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "admin@example.com"
    assert body["role"] == "admin"
    # Password must never be persisted in the read model.
    assert "password" not in body
    assert "hashed_password" not in body


@pytest.mark.anyio
async def test_register_rejects_short_password(client):
    resp = await client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "123", "role": "viewer"},
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_register_rejects_duplicate_email(client):
    payload = {
        "email": "dupe@example.com",
        "password": "Password123!",
        "role": "viewer",
    }
    first = await client.post("/api/auth/register", json=payload)
    assert first.status_code == 201
    second = await client.post("/api/auth/register", json=payload)
    assert second.status_code == 400


@pytest.mark.anyio
async def test_login_returns_bearer_token(client):
    await client.post(
        "/api/auth/register",
        json={
            "email": "alice@example.com",
            "password": "Password123!",
            "role": "operator",
        },
    )
    resp = await client.post(
        "/api/auth/login",
        data={"username": "alice@example.com", "password": "Password123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 0


@pytest.mark.anyio
async def test_login_rejects_bad_credentials(client):
    resp = await client.post(
        "/api/auth/login",
        data={"username": "nobody@example.com", "password": "wrong"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_me_rejects_unauthenticated(client):
    """Unauthenticated rejection on a protected endpoint."""
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_me_returns_current_user(client, auth_token):
    token = await auth_token(email="alice@example.com", role="operator")
    resp = await client.get("/api/auth/me", headers=bearer(token))
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"
    assert resp.json()["role"] == "operator"


@pytest.mark.anyio
async def test_role_denial_on_write(client, auth_token):
    """Role denial: a viewer must not create incidents (operator+ only)."""
    token = await auth_token(email="viewer@example.com", role="viewer")
    resp = await client.post(
        "/api/incidents",
        json={"title": "x" * 20, "description": "should be forbidden"},
        headers=bearer(token),
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_unauthenticated_rejected_on_incidents(client):
    resp = await client.get("/api/incidents")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_tampered_token_rejected(client):
    resp = await client.get(
        "/api/incidents", headers={"Authorization": "Bearer not.a.real.token"}
    )
    assert resp.status_code == 401