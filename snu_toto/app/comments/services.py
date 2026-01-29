import base64
import uuid
from typing import Annotated, Optional
from datetime import datetime
from fastapi import Depends
from snu_toto.app.comments.models import Comment
from snu_toto.app.comments.repositories import CommentRepository
from snu_toto.app.comments.schemas import (
    CommentCreateRequest,
    CommentUpdateRequest,
    CommentResponse,
    CommentListResponse
)
from snu_toto.app.comments.exceptions import (
    InvalidCursorException,
    CommentNotFoundException,
    NotCommentOwnerException
)
from snu_toto.app.events.repositories import EventRepositories
from snu_toto.app.events.exceptions import EventNotFoundError
from snu_toto.app.users.models import UserRole


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

    async def get_comments(
        self,
        event_id: str,
        cursor: Optional[str] = None,
        limit: int = 20
    ) -> CommentListResponse:
        """댓글 목록 조회 (커서 기반 페이지네이션)"""
        # 이벤트 존재 확인
        event = await self.event_repo.get_event_by_id(event_id)
        if not event:
            raise EventNotFoundError()
        
        # 커서 디코딩
        cursor_created_at = None
        cursor_comment_id = None
        
        if cursor:
            try:
                decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
                created_at_str, comment_id = decoded.split('_', 1)
                cursor_created_at = datetime.fromisoformat(created_at_str)
                cursor_comment_id = comment_id
            except Exception:
                raise InvalidCursorException()
        
        # 댓글 조회
        comments, has_more = await self.comment_repo.get_comments_by_event_id_with_cursor(
            event_id=event_id,
            cursor_created_at=cursor_created_at,
            cursor_comment_id=cursor_comment_id,
            limit=limit
        )
        
        # 응답 생성
        comment_responses = [
            CommentResponse(
                comment_id=comment.comment_id,
                event_id=comment.event_id,
                user_id=comment.user_id,
                nickname=comment.user.nickname,
                content=comment.content,
                created_at=comment.created_at,
                updated_at=comment.updated_at
            )
            for comment in comments
        ]
        
        # next_cursor 생성
        next_cursor = None
        if has_more and comments:
            last_comment = comments[-1]
            cursor_data = f"{last_comment.created_at.isoformat()}_{last_comment.comment_id}"
            next_cursor = base64.urlsafe_b64encode(cursor_data.encode()).decode()
        
        return CommentListResponse(
            comments=comment_responses,
            next_cursor=next_cursor,
            has_more=has_more
        )

    async def update_comment(
        self,
        comment_id: str,
        user_id: str,
        data: CommentUpdateRequest
    ) -> CommentResponse:
        """댓글 수정"""
        # 댓글 조회
        comment = await self.comment_repo.get_comment_by_id(comment_id)
        if not comment:
            raise CommentNotFoundException()
        
        # 작성자 확인
        if comment.user_id != user_id:
            raise NotCommentOwnerException()
        
        # 내용 수정
        comment.content = data.content.strip()
        comment.updated_at = datetime.now()
        
        updated_comment = await self.comment_repo.update_comment(comment)
        
        return CommentResponse(
            comment_id=updated_comment.comment_id,
            event_id=updated_comment.event_id,
            user_id=updated_comment.user_id,
            nickname=updated_comment.user.nickname,
            content=updated_comment.content,
            created_at=updated_comment.created_at,
            updated_at=updated_comment.updated_at
        )

    async def delete_comment(
        self,
        comment_id: str,
        user_id: str,
        user_role: UserRole
    ) -> None:
        """댓글 삭제"""
        # 댓글 조회
        comment = await self.comment_repo.get_comment_by_id(comment_id)
        if not comment:
            raise CommentNotFoundException()
        
        # 권한 확인 (작성자 본인 또는 관리자)
        if comment.user_id != user_id and user_role != UserRole.ADMIN:
            raise NotCommentOwnerException()
        
        # 삭제
        await self.comment_repo.delete_comment(comment)
