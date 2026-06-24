"""Shared config, HTTP helpers and output formatting for the pwn-tools checks.

Every check receives a Ctx (the target: direct URL, proxy URL, anon key, attacker token/uid)
and prints two coloured lines — DIRECT (raw Supabase) in red, PROXY (:8001) in green.
"""
import base64
import json
from dataclasses import dataclass, field

import httpx

# ANSI colors — red = direct (leaks), green = proxy (safe), yellow = warning
RED, GREEN, YELLOW, BOLD, DIM, RESET = (
    "\033[31m", "\033[32m", "\033[33m", "\033[1m", "\033[2m", "\033[0m",
)

@dataclass
class Ctx:
    """One target run: the two base URLs, the anon key, and (after login) the attacker token/uid."""
    direct: str          # Supabase project URL, e.g. https://xxxx.supabase.co
    proxy: str           # proxy base, e.g. http://localhost:8001/api/db
    key: str             # anon / publishable key
    token: str | None = None
    me: str | None = None
    buckets: list = field(default_factory=list)    # storage buckets recon found in the JS
    functions: list = field(default_factory=list)  # edge function names recon found
    rpcs: list = field(default_factory=list)        # RPC names recon found

    def _headers(self, token: str | None) -> dict:
        h = {"apikey": self.key}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def send(self, method, base, url, token=None, *, headers=None, **kw):
        """One request to base+url. Returns None if the host (usually the proxy) isn't up."""
        h = self._headers(token)
        if headers:
            h.update(headers)
        try:
            return httpx.request(method, f"{base}{url}", headers=h, timeout=15, **kw)
        except httpx.ConnectError:
            return None

    def get(self, base, path, token=None, **params):
        return self.send("GET", base, f"/rest/v1/{path}", token, params=params)


def sub(token: str) -> str:
    """uid from a JWT (the 'sub' claim), no signature check — just to label rows."""
    seg = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4)))["sub"]


def rows(r: httpx.Response | None) -> list:
    return r.json() if r is not None and r.status_code == 200 and isinstance(r.json(), list) else []


def blocked(r: httpx.Response | None, *codes: int) -> bool:
    return r is not None and r.status_code in codes


def proxied(r: httpx.Response | None) -> bool:
    """True only if the proxy actually forwarded to Supabase (a 200 JSON response). An unrouted
    path falls through to the SPA (200 text/html) or 405 — that's NOT a leak, so this returns False."""
    return r is not None and r.status_code == 200 and "json" in r.headers.get("content-type", "").lower()


def total(r: httpx.Response | None) -> str:
    """Total row count from PostgREST's Content-Range header (e.g. '0-24/25' -> '25')."""
    cr = r.headers.get("content-range", "") if r is not None else ""
    return cr.split("/")[-1] if "/" in cr else "?"


def gql_collections(r: httpx.Response | None) -> list:
    """Collection (table) names from a pg_graphql introspection response."""
    if r is None or r.status_code != 200:
        return []
    fields = (((r.json().get("data") or {}).get("__schema") or {}).get("queryType") or {}).get("fields") or []
    return [f["name"] for f in fields if f["name"].endswith("Collection")]


def gql_notes(r: httpx.Response | None) -> list:
    """Pull notes out of a pg_graphql privateCollection response."""
    if r is None or r.status_code != 200:
        return []
    edges = (((r.json().get("data") or {}).get("privateCollection")) or {}).get("edges") or []
    return [e["node"]["data"].get("notes") for e in edges]


def line(label: str, r: httpx.Response | None, extra: str = "") -> None:
    color = RED if label == "DIRECT" else GREEN
    code = "----" if r is None else r.status_code
    note = "(proxy not running on :8001)" if r is None else extra
    print(f"   {color}{label:7} {code}{RESET}  {note}")


def banner(title: str) -> None:
    print(f"\n{BOLD}{'─' * 3} {title} {'─' * 3}{RESET}")
