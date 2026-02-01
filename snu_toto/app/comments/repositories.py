from typing import Annotated
from datetime import datetime
from fastapi import Depends
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from snu_toto.app.core.database import get_db_session
from snu_toto.app.comments.models import Comment


class CommentRepository:
    def __init__(self, session: Annotated[AsyncSession, Depends(get_db_session)]) -> None:
        self.session = session

    async def create_comment(self, comment: Comment) -> Comment:
        """댓글 생성"""
        self.session.add(comment)
        await self.session.flush()
        await self.session.refresh(comment, attribute_names=["user"])
        return comment

    async def get_comment_by_id(self, comment_id: str) -> Comment | None:
        """댓글 ID로 단일 댓글 조회 (user 정보 포함)"""
        result = await self.session.execute(
            select(Comment)
            .where(Comment.comment_id == comment_id)
            .options(selectinload(Comment.user))
        )
        return result.scalar_one_or_none()

    async def get_comments_by_event_with_cursor(
        self,
        event_id: str,
        cursor_created_at: datetime | None = None,
        cursor_comment_id: str | None = None,
        limit: int = 20
    ) -> list[Comment]:
        """커서 기반 댓글 목록 조회 (최신순)"""
        query = (
            select(Comment)
            .where(Comment.event_id == event_id)
            .options(selectinload(Comment.user))
        )

        # 커서 적용 (created_at DESC, comment_id DESC)
        if cursor_created_at and cursor_comment_id:
            query = query.where(
                or_(
                    Comment.created_at < cursor_created_at,
                    and_(
                        Comment.created_at == cursor_created_at,
                        Comment.comment_id < cursor_comment_id
                    )
                )
            )

        query = query.order_by(
            Comment.created_at.desc(),
            Comment.comment_id.desc()
        ).limit(limit + 1)  # has_more 판단을 위해 limit + 1 조회

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_comment(self, comment: Comment) -> Comment:
        """댓글 수정"""
        await self.session.flush()
        await self.session.refresh(comment, attribute_names=["user"])
        return comment

    async def delete_comment(self, comment: Comment) -> None:
        """댓글 삭제"""
        await self.session.delete(comment)
        await self.session.flush()
