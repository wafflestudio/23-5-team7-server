from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from snu_toto.app.admin.services import AdminServices
from snu_toto.app.auth.dependencies import get_current_admin_user
from snu_toto.app.bets.schemas import AdminBetListResponse
from snu_toto.app.core.database import get_db_session
from snu_toto.app.users.dependencies import get_user_service
from snu_toto.app.users.models import User
from snu_toto.app.users.schemas import AdminUserListResponse, UserAdminResponse, UserRoleUpdateRequest, UserStatus, UserSuspendRequest, UserSuspendResponse
from snu_toto.app.users.services import UserService


admin_router = APIRouter()


@admin_router.get("/events/{event_id}/bets", status_code=200)
async def get_event_bets_for_admin(
    event_id: str,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    admin_service: AdminServices = Depends(),
    current_admin: User = Depends(get_current_admin_user)
)->AdminBetListResponse:
    """[관리자용] 특정 이벤트의 전체 베팅 조회"""
    return await admin_service.get_event_bets_for_admin(
        event_id=event_id,
        page=page,
        limit=limit
    )

@admin_router.patch("/users/{user_id}/role", status_code=200)
async def update_user_role(
    user_id: str,
    payload: UserRoleUpdateRequest,
    admin_service: AdminServices = Depends(),
    current_admin: User = Depends(get_current_admin_user)
)->UserAdminResponse:
    """[관리자용] 유저 권한 변경"""
    return await admin_service.update_user_role(
        current_admin_id=current_admin.user_id,
        target_user_id=user_id,
        data=payload
    )

@admin_router.post("/users/{user_id}/suspend", status_code=200)
async def suspend_user(
    user_id: str,
    payload: UserSuspendRequest,
    admin_service: AdminServices = Depends(),
    current_admin: User = Depends(get_current_admin_user)
)->UserSuspendResponse:
    """[관리자용] 유저 이용 정지"""
    return await admin_service.suspend_user(
        current_admin_id=current_admin.user_id,
        target_user_id=user_id,
        data=payload
    )

@admin_router.get("/users")
async def get_admin_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1),
    search: Optional[str] = None,
    status_filter: Optional[UserStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_admin_user),
    user_service: UserService = Depends(get_user_service)
)->AdminUserListResponse:  
    return await user_service.get_users_for_admin(page, limit, search, status_filter)
