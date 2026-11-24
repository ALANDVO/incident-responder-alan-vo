from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings
import base64
import hashlib
import os
import secrets


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify a JWT token and return the payload."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


class TokenData:
    def __init__(self, user_id: int, email: str, roles: list[str]):
        self.user_id = user_id
        self.email = email
        self.roles = roles


# ---------------------------------------------------------------------------
# Keycloak OIDC PKCE support
# ---------------------------------------------------------------------------

# RFC 7636 §4.2/§4.3: only "S256" (SHA-256) is a mandatory-to-implement method.
PKCE_CODE_CHALLENGE_METHOD = "S256"

# RFC 7636 §4.1: code_verifier is 43-128 chars of [A-Z a-z 0-9 - . _ ~].
_VERIFIER_ALLOWED = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
)


def pkce_s256_challenge(code_verifier: str) -> str:
    """Compute the S256 code challenge for a code verifier (RFC 7636 §4.2).

    challenge = BASE64URL-ENCODE(SHA256(ASCII(code_verifier)))
    """
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def generate_pkce_pair() -> Tuple[str, str]:
    """Generate a PKCE code verifier and its S256 code challenge.

    Returns:
        Tuple of (code_verifier, code_challenge)
        - code_verifier: 43-char base64url string drawn from 32 random bytes
        - code_challenge: S256 (SHA-256 + base64url) hash of the verifier
    """
    verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
    return verifier, pkce_s256_challenge(verifier)


def verify_pkce(
    code_verifier: Optional[str],
    code_challenge: str,
    method: str = PKCE_CODE_CHALLENGE_METHOD,
) -> bool:
    """Validate a PKCE code_verifier against the stored code_challenge.

    Mirrors the check an authorization server performs during the token
    exchange: recompute the challenge from the supplied verifier and compare
    in constant time. Returns ``False`` for malformed input rather than
    raising, so callers can map the result to an opaque ``invalid_grant``
    response without leaking verifier state.

    Args:
        code_verifier: Verifier echoed by the client in the token request.
        code_challenge: Challenge stored from the authorization request.
        method: PKCE challenge method; only ``S256`` is supported.

    Returns:
        True if the verifier hashes to the challenge, else False.
    """
    if method != PKCE_CODE_CHALLENGE_METHOD:
        return False
    if not code_verifier or not code_challenge:
        return False
    if not (43 <= len(code_verifier) <= 128):
        return False
    if any(ch not in _VERIFIER_ALLOWED for ch in code_verifier):
        return False
    try:
        expected = pkce_s256_challenge(code_verifier)
    except (UnicodeEncodeError, ValueError):
        return False
    # Constant-time compare to avoid timing oracle on the challenge.
    return secrets.compare_digest(expected, code_challenge)


# end of Keycloak OIDC PKCE support
