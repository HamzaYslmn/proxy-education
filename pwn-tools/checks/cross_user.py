"""Cross-user read — ask for someone else's row by id (IDOR). The proxy overwrites any id
filter with eq.<your uid>, so you can never name another victim.
"""
from core import line, rows

PHASE = "READ"
TITLE = "Cross-user read:  private?id=eq.<victim>"


def run(ctx):
    others = [x["id"] for x in rows(ctx.get(ctx.direct, "private", ctx.token, select="id,data")) if x.get("id") != ctx.me]
    victim = others[0] if others else ctx.me
    d = ctx.get(ctx.direct, "private", ctx.token, select="data", id=f"eq.{victim}")
    line("DIRECT", d, f"victim {victim[:8]}…  notes: {[x['data'].get('notes') for x in rows(d)]}")
    p = ctx.get(ctx.proxy, "private", ctx.token, select="data", id=f"eq.{victim}")
    line("PROXY", p, f"got your own row, not the victim's: {[x['data'].get('notes') for x in rows(p)]}")
