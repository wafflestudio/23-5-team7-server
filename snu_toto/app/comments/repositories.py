from typing import Annotated, List, Tuple, Optional
from datetime import datetime
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

    async def get_comments_by_event_id_with_cursor(
        self,
        event_id: str,
        cursor_created_at: Optional[datetime] = None,
        cursor_comment_id: Optional[str] = None,
        limit: int = 20
    ) -> Tuple[List[Comment], bool]:
        """이벤트의 댓글 목록 조회 (커서 기반 페이지네이션)"""
        query = select(Comment).where(Comment.event_id == event_id)
        
        # 커서 조건 (created_at, comment_id)
        if cursor_created_at and cursor_comment_id:
            query = query.where(
                (Comment.created_at < cursor_created_at) |
                ((Comment.created_at == cursor_created_at) & (Comment.comment_id < cursor_comment_id))
            )
        
        # 정렬: created_at 내림차순, comment_id 내림차순
        query = query.order_by(Comment.created_at.desc(), Comment.comment_id.desc())
        
        # User 정보 join
        query = query.options(selectinload(Comment.user))
        
        # limit + 1 조회 (has_more 판단용)
        query = query.limit(limit + 1)
        
        result = await self.session.execute(query)
        comments = list(result.scalars().all())
        
        # has_more 판단
        has_more = len(comments) > limit
        if has_more:
            comments = comments[:limit]
        
        return comments, has_more
