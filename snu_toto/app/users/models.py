import enum
import uuid
from sqlalchemy import String, Integer, DateTime, Boolean, Enum, ForeignKey, func, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from snu_toto.app.core.database import Base
from typing import TYPE_CHECKING, Optional

from snu_toto.app.core.date_utils import get_kst_now

if TYPE_CHECKING:
    from snu_toto.app.bets.models import Bet
    from snu_toto.app.events.models import Event
    from snu_toto.app.comments.models import Comment

class UserRole(str, enum.Enum):
    """관리자 여부를 위한 Enum"""
    USER = "USER"
    ADMIN = "ADMIN"

class SocialType(enum.Enum):
    LOCAL = "LOCAL"
    GOOGLE = "GOOGLE"
    KAKAO = "KAKAO"

class PointReason(str, enum.Enum):
    """포인트 기록 변경 사유를 위한 Enum"""
    SIGNUP = "SIGNUP"
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
    hashed_password: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True # 소셜 로그인의 경우 password를 저장하지 않음
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
        default=get_kst_now, 
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
        nullable=False
    )

    # 서울대 이메일 인증 여부
    is_snu_verified: Mapped[bool] = mapped_column(
        Boolean, 
        default=False,
        server_default="0",
        nullable=False
    )

    # 소셜 로그인 타입
    social_type: Mapped[SocialType] = mapped_column(
        Enum(SocialType), 
        default=SocialType.LOCAL,
        server_default="LOCAL"
    )

    # 소셜 ID
    social_id: Mapped[Optional[str]] = mapped_column(
        String(200), 
        nullable=True, 
    )

    # 정지 풀리는 시각
    suspended_until: Mapped[Optional[DateTime]] = mapped_column(
        DateTime, 
        nullable=True
    )

    # 정지 사유
    suspension_reason: Mapped[Optional[str]] = mapped_column(
        String(50), 
        nullable=True
    )

    # 탈퇴여부
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, 
        default=False,
        server_default="0",
        nullable=False
    )


    point_histories: Mapped[list["PointHistory"]] = relationship("PointHistory", back_populates="user")
    bets: Mapped[list["Bet"]] = relationship("Bet", back_populates="user")
    created_events: Mapped[list["Event"]] = relationship("Event", back_populates="creator")
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    withdrawal_info: Mapped["UserWithdrawal"] = relationship("UserWithdrawal", back_populates="user", uselist=False)

    __table_args__ = (
        CheckConstraint("points >= 0", name="check_points_positive"),
        CheckConstraint("CHAR_LENGTH(nickname) >= 2", name="check_nickname_length"),
        UniqueConstraint('social_type', 'social_id', name='uq_social_type_id'),
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
        default=get_kst_now,
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

class UserWithdrawal(Base):
    """회원 탈퇴 이력 및 재가입 제한 관리를 위한 테이블"""
    __tablename__ = "user_withdrawal"

    # ID
    withdrawal_id : Mapped[str] = mapped_column(
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

    # 이메일
    hashed_email: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        index=True
    )

    # 4. 탈퇴 시각: 현재 시각 저장
    deleted_at: Mapped[DateTime] = mapped_column(
        DateTime, 
        default=get_kst_now,
        nullable=False
    )

    user = relationship("User", back_populates="withdrawal_info")