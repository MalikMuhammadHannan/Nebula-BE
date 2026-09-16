from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from slugify import slugify
from sqlalchemy.orm import Session

from app.core.jwt import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.models.blogs import Blog
from app.schema.ai_blog import GenerateBlogRequest
from app.schema.blogs import BlogResponse
from app.services.cloudinary import upload_image
from app.ai.embeddings import embedding_service
from app.ai.blog_agent import generate_blog_from_query

router = APIRouter(
    prefix="/ai-blogs",
    tags=["AI Blogs"]
)


@router.post("/generate", response_model=BlogResponse)
def generate_ai_blog(
    payload: GenerateBlogRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    result = generate_blog_from_query(payload.query)
    if not result or not result.get("content"):
        raise HTTPException(status_code=422, detail="Could not generate a blog for this query")

    title = result["title"]
    description = result["description"]
    content = result["content"]

    image_url = None
    for image in result.get("images", []):
        try:
            image_url = upload_image(image)["url"]
            break
        except Exception:
            continue

    blog = Blog(
        title=title,
        slug=f"{slugify(title)}-{uuid4().hex[:6]}",
        description=description,
        content=content,
        image_url=image_url,
        author_id=current_user.id,
        embedding=embedding_service.embed_texts([f"{title}\n{description}\n{content}"])[0],
    )

    db.add(blog)
    db.commit()
    db.refresh(blog)

    return blog
