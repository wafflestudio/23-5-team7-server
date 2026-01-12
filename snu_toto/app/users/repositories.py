from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from snu_toto.app.users.models import User

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        result = await self.db.execute(select(User).filter(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_nickname(self, nickname: str) -> Optional[User]:
        """닉네임으로 사용자 조회"""
        result = await self.db.execute(select(User).filter(User.nickname == nickname))
        return result.scalar_one_or_none()

    async def get_by_social_id(self, social_type: str, social_id: str) -> Optional[User]:
        """소셜 타입과 ID로 사용자 조회"""
        result = await self.db.execute(
            select(User).filter(
                User.social_type == social_type,
                User.social_id == social_id
            )
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """사용자 객체를 DB에 저장"""
        self.db.add(user)
        await self.db.flush() 
        return user