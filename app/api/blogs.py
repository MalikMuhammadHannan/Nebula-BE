from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.jwt import get_current_user
from app.database.session import get_db
from app.models.blogs import Blog
from app.models.user import User
from app.schema.blogs import BlogCreate, BlogResponse,BlogUpdate
from typing import List
from slugify import slugify
from app.services.cloudinary import delete_upload_image
from app.ai.embeddings import embedding_service



router = APIRouter(
    prefix="/blogs"
    ,tags=["Blogs"]
)


def _embed_blog_text(title: str, description: str, content: str) -> list[float]:
    text = f"{title}\n{description}\n{content}"
    return embedding_service.embed_texts([text])[0]


@router.post("/",response_model=BlogResponse)
def create_blog(blog_data:BlogCreate, db:Session = Depends(get_db),
                current_user:User=Depends(get_current_user)):
    blog = Blog(
        title=blog_data.title,
        slug=slugify(blog_data.title),
        description=blog_data.description,
        image_url=blog_data.image_url,
        author_id=current_user.id,
        content=blog_data.content,
        embedding=_embed_blog_text(blog_data.title, blog_data.description, blog_data.content)
    )

    db.add(blog)
    db.commit()
    db.refresh(blog)

    return blog


@router.get("/public", response_model=List[BlogResponse])
def get_blogs(db: Session = Depends(get_db)):
    return db.query(Blog).all()


@router.get("/public/{id}", response_model=BlogResponse)
def get_blog(id: int, db: Session = Depends(get_db)):
    blog = db.query(Blog).filter(Blog.id == id).first()

    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    return blog

@router.get("/",response_model=List[BlogResponse])
def get_blogs(
    db: Session = Depends(get_db),current_user:User=Depends(get_current_user)
    
):
    blogs = db.query(Blog).filter(Blog.author_id == current_user.id).all()
    return blogs


@router.get("/{id}",response_model=BlogResponse)
def get_single_blog(id:int,db:Session=Depends(get_db)):
    get_blog= db.query(Blog).filter(id == Blog.id)
    
    if not get_blog:
        raise HTTPException(status_code=404,detail="Blog not found")
    
    return get_blog


@router.patch("/{id}",response_model=BlogResponse)
def update_blog(id:str, blog_data:BlogUpdate,db:Session = Depends(get_db),current_user:User=Depends(get_current_user)):
    blog = db.query(Blog).filter(Blog.id == id).first()
    if not blog:
            raise HTTPException(status_code=404,detail="Blog not found")
    if blog.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not allowed"
        )
        
    if blog_data.image_url and blog_data.image_url != blog.image_url:
            delete_upload_image(blog.image_url)

    updated_blog = blog_data.model_dump(exclude_unset=True)
    for key,values in updated_blog.items():
        setattr(blog,key,values)

    if {"title", "description", "content"} & updated_blog.keys():
        blog.embedding = _embed_blog_text(blog.title, blog.description, blog.content)

    db.commit()
    db.refresh(blog)

    return blog
    

@router.delete("/{id}")
def delete_blog(
    id:int,
    db:Session=Depends(get_db),
    current_user:User=Depends(get_current_user)
):

    blog = db.query(Blog).filter(
        Blog.id==id
    ).first()


    if not blog:
        raise HTTPException(
            404,
            "Blog not found"
        )
    if blog.author_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Not allowed"
            )
    db.delete(blog)
    if blog.image_url:
        delete_upload_image(blog.image_url)
    db.commit()


    return {
        "message":"Blog deleted"
    }