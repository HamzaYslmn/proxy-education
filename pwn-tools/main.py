"""pwn-tools — a teaching CLI for Supabase misconfigurations.

Run with no arguments for an interactive menu (pick things by number):

    python main.py

Or non-interactively:

    python main.py recon <site-url>     # extract Supabase URL/keys/tables from a site's HTML+JS
    python main.py test                 # recon the frontend for the URL+key, then run every check

`test` reads the Supabase URL + anon key straight out of the frontend (no hardcoded creds) and
runs DIRECT (raw Supabase) vs PROXY. Red = direct, green = proxy.
⚠️ Educational / authorized testing only.
"""
import argparse
import sys

import auth
import recon as recon_mod
from checks import ALL, PHASE_TITLES
from core import BOLD, DIM, RED, RESET, Ctx, banner

# Force UTF-8 output so box-drawing/dash chars don't crash on legacy Windows code pages or pipes.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Defaults for the local teaching demo.
DEMO_FRONTEND = "http://localhost:5173/"
DEMO_PROXY = "http://localhost:8001/api/db"


def ask(prompt: str, default: str = "") -> str:
    try:
        return input(prompt).strip() or default
    except (EOFError, KeyboardInterrupt):
        return "0"


def setup_ctx(frontend: str, proxy: str) -> Ctx | None:
    """Recon the frontend for the Supabase URL + anon key, register the demo users, return a Ctx."""
    found = recon_mod.recon(frontend)
    if not (found["urls"] and found["anon_keys"]):
        print(f"{RED}could not extract a Supabase URL + key from {frontend} — is the frontend running?{RESET}")
        return None
    ctx = Ctx(direct=found["urls"][0], proxy=proxy.rstrip("/"), key=found["anon_keys"][0],
              buckets=found.get("buckets", []), functions=found.get("functions", []), rpcs=found.get("rpcs", []))
    n = auth.register(ctx)
    print(f"\n{BOLD}registered {n} users — attacking as {auth.USERS[0][0]}{RESET}  uid={ctx.me}")
    return ctx


def list_checks() -> None:
    """Print every check, numbered, grouped by phase, in attacker-chain order."""
    print(f"\n  {DIM}attack order: recon → read → pivot → scale → tamper → surface → auth{RESET}")
    phase = None
    for i, c in enumerate(ALL, 1):
        if c.PHASE != phase:
            phase = c.PHASE
            print(f"\n  {BOLD}{PHASE_TITLES[phase]}{RESET}")
        print(f"    {i:2})  {c.TITLE}")


def parse_selection(s: str):
    """Input → ordered [(index, check)]: ''/'all', a number '7', a range '5-9', or a phase name."""
    s = s.strip().lower()
    items = list(enumerate(ALL, 1))
    if s in ("", "all", "a"):
        return items
    if s in {c.PHASE.lower() for c in ALL}:
        return [(i, c) for i, c in items if c.PHASE.lower() == s]
    if "-" in s:
        try:
            lo, hi = (int(x) for x in s.split("-", 1))
        except ValueError:
            return []
        return [(i, c) for i, c in items if lo <= i <= hi]
    if s.isdigit() and 1 <= int(s) <= len(ALL):
        return [items[int(s) - 1]]
    return []


def run_selection(ctx: Ctx, items, step: bool = False) -> None:
    """Run the selected checks in attack order with phase banners; if step, pause after each."""
    phase = None
    for n, (i, c) in enumerate(items):
        if c.PHASE != phase:
            phase = c.PHASE
            banner(PHASE_TITLES[phase])
        print(f"\n{i}) {c.TITLE}")
        c.run(ctx)
        if step and n < len(items) - 1 and ask(f"   {DIM}[enter] next · q quit ›{RESET} ") == "q":
            break


def menu() -> None:
    frontend, proxy, ctx = DEMO_FRONTEND, DEMO_PROXY, None
    while True:
        print(f"\n{BOLD}═══ pwn-tools · Supabase misconfig demo ═══{RESET}")
        print(f"  {DIM}frontend {frontend}   proxy {proxy}{RESET}")
        print("  1) Recon the frontend   — extract URL, keys, tables")
        print("  2) Show check list      — all, in attack order")
        print(f"  3) Run ALL              — full chain, 1→{len(ALL)}")
        print("  4) Run a selection      — a #, a range (5-9), or a phase")
        print("  5) Step through         — one at a time, pause between")
        print("  6) Settings             — frontend / proxy URLs")
        print("  0) Quit")
        choice = ask("> ")
        if choice == "1":
            recon_mod.recon(ask(f"site url [{frontend}]› ", frontend))
        elif choice == "2":
            list_checks()
        elif choice == "3":
            ctx = ctx or setup_ctx(frontend, proxy)
            if ctx:
                run_selection(ctx, parse_selection("all"))
        elif choice in ("4", "5"):
            list_checks()
            sel = parse_selection(ask("\n  which? (#, range like 5-9, phase, or all) › "))
            if not sel:
                print("  nothing matched that")
                continue
            ctx = ctx or setup_ctx(frontend, proxy)
            if ctx:
                run_selection(ctx, sel, step=(choice == "5"))
        elif choice == "6":
            frontend = ask(f"frontend [{frontend}]› ", frontend)
            proxy = ask(f"proxy [{proxy}]› ", proxy)
            ctx = None  # creds may have changed; re-recon on next run
        elif choice in ("0", "q"):
            print("bye")
            return
        else:
            print("? pick a number")


def cmd_recon(args):
    found = recon_mod.recon(args.url)
    if found["urls"] and found["anon_keys"]:
        print(f"\n  {DIM}next: python main.py test --frontend {args.url}{RESET}")


def cmd_test(args):
    ctx = setup_ctx(args.frontend, args.proxy)
    if not ctx:
        raise SystemExit(1)
    run_selection(ctx, parse_selection("all"))


def main():
    ap = argparse.ArgumentParser(prog="pwn-tools", description="Supabase misconfig teaching CLI")
    sp = ap.add_subparsers(dest="cmd")

    r = sp.add_parser("recon", help="extract Supabase URL/keys/tables from a website's HTML+JS")
    r.add_argument("url", help="a site URL, e.g. https://example.com")

    t = sp.add_parser("test", help="recon the frontend for the Supabase URL+key, then run all checks")
    t.add_argument("--frontend", default=DEMO_FRONTEND, help="frontend URL to recon for the Supabase URL+key")
    t.add_argument("--proxy", default=DEMO_PROXY, help="proxy base URL")

    args = ap.parse_args()
    if args.cmd == "recon":
        cmd_recon(args)
    elif args.cmd == "test":
        cmd_test(args)
    else:
        menu()  # no subcommand → interactive


if __name__ == "__main__":
    main()
