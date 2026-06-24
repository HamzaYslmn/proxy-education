"""Unbounded page size — scrape the whole table in one request. The proxy caps limit at 100 (422)."""
from core import blocked, line, rows

PHASE = "SCALE"
TITLE = "Oversized limit:  public?limit=100000"


def run(ctx):
    d = ctx.get(ctx.direct, "public", ctx.token, select="data", limit=100000)
    line("DIRECT", d, f"returned {len(rows(d))} rows in one shot (only PostgREST's db-max-rows caps it)")
    p = ctx.get(ctx.proxy, "public", ctx.token, select="data", limit=100000)
    line("PROXY", p, "BLOCKED — limit capped at 100" if blocked(p, 422) else "")
