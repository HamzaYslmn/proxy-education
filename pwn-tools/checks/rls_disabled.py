"""RLS-disabled table — `logs` never had RLS enabled (the #1 Supabase mistake). With RLS off the
anon role's default grants apply directly, so it reads with no token. The proxy doesn't route it.
"""
from core import line, proxied, rows

PHASE = "READ"
TITLE = "RLS-disabled table:  logs?select=*  (no auth)"


def run(ctx):
    d = ctx.get(ctx.direct, "logs", None, select="*")
    line("DIRECT", d, f"LEAKED {len(rows(d))} rows from an unprotected table: {[x.get('message') for x in rows(d)]}")
    p = ctx.get(ctx.proxy, "logs", None, select="*")
    line("PROXY", p, "BLOCKED — table not routed" if not proxied(p) else "LEAKED via proxy?!")
