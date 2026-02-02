from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from enum import Enum
from datetime import datetime

from snu_toto.app.common.exceptions import InvalidFormatException, MissingRequiredFieldException
from snu_toto.app.common.schemas import PaginationInfo
from snu_toto.app.users.exceptions import *
from snu_toto.app.users.models import PointReason, SocialType, UserRole
from snu_toto.app.bets.models import BetStatus


class UserSignupRequest(BaseModel):
    email: EmailStr
    password: Optional[str] = Field(None, min_length=8, max_length=20)
    nickname: str = Field(..., min_length=2, max_length=20)
    social_type: SocialType = SocialType.LOCAL
    social_id: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_snu_email(cls, v: str) -> str:
        """@snu.ac.kr 도메인 검증 (ERR_010)"""
        if not v.endswith("@snu.ac.kr"):
            raise OnlySnuEmailAllowedException()
        return v

    @model_validator(mode='after')
    def check_pass_and_social(self) -> 'UserSignupRequest':
        """비밀번호 또는 소셜 ID 필수 여부 체크 (ERR_016, ERR_017)"""
        if self.social_type == SocialType.LOCAL and not self.password: # 로컬 가입 - 비밀번호 누락
            raise MissingPasswordException()
        if self.social_type != SocialType.LOCAL and not self.social_id: # 소셜 가입 - 소셜ID 누락
            raise MissingSocialIdException()
        return self

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    user_id: str
    email: EmailStr
    points: int = 10000
    role: UserRole = UserRole.USER
    is_snu_verified: bool = False
    is_verified: bool = False
    social_type: SocialType = SocialType.LOCAL
    created_at: datetime

# 참여 중인 베팅 내역 조회용 스키마
class UserBetItem(BaseModel):
    """사용자 베팅 내역 아이템"""
    model_config = ConfigDict(from_attributes=True)
    
    bet_id: str
    event_id: str
    event_title: str
    option_id: str
    option_name: str
    amount: int
    status: BetStatus
    created_at: datetime

class UserBetsResponse(BaseModel):
    """사용자 베팅 내역 조회 응답"""
    total_count: int
    bets: List[UserBetItem]

# 내 포인트 내역 조회용 스키마 (베팅 정보 통합)
class UserPointHistoryItem(BaseModel):
    """사용자 포인트 내역 아이템 (베팅 세부 정보 포함)"""
    model_config = ConfigDict(from_attributes=True)
    
    history_id: str
    reason: PointReason
    change_amount: int
    points_after: int
    bet_id: Optional[str] = None
    event_id: Optional[str] = None
    event_title: Optional[str] = None
    option_id: Optional[str] = None
    option_name: Optional[str] = None
    created_at: datetime

class UserPointHistoryResponse(BaseModel):
    """사용자 포인트 내역 조회 응답"""
    current_balance: int
    total_count: int
    history: List[UserPointHistoryItem]
# 프로필 조회용 스키마
class UserProfileResponse(BaseModel):
    """사용자 프로필 조회 응답"""
    model_config = ConfigDict(from_attributes=True)
    
    user_id: str
    email: EmailStr
    nickname: str
    points: int
    role: UserRole
    is_verified: bool
    is_snu_verified: bool
    social_type: SocialType
    created_at: datetime

# 통계 조회용 스키마
class UserPointsStats(BaseModel):
    """포인트 통계"""
    current_balance: int
    total_earned: int
    total_spent: int

class UserBetsStats(BaseModel):
    """베팅 통계"""
    total_bets_count: int
    pending_count: int
    win_count: int
    lose_count: int
    refunded_count: int
    win_rate: float

class UserStatsResponse(BaseModel):
    """사용자 통계 조회 응답"""
    points: UserPointsStats
    bets: UserBetsStats

# 랜킹 조회용 스키마
class UserRankingResponse(BaseModel):
    """사용자 랜킹 조회 응답"""
    rank: int
    total_users: int
    percentile: float
    my_points: int
class UserRankItem(BaseModel):
    rank: int
    nickname: str
    points: int

class UserTopRankingResponse(BaseModel):
    total_count: int  # 전체 순위권 대상 유저 수
    updated_at: datetime
    rankings: List[UserRankItem]
      
# 닉네임 변경용 스키마
class UpdateNicknameRequest(BaseModel):
    """닉네임 변경 요청"""
    nickname: str = Field(..., min_length=2, max_length=20)

class UpdateNicknameResponse(BaseModel):
    """닉네임 변경 응답"""
    message: str
    nickname: str

# 비밀번호 변경용 스키마
class UpdatePasswordRequest(BaseModel):
    """비밀번호 변경 요청"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=20)

class UpdatePasswordResponse(BaseModel):
    """비밀번호 변경 응답"""
    message: str

class UserRoleUpdateRequest(BaseModel):
    role: UserRole = Field(...)

class UserAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: str
    nickname: str
    role: UserRole

class UserSuspendRequest(BaseModel):
    suspension_hours: int = Field(..., ge=1)
    suspension_reason: str = Field(..., min_length=1, max_length=50)

class SuspensionInfo(BaseModel):
    suspension_reason: str
    suspended_at: datetime
    suspended_until: datetime

class UserSuspendResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    suspension_info: SuspensionInfo

class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"

class AdminUserResponse(BaseModel):
    user_id: str
    email: str
    nickname: str
    points: int
    status: UserStatus
    role: str
    is_snu_verified: bool
    created_at: datetime
    suspended_until: Optional[datetime] = None

class AdminUserListResponse(BaseModel):
    users: List[AdminUserResponse]
    pagination: PaginationInfo


