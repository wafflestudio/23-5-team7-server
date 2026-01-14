from typing import Optional
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis, from_url
from jose import jwt, JWTError

from snu_toto.app.core.config import AUTH_SETTINGS, REDIS_SETTINGS
from snu_toto.app.core.database import get_db_session
from snu_toto.app.users.models import User
from snu_toto.app.users.repositories import UserRepository
from snu_toto.app.auth.services import AuthService, VerificationService
from snu_toto.app.auth.providers.google import GoogleAuthClient
from snu_toto.app.auth.exceptions import BadAuthHeaderException, UnauthenticatedException, InvalidTokenException

security = HTTPBearer(auto_error=False)

# 전역적으로 사용할 구글 클라이언트 인스턴스
google_client = GoogleAuthClient()

def get_auth_service(db: AsyncSession = Depends(get_db_session)) -> AuthService:
    """AuthService에 필요한 의존성을 주입하여 생성"""
    user_repo = UserRepository(db)
    return AuthService(user_repo, google_client)


async def get_redis():
    """Redis 연결"""
    redis = from_url(REDIS_SETTINGS.URL, decode_responses=False)
    try:
        yield redis
    finally:
        await redis.close()

def get_verification_service(redis: Redis = Depends(get_redis)):
    """인증 서비스 반환"""
    return VerificationService(redis)

async def get_current_unverified_user(
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
):
    """토큰 확인하여 인증되지 않은 유저 반환"""

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
        purpose: str = payload.get("purpose")

        # 토큰이 인증 전용인지 확인
        if purpose != "verification":
            raise InvalidTokenException()

    except JWTError:
        raise InvalidTokenException()

    # 토큰에 적힌 유저 ID가 DB에 있는지 확인
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise InvalidTokenException()

    return user

async def get_current_user(
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """유효한 액세스 토큰을 확인하여 현재 로그인한 유저 객체 반환"""

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
        purpose: str = payload.get("purpose")

        # 토큰이 일반 액세스 전용인지 확인
        if purpose != "access":
            raise InvalidTokenException()

        if user_id is None:
            raise InvalidTokenException()

    except JWTError:
        raise InvalidTokenException()

    # DB에서 유저 조회
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise InvalidTokenException()

    return user