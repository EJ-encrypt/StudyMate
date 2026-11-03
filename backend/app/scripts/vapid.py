"""Generate the VAPID key pair web push needs. Run once:

    python -m app.scripts.vapid

and copy both lines into the environment (Vercel project settings, and .env
for local use). Keep the private key secret; the public one is sent to
browsers. Changing the pair later invalidates every existing subscription.
"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def main() -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    private = key.private_numbers().private_value.to_bytes(32, "big")
    public = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    print(f"VAPID_PUBLIC_KEY={_b64url(public)}")
    print(f"VAPID_PRIVATE_KEY={_b64url(private)}")


if __name__ == "__main__":
    main()
