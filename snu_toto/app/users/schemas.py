from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from enum import Enum
from datetime import datetime

from snu_toto.app.common.exceptions import InvalidFormatException, MissingRequiredFieldException
from snu_toto.app.users.exceptions import *
from snu_toto.app.users.models import SocialType, UserRole


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