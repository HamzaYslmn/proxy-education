"""Recon: point at a website, fetch its HTML + linked JS, and extract everything Supabase the
frontend leaks — project URL, API keys (classified by privilege), and table / RPC / bucket /
edge-function names. Read-only — it never touches Supabase, only the target's own assets.
"""
import base64
import json
import re
from urllib.parse import urljoin, urlsplit

import httpx

from core import BOLD, GREEN, RED, RESET, YELLOW

# Project URL (ref is ~20 lowercase alphanumerics) — also the functions subdomain + custom hosts.
URL_RE = re.compile(r"https://[a-z0-9]{16,}\.(?:supabase\.(?:co|in)|functions\.supabase\.co)")
# Keys: new format (sb_publishable_ / sb_secret_), Management-API PAT (sbp_), and legacy JWTs (eyJ…).
PUBLISHABLE_RE = re.compile(r"sb_publishable_[A-Za-z0-9_]+")
SECRET_RE = re.compile(r"sb_secret_[A-Za-z0-9_]+")
PAT_RE = re.compile(r"sbp_[A-Za-z0-9]{36,}")
JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")
# Names the attack phase can probe, from supabase-js call sites and raw REST/Storage/Functions URLs.
FROM_RE = re.compile(r"""\.from\(\s*['"]([a-zA-Z_]\w*)['"]""")
REST_RE = re.compile(r"/rest/v1/([a-zA-Z_]\w*)")
RPC_RE = re.compile(r"""\.rpc\(\s*['"]([a-zA-Z_]\w*)['"]""")
RPC_URL_RE = re.compile(r"/rest/v1/rpc/([a-zA-Z_]\w*)")
STORAGE_RE = re.compile(r"""\.storage\s*\.\s*from\(\s*['"]([a-zA-Z0-9_-]+)['"]""")
STORAGE_URL_RE = re.compile(r"/storage/v1/object/(?:public|sign|authenticated|list|info)/([a-zA-Z0-9_-]+)")
FUNC_RE = re.compile(r"""\.invoke\(\s*['"]([a-zA-Z0-9_-]+)['"]""")
FUNC_URL_RE = re.compile(r"/functions/v1/([a-zA-Z0-9_-]+)")
SCRIPT_SRC_RE = re.compile(r"""<script[^>]+src=['"]([^'"]+)['"]""", re.I)
# ES-module imports/exports so we can crawl the graph (Vite dev serves one file per module).
IMPORT_RE = re.compile(r"""(?:import|export)[^'"]*?from\s*['"]([^'"]+)['"]|import\(\s*['"]([^'"]+)['"]""")


def _jwt_claims(tok: str) -> dict:
    """Decode a JWT payload (no signature check) → its claims, or {} if it isn't a JWT."""
    try:
        seg = tok.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4)))
    except Exception:
        return {}


def fetch_all(url: str, max_files: int = 80) -> str:
    """Fetch the page and crawl its JS module graph (same-origin), returning all the text.

    Follows `import … from '/src/…'`, so it works against a production bundle AND a Vite dev
    server — reaching the module where Vite injected the Supabase URL + key, not just the entry
    script. Vendor chunks (/node_modules/) are skipped.
    """
    origin = urlsplit(url).netloc
    seen: set[str] = set()
    texts = []
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "pwn-tools"}) as c:
        html = c.get(url).text
        texts.append(html)
        queue = [urljoin(url, s) for s in SCRIPT_SRC_RE.findall(html)]
        while queue and len(seen) < max_files:
            u = queue.pop(0)
            if u in seen:
                continue
            seen.add(u)
            parts = urlsplit(u)
            if parts.netloc != origin or "/node_modules/" in parts.path:
                continue  # same-origin app code only; skip vendor chunks
            try:
                js = c.get(u).text
            except Exception:
                continue
            texts.append(js)
            for a, b in IMPORT_RE.findall(js):
                spec = a or b
                if spec.startswith((".", "/")):
                    queue.append(urljoin(u, spec))
    return "\n".join(texts)


def extract(text: str) -> dict:
    """Pull Supabase URL, keys (classified) and table/RPC/bucket/function names out of HTML/JS."""
    # Keep only Supabase JWTs (they carry a project `ref` or a supabase issuer) so we don't
    # mislabel Stripe/Auth0/Clerk tokens that also start with eyJ.
    sup = {}
    for t in set(JWT_RE.findall(text)):
        c = _jwt_claims(t)
        if c.get("ref") or "supabase" in str(c.get("iss", "")):
            sup[t] = c

    urls = sorted(set(URL_RE.findall(text)))
    if not urls:  # reconstruct from a JWT's project ref if the *.supabase.co string was obfuscated
        urls = sorted({f"https://{c['ref']}.supabase.co" for c in sup.values() if c.get("ref")})

    buckets = sorted(set(STORAGE_RE.findall(text)) | set(STORAGE_URL_RE.findall(text)))
    tables = sorted((set(FROM_RE.findall(text)) | set(REST_RE.findall(text))) - {"rpc"} - set(buckets))
    return {
        "urls": urls,
        "anon_keys": sorted(set(PUBLISHABLE_RE.findall(text)) | {t for t, c in sup.items() if c.get("role") == "anon"}),
        "service_keys": sorted(set(SECRET_RE.findall(text)) | {t for t, c in sup.items() if c.get("role") == "service_role"}),
        "pats": sorted(set(PAT_RE.findall(text))),
        "tables": tables,
        "rpcs": sorted(set(RPC_RE.findall(text)) | set(RPC_URL_RE.findall(text))),
        "buckets": buckets,
        "functions": sorted(set(FUNC_RE.findall(text)) | set(FUNC_URL_RE.findall(text))),
    }


def recon(url: str) -> dict:
    print(f"{BOLD}recon {url}{RESET}")
    f = extract(fetch_all(url))
    print(f"  {GREEN}URL{RESET}            {f['urls'] or '—'}")
    print(f"  {GREEN}anon key{RESET}       {f['anon_keys'] or '—'}")
    if f["service_keys"]:
        print(f"  {RED}{BOLD}SERVICE KEY !!{RESET} {f['service_keys']}  {RED}← role=service_role: full DB + auth, RLS bypassed{RESET}")
    if f["pats"]:
        print(f"  {RED}{BOLD}PAT (sbp_) !!{RESET}  {f['pats']}  {RED}← Management API: every project & key{RESET}")
    print(f"  {GREEN}tables ({len(f['tables'])}){RESET}     {f['tables'] or '—'}")
    if f["rpcs"]:
        print(f"  {GREEN}rpc fns{RESET}        {f['rpcs']}")
    if f["buckets"]:
        print(f"  {GREEN}buckets{RESET}        {f['buckets']}")
    if f["functions"]:
        print(f"  {GREEN}edge fns{RESET}       {f['functions']}")
    if not f["urls"]:
        print(f"  {YELLOW}no Supabase config found — the page may not use Supabase, or its bundles weren't reachable{RESET}")
    return f
