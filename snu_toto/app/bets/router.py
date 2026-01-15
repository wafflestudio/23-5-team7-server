from fastapi import APIRouter, Depends, status
from snu_toto.app.bets.schemas import BetCreateRequest, BetResponse
from snu_toto.app.bets.services import BetService
from snu_toto.app.bets.dependencies import get_bet_service
from snu_toto.app.auth.dependencies import get_current_user
from snu_toto.app.users.models import User


bets_router = APIRouter()


@bets_router.post("/{event_id}/bets", status_code=status.HTTP_201_CREATED, response_model=BetResponse)
async def create_bet(
    event_id: str,
    request: BetCreateRequest,
    bet_service: BetService = Depends(get_bet_service),
    current_user: User = Depends(get_current_user)
) -> BetResponse:
    return await bet_service.create_bet(event_id, request, current_user)