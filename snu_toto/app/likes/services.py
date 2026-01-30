from sqlalchemy.ext.asyncio import AsyncSession
from snu_toto.app.likes.repositories import LikeRepository
from snu_toto.app.likes.exceptions import LikeAlreadyExistsException, LikeNotFoundException
from snu_toto.app.likes.models import EventLike
from snu_toto.app.events.repositories import EventRepositories
from snu_toto.app.events.exceptions import EventNotFoundError


class LikeService:
    """좋아요 관련 로직"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.like_repo = LikeRepository(session)
        self.event_repo = EventRepositories(session)

    async def add_like(self, event_id: str, user_id: str) -> EventLike:
        """
        좋아요 추가
        """
        # 이벤트 존재 확인
        event = await self.event_repo.get_event_by_id(event_id)
        if not event:
            raise EventNotFoundError()
        
        # 이미 좋아요를 눌렀는지 확인
        existing_like = await self.like_repo.get_like_by_event_and_user(
            event_id, user_id
        )
        if existing_like:
            raise LikeAlreadyExistsException()
        
        # 좋아요 생성
        like = await self.like_repo.create_like(event_id, user_id)
        
        # 이벤트의 like_count 증가
        event.like_count += 1
        
        await self.session.commit()
        return like

    async def remove_like(self, event_id: str, user_id: str) -> str:
        """
        좋아요 취소
        """
        # 이벤트 존재 확인
        event = await self.event_repo.get_event_by_id(event_id)
        if not event:
            raise EventNotFoundError()
        
        # 좋아요 존재 확인
        existing_like = await self.like_repo.get_like_by_event_and_user(
            event_id, user_id
        )
        if not existing_like:
            raise LikeNotFoundException()
        
        # 좋아요 삭제
        await self.like_repo.delete_like(existing_like)
        
        # 이벤트의 like_count 감소
        if event.like_count > 0:
            event.like_count -= 1
        
        await self.session.commit()
        return event_id
