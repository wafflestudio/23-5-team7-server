from typing import Annotated
from fastapi import APIRouter, Depends
from snu_toto.app.bets.dependencies import get_bet_service
from snu_toto.app.bets.services import BetServices
from snu_toto.app.bets.schemas import BetCreateRequest, BetCreateResponse
from snu_toto.app.users.models import User
from snu_toto.app.auth.dependencies import get_current_user

bet_router = APIRouter()

@bet_router.post("/events/{event_id}/bets", status_code=201)
async def create_bet(
    event_id: str,
    bet_data: BetCreateRequest,
    bet_service: Annotated[BetServices, Depends(get_bet_service)],
    current_user: User = Depends(get_current_user)
) -> BetCreateResponse:
    """베팅 생성 API"""
    bet = await bet_service.create_bet(
        user_id=current_user.user_id,
        event_id=event_id,
        bet_data=bet_data
    )
    
    return bet