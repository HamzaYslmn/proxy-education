"""JOIN / resource embedding — reach `private` THROUGH `public` via the foreign key. The proxy's
select validator rejects any parenthesised embed (422).
"""
from core import blocked, line, rows

PHASE = "PIVOT"
TITLE = "JOIN embedding:  public?select=*,private(*)"


def run(ctx):
    d = ctx.get(ctx.direct, "public", ctx.token, select="*,private(*)")
    # The computed relationship returns `setof private`, so PostgREST embeds it as a list per row.
    embedded = [p for row in rows(d) for p in (row.get("private") or [])]
    leaked = [(p.get("data") or {}).get("notes") for p in embedded]
    line("DIRECT", d, f"LEAKED {len(leaked)} users' notes: {leaked}")
    p = ctx.get(ctx.proxy, "public", ctx.token, select="*,private(*)")
    line("PROXY", p, "BLOCKED — embeds refused" if blocked(p, 422) else "")
