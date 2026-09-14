from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database.session import get_db
from app.core.jwt import get_current_user
from app.models.like import Like

router = APIRouter()


@router.post("/blogs/{blog_id}/like")
def like_blog(
    blog_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    like = Like(blog_id=blog_id, user_id=current_user.id)
    db.add(like)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Already liked")

    total = db.query(Like).filter(Like.blog_id == blog_id).count()
    return {"status": "liked", "total_likes": total}


@router.delete("/blogs/{blog_id}/like")
def unlike_blog(
    blog_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    like = (
        db.query(Like)
        .filter(Like.blog_id == blog_id, Like.user_id == current_user.id)
        .first()
    )
    if not like:
        raise HTTPException(404, "Like not found")

    db.delete(like)
    db.commit()

    total = db.query(Like).filter(Like.blog_id == blog_id).count()
    return {"status": "unliked", "total_likes": total}