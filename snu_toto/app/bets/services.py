import uuid
from typing import Annotated, TYPE_CHECKING
from fastapi import Depends
from snu_toto.app.bets.repositories import BetRepositories
from snu_toto.app.bets.exceptions import (
    EventNotFoundError,
    InsufficientBalanceError,
    OptionNotFoundError,
    EventNotOpenError,
    DuplicateBetError
)
from snu_toto.app.bets.models import Bet, BetStatus
from snu_toto.app.bets.schemas import BetCreateRequest, BetCreateResponse
from snu_toto.app.events.models import EventStatus
from snu_toto.app.events.services import EventServices

class BetServices:
    def __init__(
        self, 
        bet_repositories: Annotated[BetRepositories, Depends()],
        event_service: Annotated["EventServices", Depends()] = None
    ) -> None:
        self.bet_repositories = bet_repositories
        self.event_service = event_service
    
    async def create_bet(
        self,
        user_id: str,
        event_id: str,
        bet_data: BetCreateRequest
    ) -> BetCreateResponse:
        """베팅 생성"""
        
        # 1. 이벤트 존재 확인
        event = await self.bet_repositories.get_event_by_id(event_id)
        if not event:
            raise EventNotFoundError()
        
        # 2. 이벤트가 OPEN 상태인지 확인
        if event.status != EventStatus.OPEN:
            raise EventNotOpenError()
        
        # 3. 옵션 존재 확인 및 해당 이벤트의 옵션인지 확인
        option = await self.bet_repositories.get_option_by_id(bet_data.option_id)
        if not option or option.event_id != event_id:
            raise OptionNotFoundError()
        
        # 4. 중복 베팅 확인
        existing_bet = await self.bet_repositories.get_bet_by_user_and_event(user_id, event_id)
        if existing_bet:
            raise DuplicateBetError()
        
        # 5. 사용자 잔액 확인
        user = await self.bet_repositories.get_user_by_id(user_id)
        if not user or user.points < bet_data.bet_amount:
            raise InsufficientBalanceError()
        
        # 6. 트랜잭션 처리
        session = self.bet_repositories.session
        
        try:
            if not session.in_transaction():
                async with session.begin():
                    # 베팅 생성
                    bet = Bet(
                        bet_id=str(uuid.uuid4()),
                        user_id=user_id,
                        event_id=event_id,
                        option_id=bet_data.option_id,
                        amount=bet_data.bet_amount,
                        status=BetStatus.PENDING
                    )
                    bet = await self.bet_repositories.create_bet(bet)
                    
                    # 사용자 포인트 차감
                    await self.bet_repositories.update_user_points(user_id, bet_data.bet_amount)
                    
                    # 옵션 통계 업데이트
                    await self.bet_repositories.update_option_stats(bet_data.option_id, bet_data.bet_amount)
            else:
                # 베팅 생성
                bet = Bet(
                    bet_id=str(uuid.uuid4()),
                    user_id=user_id,
                    event_id=event_id,
                    option_id=bet_data.option_id,
                    amount=bet_data.bet_amount,
                    status=BetStatus.PENDING
                )
                bet = await self.bet_repositories.create_bet(bet)
                
                # 사용자 포인트 차감
                await self.bet_repositories.update_user_points(user_id, bet_data.bet_amount)
                
                # 옵션 통계 업데이트
                await self.bet_repositories.update_option_stats(bet_data.option_id, bet_data.bet_amount)
                
                await session.flush()
            
            response = BetCreateResponse(
                bet_id=bet.bet_id,
                user_id=bet.user_id,
                event_id=bet.event_id,
                option_id=bet.option_id,
                option_name=option.name,
                bet_amount=bet.amount,
                created_at=bet.created_at,
                status=bet.status
            )
            
            # 베팅 완료 후 실시간 배당률 브로드캐스트
            if self.event_service:
                await self.event_service.update_odds_and_broadcast(event_id)
            
            return response
        except Exception as e:
            # 커스텀 예외는 그대로 전달
            if isinstance(e, (EventNotFoundError, InsufficientBalanceError, OptionNotFoundError, 
                            EventNotOpenError, DuplicateBetError)):
                raise
            # 그 외 예외는 재발생
            raise