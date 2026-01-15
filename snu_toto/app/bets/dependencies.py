from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from snu_toto.app.core.database import get_db_session
from snu_toto.app.bets.services import BetService

# BetService를 생성해서 반환
def get_bet_service(db: AsyncSession = Depends(get_db_session)) -> BetService:
    return BetService(db)
