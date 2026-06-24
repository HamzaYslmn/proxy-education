"""Storage buckets — Supabase exposes the Storage API at /storage/v1/*. Anyone with the anon key
can enumerate buckets and probe object read/write permissions. The proxy routes only the DB, so
/storage is unreachable through it.
"""
from core import line, proxied

PHASE = "SURFACE"
TITLE = "Storage buckets:  GET /storage/v1/bucket"


def run(ctx):
    d = ctx.send("GET", ctx.direct, "/storage/v1/bucket", ctx.token)
    if d is not None and d.status_code == 200 and isinstance(d.json(), list):
        extra = f"Storage API reachable — {len(d.json())} bucket(s) visible to your role"
    else:
        extra = f"Storage API reachable (status {d.status_code if d is not None else '—'})"
    line("DIRECT", d, extra)
    p = ctx.send("GET", ctx.proxy, "/storage/v1/bucket", ctx.token)
    line("PROXY", p, "BLOCKED — /storage not routed" if not proxied(p) else "LEAKED via proxy?!")
