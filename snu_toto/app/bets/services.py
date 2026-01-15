import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from snu_toto.app.bets.models import Bet, BetStatus
from snu_toto.app.bets.repositories import BetRepository
from snu_toto.app.bets.schemas import BetCreateRequest, BetResponse
from snu_toto.app.bets.exceptions import (
    EventNotFoundError,
    OptionNotFoundError,
    EventNotOpenError,
    DuplicateBetError,
    InsufficientBalanceError
)
from snu_toto.app.events.repositories import EventRepositories
from snu_toto.app.events.models import EventStatus
from snu_toto.app.users.models import User, PointHistory, PointReason


class BetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.bet_repo = BetRepository(db)
        self.event_repo = EventRepositories(db)

    async def create_bet(
        self, 
        event_id: str, 
        request: BetCreateRequest,
        user: User
    ) -> BetResponse:
        # 이벤트 조회
        event = await self.event_repo.get_event_by_id(event_id)

        if not event:
            raise EventNotFoundError()

        # 이벤트 상태 확인
        if event.status != EventStatus.OPEN:
            raise EventNotOpenError()

        # 옵션 확인
        option = await self.bet_repo.get_option_by_id(request.option_id)
        if not option:
            raise OptionNotFoundError()

        # 옵션이 해당 이벤트에 속하는지 확인
        if option.event_id != event_id:
            raise OptionNotFoundError()

        # 중복 베팅 확인
        existing_bet = await self.bet_repo.get_bet_by_user_and_event(
            user_id=user.user_id,
            event_id=event_id
        )
        if existing_bet:
            raise DuplicateBetError()

        # 잔액 확인
        if user.points < request.bet_amount:
            raise InsufficientBalanceError()

        # 베팅 생성
        new_bet = Bet(
            user_id=user.user_id,
            event_id=event_id,
            option_id=request.option_id,
            amount=request.bet_amount,
            status=BetStatus.PENDING
        )
        bet = await self.bet_repo.create_bet(new_bet)

        # 유저 포인트 차감
        await self.bet_repo.deduct_points(user, request.bet_amount)

        # 옵션의 총 베팅 금액 및 참여 인원 증가
        await self.bet_repo.update_option_stats(option, request.bet_amount)

        # 포인트 히스토리 기록
        point_history = PointHistory(
            user_id=user.user_id,
            bet_id=bet.bet_id,
            change_amount=-request.bet_amount,
            reason=PointReason.BET,
            points_after=user.points
        )
        await self.bet_repo.create_point_history(point_history)

        # 커밋
        await self.bet_repo.commit()

        # 응답 생성
        return BetResponse(
            bet_id=bet.bet_id,
            user_id=bet.user_id,
            event_id=bet.event_id,
            option_id=bet.option_id,
            option_name=option.name,
            bet_amount=bet.amount,
            created_at=bet.created_at,
            status=bet.status
        )