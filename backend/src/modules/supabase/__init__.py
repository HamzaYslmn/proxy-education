# MARK: Supabase module
#   proxy.py  — routes INCOMING requests (publishable key + the user's JWT)
#   client.py — service-role admin client for INTERNAL/backend operations (RLS bypassed)
#   auth.py   — token verification + admin user ops (uses client.py)
from .client import init  # noqa: F401
from .proxy import auth_proxy, close_session, get_session, supabase_proxy  # noqa: F401
from .auth import delete_user, get_user_info, verify_token  # noqa: F401
