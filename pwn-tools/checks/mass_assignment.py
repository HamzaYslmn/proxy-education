"""Mass assignment — write a column the app never meant to expose (here: created_at). An impossible
filter means nothing is actually modified; we only probe whether the field is accepted. The proxy's
body model is data-only, so any extra field is rejected (422).
"""
from core import blocked, line

PHASE = "TAMPER"
TITLE = "Mass assignment:  PATCH private { created_at }  (forbidden column)"
NOBODY = "00000000-0000-0000-0000-000000000000"


def run(ctx):
    body = {"created_at": "2000-01-01T00:00:00Z"}
    d = ctx.send("PATCH", ctx.direct, f"/rest/v1/private?id=eq.{NOBODY}", ctx.token, json=body)
    line("DIRECT", d, "PostgREST accepts the column — no app-level schema guard" if blocked(d, 200, 204) else "")
    p = ctx.send("PATCH", ctx.proxy, f"/rest/v1/private?id=eq.{NOBODY}", ctx.token, json=body)
    line("PROXY", p, "BLOCKED — body is data-only (extra fields rejected)" if blocked(p, 422) else "")
