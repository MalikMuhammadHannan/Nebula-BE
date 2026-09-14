from sqlalchemy import String, Text, Boolean , DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column,relationship
from datetime import datetime,timezone
from pgvector.sqlalchemy import Vector


from app.database.base import Base
from app.models.like import Like
from app.models.comments import Comment


class Blog(Base):
    __tablename__ = "blogs"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    image_public_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    is_published: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    author = relationship(
        "User",
        back_populates="blogs"
    )
    comments: Mapped[list["Comment"]] = relationship(
    "Comment", back_populates="blog", cascade="all, delete-orphan"
    )   
    likes: Mapped[list["Like"]] = relationship(
        "Like", back_populates="blog", cascade="all, delete-orphan"
    )