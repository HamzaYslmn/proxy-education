"""GoTrue exposes its whole auth posture UNAUTHENTICATED at /auth/v1/settings — open signup, email
autoconfirm, which OAuth providers are on. Free recon: it tells an attacker which auth attacks to
fire. The proxy forwards /auth/v1/* (login needs it), so this is a Supabase-config finding, not the
proxy's to fix (a stricter proxy could refuse /auth/v1/settings).
"""
from core import RESET, YELLOW, line

PHASE = "AUTH"
TITLE = "Auth config disclosure:  GET /auth/v1/settings"


def run(ctx):
    d = ctx.send("GET", ctx.direct, "/auth/v1/settings", None)
    s = d.json() if d is not None and d.status_code == 200 and "json" in d.headers.get("content-type", "") else {}
    if s:
        bits = ["signup OPEN" if not s.get("disable_signup") else "signup closed"]
        if s.get("mailer_autoconfirm"):
            bits.append("email autoconfirm ON")
        providers = sorted(k for k, v in (s.get("external") or {}).items() if v)
        line("DIRECT", d, f"config leaked — {', '.join(bits)}; providers={providers or '—'}")
    else:
        line("DIRECT", d, f"settings not readable (status {d.status_code if d is not None else '—'})")
    p = ctx.send("GET", ctx.proxy, "/auth/v1/settings", None)
    code = p.status_code if p is not None else "----"
    print(f"   {YELLOW}{'PROXY':7} {code}{RESET}  forwarded — auth config is Supabase's job, not the proxy's")
