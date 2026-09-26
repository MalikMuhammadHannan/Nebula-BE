from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column,relationship
from datetime import datetime, timezone
from sqlalchemy import DateTime
from app.database.base import Base
from app.models.like import Like
from app.models.comments import Comment

class User(Base):
    __tablename__ = "users"
    id :Mapped[int] = mapped_column(primary_key=True)
    full_name :Mapped[str] = mapped_column(String(100),nullable=False) 
    email :Mapped[str]= mapped_column(
        String(225),
        unique=True,
        index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255))

    role: Mapped[str] = mapped_column(
        String(20),
        default="user", # admin, editor, user
    )  

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    
    blogs = relationship(
        "Blog",
        back_populates="author"
    )
    documents = relationship(
        "Document",
        back_populates="owner"
    )
    comments: Mapped[list["Comment"]] = relationship(
    "Comment", back_populates="user", cascade="all, delete-orphan"
    )
    likes: Mapped[list["Like"]] = relationship(
        "Like", back_populates="user", cascade="all, delete-orphan"
    )
    token_balance : Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    purchases = relationship(
        "Purchase", back_populates="user", cascade="all, delete-orphan"
    )