"""UUID enumeration — the `gt` range operator walks every id in order, no victim list needed.
The proxy ignores client filters and forces id = eq.<you>, so the range op returns just your row.
"""
from core import line, rows

PHASE = "READ"
TITLE = "UUID enumeration:  private?id=gt.<zero-uuid>&order=id"
ZERO = "00000000-0000-0000-0000-000000000000"


def run(ctx):
    d = ctx.get(ctx.direct, "private", ctx.token, select="id,data", id=f"gt.{ZERO}", order="id")
    line("DIRECT", d, f"walked {len(rows(d))} rows by id range: {[x['data'].get('notes') for x in rows(d)]}")
    p = ctx.get(ctx.proxy, "private", ctx.token, select="data", id=f"gt.{ZERO}", order="id")
    line("PROXY", p, f"{len(rows(p))} row — gt ignored, id forced to eq.you")
