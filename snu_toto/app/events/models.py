import enum
import uuid
from sqlalchemy import String, Integer, DateTime, Boolean, Enum, ForeignKey, Text, func, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.users.models import User
    from app.bets.models import Bet

class EventStatus(str, enum.Enum):
    """이벤트 상태를 위한 Enum"""
    READY = "READY"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    SETTLED = "SETTLED"
    CANCELLED = "CANCELLED"

class Event(Base):
    """이벤트 테이블"""
    __tablename__ = "events"

    # 이벤트 ID
    event_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    # 생성한 유저 ID
    creator_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("users.user_id"), 
        nullable=False
    )
    
    # 제목
    title: Mapped[str] = mapped_column(
        String(100), 
        nullable=False
    )
    
    # 설명
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    
    # 상태
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus), 
        default=EventStatus.READY, 
        server_default="READY",
        nullable=False
    )
    
    # 이벤트 생성시각
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, 
        server_default=func.now(), 
        nullable=False
    )
    
    # 이벤트 오픈시각 
    start_at: Mapped[DateTime | None] = mapped_column(
        DateTime, 
        nullable=True
    )
    
    # 이벤트 종료시각
    end_at: Mapped[DateTime] = mapped_column(
        DateTime, 
        nullable=False
    )

    options: Mapped[list["EventOption"]] = relationship("EventOption", back_populates="event")
    images: Mapped[list["EventImage"]] = relationship("EventImage", back_populates="event")
    creator: Mapped["User"] = relationship("User", back_populates="created_events")
    bets: Mapped[list["Bet"]] = relationship("Bet", back_populates="event")

    __table_args__ = (
        CheckConstraint("CHAR_LENGTH(title) >= 5", name="check_event_title_length"),
        CheckConstraint("start_at >= created_at", name="check_event_start_after_created"), # start_at가 NULL이어도 통과
        CheckConstraint("end_at > start_at", name="check_event_end_after_start"),
    )

class EventOption(Base):
    """이벤트 옵션 테이블"""
    __tablename__ = "event_options"

    # 옵션 ID
    option_id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # 이벤트 ID
    event_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("events.event_id"), 
        nullable=False
    )
    
    # 옵션 이름
    name: Mapped[str] = mapped_column(
        String(50), 
        nullable=False
    )
    
    # 옵션 순서
    order: Mapped[int] = mapped_column(
        Integer, 
        nullable=False
    )
    
    # 총 베팅 금액 
    total_bet_amount: Mapped[int] = mapped_column(
        Integer, 
        default=0, 
        server_default="0",
        nullable=False
    )
    
    # 승리여부
    is_winner: Mapped[bool | None] = mapped_column(
        Boolean, 
        nullable=True
    )

    event: Mapped["Event"] = relationship("Event", back_populates="options")
    bets: Mapped[list["Bet"]] = relationship("Bet", back_populates="option")

    __table_args__ = (
        UniqueConstraint("event_id", "name", name="uq_event_option_name"),
        CheckConstraint("`order` >= 0", name="check_option_order_positive"),
        CheckConstraint("total_bet_amount >= 0", name="check_total_bet_positive"),
    )

class EventImage(Base):
    """이벤트 이미지 테이블"""
    __tablename__ = "event_images"

    # 이미지 ID
    image_id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # 이벤트 ID
    event_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("events.event_id"), 
        nullable=False
    )
    
    # 이미지 URL
    image_url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False
    )
    
    # 순서
    display_order: Mapped[int] = mapped_column(
        Integer, 
        default=0, 
        server_default="0",
        nullable=False
    )

    event: Mapped["Event"] = relationship("Event", back_populates="images")