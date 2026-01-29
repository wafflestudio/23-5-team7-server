from typing import Annotated, Optional
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from snu_toto.app.comments.models import Comment
from snu_toto.app.core.database import get_db_session


class CommentRepository:
    def __init__(self, session: Annotated[AsyncSession, Depends(get_db_session)]) -> None:
        self.session = session

    async def create_comment(self, comment: Comment) -> Comment:
        """댓글 생성"""
        self.session.add(comment)
        await self.session.commit()
        await self.session.refresh(comment)
        # User 정보 로드
        await self.session.refresh(comment, ['user'])
        return comment
