from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from datetime import datetime, timedelta

from snu_toto.app.core.date_utils import get_kst_now
from snu_toto.app.events.models import EventStatus
from snu_toto.app.events.exceptions import DuplicateOptionNameError, InvalidDateError, InvalidOptionCountError, InvalidOptionNameError
from snu_toto.app.events.models import EventStatus

class OptionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    option_image_index: int = Field(...)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str):
        if not v.strip():
            raise InvalidOptionNameError()
        return v

class EventImageIndexRequest(BaseModel):
    image_index: int

class EventCreateRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=100)
    description: Optional[str] = None
    start_at: datetime
    end_at: datetime
    options: List[OptionCreateRequest]
    images: List[EventImageIndexRequest] = []

    @field_validator('options')
    @classmethod
    def validate_options_count(cls, v: List[OptionCreateRequest]):
        if not (2 <= len(v) <= 10):
            raise InvalidOptionCountError()
        
        names = [opt.name for opt in v]
        if len(names) != len(set(names)):
            raise DuplicateOptionNameError()
        return v

    @model_validator(mode='after')
    def validate_dates(self) -> 'EventCreateRequest':
        now = get_kst_now()
        # 생성일 기준 최소 2일 후 시작 가능
        if self.start_at <= now + timedelta(days=2):
            raise InvalidDateError()
        # 시작일 기준 최소 1일 후 종료 가능
        if self.end_at <= self.start_at + timedelta(days=1):
            raise InvalidDateError()
        return self
    
class OptionCreateResponse(BaseModel):
    option_id: str
    name: str
    order: int
    participant_count: int = 0
    option_total_amount: int = 0
    is_winner: Optional[bool] = None

class EventCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    event_id: str
    creator_id: str
    title: str
    description: Optional[str]
    status: EventStatus
    created_at: datetime
    start_at: datetime
    end_at: datetime
    options: List[OptionCreateResponse]

class EventStatusUpdateRequest(BaseModel):
    status: EventStatus = Field(...)

class OptionResponse(BaseModel):
    option_id: str
    name: str
    option_total_amount: int
    participant_count: int
    odds: float
    is_winner: bool | None
    option_image_url: str | None
    my_bet_amount: int | None = None  # None: 로그인 안함, 0: 베팅 안함, >0: 베팅 금액

class ImageResponse(BaseModel):
    image_url: str

class EventDetailResponse(BaseModel):
    event_id: str
    title: str
    description: str | None
    status: EventStatus
    total_participants: int
    created_at: datetime
    start_at: datetime
    end_at: datetime
    like_count: int
    is_liked: bool | None
    is_eligible: bool
    my_total_bet_amount: int | None = None  # None: 로그인 안함, 0: 베팅 안함, >0: 총 베팅 금액
    options: list[OptionResponse]
    images: list[ImageResponse]

class EventListResponse(BaseModel):
    events: list[EventDetailResponse]
    next_cursor: str | None
    has_more: bool
    
class EventSettleRequest(BaseModel):
    winner_option_ids: List[str] = Field(...)

class WinnerOptionDetail(BaseModel):
    option_id: str
    name: str

class EventSettleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    status: EventStatus # 항상 SETTLED
    winner: List[WinnerOptionDetail]
