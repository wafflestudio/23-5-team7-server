from typing import Annotated
from fastapi import APIRouter, Depends, status
from snu_toto.app.comments.services import CommentService
from snu_toto.app.comments.schemas import CommentCreateRequest, CommentResponse
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
