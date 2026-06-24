"""Anonymous sign-in — POST /auth/v1/signup with an empty body. If GoTrue's anonymous users are
enabled, it mints a REAL authenticated session (access_token, role=authenticated, is_anonymous) for
nobody, with no credentials. That bypasses every RLS policy written as the common (wrong) gate
`auth.role() = 'authenticated'`. Forwarded by the proxy — a Supabase-config issue.
"""
from core import RESET, YELLOW, line

PHASE = "AUTH"
TITLE = "Anonymous sign-in:  POST /auth/v1/signup  {}"


def run(ctx):
    d = ctx.send("POST", ctx.direct, "/auth/v1/signup", None, json={})
    body = d.json() if d is not None and "json" in d.headers.get("content-type", "") else {}
    if d is not None and d.status_code == 200 and body.get("access_token"):
        line("DIRECT", d, "GOT a real authenticated session with NO credentials (is_anonymous)")
    else:
        why = body.get("msg") or body.get("error_code") or body.get("error_description") or "rejected"
        line("DIRECT", d, f"anonymous sign-in unavailable ({why})")
    p = ctx.send("POST", ctx.proxy, "/auth/v1/signup", None, json={})
    code = p.status_code if p is not None else "----"
    print(f"   {YELLOW}{'PROXY':7} {code}{RESET}  forwarded — same GoTrue response (proxy doesn't gate auth)")
