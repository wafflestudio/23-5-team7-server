from datetime import datetime
from pydantic import BaseModel, Field


class LikeResponse(BaseModel):
    """좋아요 응답 스키마"""
    like_id: str = Field(..., description="좋아요 ID")
    event_id: str = Field(..., description="이벤트 ID")
    user_id: str = Field(..., description="사용자 ID")
    created_at: datetime = Field(..., description="좋아요 생성 시각")

    class Config:
        from_attributes = True


class LikeDeleteResponse(BaseModel):
    """좋아요 취소 응답 스키마"""
    message: str = Field(..., description="응답 메시지")
    event_id: str = Field(..., description="이벤트 ID")
