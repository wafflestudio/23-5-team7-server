from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from snu_toto.app.comments.exceptions import EmptyCommentContentError


class CommentCreateRequest(BaseModel):
    """댓글 생성 요청"""
    content: str = Field(..., min_length=1, max_length=2000, description="댓글 내용 (1~2000자)")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str):
        if not v.strip():
            raise EmptyCommentContentError()
        return v


class CommentUpdateRequest(BaseModel):
    """댓글 수정 요청"""
    content: str = Field(..., min_length=1, max_length=2000, description="댓글 내용 (1~2000자)")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str):
        if not v.strip():
            raise EmptyCommentContentError()
        return v


class CommentResponse(BaseModel):
    """댓글 응답"""
    model_config = ConfigDict(from_attributes=True)

    comment_id: str
    event_id: str
    user_id: str
    nickname: str
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class CommentListResponse(BaseModel):
    """댓글 목록 응답"""
    comments: list[CommentResponse]
    next_cursor: Optional[str] = None
    has_more: bool
