# MARK: private table — notes. id = your auth uid. The proxy forces id = request.state.user_uid,
# so even with the deliberately-broken "select using(true)" RLS, the proxy only returns YOUR row.
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator

from middleware.middleware import RATE_LIMIT, limiter
from modules.supabase import supabase_proxy

from . import SCHEMA

TABLE = "private"

router = APIRouter(prefix=f"/db/rest/v1/{TABLE}", tags=[TABLE])
security = HTTPBearer(auto_error=False)


class PrivateData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    notes: str = ""


# MARK: GET — own row only (id is forced to the caller's uid)
class GetQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    select: str = "data"
    id: str | None = Field(None, description="forced to your uid")
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)
    order: str | None = None

    @field_validator("select")
    @classmethod
    def _block_join(cls, v: str | None) -> str | None:
        """Stop PostgREST embedding (joins) — the exfiltration vector, e.g. select=data,public(*)."""
        if v and ("(" in v or ")" in v):
            raise ValueError("joins (embeds) are not allowed via the proxy")
        return v


@router.get("")
@limiter.limit(RATE_LIMIT)
async def get_private(
    request: Request,
    query: GetQuery = Query(...),
    _: HTTPAuthorizationCredentials | None = Depends(security),
):
    uid = request.state.user_uid
    if not uid:
        raise HTTPException(401, "Authentication required")
    query.id = f"eq.{uid}"  # 🔒 ignore client filter; scope to caller
    return await supabase_proxy(request, TABLE, query, schema=SCHEMA)


# MARK: POST — create the notes row once at first login. id defaults to your uid in the DB
# (and RLS enforces id = auth.uid()), so the body carries only `data`.
class PostQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    select: str = "id"

    @field_validator("select")
    @classmethod
    def _block_join(cls, v: str | None) -> str | None:
        """Stop PostgREST embedding (joins) on the insert's returned representation."""
        if v and ("(" in v or ")" in v):
            raise ValueError("joins (embeds) are not allowed via the proxy")
        return v


class PostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data: PrivateData


@router.post("")
@limiter.limit(RATE_LIMIT)
async def create_private(
    request: Request,
    body: PostBody,
    query: PostQuery = Query(...),
    _: HTTPAuthorizationCredentials | None = Depends(security),
):
    if not request.state.user_uid:
        raise HTTPException(401, "Authentication required")
    return await supabase_proxy(request, TABLE, query, body, SCHEMA)


# MARK: PATCH — save notes on your own row (id forced to your uid)
class PatchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str | None = Field(None, description="forced to your uid")
    select: str | None = None

    @field_validator("select")
    @classmethod
    def _block_join(cls, v: str | None) -> str | None:
        """Stop PostgREST embedding (joins) on the update's returned representation."""
        if v and ("(" in v or ")" in v):
            raise ValueError("joins (embeds) are not allowed via the proxy")
        return v


class PatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data: PrivateData


@router.patch("")
@limiter.limit(RATE_LIMIT)
async def update_private(
    request: Request,
    body: PatchBody,
    query: PatchQuery = Query(...),
    _: HTTPAuthorizationCredentials | None = Depends(security),
):
    uid = request.state.user_uid
    if not uid:
        raise HTTPException(401, "Authentication required")
    query.id = f"eq.{uid}"  # 🔒 can only patch your own row
    return await supabase_proxy(request, TABLE, query, body, SCHEMA)
