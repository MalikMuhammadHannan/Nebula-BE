from pydantic import BaseModel


class GenerateBlogRequest(BaseModel):
    query: str
