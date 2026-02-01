from typing import Annotated
from fastapi import Depends
from snu_toto.app.comments.models import Comment
from snu_toto.app.comments.repositories import CommentRepository
from snu_toto.app.comments.schemas import CommentCreateRequest, CommentResponse
from snu_toto.app.events.repositories import EventRepositories
from snu_toto.app.events.exceptions import EventNotFoundError
from snu_toto.app.core.date_utils import get_kst_now


class CommentService:
    def __init__(
        self,
        comment_repository: Annotated[CommentRepository, Depends()],
        event_repository: Annotated[EventRepositories, Depends()]
    ):
        self.comment_repository = comment_repository
        self.event_repository = event_repository

    async def create_comment(
        self,
        event_id: str,
        user_id: str,
        nickname: str,
        data: CommentCreateRequest
    ) -> CommentResponse:
        """댓글 생성"""
        # 이벤트 존재 여부 확인
        event = await self.event_repository.get_event_by_id(event_id)
        if not event:
            raise EventNotFoundError()

        # 댓글 생성
        comment = Comment(
            event_id=event_id,
            user_id=user_id,
            content=data.content.strip(),
            created_at=get_kst_now()
        )

        created_comment = await self.comment_repository.create_comment(comment)
        
        # 응답 생성 (nickname 추가)
        return CommentResponse(
            comment_id=created_comment.comment_id,
            event_id=created_comment.event_id,
            user_id=created_comment.user_id,
            nickname=nickname,
            content=created_comment.content,
            created_at=created_comment.created_at,
            updated_at=created_comment.updated_at
        )
