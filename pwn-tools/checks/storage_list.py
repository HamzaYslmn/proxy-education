"""Storage object enumeration — POST /storage/v1/object/list/<bucket>. A missing SELECT policy on
storage.objects lets the anon role walk a bucket's whole file tree (even a "public" bucket needs a
SELECT policy to LIST, so a returned listing is itself the finding). Buckets come from recon's JS
scan plus a small wordlist. The proxy routes no /storage, so every probe 404s through it.
"""
from core import GREEN, RED, RESET, proxied

PHASE = "SURFACE"
TITLE = "Storage object list:  POST /storage/v1/object/list/<bucket>"
WORDLIST = ["public", "avatars", "uploads", "files", "media"]


def run(ctx):
    body = {"prefix": "", "limit": 100}
    targets = list(dict.fromkeys((ctx.buckets or []) + WORDLIST))
    leaked, proxy_ok = [], True
    for b in targets:
        d = ctx.send("POST", ctx.direct, f"/storage/v1/object/list/{b}", ctx.token, json=body)
        if d is not None and d.status_code == 200 and isinstance(d.json(), list) and d.json():
            leaked.append(f"{b}({len(d.json())})")
        if proxied(ctx.send("POST", ctx.proxy, f"/storage/v1/object/list/{b}", ctx.token, json=body)):
            proxy_ok = False
    print(f"   {RED}{'DIRECT':7}    {RESET} listable buckets ({len(targets)} probed): {leaked or '—'}")
    print(f"   {GREEN}{'PROXY':7}    {RESET} {'BLOCKED — /storage not routed' if proxy_ok else 'LEAKED via proxy?!'}")
