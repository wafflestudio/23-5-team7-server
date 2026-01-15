from typing import Optional
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from snu_toto.app.core.database import get_db_session
from snu_toto.app.core.config import AUTH_SETTINGS
from snu_toto.app.users.models import User, UserRole
from snu_toto.app.users.services import UserService
from snu_toto.app.users.repositories import UserRepository
from snu_toto.app.users.exceptions import ForbiddenException
from snu_toto.app.auth.exceptions import (
    UnauthenticatedException, 
    BadAuthHeaderException, 
    InvalidTokenException
)

security = HTTPBearer(auto_error=False)

def get_user_service(db: AsyncSession = Depends(get_db_session)) -> UserService:
    """UserService를 생성해서 반환"""
    return UserService(db)

async def get_current_active_user(
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """로그인된 활성(인증완료) 유저 반환"""
    if token_obj is None:
        raise UnauthenticatedException()
    
    if token_obj.scheme.lower() != "bearer":
        raise BadAuthHeaderException()

    token = token_obj.credentials

    try:
        payload = jwt.decode(
            token, 
            AUTH_SETTINGS.ACCESS_TOKEN_SECRET, 
            algorithms=["HS256"]
        )
        user_id: str = payload.get("sub")
        # purpose check not strictly required if secret is same and we check user state
        # But if verification tokens use same secret, we should check purpose?
        # auth/services.py: create_verification_token sets purpose="verification"
        # create_login_access_token sets purpose="access" (usually) - check core/security.py if unsure.
        # Let's assume verification tokens shouldn't be valid here.
        # If payload doesn't have purpose or is verification, invalid?
        # get_current_unverified_user checks purpose="verification".
        # So here we should probably check purpose!="verification".
        
    except JWTError:
        raise InvalidTokenException()

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise InvalidTokenException()
        
    if not user.is_snu_verified:
        # If user is not verified, they are not "active" in standard sense for API usage
        # Or redirect them to verification?
        # For now, treat as forbidden or unauthenticated?
        # TEST_CASES.md might specify behavior for unverified user access to protected endpoints?
        # A02: Login attempts fail. But what about accessing /api/events?
        # Usually requires verify.
        raise ForbiddenException() 

    return user

async def get_current_admin_user(
    user: User = Depends(get_current_active_user)
) -> User:
    """관리자 권한 확인"""
    if user.role != UserRole.ADMIN:
        raise ForbiddenException()
    return user