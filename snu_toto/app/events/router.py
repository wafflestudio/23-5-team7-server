from typing import Annotated, List
from fastapi import APIRouter, Depends, Query
from snu_toto.app.events.models import EventStatus
from snu_toto.app.events.services import EventServices
from snu_toto.app.events.schemas import EventDetailResponse

event_router = APIRouter()

@event_router.get("/", status_code=200)
async def get_events(
    event_service: Annotated[EventServices, Depends()],
    status: EventStatus | None = Query(None)
) -> List[EventDetailResponse]:
    """이벤트 목록 조회 API"""
    events = await event_service.get_events(status)
    return events

@event_router.get("/{event_id}", status_code=200)
async def get_event_details(
    event_id: str,
    event_service: Annotated[EventServices, Depends()]
) -> EventDetailResponse:
    """이벤트 상세 조회 API"""
    event_details = await event_service.get_event_details(event_id)
    return event_details