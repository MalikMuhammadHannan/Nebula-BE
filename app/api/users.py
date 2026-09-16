from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.jwt import require_admin
from app.ai.user_agent import find_users_from_query
from app.models.user import User
from app.schema.user import AssistantQuery, AssistantResponse, ConfirmActionRequest, UserResponse


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("/", response_model=list[UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return db.query(User).filter(User.role != "admin").all()


@router.post("/assistant", response_model=AssistantResponse)
def ai_assistant(
    payload: AssistantQuery,
    current_user: User = Depends(require_admin),
):
    result = find_users_from_query(payload.query)
    action = result["action"]
    matches = result["matches"]

    if not matches:
        raise HTTPException(
            status_code=404,
            detail="Could not find a matching user",
        )

    verb = {"activate": "Activate", "deactivate": "Deactivate"}.get(action, "Confirm action on")

    if len(matches) == 1:
        m = matches[0]
        message = f"Found {m['full_name']} ({m['email']}). {verb} this user?"
    else:
        message = "Multiple users matched — please be more specific."

    return AssistantResponse(action=action, matches=matches, message=message)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: int,
    payload: ConfirmActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    db.commit()
    db.refresh(user)

    return user


@router.post("/{user_id}/activate", response_model=UserResponse)
def activate_user(
    user_id: int,
    payload: ConfirmActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    db.commit()
    db.refresh(user)

    return user
