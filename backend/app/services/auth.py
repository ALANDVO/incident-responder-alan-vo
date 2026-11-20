from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings
import base64
import hashlib
import os


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

def generate_pkce_pair() -> Tuple[str, str]:
    """Generate a PKCE code verifier and code challenge pair.

    Returns:
        Tuple of (code_verifier, code_challenge)
        - code_verifier: random 32-byte base64url-encoded string (88 chars)
        - code_challenge: SHA-256 hash of verifier, base64url-encoded (43 chars)
    """
    verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
    # SHA-256 hash of the verifier, base64url-encoded
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    return verifier, challenge


def pkce_code_verifier_from_challenge(challenge: str) -> Optional[str]:
    """Recover the code verifier from a code challenge (not recommended; store it server-side).

    This is provided for completeness only; in practice the verifier should be stored
    in the session and never reconstructed from the challenge.
    """
    # Cannot reliably reverse SHA-256; return None
    return None

# end of Keycloak OIDC PKCE support
