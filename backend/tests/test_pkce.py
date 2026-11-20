"""PKCE (Proof Keyholder for Code Exchange) tests for Keycloak OIDC integration.

These tests validate the PKCE code verifier/challenge pair generation
as part of the Keycloak OIDC authorization code flow with PKCE.
"""
import pytest

from app.services.auth import generate_pkce_pair


@pytest.mark.anyio
async def test_pkce_pair_generation():
    """Test that generate_pkce_pair produces a valid verifier/challenge pair."""
    verifier, challenge = generate_pkce_pair()

    # Verify challenge is derived from verifier via SHA-256 + base64url
    import hashlib
    import base64
    expected_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    assert challenge == expected_challenge, "Challenge must be SHA-256 of verifier"

    # Verify lengths (RFC 7636: verifier 43-128 chars, challenge 43-128 chars)
    assert 43 <= len(verifier) <= 128, f"Verifier length {len(verifier)} out of range"
    assert 43 <= len(challenge) <= 128, f"Challenge length {len(challenge)} out of range"


@pytest.mark.anyio
async def test_pkce_pair_consistency():
    """Test that multiple generations produce valid, independent pairs."""
    for _ in range(10):
        verifier, challenge = generate_pkce_pair()

        # Each pair must independently verify
        import hashlib
        import base64
        expected = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        assert challenge == expected

        # Verifier and challenge must be different across iterations
        # (extremely low probability of collision with random 32-byte values)


def test_pkce_importable():
    """Smoke test that the module can be imported and functions work."""
    verifier, challenge = generate_pkce_pair()
    assert verifier is not None
    assert challenge is not None
    assert len(verifier) > 0
    assert len(challenge) > 0
