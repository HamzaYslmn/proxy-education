"""The OpenAPI root (GET /rest/v1/) maps every table, column and relationship — free recon."""
from core import line, proxied

PHASE = "RECON"
TITLE = "Schema dump:  GET /rest/v1/"


def run(ctx):
    d = ctx.send("GET", ctx.direct, "/rest/v1/", ctx.token)
    spec = d.json() if d is not None and d.status_code == 200 else {}
    tables = spec.get("definitions") or spec.get("components", {}).get("schemas") or {}
    line("DIRECT", d, f"OpenAPI exposed — {len(tables)} tables/columns enumerable")
    p = ctx.send("GET", ctx.proxy, "/rest/v1/", ctx.token)
    line("PROXY", p, "BLOCKED — root not exposed" if not proxied(p) else "LEAKED via proxy?!")
