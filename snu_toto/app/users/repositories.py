from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from snu_toto.app.users.models import User
from snu_toto.app.bets.models import Bet, BetStatus
from snu_toto.app.events.models import Event, EventOption

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """ID로 사용자 조회"""
        result = await self.db.execute(select(User).filter(User.user_id == user_id))
        return result.scalar_one_or_none()

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

    async def get_user_bets(
        self,
        user_id: str,
        status: Optional[BetStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[List[dict], int]:
        """
        사용자의 베팅 내역 조회 (필터링, 페이지네이션 지원)
        """
        # 베팅 내역 조회 쿼리 (조인 포함)
        query = (
            select(
                Bet.bet_id,
                Bet.event_id,
                Event.title.label("event_title"),
                Bet.option_id,
                EventOption.name.label("option_name"),
                Bet.amount,
                Bet.status,
                Bet.created_at
            )
            .join(Event, Bet.event_id == Event.event_id)
            .join(EventOption, Bet.option_id == EventOption.option_id)
            .where(Bet.user_id == user_id)
        )
        
        # 상태 필터링
        if status:
            query = query.where(Bet.status == status)
        
        # 최신 순으로 정렬
        query = query.order_by(Bet.created_at.desc())
        
        # 전체 개수 조회
        count_query = select(func.count()).select_from(Bet).where(Bet.user_id == user_id)
        if status:
            count_query = count_query.where(Bet.status == status)
        
        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar()
        
        # 페이지네이션 적용
        query = query.limit(limit).offset(offset)
        
        # 실행
        result = await self.db.execute(query)
        bets = result.mappings().all()
        
        return [dict(bet) for bet in bets], total_count
 
        return user