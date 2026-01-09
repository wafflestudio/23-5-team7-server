from pydantic import BaseModel, EmailStr, Field
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

# 인증번호 발송 응답
class EmailSendResponse(BaseModel):
    message: str = "인증번호가 가입하신 이메일로 전송되었습니다."

# 인증번호 확인 요청
class EmailConfirmRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)

# 인증번호 확인 응답
class EmailConfirmResponse(BaseModel):
    email: EmailStr
    is_snu_verified: bool
    message: str = "이메일 인증이 완료되었습니다. 다시 로그인해주세요."


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserLoginResult(BaseModel):
    user_id: str
    nickname: str
    is_snu_verified: bool
    points: int

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserLoginResult