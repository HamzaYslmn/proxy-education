# MARK: public table — world-readable profile. id = your auth uid, and also the FK into private.
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator

from middleware.middleware import RATE_LIMIT, limiter
from modules.supabase import supabase_proxy

from . import SCHEMA

TABLE = "public"

router = APIRouter(prefix=f"/db/rest/v1/{TABLE}", tags=[TABLE])
security = HTTPBearer(auto_error=False)


# MARK: GET — read profiles; embeds refused so you cannot pivot to private here
class GetQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    select: str = "data"
    id: str | None = Field(None, description="eq.<uuid>")
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)
    order: str | None = None

    @field_validator("select")
    @classmethod
    def _block_join(cls, v: str | None) -> str | None:
        """Stop PostgREST embedding (joins) — the exfiltration vector, e.g. select=data,private(*)."""
        if v and ("(" in v or ")" in v):
            raise ValueError("joins (embeds) are not allowed via the proxy")
        return v


@router.get("")
@limiter.limit(RATE_LIMIT)
async def get_public(
    request: Request,
    query: GetQuery = Query(...),
    _: HTTPAuthorizationCredentials | None = Depends(security),
):
    return await supabase_proxy(request, TABLE, query, schema=SCHEMA)


# MARK: POST — create the profile once at first login. id defaults to your uid in the DB
# (and RLS enforces id = auth.uid()), so the body carries only `data` — no id to spoof.
class PostQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    select: str = "data"

    @field_validator("select")
    @classmethod
    def _block_join(cls, v: str | None) -> str | None:
        """Stop PostgREST embedding (joins) on the insert's returned representation."""
        if v and ("(" in v or ")" in v):
            raise ValueError("joins (embeds) are not allowed via the proxy")
        return v


class PublicData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str
    registered_at: str


class PostBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data: PublicData


@router.post("")
@limiter.limit(RATE_LIMIT)
async def create_public(
    request: Request,
    body: PostBody,
    query: PostQuery = Query(...),
    _: HTTPAuthorizationCredentials | None = Depends(security),
):
    if not request.state.user_uid:
        raise HTTPException(401, "Authentication required")
    return await supabase_proxy(request, TABLE, query, body, SCHEMA)
