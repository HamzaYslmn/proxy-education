"""Unfiltered read — the client picks the filter, so with no filter the whole table comes back.
The proxy forces id = your uid, so the same request returns only your row.
"""
from core import line, rows

PHASE = "READ"
TITLE = "Unfiltered dump:  private?select=data"


def run(ctx):
    d = ctx.get(ctx.direct, "private", ctx.token, select="data")
    line("DIRECT", d, f"LEAKED {len(rows(d))} rows: {[x['data'].get('notes') for x in rows(d)]}")
    p = ctx.get(ctx.proxy, "private", ctx.token, select="data")
    line("PROXY", p, f"{len(rows(p))} row — only yours (filter forced to your uid)")
