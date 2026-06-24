"""No application-level rate limit on direct — every attack above can be automated at full speed.
The proxy caps each route at 10/min per IP (429).
"""
import httpx

from core import GREEN, RESET, line

PHASE = "TAMPER"
TITLE = "Rate limit:  25 rapid reads"


def run(ctx):
    dc = [ctx.get(ctx.direct, "public", ctx.token, select="data").status_code for _ in range(25)]
    pc = [(ctx.get(ctx.proxy, "public", ctx.token, select="data") or httpx.Response(0)).status_code for _ in range(25)]
    line("DIRECT", httpx.Response(200), f"{dc.count(200)}x200  {dc.count(429)}x429  (no app cap)")
    print(f"   {GREEN}PROXY   ----{RESET}  {pc.count(200)}x200  {pc.count(429)}x429  (10/min cap)")
