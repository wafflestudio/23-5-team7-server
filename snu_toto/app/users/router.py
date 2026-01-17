from fastapi import APIRouter, Depends, status

from snu_toto.app.users.schemas import UserSignupRequest, UserResponse
from snu_toto.app.users.services import UserService
from snu_toto.app.users.dependencies import get_user_service


users_router = APIRouter()

@users_router.post("", status_code=status.HTTP_201_CREATED)
async def signup(
    user_in: UserSignupRequest, 
    user_service: UserService = Depends(get_user_service) 
) -> UserResponse:
    return await user_service.signup(user_in)

##################################################################################

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from snu_toto.app.users.models import User 
from snu_toto.app.core.database import get_db_session
@users_router.delete("/debug/delete-by-email", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_by_email_debug(
    email: str, 
    session: AsyncSession = Depends(get_db_session)
):
    """
    [임시/디버그] 특정 이메일을 가진 유저를 DB에서 즉시 삭제합니다.
    주의: 서비스 레이어를 거치지 않고 직접 DB에 접근합니다.
    """
    try:
        # 1. 삭제 쿼리 생성 및 실행
        stmt = delete(User).where(User.email == email)
        result = await session.execute(stmt)
        
        # 2. 실제 삭제된 행이 있는지 확인 (선택 사항)
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"이메일 {email}을(를) 가진 유저가 존재하지 않습니다."
            )
        
        # 3. 변경 사항 반영 (Commit)
        await session.commit()
        return None

    except Exception as e:
        # 에러 발생 시 롤백
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"삭제 중 오류 발생: {str(e)}"
        )