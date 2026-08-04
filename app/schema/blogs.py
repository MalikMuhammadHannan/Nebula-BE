from pydantic import BaseModel
from datetime import datetime

class BlogCreate(BaseModel):
    title : str
    description:str
    image_url :str | None = None
    content: str

    
class BlogUpdate(BaseModel):
    title : str | None = None
    description:str | None = None
    image_url :str | None = None
    content: str | None = None
    
class BlogResponse(BaseModel):
    id: int
    title: str
    description: str
    image_url: str | None
    author_id: int
    created_at: datetime
    content: str


    class Config:
        from_attributes = True