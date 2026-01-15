from typing import Annotated, Sequence, List, Tuple
import uuid
from datetime import datetime

from fastapi import Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from snu_toto.app.events.exceptions import EventNotFoundError
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

    async def get_events_with_cursor(
        self,
        status: EventStatus | None = None,
        cursor_end_at: datetime | None = None,
        cursor_event_id: str | None = None,
        limit: int = 10
    ) -> Tuple[List[Event], bool]:
        """커서 기반 페이지네이션으로 이벤트 목록 조회 (마감 임박순)"""
        query = select(Event)
        
        # 상태 필터링
        if status:
            query = query.where(Event.status == status)
        
        # 커서 조건 (end_at, event_id)
        # 커서보다 나중에 마감되는 이벤트 or 같은 마감 시간이지만 event_id가 더 큰 이벤트
        if cursor_end_at and cursor_event_id:
            query = query.where(
                (Event.end_at > cursor_end_at) |
                ((Event.end_at == cursor_end_at) & (Event.event_id > cursor_event_id))
            )
        
        # 정렬: end_at 오름차순, event_id 오름차순 (동일한 end_at 처리)
        query = query.order_by(Event.end_at.asc(), Event.event_id.asc())
        
        # limit + 1 조회 (has_more 판단용)
        query = query.limit(limit + 1)
        
        result = await self.session.execute(query)
        events = list(result.scalars().all())
        
        # has_more 판단
        has_more = len(events) > limit
        if has_more:
            events = events[:limit]  # 실제로는 limit 개만 반환
        
        return events, has_more


    async def create_event(self, event: Event) -> Event:
        """이벤트, 옵션, 이미지를 DB에 저장"""
        self.session.add(event) # SQLAlchemy의 relationship 덕분에 Event 객체의 options와 images 리스트도 한 번에 저장
        
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def update_event_status(self, event_id: str, new_status: EventStatus) -> None:
        """이벤트의 상태를 업데이트"""
        result = await self.session.execute(update(Event).where(Event.event_id == event_id).values(status=new_status))
        
        # rowcount를 통해 실제 업데이트된 행이 있는지 확인
        if result.rowcount <= 0:
            raise EventNotFoundError()
    
    async def update_status_conditionally(self, event_id: str, target_status: EventStatus, expected_status: EventStatus) -> bool:
        """기대하는 상태일 때만 목표 상태로 변경"""
        result = await self.session.execute((
            update(Event)
            .where(Event.event_id == event_id)
            .where(Event.status == expected_status)
            .values(status=target_status)
        ))
        # 실제 업데이트된 행이 있으면 True, 없으면(상태가 이미 바뀌었거나 ID가 없으면) False 반환
        return result.rowcount > 0
