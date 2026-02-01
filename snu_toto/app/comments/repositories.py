from typing import Annotated
from fastapi import Depends
from sqlalchemy import select
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
