"""Minimal HS256 JWT generator — stdlib only, no PyJWT needed.

HS256 is what a Supabase *legacy* JWT secret signs with (anon / service_role tokens, and any
user token on an HS256 project). Newer projects sign user tokens with ES256 (asymmetric) — you
can't forge those without Supabase's private key, so this covers the HS256 case only.

    from modules.jwt.jwtgenerator import encode, supabase_token
    encode({"sub": "123", "role": "authenticated"}, secret)
    supabase_token(secret, sub="user-uuid", role="authenticated", ttl=3600)
"""
import base64
import hashlib
import hmac
import json
import time


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def encode(payload: dict, secret: str, alg: str = "HS256") -> str:
    if alg != "HS256":
        raise ValueError("only HS256 is supported")
    header = _b64(json.dumps({"alg": alg, "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header}.{body}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64(sig)}"


def supabase_token(secret: str, sub: str, role: str = "authenticated", ttl: int = 3600,
                   **extra) -> str:
    """A Supabase-shaped HS256 token: iss/sub/role/aud/iat/exp plus any extra claims."""
    now = int(time.time())
    return encode({
        "iss": "supabase", "sub": sub, "role": role, "aud": "authenticated",
        "iat": now, "exp": now + ttl, **extra,
    }, secret)


if __name__ == "__main__":
    secret = "patates"
    tok = supabase_token(secret, sub="00000000-0000-0000-0000-000000000001", email="neo@test.com")
    print(tok)

    # self-check: signature verifies and the payload round-trips
    h, b, s = tok.split(".")
    expect = _b64(hmac.new(secret.encode(), f"{h}.{b}".encode(), hashlib.sha256).digest())
    assert hmac.compare_digest(s, expect), "signature mismatch"
    pad = lambda x: x + "=" * (-len(x) % 4)
    claims = json.loads(base64.urlsafe_b64decode(pad(b)))
    assert claims["role"] == "authenticated" and claims["exp"] > claims["iat"]
    print("ok:", claims)
