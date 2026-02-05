import uuid
from sqlalchemy import String, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from snu_toto.app.core.database import Base
from typing import TYPE_CHECKING
from snu_toto.app.core.date_utils import get_kst_now

if TYPE_CHECKING:
    from snu_toto.app.events.models import Event
    from snu_toto.app.users.models import User


class Comment(Base):
    """댓글 테이블"""
    __tablename__ = "comments"

    # 댓글 ID
    comment_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # 이벤트 ID (FK)
    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("events.event_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 유저 ID (FK)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )

    # 댓글 내용 (1~500자)
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # 작성 시각
    created_at: Mapped[DateTime] = mapped_column(
        DateTime,
        nullable=False,
        default=get_kst_now
    )

    # 수정 시각 (Nullable)
    updated_at: Mapped[DateTime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    event: Mapped["Event"] = relationship("Event", back_populates="comments")
    user: Mapped["User"] = relationship("User", back_populates="comments")

    # 제약 조건: 댓글 내용은 1~2000자
    __table_args__ = (
        CheckConstraint(
            "LENGTH(content) >= 1 AND LENGTH(content) <= 2000",
            name="ck_comment_content_length_v2"
        ),
    )
