# MARK: Supabase proxy — aiohttp raw HTTP forwarding (PUBLISHABLE_KEY only)
import os
from urllib.parse import urlencode

import aiohttp
from fastapi import HTTPException, Request
from fastapi.responses import Response

from middleware import log

# MARK: Configuration (public key only — SERVICE_KEY stays in client.py)
URL = os.getenv("SUPABASE_URL", "")
PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
DOMAIN = URL.split("//")[1].split("/")[0] if URL else ""

_SKIP_REQ = frozenset(
    ["content-length", "accept-encoding", "host", "transfer-encoding", "connection"]
)
_SKIP_RESP = frozenset(
    ["transfer-encoding", "content-encoding", "content-length", "connection"]
)
_WRITE_METHODS = frozenset(["POST", "PATCH", "PUT"])

# MARK: Session management
_session: aiohttp.ClientSession | None = None


async def get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
    return _session


async def close_session():
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None


# MARK: Error logging
def _log_error(method: str, url: str, status: int = None, body=None, response: bytes = None, error: str = None):
    msg = f"[PROXY] {method} {url}"
    if status:
        msg += f" -> {status}"
    if body:
        msg += "\n  REQ: [REDACTED]" if "/auth/v1/" in url else f"\n  REQ: {body}"
    if response:
        msg += f"\n  RES: {response.decode(errors='ignore')}"
    if error:
        msg += f"\n  ERR: {error}"
    log.error(msg)


def _is_valid_jwt(auth_header: str) -> bool:
    return auth_header.startswith("Bearer ") and auth_header[7:].count(".") == 2


# MARK: Upstream headers — pass the caller's through (minus hop-by-hop), then force the ones we
# must own: host, apikey, schema. Confidentiality lives in the query guards, not the headers.
def _build_headers(request: Request, schema: str) -> dict[str, str]:
    headers = {k: v for k, v in request.headers.items() if k.lower() not in _SKIP_REQ}
    headers["host"] = DOMAIN
    headers["apikey"] = PUBLISHABLE_KEY
    headers["content-profile"] = schema
    headers["accept-profile"] = schema
    if not _is_valid_jwt(headers.get("authorization", "")):
        headers.pop("authorization", None)  # anon (apikey only)
    return headers


# MARK: Core — low-level HTTP forwarding (PUBLISHABLE_KEY + user JWT)
async def _forward(
    api: str,
    request: Request,
    path: str,
    body: dict = None,
    schema: str = "public",
) -> Response:
    url = f"{URL}/{api}/v1/{path.lstrip('/')}"

    headers = _build_headers(request, schema)

    session = await get_session()
    method = request.method
    json_body = body if method in _WRITE_METHODS else None

    try:
        async with session.request(
            method, url, json=json_body, headers=headers, allow_redirects=False
        ) as resp:
            content = await resp.read()
            status = resp.status

            if status >= 400:
                _log_error(method, url, status, body=json_body, response=content)

            resp_headers = {
                k: v for k, v in resp.headers.items() if k.lower() not in _SKIP_RESP
            }
            return Response(
                content=content,
                status_code=status,
                headers=resp_headers,
                media_type=resp_headers.get("content-type"),
            )

    except aiohttp.ClientError as e:
        _log_error(method, url, body=json_body, error=str(e))
        raise HTTPException(status_code=502, detail="Proxy failed")
    except Exception as e:
        _log_error(method, url, body=json_body, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# MARK: REST proxy — shorthand for table operations
async def supabase_proxy(
    request: Request,
    table: str,
    query=None,
    body=None,
    schema: str = "public",
) -> Response:
    """Proxy REST request. Accepts Pydantic models for query/body."""
    query_dict = (
        query.model_dump(exclude_none=True, by_alias=True)
        if hasattr(query, "model_dump")
        else (query or {})
    )
    body_dict = (
        body.model_dump(exclude_none=True, by_alias=True)
        if hasattr(body, "model_dump")
        else body
    )

    query_string = urlencode(query_dict, doseq=True)
    path = f"/{table}?{query_string}" if query_string else f"/{table}"

    return await _forward("rest", request, path, body_dict, schema)


# MARK: Auth proxy — raw redirect to Supabase GoTrue
async def auth_proxy(request: Request, path: str, body: dict = None) -> Response:
    """Proxy request to Supabase GoTrue Auth API."""
    return await _forward("auth", request, path, body)
