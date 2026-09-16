from pydantic import BaseModel,EmailStr

class UserCreate(BaseModel):
    full_name:str
    email:EmailStr
    password:str


class AssistantQuery(BaseModel):
    query:str


class UserResponse(BaseModel):
    id:int
    full_name:str
    email:str
    role:str
    is_active:bool

    class Config:
        from_attributes = True


class AssistantResponse(BaseModel):
    action: str | None
    matches: list[UserResponse]
    message: str


class ConfirmActionRequest(BaseModel):
    confirm: bool