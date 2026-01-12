from pydantic import BaseModel, EmailStr
from typing import Optional

class GoogleUserResult(BaseModel):
    email: EmailStr
    nickname: Optional[str] = None
    is_snu_verified: bool = False

class GoogleAuthResponse(BaseModel):
    message: str
    needs_signup: bool = False

    # 성공 응답 1
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user: Optional[GoogleUserResult] = None
    
    # 성공 응답 2 (신규 유저)
    email: Optional[EmailStr] = None
    social_id: Optional[str] = None
    social_type: Optional[str] = None
    