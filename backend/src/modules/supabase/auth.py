# MARK: Auth — token verification, user management (admin/service-key ops)
from middleware import log

from .client import _db


# MARK: Token verification
async def verify_token(token: str) -> str:
    """Verify JWT token. Returns user_uuid."""
    if not token:
        raise ValueError("Token required")
    try:
        response = await _db().auth.get_user(token)
    except Exception as e:
        log.warning(f"Token verification failed: {e}")
        raise ValueError("Session expired or invalid")
    user = response.user
    if not user:
        raise ValueError("Invalid token")
    if not user.email_confirmed_at:
        raise ValueError("Email not verified")
    return user.id


# MARK: User management
async def delete_user(uuid: str) -> None:
    await _db().auth.admin.delete_user(uuid)


async def get_user_info(uuid: str):
    return await _db().auth.admin.get_user_by_id(uuid)