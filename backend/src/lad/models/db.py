from sqlalchemy import (
    DateTime,
    ForeignKey,
    Text,
    String
)
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


class Chat(Base):
    __tablename__ = "chat"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Messages(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chat.id", ondelete="CASCADE"), nullable=False, index=True
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
