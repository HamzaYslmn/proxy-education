"""Count leak — Prefer: count=exact returns the EXACT total in the Content-Range header, no rows
read. Direct counts the whole table; the proxy forces id = your uid, so you only count your own.
"""
from core import line, total

PHASE = "SCALE"
TITLE = "Count leak:  private?select=id  (Prefer: count=exact)"


def run(ctx):
    hdr = {"Prefer": "count=exact"}
    d = ctx.send("GET", ctx.direct, "/rest/v1/private?select=id", ctx.token, headers=hdr)
    line("DIRECT", d, f"total private rows = {total(d)} (everyone's)")
    p = ctx.send("GET", ctx.proxy, "/rest/v1/private?select=id", ctx.token, headers=hdr)
    line("PROXY", p, f"count = {total(p)} — only yours (filter forced to your uid)")
