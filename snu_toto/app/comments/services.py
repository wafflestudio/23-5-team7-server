import uuid
from typing import Annotated
from fastapi import Depends
from snu_toto.app.comments.models import Comment
from snu_toto.app.comments.repositories import CommentRepository
from snu_toto.app.comments.schemas import CommentCreateRequest, CommentResponse
from snu_toto.app.events.repositories import EventRepositories
from snu_toto.app.events.exceptions import EventNotFoundError


class CommentService:
    def __init__(
        self,
        comment_repo: Annotated[CommentRepository, Depends()],
        event_repo: Annotated[EventRepositories, Depends()]
    ) -> None:
        self.comment_repo = comment_repo
        self.event_repo = event_repo

    async def create_comment(
        self,
        event_id: str,
        user_id: str,
        data: CommentCreateRequest
    ) -> CommentResponse:
        """댓글 작성"""
        # 이벤트 존재 확인
        event = await self.event_repo.get_event_by_id(event_id)
        if not event:
            raise EventNotFoundError()
        
        # 댓글 생성
        comment = Comment(
            comment_id=str(uuid.uuid4()),
            event_id=event_id,
            user_id=user_id,
            content=data.content.strip()
        )
        
        created_comment = await self.comment_repo.create_comment(comment)
        
        return CommentResponse(
            comment_id=created_comment.comment_id,
            event_id=created_comment.event_id,
            user_id=created_comment.user_id,
            nickname=created_comment.user.nickname,
            content=created_comment.content,
            created_at=created_comment.created_at,
            updated_at=created_comment.updated_at
        )
