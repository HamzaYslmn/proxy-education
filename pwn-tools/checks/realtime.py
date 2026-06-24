"""Realtime — Supabase streams table changes over a WebSocket at /realtime/v1/websocket. With loose
RLS an attacker subscribes to other users' INSERT/UPDATE/DELETE live. We do NOT open a socket here
(this tool is HTTP-only), and the proxy is HTTP-only too — it speaks no WebSocket, so it routes no
/realtime at all. Passed, with a note.
"""
from core import DIM, GREEN, RED, RESET

PHASE = "SURFACE"
TITLE = "Realtime:  WSS /realtime/v1/websocket  (WebSocket)"


def run(ctx):
    print(f"   {RED}{'DIRECT':7} ~~~~{RESET}  Realtime WS endpoint exists — subscribe to table changes if RLS is loose")
    print(f"   {GREEN}{'PROXY':7} ----{RESET}  not supported — proxy is HTTP-only, routes no /realtime (WebSocket blocked by design)")
    print(f"   {DIM}            (passed: WebSocket testing is out of scope for this httpx tool){RESET}")
