from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from snu_toto.app.core.database import get_db_session, engine, Base
from snu_toto.app.core.config import SETTINGS
from snu_toto.app.users.models import User
from snu_toto.app.events.models import Event, EventOption
from snu_toto.app.bets.models import Bet

# seed 함수들 import
from .seed_test_data import create_test_users, create_test_events, create_test_bets


admin_router = APIRouter()


@admin_router.post("/reset-database")
async def reset_database(db: AsyncSession = Depends(get_db_session)):
    """
    DB를 완전히 초기화합니다. (모든 테이블 삭제 후 재생성)
    
    주의: 프로덕션 환경에서는 사용하지 마세요!
    """
    # 프로덕션 환경 체크
    if SETTINGS.is_prod:
        raise HTTPException(
            status_code=403,
            detail="이 엔드포인트는 프로덕션 환경에서 사용할 수 없습니다."
        )
    
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


@admin_router.post("/seed-test-data")
async def seed_test_data(db: AsyncSession = Depends(get_db_session)):
    """
    테스트용 사용자, 이벤트, 베팅 데이터를 생성합니다.
    
    - 6명의 테스트 사용자
    - 8개의 다양한 이벤트
    - 여러 베팅 데이터
    
    주의: 프로덕션 환경에서는 사용하지 마세요!
    """
    # 프로덕션 환경 체크
    if SETTINGS.is_prod:
        raise HTTPException(
            status_code=403,
            detail="이 엔드포인트는 프로덕션 환경에서 사용할 수 없습니다."
        )
    
    try:
        # 1. 사용자 생성
        user_ids = await create_test_users(db)
        await db.commit()
        
        # 2. 이벤트 생성
        events = await create_test_events(db, user_ids[0])  # 관리자가 생성
        await db.commit()
        
        # 3. 베팅 생성
        await create_test_bets(db, user_ids, events)
        await db.commit()
        
        # 통계 정보 가져오기
        user_count = len(user_ids)
        event_count = len(events)
        
        bet_result = await db.execute(select(Bet))
        bet_count = len(bet_result.scalars().all())
        
        return {
            "status": "success",
            "message": "테스트 데이터가 성공적으로 생성되었습니다.",
            "data": {
                "users_created": user_count,
                "events_created": event_count,
                "bets_created": bet_count
            }
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"테스트 데이터 생성 중 오류가 발생했습니다: {str(e)}"
        )


@admin_router.post("/reset-and-seed")
async def reset_and_seed_database(db: AsyncSession = Depends(get_db_session)):
    """
    데이터베이스를 초기화하고 테스트 데이터를 생성합니다.
    
    DB 삭제 → 재생성 → 테스트 데이터 생성을 한 번에 수행합니다.
    
    주의: 프로덕션 환경에서는 사용하지 마세요!
    """
    # 프로덕션 환경 체크
    if SETTINGS.is_prod:
        raise HTTPException(
            status_code=403,
            detail="이 엔드포인트는 프로덕션 환경에서 사용할 수 없습니다."
        )
    
    try:
        # 1. DB 초기화
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        
        # 2. 테스트 데이터 생성
        user_ids = await create_test_users(db)
        await db.commit()
        
        events = await create_test_events(db, user_ids[0])
        await db.commit()
        
        await create_test_bets(db, user_ids, events)
        await db.commit()
        
        # 통계 정보
        user_count = len(user_ids)
        event_count = len(events)
        
        bet_result = await db.execute(select(Bet))
        bet_count = len(bet_result.scalars().all())
        
        return {
            "status": "success",
            "message": "데이터베이스가 초기화되고 테스트 데이터가 생성되었습니다.",
            "data": {
                "users_created": user_count,
                "events_created": event_count,
                "bets_created": bet_count
            }
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"데이터베이스 초기화 및 테스트 데이터 생성 중 오류가 발생했습니다: {str(e)}"
        )
