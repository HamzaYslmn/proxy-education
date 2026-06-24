# ./middleware/middleware.py
import time

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from modules.supabase import verify_token

# Per-route, per-IP limit. Applied via @limiter.limit(RATE_LIMIT) on the proxy handlers.
RATE_LIMIT = "10/minute"
limiter = Limiter(key_func=get_remote_address)


async def _resolve_user(request: Request) -> None:
    """Read the Bearer JWT, verify it with Supabase, and stash uid/token on request.state.
    Leaves them None on any miss — auth is optional here; routes raise 401 as needed."""
    request.state.user_uid = None
    request.state.token = None
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return
    token = auth[7:].strip()
    if token.count(".") != 2:
        return
    try:
        uid = await verify_token(token)
    except Exception:
        return
    if uid:
        request.state.user_uid = uid
        request.state.token = token


def add_middlewares(app):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def enforce_request_policies(request: Request, call_next):
        await _resolve_user(request)  # sets request.state.user_uid / token from the Supabase JWT
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Process-Time"] = f"{time.perf_counter() - start:0.4f}"
        return response
