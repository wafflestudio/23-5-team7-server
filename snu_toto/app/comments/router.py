from typing import Annotated
from fastapi import APIRouter, Depends, Query, Response
from pydantic import ValidationError
from snu_toto.app.comments.services import CommentService
from snu_toto.app.comments.schemas import CommentCreateRequest, CommentUpdateRequest, CommentResponse, CommentListResponse
from snu_toto.app.auth.dependencies import get_current_user
from snu_toto.app.users.models import User, UserRole
from snu_toto.app.common.exceptions import SnutotoException, InvalidFormatException


comment_router = APIRouter()


@comment_router.post("/events/{event_id}/comments", status_code=201)
async def create_comment(
    event_id: str,
    data: CommentCreateRequest,
    service: Annotated[CommentService, Depends()],
    current_user: User = Depends(get_current_user)
) -> CommentResponse:
    """댓글 작성"""
    try:
        return await service.create_comment(
            event_id=event_id,
            user_id=current_user.user_id,
            nickname=current_user.nickname,
            data=data
        )
    except ValidationError as e:
        # Pydantic validation 에러 처리
        for error in e.errors():
            original_error = error.get("ctx", {}).get("error")
            if isinstance(original_error, SnutotoException):
                raise original_error
        raise


@comment_router.get("/events/{event_id}/comments", status_code=200)
async def get_comments(
    event_id: str,
    service: Annotated[CommentService, Depends()],
    cursor: str | None = Query(None, description="다음 페이지를 위한 커서"),
    limit: int = Query(20, ge=1, le=100, description="한 번에 가져올 댓글 수")
) -> CommentListResponse:
    """댓글 목록 조회 (커서 기반 페이지네이션)"""
    # limit 범위 검증 (Query에서 자동 처리되지만 명시적 에러를 위해)
    if limit < 1 or limit > 100:
        raise InvalidFormatException()
    
    return await service.get_comments_by_event(
        event_id=event_id,
        cursor=cursor,
        limit=limit
    )


@comment_router.patch("/comments/{comment_id}", status_code=200)
async def update_comment(
    comment_id: str,
    data: CommentUpdateRequest,
    service: Annotated[CommentService, Depends()],
    current_user: User = Depends(get_current_user)
) -> CommentResponse:
    """댓글 수정 (작성자만 가능)"""
    try:
        return await service.update_comment(
            comment_id=comment_id,
            user_id=current_user.user_id,
            data=data
        )
    except ValidationError as e:
        # Pydantic validation 에러 처리
        for error in e.errors():
            original_error = error.get("ctx", {}).get("error")
            if isinstance(original_error, SnutotoException):
                raise original_error
        raise


@comment_router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: str,
    service: Annotated[CommentService, Depends()],
    current_user: User = Depends(get_current_user)
) -> Response:
    """댓글 삭제 (작성자 또는 관리자만 가능)"""
    is_admin = current_user.role == UserRole.ADMIN
    await service.delete_comment(
        comment_id=comment_id,
        user_id=current_user.user_id,
        is_admin=is_admin
    )
    return Response(status_code=204)
