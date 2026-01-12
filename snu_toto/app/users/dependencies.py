from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from snu_toto.app.core.database import get_db_session
from snu_toto.app.users.services import UserService

def get_user_service(db: AsyncSession = Depends(get_db_session)) -> UserService:
    """UserService를 생성해서 반환"""
    return UserService(db)