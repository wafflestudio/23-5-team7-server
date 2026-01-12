from pydantic import BaseModel
from datetime import datetime
from snu_toto.app.events.models import EventStatus

class OptionResponse(BaseModel):
    option_id: str
    name: str
    option_total_amount: int
    participant_count: int
    odds: float
    is_winner: bool | None
    option_image_url: str | None

class ImageResponse(BaseModel):
    image_url: str

class EventDetailResponse(BaseModel):
    event_id: str
    title: str
    description: str | None
    status: EventStatus
    total_participants: int
    end_at: datetime
    options: list[OptionResponse]
    images: list[ImageResponse]
