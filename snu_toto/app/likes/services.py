from sqlalchemy.ext.asyncio import AsyncSession
from snu_toto.app.likes.repositories import LikeRepository
from snu_toto.app.likes.exceptions import LikeAlreadyExistsException
from snu_toto.app.likes.models import EventLike
from snu_toto.app.events.repositories import EventRepositories
from snu_toto.app.events.exceptions import EventNotFoundError


class LikeService:
    """좋아요 관련 로직"""

    @staticmethod
    async def add_like(db: AsyncSession, event_id: str, user_id: str) -> EventLike:
        """
        좋아요 추가
        """
        # 이벤트 존재 확인
        event_repo = EventRepositories(db)
        event = await event_repo.get_event_by_id(event_id)
        if not event:
            raise EventNotFoundError()
        
        # 이미 좋아요를 눌렀는지 확인
        existing_like = await LikeRepository.get_like_by_event_and_user(
            db, event_id, user_id
        )
        if existing_like:
            raise LikeAlreadyExistsException()
        
        # 좋아요 생성
        like = await LikeRepository.create_like(db, event_id, user_id)
        
        # 이벤트의 like_count 증가
        event.like_count += 1
        
        await db.commit()
        return like
