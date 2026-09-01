from pydantic import BaseModel
from datetime import datetime


class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    session_id: str
    filename: str
    file_type: str
    status: str


class DocumentQueryRequest(BaseModel):
    session_id: str
    query: str