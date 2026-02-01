from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from snu_toto.app.comments.exceptions import EmptyCommentContentError


class CommentCreateRequest(BaseModel):
    """댓글 생성 요청"""
    content: str = Field(..., min_length=1, max_length=500, description="댓글 내용 (1~500자)")

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
