"""
사용자 랭킹 배치 작업 스케줄러
매시 정각(00분)에 전체 유저의 랭킹을 계산하여 Redis에 저장
"""
import asyncio
import json
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from snu_toto.app.core.config import DB_SETTINGS, REDIS_SETTINGS
from snu_toto.app.users.models import User
from redis.asyncio import from_url


async def update_all_rankings():
    """
    매시 정각에 실행되는 배치 작업
    전체 유저의 랭킹을 계산하여 Redis에 저장
    """
    updated_at = datetime.now().isoformat() # 배치 시작 시각 기록
    print(f"[{datetime.now()}] 랭킹 업데이트 시작...")
    
    # DB 연결
    engine = create_async_engine(DB_SETTINGS.url)
    AsyncSessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. 전체 유저를 포인트 순으로 조회
            result = await session.execute(
                select(User.user_id, User.points, User.nickname)
                .where(User.is_deleted == False) # 탈퇴 유저 제외
                .order_by(User.points.desc())
            )
            users = result.all()
            total_users = len(users)
            
            if total_users == 0:
                print("[랭킹 업데이트] 유저가 없습니다.")
                return
            
            # 2. Redis 연결
            redis = await from_url(REDIS_SETTINGS.URL, decode_responses=True)
            
            try:
                # 3. 파이프라인으로 일괄 저장 (성능 최적화)
                pipe = redis.pipeline()

                # 다음 정각까지 유효 (남은 시간 계산)
                now = datetime.now()
                seconds_until_next_hour = 3600 - (now.minute * 60 + now.second)

                # 글로벌 데이터: 전체 유저 수 저장
                pipe.setex("ranking:total_count", seconds_until_next_hour, str(total_users))

                # 글로벌 데이터: 상위 1000명 리스트 저장 (JSON)
                top_rankings = [
                    {"rank": i + 1, "nickname": u.nickname, "points": u.points}
                    for i, u in enumerate(users[:1000])
                ]
                pipe.setex("ranking:top_list", seconds_until_next_hour, json.dumps(top_rankings))
                
                # 개인 데이터: 유저별 상세 랭킹 저장
                for rank, (user_id, points, _) in enumerate(users, start=1):
                    ranking_data = {
                        "rank": rank,
                        "total_users": total_users,
                        "percentile": round(rank / total_users * 100, 1),
                        "my_points": points
                    }
                    pipe.setex(f"user_ranking:{user_id}", seconds_until_next_hour, json.dumps(ranking_data))
                
                # 기준 시각 저장
                pipe.setex("ranking:updated_at", seconds_until_next_hour, updated_at)
                
                # 4. 일괄 실행
                await pipe.execute()
                
                print(f"[랭킹 업데이트] 완료 - {total_users}명의 랭킹 업데이트됨")
                
            finally:
                await redis.close()
                
        except Exception as e:
            print(f"[랭킹 업데이트] 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()


def start_ranking_scheduler():
    """
    랭킹 업데이트 스케줄러 시작
    매시 정각(00분)에 실행
    """
    scheduler = AsyncIOScheduler()
    
    # 매시 정각에 실행 (cron: 0분마다)
    scheduler.add_job(
        update_all_rankings,
        'cron',
        minute=0,
        id='update_rankings',
        replace_existing=True
    )
    
    # 즉시 한 번 실행 (서버 시작 시 초기 데이터 생성)
    scheduler.add_job(
        update_all_rankings,
        id='initial_ranking_update',
        replace_existing=True
    )
    
    scheduler.start()
    print("[스케줄러] 랭킹 업데이트 스케줄러 시작됨 (매시 00분 실행)")
    
    return scheduler
