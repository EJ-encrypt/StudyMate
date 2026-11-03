"""Stand-ins for Supabase Auth in tests.

The API only verifies tokens; accounts are created in Supabase. Tests mint
tokens shaped like Supabase's (HS256 with the project secret, audience
"authenticated") so every request runs through the real verification and
first-request provisioning code.
"""

import time
import uuid

import jwt

TEST_JWT_SECRET = "test-supabase-jwt-secret-that-is-long-enough"


def user_id_for(email: str) -> uuid.UUID:
    # Deterministic, so the same email is the same account across requests.
    return uuid.uuid5(uuid.NAMESPACE_URL, f"studymate-test:{email}")


def token_for(email: str, full_name: str = "Test Student", **overrides) -> str:
    claims = {
        "sub": str(user_id_for(email)),
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": int(time.time()) + 3600,
        "user_metadata": {"full_name": full_name},
    }
    claims.update(overrides)
    return jwt.encode(claims, TEST_JWT_SECRET, algorithm="HS256")


def auth_headers(email: str, full_name: str = "Test Student") -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(email, full_name)}"}
