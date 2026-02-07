from typing import Optional
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis
from snu_toto.app.auth.dependencies import get_redis
from snu_toto.app.core.database import get_db_session, engine, Base
from snu_toto.app.users.models import PointHistory, User
from snu_toto.app.events.models import Event, EventImage, EventStatus
from snu_toto.app.bets.models import Bet


# 스키마
class CreateTestEventRequest(BaseModel):
    title: Optional[str] = Field(None, description="이벤트 제목 (미지정 시 자동 생성)")
    options: list[str] = Field(["옵션1", "옵션2"], description="이벤트 옵션 리스트")
    status: EventStatus = Field(EventStatus.READY, description="이벤트 상태")
    start_days: int = Field(3, description="시작 시간 (현재로부터 며칠 후, 음수 가능)")
    end_days: int = Field(4, description="종료 시간 (현재로부터 며칠 후)")
    is_eligible: bool = Field(True, description="선정 여부")
    like_count: int = Field(0, ge=0, description="좋아요 개수")
    bet_count: int = Field(0, ge=0, description="베팅 개수 (OPEN 상태일 때만 적용)")


router = APIRouter()


@router.post("/clear-data")
async def clear_test_data(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Seed data로 생성된 테스트 데이터만 삭제 (사용자가 직접 생성한 데이터는 유지).
    이메일 패턴으로 인식해서 삭제합니다.
    admin@snu.ac.kr,
    user%@snu.ac.kr \
    """
    try:
        from snu_toto.app.likes.models import EventLike
        from snu_toto.app.comments.models import Comment
        from snu_toto.app.events.models import EventOption
        from sqlalchemy import delete
        
        # 1. 테스트 유저 조회 (이메일 패턴으로 식별)
        test_user_result = await db.execute(
            select(User).where(
                (User.email == "admin@snu.ac.kr") | 
                (User.email.like("user%@snu.ac.kr"))
            )
        )
        test_users = test_user_result.scalars().all()
        test_user_ids = [u.user_id for u in test_users]
        
        if not test_user_ids:
            return {"message": "삭제할 테스트 데이터가 없습니다."}
        
        # 2. 테스트 유저가 생성한 이벤트 조회
        test_event_result = await db.execute(
            select(Event).where(Event.creator_id.in_(test_user_ids))
        )
        test_events = test_event_result.scalars().all()
        test_event_ids = [e.event_id for e in test_events]
        
        # 3. 테스트 이벤트 관련 데이터 삭제
        if test_event_ids:
            # 좋아요 삭제
            await db.execute(delete(EventLike).where(EventLike.event_id.in_(test_event_ids)))
            # 베팅 삭제
            await db.execute(delete(Bet).where(Bet.event_id.in_(test_event_ids)))
            # 댓글 삭제
            try:
                await db.execute(delete(Comment).where(Comment.event_id.in_(test_event_ids)))
            except:
                pass
            # 이벤트 옵션 삭제
            await db.execute(delete(EventOption).where(EventOption.event_id.in_(test_event_ids)))
            # 이벤트 삭제
            await db.execute(delete(Event).where(Event.event_id.in_(test_event_ids)))
        
        # 4. 테스트 유저의 베팅 삭제 (다른 이벤트에 참여한 경우)
        await db.execute(delete(Bet).where(Bet.user_id.in_(test_user_ids)))
        
        # 5. 테스트 유저 삭제
        await db.execute(delete(User).where(User.user_id.in_(test_user_ids)))
        
        await db.commit()
        
        return {
            "message": "테스트 데이터가 삭제되었습니다.",
            "deleted": {
                "users": len(test_user_ids),
                "events": len(test_event_ids) if test_event_ids else 0
            }
        }
    except Exception as e:
        await db.rollback()
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"데이터 삭제 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
        )


@router.post("/reset-database")
async def reset_database(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis)
):
    """DB 초기화 (모든 테이블 삭제 후 재생성) + Redis 랭킹 캐시 삭제"""
    try:
        # 모든 모델 import (Base.metadata에 등록하기 위함)
        from snu_toto.app.users.models import User, PointHistory
        from snu_toto.app.events.models import Event, EventOption, EventImage
        from snu_toto.app.bets.models import Bet
        from snu_toto.app.likes.models import EventLike
        from snu_toto.app.comments.models import Comment
        
        # DB 테이블 삭제 및 재생성
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        
        # Redis 랭킹 캐시 삭제
        ranking_keys = await redis.keys("ranking:*")
        user_ranking_keys = await redis.keys("user_ranking:*")
        all_keys = ranking_keys + user_ranking_keys
        if all_keys:
            await redis.delete(*all_keys)
        
        return {
            "message": "데이터베이스가 초기화되었습니다.",
            "redis_keys_deleted": len(all_keys)
        }
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"DB 초기화 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
        )


@router.post("/seed-data")
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
        from snu_toto.app.test_data.seed_data import Seeder
        
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
            "message": "테스트 데이터가 생성되었습니다.",
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


@router.post("/reset-and-seed-data")
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
        
        # 2. 시딩
        from snu_toto.app.test_data.seed_data import Seeder
        
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
            "message": "데이터베이스가 초기화되고 테스트 데이터가 생성되었습니다.",
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


@router.delete("/users/by-email/{email}")
async def delete_user_by_email(
    email: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    특정 이메일의 사용자와 관련 데이터를 삭제합니다.
    
    - email: 삭제할 사용자의 이메일
    
    삭제되는 데이터:
    - 사용자가 생성한 이벤트 (및 해당 이벤트의 좋아요, 베팅, 댓글, 옵션)
    - 사용자의 베팅
    - 사용자의 좋아요
    - 사용자가 작성한 댓글
    - 사용자의 포인트 기록
    - 사용자 자체
    """
    try:
        from snu_toto.app.likes.models import EventLike
        from snu_toto.app.comments.models import Comment
        from snu_toto.app.events.models import EventOption
        from sqlalchemy import delete
        
        # 사용자 존재 확인
        user_result = await db.execute(
            select(User).where(User.email == email)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"이메일 '{email}'에 해당하는 사용자를 찾을 수 없습니다."
            )
        
        user_id = user.user_id
        
        # 사용자가 생성한 이벤트 조회
        event_result = await db.execute(
            select(Event).where(Event.creator_id == user_id)
        )
        user_events = event_result.scalars().all()
        event_ids = [e.event_id for e in user_events]
        
        # 사용자가 생성한 이벤트 관련 데이터 삭제
        if event_ids:
            # 이벤트 좋아요 삭제
            await db.execute(delete(EventLike).where(EventLike.event_id.in_(event_ids)))
            
            # 이벤트 베팅 삭제
            await db.execute(delete(Bet).where(Bet.event_id.in_(event_ids)))
            
            # 이벤트 댓글 삭제
            try:
                await db.execute(delete(Comment).where(Comment.event_id.in_(event_ids)))
            except:
                pass
            
            # 이벤트 옵션 삭제
            await db.execute(delete(EventOption).where(EventOption.event_id.in_(event_ids)))
            
            # 이벤트 삭제
            await db.execute(delete(Event).where(Event.event_id.in_(event_ids)))
        
        # 사용자의 베팅 삭제 (다른 이벤트에 참여한 경우)
        await db.execute(delete(Bet).where(Bet.user_id == user_id))
        
        # 사용자의 좋아요 삭제
        await db.execute(delete(EventLike).where(EventLike.user_id == user_id))
        
        # 사용자가 작성한 댓글 삭제 (다른 이벤트에 작성한 댓글)
        try:
            await db.execute(delete(Comment).where(Comment.user_id == user_id))
        except:
            pass

        # 사용자의 포인트 기록 삭제
        await db.execute(delete(PointHistory).where(PointHistory.user_id == user_id))
        
        # 사용자 삭제
        await db.execute(delete(User).where(User.user_id == user_id))
        
        await db.commit()
        
        return {
            "message": f"사용자 '{email}'가 삭제되었습니다.",
            "deleted": {
                "user_id": user_id,
                "email": email,
                "events_count": len(event_ids)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"사용자 삭제 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
        )


@router.delete("/events/{event_id}")
async def delete_event_by_id(
    event_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    특정 ID의 이벤트와 관련 데이터를 삭제합니다.
    
    - event_id: 삭제할 이벤트의 ID
    
    삭제되는 데이터:
    - 이벤트에 연결된 좋아요
    - 이벤트에 연결된 베팅
    - 이벤트에 연결된 댓글
    - 이벤트에 연결된 이미지
    - 이벤트 옵션
    - 이벤트 자체
    """
    try:
        from snu_toto.app.likes.models import EventLike
        from snu_toto.app.comments.models import Comment
        from snu_toto.app.events.models import EventOption
        from sqlalchemy import delete
        
        # 이벤트 존재 확인
        event_result = await db.execute(
            select(Event).where(Event.event_id == event_id)
        )
        event = event_result.scalar_one_or_none()
        
        if not event:
            raise HTTPException(
                status_code=404,
                detail=f"이벤트 ID {event_id}를 찾을 수 없습니다."
            )
        
        # 관련 데이터 삭제
        # 좋아요 삭제
        await db.execute(delete(EventLike).where(EventLike.event_id == event_id))
        
        # 베팅 삭제
        await db.execute(delete(Bet).where(Bet.event_id == event_id))
        
        # 댓글 삭제
        try:
            await db.execute(delete(Comment).where(Comment.event_id == event_id))
        except:
            pass

        await db.execute(delete(EventImage).where(EventImage.event_id == event_id))
        
        # 이벤트 옵션 삭제
        await db.execute(delete(EventOption).where(EventOption.event_id == event_id))
        
        # 이벤트 삭제
        await db.execute(delete(Event).where(Event.event_id == event_id))
        
        await db.commit()
        
        return {
            "message": f"이벤트 ID {event_id}가 삭제되었습니다.",
            "deleted_event_id": event_id
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"이벤트 삭제 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
        )


@router.post("/create-test-event")
async def create_custom_test_event(
    request: CreateTestEventRequest = Body(...),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis)
):
    """
    조건을 선택하여 테스트 이벤트 생성
    
    - title: 이벤트 제목 (미지정 시 자동 생성)
    - options: 옵션 리스트 (기본값: ["옵션1", "옵션2"])
    - status: 이벤트 상태 (READY/OPEN/CLOSED)
    - start_days: 시작 시간 (현재로부터 며칠 후, 음수 가능)
    - end_days: 종료 시간 (현재로부터 며칠 후)
    - is_eligible: 선정 여부 (기본값: True)
    - like_count: 좋아요 개수
    - bet_count: 베팅 개수 (OPEN 상태일 때만 적용)
    """
    try:
        from snu_toto.app.test_data.seed_data import EventBuilder
        from snu_toto.app.events.services import EventServices
        from snu_toto.app.events.repositories import EventRepositories
        import random
        
        # 제목 자동 생성
        title = request.title or f"{request.status.value} 테스트이벤트"
        
        # start_days와 end_days 검증: start + 1일 <= end
        if request.start_days + 1 > request.end_days:
            raise HTTPException(
                status_code=400,
                detail=f"종료 시간은 시작 시간보다 최소 1일 이후여야 합니다. (start_days={request.start_days}, end_days={request.end_days})"
            )
        
        # 사용자 조회 (좋아요/베팅용)
        user_result = await db.execute(select(User))
        users = user_result.scalars().all()
        
        if not users:
            raise HTTPException(status_code=400, detail="사용자가 없습니다. 먼저 /test/seed-data를 실행하세요.")
        
        admin_user = next((u for u in users if u.role.value == "ADMIN"), users[0])
        
        # EventBuilder 초기화
        event_service = EventServices(EventRepositories(db), redis)
        event_builder = EventBuilder(event_service, db)
        
        # 좋아요 대상 사용자 선택
        like_users = random.sample(users, min(request.like_count, len(users))) if request.like_count > 0 else []
        
        # 베팅 데이터 생성 (OPEN 상태일 때만)
        bet_users = []
        if request.status == EventStatus.OPEN and request.bet_count > 0:
            available_users = [u for u in users if u.user_id != admin_user.user_id]
            selected_users = random.sample(available_users, min(request.bet_count, len(available_users)))
            bet_users = [
                (u, random.choice(request.options), random.randint(500, 3000))
                for u in selected_users
            ]
        
        # 이벤트 생성
        event = await event_builder.create_event(
            creator_id=admin_user.user_id,
            title=title,
            options=request.options,
            status=request.status,
            start_offset=timedelta(days=request.start_days),
            end_offset=timedelta(days=request.end_days),
            is_eligible=request.is_eligible,
            like_users=like_users,
            bet_users=bet_users
        )
        
        await db.commit()
        
        return {
            "message": "테스트 이벤트가 생성되었습니다.",
            "event": {
                "event_id": event.event_id,
                "title": event.title,
                "status": event.status.value,
                "start_at": event.start_at.isoformat(),
                "end_at": event.end_at.isoformat(),
                "is_eligible": event.is_eligible,
                "like_count": event.like_count,
                "options": request.options
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"테스트 이벤트 생성 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
        )


@router.post("/create-waffle-final-event")
async def create_waffle_final_event(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis)
):
    """
    와플 최종 발표 우승팀 예측 이벤트 생성
    
    - 제목: 와플 최종 발표 우승팀은?
    - 옵션: 1조~10조 팀명
    - 상태: OPEN
    - 시작: 2일 전
    - 종료: 오늘 오후 5시
    - 선정: True
    - 좋아요: 5개
    """
    try:
        from snu_toto.app.events.services import EventServices
        from snu_toto.app.events.repositories import EventRepositories
        from snu_toto.app.core.date_utils import get_kst_now
        from snu_toto.app.core.security import get_password_hash
        from snu_toto.app.users.models import UserRole, SocialType
        import uuid
        from snu_toto.app.events.models import EventOption
        from snu_toto.app.likes.models import EventLike
        
        # 사용자 조회
        user_result = await db.execute(select(User))
        users = list(user_result.scalars().all())
        
        # 사용자가 없으면 테스트 사용자 5명 생성
        if not users:
            for i in range(5):
                user = User(
                    user_id=str(uuid.uuid4()),
                    email=f"admin{i}@snu.ac.kr",
                    nickname=f"와플관리자{i}",
                    hashed_password=get_password_hash("test123!"),
                    points=50000,
                    role=UserRole.ADMIN,
                    is_verified=True,
                    is_snu_verified=True,
                    social_type=SocialType.LOCAL
                )
                db.add(user)
                users.append(user)
            await db.flush()
        
        admin_user = next((u for u in users if u.role.value == "ADMIN"), users[0])
        
        # 시간 설정
        now = get_kst_now()
        start_at = now - timedelta(days=2)
        end_at = now.replace(hour=17, minute=0, second=0, microsecond=0)
        created_at = start_at - timedelta(hours=1)
        
        # 이벤트 생성
        event = Event(
            event_id=str(uuid.uuid4()),
            creator_id=admin_user.user_id,
            title="와플 최종 발표 우승팀은?",
            description="와플스튜디오 최종 발표 우승팀을 예측해보세요!",
            status=EventStatus.OPEN,
            created_at=created_at,
            start_at=start_at,
            end_at=end_at,
            is_eligible=True,
            like_count=0
        )
        db.add(event)
        await db.flush()
        
        # 옵션 생성
        options = [
            "1조 행샤", "2조 알리샤", "3조 SNUXI", "4조 Moiming", "5조 샤터디",
            "6조 바로바로", "7조 스누토토", "8조 AllClear", "9조 감귤마켓", "10조 1gram"
        ]
        for idx, name in enumerate(options):
            opt = EventOption(
                option_id=str(uuid.uuid4()),
                event_id=event.event_id,
                name=name,
                order=idx,
                participant_count=0,
                option_total_amount=0
            )
            db.add(opt)
        await db.flush()
        
        # 좋아요 5개 추가
        like_users = users[:min(5, len(users))]
        for user in like_users:
            db.add(EventLike(
                like_id=str(uuid.uuid4()),
                event_id=event.event_id,
                user_id=user.user_id
            ))
            event.like_count += 1
        await db.flush()
        
        # Redis 스케줄러에 등록
        event_service = EventServices(EventRepositories(db), redis)
        await event_service._add_to_event_scheduler(event.event_id, event.start_at, event.end_at)
        
        await db.commit()
        
        return {
            "message": "와플 최종 발표 이벤트가 생성되었습니다.",
            "event": {
                "event_id": event.event_id,
                "title": event.title,
                "status": event.status.value,
                "start_at": event.start_at.isoformat(),
                "end_at": event.end_at.isoformat(),
                "is_eligible": event.is_eligible,
                "like_count": event.like_count,
                "options": options
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"와플 이벤트 생성 중 오류 발생: {str(e)}\n{traceback.format_exc()}"
        )
