from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis
from snu_toto.app.admin.services import AdminServices
from snu_toto.app.auth.dependencies import get_current_admin_user, get_redis
from snu_toto.app.bets.schemas import AdminBetListResponse
from snu_toto.app.core.database import get_db_session, engine, Base
from snu_toto.app.core.config import SETTINGS
from snu_toto.app.users.dependencies import get_user_service
from snu_toto.app.users.models import User
from snu_toto.app.events.models import Event, EventOption, EventStatus
from snu_toto.app.bets.models import Bet
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


################################################################
############# DB 초기화 및 테스트 데이터 생성 관련 코드 ############# 
################################################################

@admin_router.post("/reset-database")
async def reset_database(db: AsyncSession = Depends(get_db_session)):
    """
    DB를 완전히 초기화합니다. (모든 테이블 삭제 후 재생성)
    
    주의: 프로덕션 환경에서는 사용하지 마세요!
    """
    
    try:
        # 모든 테이블 삭제
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        # 모든 테이블 재생성
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        return {
            "status": "success",
            "message": "데이터베이스가 초기화되었습니다."
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"데이터베이스 초기화 중 오류가 발생했습니다: {str(e)}"
        )


################################################################
############# Factory 패턴 기반 시딩 ############# 
################################################################

@admin_router.post("/seed-data")
async def seed_with_factory(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis)
):
    """
    생성되는 데이터:
    - 6명의 테스트 사용자
    - READY 이벤트 4개 (배치 선정 대기 2개, 1분 후 상태전환 2개)
    - OPEN 이벤트 3개 (1분/1시간/1일 후 종료)
    - CLOSED 이벤트 2개
    - 랜덤 베팅 데이터
    """
    try:
        from snu_toto.app.admin.seed_data import Seeder
        
        seeder = Seeder(db, redis)
        await seeder.seed()
        
        # 통계
        user_result = await db.execute(select(User))
        user_count = len(user_result.scalars().all())
        
        event_result = await db.execute(select(Event))
        all_events = event_result.scalars().all()
        
        ready_count = len([e for e in all_events if e.status == EventStatus.READY])
        open_count = len([e for e in all_events if e.status == EventStatus.OPEN])
        closed_count = len([e for e in all_events if e.status == EventStatus.CLOSED])
        
        bet_result = await db.execute(select(Bet))
        bet_count = len(bet_result.scalars().all())
        
        return {
            "status": "success",
            "message": "시드 데이터가 생성되었습니다.",
            "data": {
                "users_created": user_count,
                "events_created": len(all_events),
                "ready_events": ready_count,
                "open_events": open_count,
                "closed_events": closed_count,
                "bets_created": bet_count
            }
        }
    except Exception as e:
        await db.rollback()
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"시딩 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
        )


@admin_router.post("/reset-and-seed-data")
async def reset_and_seed_with_factory(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis)
):
    """
    DB 초기화 + 시딩을 한 번에 실행
    
    READY 이벤트:
    - 배치 선정 대기 2개: 3일 후 시작 예정, is_eligible=False (좋아요 6개/2개)
    - 1분 후 상태전환 2개: is_eligible=True → OPEN, is_eligible=False → CANCELLED
    """
    try:
        # 1. DB 초기화
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        
        # 2. Factory 시딩
        from snu_toto.app.admin.seed_data import Seeder
        
        seeder = Seeder(db, redis)
        await seeder.seed()
        
        # 통계
        user_result = await db.execute(select(User))
        user_count = len(user_result.scalars().all())
        
        event_result = await db.execute(select(Event))
        all_events = event_result.scalars().all()
        
        ready_count = len([e for e in all_events if e.status == EventStatus.READY])
        open_count = len([e for e in all_events if e.status == EventStatus.OPEN])
        closed_count = len([e for e in all_events if e.status == EventStatus.CLOSED])
        
        bet_result = await db.execute(select(Bet))
        bet_count = len(bet_result.scalars().all())
        
        return {
            "status": "success",
            "message": "DB가 초기화되고 데이터가 생성되었습니다.",
            "data": {
                "users_created": user_count,
                "events_created": len(all_events),
                "ready_events": ready_count,
                "open_events": open_count,
                "closed_events": closed_count,
                "bets_created": bet_count
            }
        }
    except Exception as e:
        await db.rollback()
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"DB 초기화 및 시딩 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
        )
