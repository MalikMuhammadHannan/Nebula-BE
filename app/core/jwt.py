from datetime import datetime, timedelta,timezone
from jose import jwt,JWTError
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES,SECRET_KEY,ALGORITHM
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends,HTTPException
from sqlalchemy.orm import Session
from app.models.user import User
from app.database.session import get_db



oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(data:dict):
    to_encode = data.copy()
    
    expire = datetime.now(timezone.utc)+timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({
        "exp":expire
    })
    
    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    
    
def get_current_user( token: str = Depends(oauth2_scheme),db:Session=Depends(get_db)):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        user_id =payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401,detail="Invalid Token")
        
    except:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )
    return current_user
