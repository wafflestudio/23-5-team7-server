from pydantic import BaseModel
from events.models import EventStatus

class OptionResponse(BaseModel):
    option_id: str
    name: str
    total_bet_amount: int
    participant_count: int
    odds: float
    is_winner: bool

class ImageResponse(BaseModel):
    url: str
    display_order: int

class EventDetailResponse(BaseModel):
    event_id: str
    title: str
    description: str
    status: EventStatus
    total_participants: int
    options: list[OptionResponse]
    images: list[ImageResponse]
