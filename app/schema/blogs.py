from pydantic import BaseModel
from datetime import datetime

class BlogCreate(BaseModel):
    title : str
    description:str
    image_url :str | None = None
    
class BlogUpdate(BaseModel):
    title : str | None = None
    description:str | None = None
    image_url :str | None = None
    
class BlogResponse(BaseModel):
    id: int
    title: str
    description: str
    image_url: str | None
    author_id: int
    created_at: datetime


    class Config:
        from_attributes = True