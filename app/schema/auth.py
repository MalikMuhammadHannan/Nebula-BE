from pydantic import BaseModel , EmailStr
from app.schema.user import UserResponse

class LoginRequest(BaseModel):
    email:EmailStr
    password:str
    
    
class TokenResponse(BaseModel):
    access_token:str
    token_type :str
    user:UserResponse   