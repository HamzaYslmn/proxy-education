"""Arbitrary filter operators — direct exposes PostgREST's whole operator set (or/like/not/in/…),
the surface for enumeration & boolean oracles. The proxy accepts only its typed params (422).
"""
from core import blocked, line, rows

PHASE = "SCALE"
TITLE = "Filter operators:  public?or=(...)"


def run(ctx):
    d = ctx.get(ctx.direct, "public", ctx.token, select="data", **{"or": f"(id.eq.{ctx.me},id.eq.{ctx.me})"})
    line("DIRECT", d, f"arbitrary boolean filters run ({len(rows(d))} row(s))")
    p = ctx.get(ctx.proxy, "public", ctx.token, select="data", **{"or": f"(id.eq.{ctx.me})"})
    line("PROXY", p, "BLOCKED — only typed params allowed" if blocked(p, 422) else "")
