from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
from snu_toto.app.bets.models import BetStatus
from snu_toto.app.common.schemas import PaginationInfo

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

class AdminBetUserResponse(BaseModel):
    user_id: str
    email: str
    nickname: str

class AdminBetOptionResponse(BaseModel):
    option_id: str
    name: str

class AdminBetResponse(BaseModel):
    bet_id: str
    user: AdminBetUserResponse
    selected_option: AdminBetOptionResponse
    amount: int
    status: BetStatus
    created_at: datetime

class AdminEventSummary(BaseModel):
    event_id: str
    title: str
    total_bet_count: int
    total_bet_amount: int

class AdminBetListResponse(BaseModel):
    event_info: AdminEventSummary
    bets: List[AdminBetResponse]
    pagination: PaginationInfo