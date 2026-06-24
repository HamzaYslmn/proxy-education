# MARK: Supabase client — admin-only (service role for backend operations)
import os

import httpx
from supabase import AClient as AsyncClient, AsyncClientOptions, create_async_client

from middleware import log

URL: str = os.getenv("SUPABASE_URL", "")
SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
DB_STORAGE: str = "default"
DB_SCHEMAS: list[str] = ["public"]

if not URL or not SERVICE_KEY:
    msg = "Supabase credentials missing: check .env"
    log.critical(msg)
    raise RuntimeError(msg)

# MARK: Admin clients — SERVICE_KEY, RLS bypassed (for backend operations)
_c: dict[str, AsyncClient] = {}


def _pool(key: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=f"{URL}/rest/v1",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        http2=True,
        limits=httpx.Limits(max_connections=500, max_keepalive_connections=100),
        timeout=30.0,
        follow_redirects=True,
    )


# MARK: Eager init — call at startup
async def init():
    from .proxy import close_session  # noqa: F401

    for schema in DB_SCHEMAS:
        k = f"admin:{schema}"
        if k not in _c:
            opts = AsyncClientOptions(schema=schema, httpx_client=_pool(SERVICE_KEY))
            _c[k] = await create_async_client(URL, SERVICE_KEY, options=opts)
    log.info(f"Supabase admin clients initialized for schemas: {DB_SCHEMAS}")


# MARK: Admin getter (service role, RLS bypassed)
def _db(schema: str = "public") -> AsyncClient:
    return _c[f"admin:{schema}"]
