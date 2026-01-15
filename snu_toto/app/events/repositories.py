from typing import Annotated, Sequence, List
import uuid

from fastapi import Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from snu_toto.app.bets.models import Bet
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
    
    async def get_event_for_settlement(self, event_id: str) -> Event | None:
        """정산을 위해 이벤트, 옵션, 베팅 내역, 베팅한 유저 정보를 모두 로드"""
        stmt = (
            select(Event)
            .where(Event.event_id == event_id)
            .options(
                selectinload(Event.options),
                selectinload(Event.bets).selectinload(Bet.user) # 베팅한 유저까지 로드
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
