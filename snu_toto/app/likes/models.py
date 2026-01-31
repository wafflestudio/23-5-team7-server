import uuid
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from snu_toto.app.core.database import Base
from snu_toto.app.core.date_utils import get_kst_now


class EventLike(Base):
    """이벤트 좋아요 테이블"""
    __tablename__ = "event_likes"

    # 좋아요 ID
    like_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # 이벤트 ID
    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("events.event_id", ondelete="CASCADE"),
        nullable=False
    )

    # 유저 ID
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )

    # 좋아요 생성 시각
    created_at: Mapped[DateTime] = mapped_column(
        DateTime,
        default=get_kst_now,
        nullable=False
    )

    # Relationships는 Event와 User 모델에서 정의됨 (순환 참조 방지)

    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_event_user_like"),
    )
