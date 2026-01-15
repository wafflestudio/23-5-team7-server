import asyncio
import time
from redis.asyncio import from_url # Redis 연결용
from snu_toto.app.core.config import REDIS_SETTINGS # Redis 설정 임포트
from snu_toto.app.core.database import AsyncSessionLocal
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
        redis = from_url(REDIS_SETTINGS.URL, decode_responses=False)
        
        try:
            # DB 세션 생성
            async with AsyncSessionLocal() as session:
                service = get_event_service_manual(session, redis)
                
                now = int(time.time())
                
                # 1. OPEN 대상 처리 (READY -> OPEN)
                open_targets = await redis.zrangebyscore("event:sched:open", "-inf", now)
                for event_id_bytes in open_targets:
                    event_id = event_id_bytes.decode('utf-8') if isinstance(event_id_bytes, bytes) else event_id_bytes
                    await service.update_event_status_auto(event_id, EventStatus.OPEN, EventStatus.READY)
                    await redis.zrem("event:sched:open", event_id)

                # 2. CLOSE 대상 처리 (OPEN -> CLOSED)
                close_targets = await redis.zrangebyscore("event:sched:close", "-inf", now)
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