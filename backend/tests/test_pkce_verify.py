"""Tests for PKCE code_verifier validation (RFC 7636 token-exchange check).

These exercise ``verify_pkce`` and the S256 challenge helper used to validate a
Keycloak authorization-code-flow-with-PKCE token request. All values are
synthetic; no real credentials or network calls are involved.
"""
import hashlib
import base64

from app.services.auth import (
    PKCE_CODE_CHALLENGE_METHOD,
    generate_pkce_pair,
    pkce_s256_challenge,
    verify_pkce,
)


def test_s256_challenge_matches_manual_computation():
    verifier = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRST0123456789-._~"
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    assert pkce_s256_challenge(verifier) == expected


def test_generated_pair_verifies():
    verifier, challenge = generate_pkce_pair()
    assert verify_pkce(verifier, challenge) is True


def test_wrong_verifier_fails():
    verifier, challenge = generate_pkce_pair()
    # Flip the verifier; challenge stays the one for the original.
    wrong = ("A" if verifier[0] != "A" else "B") + verifier[1:]
    assert verify_pkce(wrong, challenge) is False


def test_tampered_challenge_fails():
    verifier, challenge = generate_pkce_pair()
    tampered = ("A" if challenge[0] != "A" else "B") + challenge[1:]
    assert verify_pkce(verifier, tampered) is False


def test_unsupported_method_rejected():
    verifier, challenge = generate_pkce_pair()
    assert verify_pkce(verifier, challenge, method="plain") is False


def test_empty_verifier_rejected():
    verifier, challenge = generate_pkce_pair()
    assert verify_pkce(None, challenge) is False
    assert verify_pkce("", challenge) is False


def test_short_verifier_rejected():
    verifier, challenge = generate_pkce_pair()
    assert verify_pkce(verifier[:42], challenge) is False


def test_illegal_char_in_verifier_rejected():
    verifier, challenge = generate_pkce_pair()
    # RFC 7636 §4.1 verifier alphabet excludes space and '+'.
    assert verify_pkce(" " + verifier[1:], challenge) is False


def test_challenge_method_constant_is_s256():
    assert PKCE_CODE_CHALLENGE_METHOD == "S256"
