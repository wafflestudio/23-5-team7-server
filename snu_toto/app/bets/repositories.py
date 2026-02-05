from typing import Annotated, List, Optional
import uuid
from fastapi import Depends
from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from snu_toto.app.core.database import get_db_session
from snu_toto.app.bets.models import Bet
from snu_toto.app.events.models import Event, EventOption
from snu_toto.app.users.models import User, PointHistory, PointReason

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
    
    async def update_user_points(self, user_id: str, amount: int, bet_id: str) -> None:
        """사용자 포인트 업데이트 및 히스토리 기록"""
        # 현재 유저 포인트 조회
        user = await self.get_user_by_id(user_id)
        if not user:
            return
        
        # 포인트 차감
        await self.session.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(points=User.points - amount)
        )
        
        # PointHistory 기록 추가
        new_points = user.points - amount
        point_history = PointHistory(
            history_id=str(uuid.uuid4()),
            user_id=user_id,
            bet_id=bet_id,
            change_amount=-amount,  # 음수로 저장 (차감)
            reason=PointReason.BET,
            points_after=new_points
        )
        self.session.add(point_history)
    
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

    async def get_bets_by_event(self, event_id: str) -> List[Bet]:
        """정산을 위해 해당 이벤트의 모든 베팅을 유저 정보와 함께 조회"""
        result = await self.db.execute(
            select(Bet)
            .where(Bet.event_id == event_id)
            .options(selectinload(Bet.user)) # 유저 포인트 업데이트를 위해 함께 로드
        )
        return result.scalars().all()

    async def get_user_by_id_for_update(self, user_id: str) -> Optional[User]:
        """비관적 락(Pessimistic Lock)을 사용하여 유저 정보 조회 (동시성 방지)"""
        result = await self.db.execute(
            select(User)
            .where(User.user_id == user_id)
            .with_for_update() # 포인트를 수정하므로 락을 겁니다.
        )
        return result.scalar_one_or_none()

    async def get_event_summary_for_admin(self, event_id: str):
        """관리자용 이벤트 베팅 요약 조회"""
        # 해당 이벤트의 총 베팅 수와 총 금액을 한 번에 계산
        stmt = (
            select(
                func.count(Bet.bet_id).label("total_count"),
                func.sum(Bet.amount).label("total_amount")
            )
            .where(Bet.event_id == event_id)
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        return {
            "total_bet_count": row.total_count or 0,
            "total_bet_amount": int(row.total_amount or 0)
        }

    async def get_bets_by_event_paginated(
        self, 
        event_id: str, 
        page: int, 
        limit: int
    ) -> List[Bet]:
        """특정 이벤트의 베팅 내역을 유저/옵션 정보와 함께 페이징 조회"""
        offset = (page - 1) * limit
        
        stmt = (
            select(Bet)
            .where(Bet.event_id == event_id)
            .options(
                selectinload(Bet.user),    # 유저 정보 조인
                selectinload(Bet.option)   # 옵션 정보 조인
            )
            .order_by(Bet.created_at.desc()) # 최신순 정렬
            .offset(offset)
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())