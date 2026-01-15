from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from snu_toto.app.bets.models import BetStatus


class BetCreateRequest(BaseModel):
    option_id: str 
    bet_amount: int = Field(..., gt=0)

class BetResponse(BaseModel):
    bet_id: str 
    user_id: str 
    event_id: str 
    option_id: str 
    option_name: str
    bet_amount: int 
    created_at: datetime
    status: BetStatus

    # ORM 객체의 속성을 읽을 수 있게 해줌
    model_config = ConfigDict(from_attributes=True)