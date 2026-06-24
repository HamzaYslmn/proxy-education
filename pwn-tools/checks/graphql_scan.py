"""GraphQL introspection enumerates every table/collection without reading a row.
Supabase auto-exposes pg_graphql at /graphql/v1; __schema hands over the whole map.
"""
from core import gql_collections, line, proxied

PHASE = "RECON"
TITLE = "GraphQL scan:  POST /graphql/v1  { __schema … }"


def run(ctx):
    q = {"query": "{ __schema { queryType { fields { name } } } }"}
    d = ctx.send("POST", ctx.direct, "/graphql/v1", ctx.token, json=q)
    line("DIRECT", d, f"enumerated tables via GraphQL: {gql_collections(d)}")
    p = ctx.send("POST", ctx.proxy, "/graphql/v1", ctx.token, json=q)
    line("PROXY", p, "BLOCKED — /graphql not routed" if not proxied(p) else "LEAKED via proxy?!")
