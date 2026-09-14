from sqlalchemy import String,Text,Integer,ForeignKey,DateTime
from sqlalchemy.orm import Mapped,mapped_column,relationship
from datetime import datetime, timezone
from app.database.base import Base


class Document(Base):
    __tablename__='documents'
    id: Mapped[int]= mapped_column(primary_key=True)
    filename:Mapped[str] = mapped_column(String(255), nullable=True) 
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf, docx, txt
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",  # pending, processing, processed, failed
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
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

    owner = relationship("User", back_populates="documents")

    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )

    chat_turns = relationship(
        "DocumentChatTurn",
        back_populates="document",
        cascade="all, delete-orphan"
    )