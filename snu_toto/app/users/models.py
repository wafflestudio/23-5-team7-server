import enum
import uuid
from sqlalchemy import String, Integer, DateTime, Boolean, Enum, ForeignKey, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.bets.models import Bet
    from app.events.models import Event

class UserRole(str, enum.Enum):
    """관리자 여부를 위한 Enum"""
    USER = "USER"
    ADMIN = "ADMIN"

class PointReason(str, enum.Enum):
    """포인트 기록 변경 사유를 위한 Enum"""
    BET = "BET"
    WIN = "WIN"
    LOSE = "LOSE"
    REFUND = "REFUND"
    ETC = "ETC"

class User(Base):
    """유저 테이블"""
    __tablename__ = "users"

    # 유저 ID
    user_id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
    )
    
    # 이메일
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        nullable=False, 
        index=True
    )
    
    # 비밀번호
    hashed_password: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )
    
    # 닉네임
    nickname: Mapped[str] = mapped_column(
        String(20), 
        unique=True, 
        nullable=False
    )
    
    # 포인트
    points: Mapped[int] = mapped_column(
        Integer, 
        default=10000,
        server_default="10000", 
        nullable=False
    )
    
    # 계정 생성 시각
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, 
        server_default=func.now(), 
        nullable=False
    )
    
    # 관리자 여부
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), 
        default=UserRole.USER, 
        server_default="USER",
        nullable=False
    )
    
    # 인증 여부
    is_verified: Mapped[bool] = mapped_column(
        Boolean, 
        default=False, 
        server_default="0",
        nullable=False,
    )

    point_histories: Mapped[list["PointHistory"]] = relationship("PointHistory", back_populates="user")
    bets: Mapped[list["Bet"]] = relationship("Bet", back_populates="user")
    created_events: Mapped[list["Event"]] = relationship("Event", back_populates="creator")

    __table_args__ = (
        CheckConstraint("points >= 0", name="check_points_positive"),
        CheckConstraint("CHAR_LENGTH(nickname) >= 2", name="check_nickname_length"),
    )

class PointHistory(Base):
    """포인트 기록 테이블"""
    __tablename__ = "point_history"

    # 기록 ID
    history_id: Mapped[str] = mapped_column(
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

    # 베팅 ID
    bet_id: Mapped[str | None] = mapped_column(
        String(36), 
        nullable=True
    )

    # 변화량
    change_amount: Mapped[int] = mapped_column(
        Integer, 
        nullable=False
    )

    # 변화 이유
    reason: Mapped[PointReason] = mapped_column(
        Enum(PointReason), 
        default=PointReason.ETC, 
        server_default="ETC",
        nullable=False
    )

    # 변화 시각
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, 
        server_default=func.now(), 
        nullable=False
    )

    # 최종 잔액
    points_after: Mapped[int] = mapped_column(
        Integer, 
        default=0, 
        server_default="0",
        nullable=False
    ) 

    user: Mapped["User"] = relationship("User", back_populates="point_histories")
    bet: Mapped["Bet | None"] = relationship("Bet", back_populates="point_histories")