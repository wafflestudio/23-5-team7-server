from typing import Annotated
from fastapi import Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from snu_toto.app.core.database import get_db_session
from snu_toto.app.bets.models import Bet
from snu_toto.app.events.models import Event, EventOption
from snu_toto.app.users.models import User

class BetRepositories:
    def __init__(self, session: Annotated[AsyncSession, Depends(get_db_session)]) -> None:
        self.session = session
    
    async def get_event_by_id(self, event_id: str) -> Event | None:
        """이벤트 조회"""
        result = await self.session.execute(
            select(Event).where(Event.event_id == event_id)
        )
        return result.scalar_one_or_none()
    
    async def get_option_by_id(self, option_id: str) -> EventOption | None:
        """옵션 조회"""
        result = await self.session.execute(
            select(EventOption).where(EventOption.option_id == option_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: str) -> User | None:
        """유저 조회"""
        result = await self.session.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_bet_by_user_and_event(self, user_id: str, event_id: str) -> Bet | None:
        """사용자의 특정 이벤트 베팅 조회"""
        result = await self.session.execute(
            select(Bet).where(
                Bet.user_id == user_id,
                Bet.event_id == event_id
            )
        )
        return result.scalar_one_or_none()
    
    async def create_bet(self, bet: Bet) -> Bet:
        """베팅 생성"""
        self.session.add(bet)
        await self.session.flush()
        await self.session.refresh(bet)
        return bet
    
    async def update_user_points(self, user_id: str, amount: int) -> None:
        """사용자 포인트 업데이트"""
        await self.session.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(points=User.points - amount)
        )
    
    async def update_option_stats(self, option_id: str, amount: int) -> None:
        """옵션 통계 업데이트 (베팅 금액, 참여자 수)"""
        await self.session.execute(
            update(EventOption)
            .where(EventOption.option_id == option_id)
            .values(
                option_total_amount=EventOption.option_total_amount + amount,
                participant_count=EventOption.participant_count + 1
            )
        )