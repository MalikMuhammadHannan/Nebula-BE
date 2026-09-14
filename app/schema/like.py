from pydantic import BaseModel


class LikeResponse(BaseModel):
    id: int
    blog_id: int
    user_id: int
    total_likes: int 

    class Config:
        from_attributes = True