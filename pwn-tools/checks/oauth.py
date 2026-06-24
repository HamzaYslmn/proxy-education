"""OAuth redirect chains — /auth/v1/authorize sends the browser to the provider and back to
`redirect_to`. If that isn't on Supabase's allowlist it's an open redirect → OAuth token theft.
This is an auth-layer CONFIG issue: the proxy forwards /auth (login needs it), so it does NOT fix
it — set your Redirect-URL allowlist in the Supabase dashboard (a stricter proxy could allowlist
the auth paths it forwards).
"""
from core import RESET, YELLOW, line

PHASE = "AUTH"
TITLE = "OAuth redirect:  GET /auth/v1/authorize?provider=…&redirect_to=evil"
EVIL = "https://evil.example.com/steal"


def run(ctx):
    path = f"/auth/v1/authorize?provider=github&redirect_to={EVIL}"
    d = ctx.send("GET", ctx.direct, path, None)
    loc = d.headers.get("location", "") if d is not None else ""
    if "evil.example.com" in loc:
        line("DIRECT", d, f"redirect_to honored → {loc[:50]}…  (open redirect / token theft)")
    else:
        line("DIRECT", d, f"GoTrue rejected the redirect (status {d.status_code if d is not None else '—'}) — allowlist enforced or provider off")
    p = ctx.send("GET", ctx.proxy, path, None)
    code = p.status_code if p is not None else "----"
    print(f"   {YELLOW}{'PROXY':7} {code}{RESET}  forwarded — redirect safety is Supabase config (allowlist), not the proxy")
