from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from snu_toto.app.likes.models import EventLike


class LikeRepository:
    """좋아요 관련 데이터베이스 작업"""

    @staticmethod
    async def create_like(db: AsyncSession, event_id: str, user_id: str) -> EventLike:
        """좋아요 생성"""
        like = EventLike(
            event_id=event_id,
            user_id=user_id
        )
        db.add(like)
        await db.flush()
        await db.refresh(like)
        return like

    @staticmethod
    async def get_like_by_event_and_user(
        db: AsyncSession, 
        event_id: str, 
        user_id: str
    ) -> EventLike | None:
        """특정 사용자의 특정 이벤트 좋아요 조회"""
        result = await db.execute(
            select(EventLike).where(
                EventLike.event_id == event_id,
                EventLike.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_like(db: AsyncSession, like: EventLike) -> None:
        """좋아요 삭제"""
        await db.delete(like)
        await db.flush()

    @staticmethod
    async def get_event_likes_count(db: AsyncSession, event_id: str) -> int:
        """특정 이벤트의 좋아요 수 조회"""
        result = await db.execute(
            select(EventLike).where(EventLike.event_id == event_id)
        )
        return len(result.scalars().all())
