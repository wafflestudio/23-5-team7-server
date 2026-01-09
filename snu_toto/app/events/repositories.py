from typing import Annotated, Sequence, List
import uuid

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from snu_toto.app.events.models import Event, EventOption
from snu_toto.app.core.database import get_db_session
from snu_toto.app.events.models import EventStatus, EventImage


class EventRepositories:
    def __init__(self, session: Annotated[AsyncSession, Depends(get_db_session)]) -> None:
        self.session = session

    async def get_event_by_id(self, event_id: str) -> Event | None:
        """이벤트 ID로 단일 이벤트 조회"""
        result = await self.session.execute(select(Event).where(Event.event_id == event_id))
        return result.scalar_one_or_none()
    
    async def get_options_by_event_id(self, event_id: str) -> List[EventOption]:
        """이벤트의 모든 옵션 조회 (순서대로 정렬)"""
        result = await self.session.execute(select(EventOption).where(EventOption.event_id == event_id).order_by(EventOption.order))
        return list(result.scalars().all())
    
    async def get_images_by_event_id(self, event_id: str) -> List[EventImage]:
        """이벤트의 모든 이미지 조회 (표시 순서대로 정렬)"""
        result = await self.session.execute(select(EventImage).where(EventImage.event_id == event_id).order_by(EventImage.display_order))
        return list(result.scalars().all())
    
    async def get_events(
            self, 
            status: EventStatus | None = None,
        ) -> List[Event]:
        """이벤트 목록 조회 (상태 필터링 옵션)"""
        query = select(Event)
        if status:
            query = query.where(Event.status == status)

        result = await self.session.execute(query)
        return list(result.scalars().all())
    

