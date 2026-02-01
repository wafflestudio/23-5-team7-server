from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import ValidationError
from snu_toto.app.comments.services import CommentService
from snu_toto.app.comments.schemas import CommentCreateRequest, CommentResponse
from snu_toto.app.auth.dependencies import get_current_user
from snu_toto.app.users.models import User
from snu_toto.app.common.exceptions import SnutotoException


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
