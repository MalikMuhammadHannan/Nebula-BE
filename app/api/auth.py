from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User

from app.schema.user import UserCreate,UserResponse
from app.core.security import hash_password

from app.schema.auth import LoginRequest, TokenResponse
from app.core.security import verify_password
from app.core.jwt import create_access_token

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.post(
    "/register",
    response_model=UserResponse
)
def register(
    user_data:UserCreate,
    db:Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        User.email ==user_data.email
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already Register"
        )
        
    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        password_hash=hash_password(
            user_data.password
        ))
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user




@router.post("/login", response_model=TokenResponse)
def login(data:LoginRequest,
          db:Session=Depends(get_db)):
    user = db.query(User).filter(
        data.email == User.email
    ).first()
    
    if not user:
        raise HTTPException(status_code=401,detail="User not found")
    
    is_password_valid = verify_password(
        hashed_password=user.password_hash,
        plain_password=data.password
    )
    
    if not is_password_valid:
        raise HTTPException(status_code=401,detail="Incorrect Password")
    
    token = create_access_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role
        }
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user":user
    }