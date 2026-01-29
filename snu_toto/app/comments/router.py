from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, status
from snu_toto.app.comments.services import CommentService
from snu_toto.app.comments.schemas import (
    CommentCreateRequest,
    CommentResponse,
    CommentListResponse
)
from snu_toto.app.auth.dependencies import get_current_user
from snu_toto.app.users.models import User

comment_router = APIRouter()


@comment_router.post("/events/{event_id}/comments", status_code=status.HTTP_201_CREATED)
async def create_comment(
    event_id: str,
    data: CommentCreateRequest,
    service: Annotated[CommentService, Depends()],
    current_user: Annotated[User, Depends(get_current_user)]
) -> CommentResponse:
    """댓글 작성"""
    return await service.create_comment(
        event_id=event_id,
        user_id=current_user.user_id,
        data=data
    )


@comment_router.get("/events/{event_id}/comments", status_code=status.HTTP_200_OK)
async def get_comments(
    event_id: str,
    service: Annotated[CommentService, Depends()],
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100)
) -> CommentListResponse:
    """댓글 목록 조회"""
    return await service.get_comments(
        event_id=event_id,
        cursor=cursor,
        limit=limit
    )
