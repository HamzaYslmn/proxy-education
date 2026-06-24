"""RPC bypass — a SECURITY DEFINER function runs as its owner and ignores RLS entirely, so one
exposed /rpc/ helper leaks everything regardless of policy. The proxy never routes /rpc.
"""
from core import line, proxied, rows

PHASE = "PIVOT"
TITLE = "RPC bypass:  POST /rest/v1/rpc/all_notes"


def run(ctx):
    d = ctx.send("POST", ctx.direct, "/rest/v1/rpc/all_notes", ctx.token, json={})
    line("DIRECT", d, f"LEAKED {len(rows(d))} notes via the function (RLS bypassed)")
    p = ctx.send("POST", ctx.proxy, "/rest/v1/rpc/all_notes", ctx.token, json={})
    line("PROXY", p, "BLOCKED — /rpc not routed" if not proxied(p) else "LEAKED via proxy?!")
