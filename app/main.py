from fastapi import FastAPI
from app.api.auth import router as auth_router
from app.api.blogs import  router as blog_router
from app.api.upload import  router as upload_router

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

