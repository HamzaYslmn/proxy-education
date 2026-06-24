"""Anonymous read — no login at all, just the publishable key. The anon key is public, so RLS
is the only wall; a loose SELECT policy hands the table to anyone.
"""
from core import blocked, line, rows

PHASE = "READ"
TITLE = "Anonymous read (no token):  private?select=data"


def run(ctx):
    d = ctx.get(ctx.direct, "private", None, select="data")
    line("DIRECT", d, f"LEAKED {len(rows(d))} rows with NO auth")
    p = ctx.get(ctx.proxy, "private", None, select="data")
    line("PROXY", p, "BLOCKED — token required" if blocked(p, 401) else "")
