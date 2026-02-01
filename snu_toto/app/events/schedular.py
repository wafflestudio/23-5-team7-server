import asyncio
import time
from redis.asyncio import from_url # Redis 연결용
from snu_toto.app.core.config import REDIS_SETTINGS # Redis 설정 임포트
from snu_toto.app.core.database import AsyncSessionLocal
from snu_toto.app.core.date_utils import get_kst_now
from snu_toto.app.events.models import EventStatus
from snu_toto.app.events.services import EventServices
from snu_toto.app.events.repositories import EventRepositories

def get_event_service_manual(session, redis) -> EventServices:
    """수동으로 세션을 주입하여 EventServices 생성"""
    repository = EventRepositories(session=session)
    return EventServices(event_repositories=repository, redis=redis)

async def auto_update_event_status():
    """1초마다 실행되는 상태 자동 업데이트 워커"""
    while True:
        # Redis 연결
        redis = from_url(REDIS_SETTINGS.URL, decode_responses=True)
        
        try:
            # DB 세션 생성
            async with AsyncSessionLocal() as session:
                service = get_event_service_manual(session, redis)
                kst_now = get_kst_now()
                now_ts = int(kst_now.timestamp())
                
                # 1. 매일 20:00 인기 이벤트 선정 배치
                if kst_now.hour == 20 and kst_now.minute == 0:
                    # 오늘 날짜로 된 전용 키 생성 (예: event:batch:done:2026-02-02)
                    today_str = kst_now.strftime("%Y-%m-%d")
                    batch_lock_key = f"event:batch:done:{today_str}"
                    
                    # Redis의 setnx를 이용하여 딱 한 번만 실행 (nx=True, ex=3600초 동안 키 유지)
                    # 성공하면(True) 오늘 처음 실행하는 것, 실패하면(False) 이미 실행된 것
                    is_first_run = await redis.set(batch_lock_key, "done", ex=3600, nx=True)
                    
                    if is_first_run:
                        print(f"[{kst_now}] 20:00 배치 시작: 상위 인기 이벤트 선정 중...")
                        await service.process_daily_event_selection()
                
                # 2. OPEN 대상 처리 (READY -> OPEN)
                open_targets = await redis.zrangebyscore("event:sched:open", "-inf", now_ts)
                for event_id_bytes in open_targets:
                    event_id = event_id_bytes.decode('utf-8') if isinstance(event_id_bytes, bytes) else event_id_bytes
                    await service.update_event_status_auto(event_id, EventStatus.OPEN, EventStatus.READY)
                    await redis.zrem("event:sched:open", event_id)

                # 3. CLOSE 대상 처리 (OPEN -> CLOSED)
                close_targets = await redis.zrangebyscore("event:sched:close", "-inf", now_ts)
                for event_id_bytes in close_targets:
                    event_id = event_id_bytes.decode('utf-8') if isinstance(event_id_bytes, bytes) else event_id_bytes
                    await service.update_event_status_auto(event_id, EventStatus.CLOSED, EventStatus.OPEN)
                    await redis.zrem("event:sched:close", event_id)

                await session.commit()

        except Exception as e:
            print(f"[Scheduler Error] {e}")
        finally:
            await redis.close()

        await asyncio.sleep(1)