"""Verify the access tokens Supabase Auth issues.

Sign-up, sign-in, password resets and email confirmation all happen between
the browser and Supabase; the API never sees a password. It only checks that
a request carries a token Supabase signed, and reads who it belongs to.

Supabase signs with one of two schemes depending on the project's age:
asymmetric keys (ES256/RS256) published at a JWKS endpoint, which is the
default for new projects, or a legacy shared secret (HS256). Both are
accepted so either kind of project works without a code change.
"""

from functools import lru_cache
from typing import Any

import jwt

from app.core.config import settings

_AUDIENCE = "authenticated"
_ASYMMETRIC = ("ES256", "RS256")


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    # Keys are cached in-process, so verification costs a network call only
    # on a cold start or when Supabase rotates its signing key.
    return jwt.PyJWKClient(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json",
        cache_keys=True,
        lifespan=3600,
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Return the token's claims, or None if it is not a valid Supabase token."""
    try:
        algorithm = jwt.get_unverified_header(token).get("alg")
        if algorithm == "HS256":
            if not settings.supabase_jwt_secret:
                return None
            key: Any = settings.supabase_jwt_secret
        elif algorithm in _ASYMMETRIC and settings.supabase_url:
            key = _jwks_client().get_signing_key_from_jwt(token).key
        else:
            return None
        return jwt.decode(token, key, algorithms=[algorithm], audience=_AUDIENCE)
    except (jwt.PyJWTError, jwt.PyJWKClientError):
        return None
