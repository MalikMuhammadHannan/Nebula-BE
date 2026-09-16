from langchain_core.tools import tool

from app.database.session import sessionLocal
from app.models.user import User


def _find_users(name: str) -> list[dict]:
    db = sessionLocal()
    try:
        users = db.query(User).filter(
            (User.full_name.ilike(f"%{name}%")) | (User.email.ilike(f"%{name}%"))
        ).all()
        return [
            {
                "id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
            }
            for u in users
        ]
    finally:
        db.close()


@tool
def find_user_tool(name: str) -> list[dict]:
    """Search for users whose full name or email contains the given text
    (case-insensitive, partial match). Returns a list of matches with
    id, full_name, email, role and is_active."""
    return _find_users(name)


@tool
def activate_user_tool(name: str) -> list[dict]:
    """Use this when the admin wants to ACTIVATE (re-enable) a user's account.
    Looks up users whose full name or email matches the given text and
    returns them so the activation can be confirmed."""
    return _find_users(name)


@tool
def deactivate_user_tool(name: str) -> list[dict]:
    """Use this when the admin wants to DEACTIVATE (disable) a user's account.
    Looks up users whose full name or email matches the given text and
    returns them so the deactivation can be confirmed."""
    return _find_users(name)
