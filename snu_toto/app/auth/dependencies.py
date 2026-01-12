from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from snu_toto.app.core.database import get_db_session
from snu_toto.app.users.repositories import UserRepository
from snu_toto.app.auth.services import AuthService
from snu_toto.app.auth.providers.google import GoogleAuthClient

# 전역적으로 사용할 구글 클라이언트 인스턴스
google_client = GoogleAuthClient()

def get_auth_service(db: AsyncSession = Depends(get_db_session)) -> AuthService:
    """AuthService에 필요한 의존성을 주입하여 생성"""
    user_repo = UserRepository(db)
    return AuthService(user_repo, google_client)