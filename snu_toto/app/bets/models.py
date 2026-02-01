import enum
import uuid
from sqlalchemy import String, Integer, DateTime, Enum, ForeignKey, func, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from snu_toto.app.core.database import Base
from typing import TYPE_CHECKING

from snu_toto.app.core.date_utils import get_kst_now

if TYPE_CHECKING:
    from snu_toto.app.users.models import User, PointHistory
    from snu_toto.app.events.models import Event, EventOption

class BetStatus(str, enum.Enum):
    """베팅 상태를 위한 Enum"""
    PENDING = "PENDING"
    WIN = "WIN"
    LOSE = "LOSE"
    REFUNDED = "REFUNDED"

class Bet(Base):
    """베팅 테이블"""
    __tablename__ = "bets"

    # 베팅 ID
    bet_id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # 유저 ID
    user_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("users.user_id"), 
        nullable=False
    )
    
    # 이벤트 ID
    event_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("events.event_id"), 
        nullable=False
    )
    
    # 옵션 ID
    option_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("event_options.option_id"), 
        nullable=False
    )
    
    # 베팅 금액
    amount: Mapped[int] = mapped_column(
        Integer, 
        nullable=False
    )
    
    # 베팅 상태
    status: Mapped[BetStatus] = mapped_column(
        Enum(BetStatus), 
        default=BetStatus.PENDING, 
        server_default="PENDING",
        nullable=False
    )
    
    # 베팅 시각
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, 
        default=get_kst_now,
        nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="bets")
    option: Mapped["EventOption"] = relationship("EventOption", back_populates="bets")
    event: Mapped["Event"] = relationship("Event", back_populates="bets")

    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="uq_user_event_bet"),
        CheckConstraint("amount >= 0", name="check_bet_amount_positive"),
    )