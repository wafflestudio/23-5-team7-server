from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from snu_toto.app.bets.models import Bet
from snu_toto.app.events.models import EventOption
from snu_toto.app.users.models import User, PointHistory, PointReason


class BetRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # 새로운 베팅을 생성
    async def create_bet(self, bet: Bet) -> Bet:
        self.db.add(bet)
        await self.db.flush()
        return bet
    # 특정 유저가 특정 이벤트에 한 베팅 조회 (중복 베팅 확인용)
    async def get_bet_by_user_and_event(self, user_id: str, event_id: str) -> Optional[Bet]:
        result = await self.db.execute(
            select(Bet).filter(
                Bet.user_id == user_id,
                Bet.event_id == event_id
            )
        )
        return result.scalar_one_or_none()

# 옵션 ID로 옵션 조회
    async def get_option_by_id(self, option_id: str) -> Optional[EventOption]:
        result = await self.db.execute(
            select(EventOption).filter(EventOption.option_id == option_id)
        )
        return result.scalar_one_or_none()

# 유저 포인트 차감
    async def deduct_points(self, user: User, amount: int) -> None:
        user.points -= amount
        await self.db.flush()

# 유저 포인트 추가
    async def add_points(self, user: User, amount: int) -> None:
        user.points += amount
        await self.db.flush()

# 옵션의 총 베팅 금액 및 참여 인원 증가
    async def update_option_stats(self, option: EventOption, bet_amount: int) -> None:
        option.option_total_amount += bet_amount
        option.participant_count += 1
        await self.db.flush()

# 포인트 히스토리 기록
    async def create_point_history(self, point_history: PointHistory) -> PointHistory:
        self.db.add(point_history)
        await self.db.flush()
        return point_history

# 트랜잭션 커밋
    async def commit(self) -> None:
        await self.db.commit()
