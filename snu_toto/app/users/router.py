from fastapi import APIRouter, Depends, status

from snu_toto.app.users.schemas import UserSignupRequest, UserResponse
from snu_toto.app.users.services import UserService
from snu_toto.app.users.dependencies import get_user_service


router = APIRouter()

@router.post("", status_code=status.HTTP_201_CREATED)
async def signup(
    user_in: UserSignupRequest, 
    user_service: UserService = Depends(get_user_service) 
) -> UserResponse:
    return await user_service.signup(user_in)