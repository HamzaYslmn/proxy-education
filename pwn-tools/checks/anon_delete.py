"""Anon write — with RLS off, the anon role's default grants apply, so anyone can DELETE the `logs`
table. An impossible filter (id=eq.-1) means nothing is actually removed; we only probe the
permission. The proxy doesn't route `logs` at all.
"""
from core import blocked, line, proxied

PHASE = "TAMPER"
TITLE = "Anon DELETE on logs:  DELETE /rest/v1/logs?id=eq.-1  (no auth)"


def run(ctx):
    d = ctx.send("DELETE", ctx.direct, "/rest/v1/logs?id=eq.-1", None)
    line("DIRECT", d, "anon CAN delete — RLS off, no policy" if blocked(d, 200, 204) else "")
    p = ctx.send("DELETE", ctx.proxy, "/rest/v1/logs?id=eq.-1", None)
    line("PROXY", p, "BLOCKED — table not routed" if not proxied(p) else "LEAKED via proxy?!")
