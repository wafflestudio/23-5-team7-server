from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from snu_toto.app.core.database import get_db_session
from snu_toto.app.auth.dependencies import get_current_user
from snu_toto.app.users.models import User
from snu_toto.app.likes.services import LikeService
from snu_toto.app.likes.schemas import LikeResponse


router = APIRouter(prefix="/api/events", tags=["likes"])


@router.post("/{event_id}/likes", status_code=status.HTTP_201_CREATED)
async def add_like(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    좋아요 추가
    """
    like = await LikeService.add_like(db, event_id, current_user.user_id)
    return LikeResponse.model_validate(like)
