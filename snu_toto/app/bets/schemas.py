from datetime import datetime
from pydantic import BaseModel, Field
from snu_toto.app.bets.models import BetStatus

class BetCreateRequest(BaseModel):
    option_id: str = Field(..., description="베팅할 옵션 ID")
    bet_amount: int = Field(..., gt=0, description="베팅 금액 (양수)")

class BetCreateResponse(BaseModel):
    bet_id: str
    user_id: str
    event_id: str
    option_id: str
    option_name: str
    bet_amount: int
    created_at: datetime
    status: BetStatus