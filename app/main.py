from fastapi import FastAPI
import app.models  # noqa: F401 ensures all models are registered before mappers configure
from app.api.auth import router as auth_router
from app.api.blogs import  router as blog_router
from app.api.upload import  router as upload_router
from app.api.document import router as document_router
from app.api.ai_blog import router as ai_blog_router
from app.api import comment, likes


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins=[
    "http://127.0.0.1:5173",
    "http://localhost:5173",  # Vite
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(blog_router)
app.include_router(upload_router)
app.include_router(document_router)
app.include_router(ai_blog_router)

app.include_router(comment.router, tags=["comment"])
app.include_router(likes.router, tags=["likes"])

