from fastapi import APIRouter, Depends, status, Query
from typing import Optional, Annotated
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from snu_toto.app.users.schemas import (
    UserSignupRequest, 
    UserResponse,
    UserBetsResponse,
    UserPointHistoryResponse,
    UserProfileResponse,
    UserStatsResponse,
    UserRankingResponse,
    UserTopRankingResponse,
    UpdateNicknameRequest,
    UpdateNicknameResponse,
    UpdatePasswordRequest,
    UpdatePasswordResponse
)
from snu_toto.app.users.services import UserService
from snu_toto.app.users.dependencies import get_user_service
from snu_toto.app.users.models import User, PointReason
from snu_toto.app.auth.dependencies import get_current_user
from snu_toto.app.bets.models import BetStatus
from snu_toto.app.core.database import get_db_session


users_router = APIRouter()

@users_router.post("", status_code=status.HTTP_201_CREATED)
async def signup(
    user_in: UserSignupRequest, 
    user_service: UserService = Depends(get_user_service) 
) -> UserResponse:
    """회원가입"""
    return await user_service.signup(user_in)

@users_router.get("/me/bets", status_code=status.HTTP_200_OK)
async def get_my_bets(
    status_filter: Optional[BetStatus] = Query(None, alias="status", description="베팅 상태 필터"),
    limit: int = Query(20, ge=1, le=100, description="페이지 크기"),
    offset: int = Query(0, ge=0, description="페이지 오프셋"),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
) -> UserBetsResponse:
    """현재 로그인한 사용자의 베팅 내역 조회 (참여 중인 베팅)"""
    return await user_service.get_my_bets(
        user_id=current_user.user_id,
        status=status_filter,
        limit=limit,
        offset=offset
    )

@users_router.get("/me/point-history", status_code=status.HTTP_200_OK)
async def get_my_point_history(
    reason_filter: Optional[PointReason] = Query(None, alias="reason", description="포인트 변경 사유 필터"),
    limit: int = Query(20, ge=1, le=100, description="페이지 크기"),
    offset: int = Query(0, ge=0, description="페이지 오프셋"),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
) -> UserPointHistoryResponse:
    """현재 로그인한 사용자의 포인트 내역 조회 (베팅 세부 정보 포함)"""
    return await user_service.get_my_point_history(
        user_id=current_user.user_id,
        reason=reason_filter,
        limit=limit,
        offset=offset
    )

@users_router.get("/me/profile", status_code=status.HTTP_200_OK, response_class=JSONResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
) -> UserProfileResponse:
    """현재 로그인한 사용자의 프로필 정보 조회"""
    profile_data = await user_service.get_my_profile(user_id=current_user.user_id)
    return JSONResponse(content=jsonable_encoder(profile_data))

@users_router.get("/me/stats", status_code=status.HTTP_200_OK)
async def get_my_stats(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
) -> UserStatsResponse:
    """현재 로그인한 사용자의 통계 정보 조회"""
    return await user_service.get_my_stats(user_id=current_user.user_id)

@users_router.get("/me/ranking", status_code=status.HTTP_200_OK)
async def get_my_ranking(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
) -> UserRankingResponse:
    """현재 로그인한 사용자의 랜킹 정보 조회"""
    return await user_service.get_my_ranking(user_id=current_user.user_id)

@users_router.patch("/me/nickname", status_code=status.HTTP_200_OK)
async def update_my_nickname(
    request: UpdateNicknameRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
) -> UpdateNicknameResponse:
    """현재 로그인한 사용자의 닉네임 변경"""
    result = await user_service.update_nickname(user_id=current_user.user_id, request=request)
    return UpdateNicknameResponse(**result)

@users_router.patch("/me/password", status_code=status.HTTP_200_OK)
async def update_my_password(
    request: UpdatePasswordRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
) -> UpdatePasswordResponse:
    """현재 로그인한 사용자의 비밀번호 변경"""
    result = await user_service.update_password(user_id=current_user.user_id, request=request)
    return UpdatePasswordResponse(**result)

@users_router.get("/ranking", status_code=200)
async def get_user_ranking(
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    user_service: UserService = Depends(get_user_service)
)->UserTopRankingResponse:
    """포인트 상위 유저 랭킹 조회"""
    return await user_service.get_top_users_with_total(limit)