from typing import Annotated
import base64
from datetime import datetime
from fastapi import Depends
from snu_toto.app.comments.models import Comment
from snu_toto.app.comments.repositories import CommentRepository
from snu_toto.app.comments.schemas import CommentCreateRequest, CommentUpdateRequest, CommentResponse, CommentListResponse
from snu_toto.app.comments.exceptions import InvalidCursorError, CommentNotFoundForUpdateError, NotCommentOwnerError
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

    async def get_comments_by_event(
        self,
        event_id: str,
        cursor: str | None = None,
        limit: int = 20
    ) -> CommentListResponse:
        """이벤트의 댓글 목록 조회 (커서 기반 페이지네이션)"""
        # 이벤트 존재 여부 확인
        event = await self.event_repository.get_event_by_id(event_id)
        if not event:
            raise EventNotFoundError()

        # 커서 파싱
        cursor_created_at = None
        cursor_comment_id = None
        
        if cursor:
            try:
                decoded = base64.b64decode(cursor).decode('utf-8')
                parts = decoded.split('_')
                if len(parts) != 2:
                    raise InvalidCursorError()
                
                cursor_created_at = datetime.fromisoformat(parts[0])
                cursor_comment_id = parts[1]
            except Exception:
                raise InvalidCursorError()

        # 댓글 목록 조회 (limit + 1개 조회)
        comments = await self.comment_repository.get_comments_by_event_with_cursor(
            event_id=event_id,
            cursor_created_at=cursor_created_at,
            cursor_comment_id=cursor_comment_id,
            limit=limit
        )

        # has_more 판단
        has_more = len(comments) > limit
        if has_more:
            comments = comments[:limit]

        # 다음 커서 생성
        next_cursor = None
        if has_more and comments:
            last_comment = comments[-1]
            cursor_str = f"{last_comment.created_at.isoformat()}_{last_comment.comment_id}"
            next_cursor = base64.b64encode(cursor_str.encode('utf-8')).decode('utf-8')

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
        comment = await self.comment_repository.get_comment_by_id(comment_id)
        if not comment:
            raise CommentNotFoundForUpdateError()

        # 권한 확인 (작성자만 수정 가능, 관리자도 불가)
        if comment.user_id != user_id:
            raise NotCommentOwnerError()

        # 댓글 수정
        comment.content = data.content.strip()
        comment.updated_at = get_kst_now()

        updated_comment = await self.comment_repository.update_comment(comment)
        
        return CommentResponse(
            comment_id=updated_comment.comment_id,
            event_id=updated_comment.event_id,
            user_id=updated_comment.user_id,
            nickname=updated_comment.user.nickname,
            content=updated_comment.content,
            created_at=updated_comment.created_at,
            updated_at=updated_comment.updated_at
        )
