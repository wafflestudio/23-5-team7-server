import uuid
from sqlalchemy import String, Text, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from snu_toto.app.core.database import Base
from typing import TYPE_CHECKING, Optional
from datetime import datetime

if TYPE_CHECKING:
    from snu_toto.app.users.models import User
    from snu_toto.app.events.models import Event

class Comment(Base):
    """댓글 테이블"""
    __tablename__ = "comments"

    # 댓글 ID
    comment_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    # 이벤트 ID
    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("events.event_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # 유저 ID
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    
    # 댓글 내용
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    # 작성 시각
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # 수정 시각
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now()
    )
    
    # 관계
    user: Mapped["User"] = relationship("User", back_populates="comments")
    event: Mapped["Event"] = relationship("Event", back_populates="comments")

    # 인덱스 (조회 성능 최적화)
    __table_args__ = (
        Index('idx_comments_event', 'event_id'),
    )
