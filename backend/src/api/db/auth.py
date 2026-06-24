# MARK: Auth proxy — forwards /db/auth/v1/* to Supabase GoTrue (signup, token, user, logout…)
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from middleware.middleware import RATE_LIMIT, limiter
from modules.supabase import auth_proxy

router = APIRouter(prefix="/db/auth/v1", tags=["auth"])
security = HTTPBearer(auto_error=False)

_WRITE = ("POST", "PUT", "PATCH")


async def _body(request: Request):
    """Parse JSON body for write methods, if present."""
    if request.method in _WRITE and int(request.headers.get("content-length", "0")) > 0:
        try:
            return await request.json()
        except Exception:
            return None
    return None


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@limiter.limit(RATE_LIMIT)
async def auth_catch_all(
    path: str,
    request: Request,
    _: HTTPAuthorizationCredentials | None = Depends(security),
):
    qs = urlencode(dict(request.query_params))
    url = f"/{path}" + (f"?{qs}" if qs else "")
    return await auth_proxy(request, url, await _body(request))
