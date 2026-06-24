"""Edge Functions — Supabase exposes deployed functions at /functions/v1/<name>. The gateway is
public (each function is JWT-gated only if it opts in); attackers enumerate and invoke them with
crafted payloads. The proxy routes no /functions.
"""
from core import line, proxied

PHASE = "SURFACE"
TITLE = "Edge Functions:  POST /functions/v1/<name>"


def run(ctx):
    # No function name is known here (recon would find `functions.invoke('x')` in the JS); the probe
    # just shows the Functions gateway is exposed. Supply a real name to actually invoke one.
    d = ctx.send("POST", ctx.direct, "/functions/v1/_probe", ctx.token, json={})
    line("DIRECT", d, f"Functions gateway reachable (status {d.status_code if d is not None else '—'} — name a real function to invoke)")
    p = ctx.send("POST", ctx.proxy, "/functions/v1/_probe", ctx.token, json={})
    line("PROXY", p, "BLOCKED — /functions not routed" if not proxied(p) else "LEAKED via proxy?!")
