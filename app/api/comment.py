from sqlalchemy.orm import Session
from fastapi import Depends,APIRouter,HTTPException

from app.database.session import get_db
from app.core.jwt import get_current_user
from app.models.comments import Comment
from app.models.like import Like
from app.models.blogs import Blog
from app.schema.comment import CommentCreate, CommentResponse

router = APIRouter()


@router.post("/blogs/{blog_id}/comments", response_model=CommentResponse)
def create_comment(
    blog_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(404,"Blog not found")
    
    comment = Comment(
        content=payload.content,
        blog_id=blog_id,
        user_id=current_user.id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    return comment


@router.get("/blogs/{blog_id}/comments", response_model=list[CommentResponse])
def list_comments(blog_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Comment)
        .filter(Comment.blog_id == blog_id)
        .order_by(Comment.created_at.desc())
        .all()
    )


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(404, "Comment not found")
    if comment.user_id != current_user.id:
        raise HTTPException(403, "Not allowed to delete this comment")

    db.delete(comment)
    db.commit()
    return {"status": "deleted"}


