"""Registry of all checks, in attacker-chain order, grouped by phase."""
from . import (anon_delete, anon_read, anon_signin, auth_settings, count_leak,
               cross_user, edge, filter_ops, graphql_read, graphql_scan,
               join_embed, mass_assignment, oauth, oversized_limit, rate_limit,
               realtime, rls_disabled, rpc_bypass, schema_dump, storage,
               storage_list, unfiltered_dump, uuid_enum)

ALL = [
    # RECON — map the API
    graphql_scan, graphql_read, schema_dump,
    # READ — pull the data
    anon_read, unfiltered_dump, cross_user, uuid_enum, rls_disabled,
    # PIVOT — reach it another way
    join_embed, rpc_bypass,
    # SCALE — enumerate & scrape
    filter_ops, oversized_limit, count_leak,
    # TAMPER & ABUSE
    mass_assignment, anon_delete, rate_limit,
    # SURFACE — other Supabase APIs beyond PostgREST
    storage, storage_list, edge, realtime,
    # AUTH — GoTrue identity surface (the proxy forwards /auth, so it can't fix these)
    auth_settings, anon_signin, oauth,
]

PHASE_TITLES = {
    "RECON": "RECON · map the API — GraphQL, then the schema",
    "READ": "READ · pull the data straight from PostgREST",
    "PIVOT": "PIVOT · reach private data through other paths",
    "SCALE": "SCALE · enumerate and scrape at volume",
    "TAMPER": "TAMPER & ABUSE · write/destroy data, hammer the API",
    "SURFACE": "SURFACE · other Supabase APIs beyond PostgREST",
    "AUTH": "AUTH · GoTrue identity surface (forwarded by the proxy — Supabase config)",
}
