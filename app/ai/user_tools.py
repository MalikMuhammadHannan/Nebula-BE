from langchain_core.tools import tool

from app.database.session import sessionLocal
from app.models.user import User


@tool
def find_user_tool(name: str) -> list[dict]:
    """Search for users whose full name contains the given text
    (case-insensitive, partial match). Returns a list of matches with
    id, full_name, email, role and is_active."""
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
