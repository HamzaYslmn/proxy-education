"""Register the demo cast so cross-user leaks have victims to steal from."""
import httpx

from core import Ctx, sub

# 3 users, each with a private note.
USERS = [
    ("neo@test.com", "test1234", "neo", "the cake is a lie"),
    ("trinity@test.com", "test1234", "trinity", "follow the white rabbit"),
    ("morpheus@test.com", "test1234", "morpheus", "there is no spoon"),
]


def auth_token(ctx: Ctx, email: str, password: str) -> str:
    """Sign in; if the user doesn't exist yet, sign up. Returns an access_token."""
    for path in ("token?grant_type=password", "signup"):
        r = httpx.post(f"{ctx.direct}/auth/v1/{path}", headers={"apikey": ctx.key},
                       json={"email": email, "password": password}, timeout=15)
        if r.status_code == 200 and "access_token" in r.json():
            return r.json()["access_token"]
    raise SystemExit(f"could not auth {email} — turn OFF email confirmation in your Supabase project")


def register(ctx: Ctx, users=USERS) -> int:
    """Sign up/in each user and seed a public+private row. Sets ctx.token/ctx.me to the first user."""
    first = None
    for email, password, username, notes in users:
        token = auth_token(ctx, email, password)
        uid = sub(token)
        # id defaults to auth.uid() in the DB; conflicts (already seeded) are ignored.
        ctx.send("POST", ctx.direct, "/rest/v1/public", token,
                 json={"data": {"username": username, "registered_at": "2026-06-25T00:00:00Z"}})
        ctx.send("POST", ctx.direct, "/rest/v1/private", token, json={"data": {"notes": notes}})
        first = first or (token, uid)
    ctx.token, ctx.me = first
    return len(users)
