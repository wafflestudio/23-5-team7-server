import asyncio
import uuid
import random
from datetime import timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from snu_toto.app.core.config import DB_SETTINGS
from snu_toto.app.core.date_utils import get_kst_now
from snu_toto.app.events.models import Event, EventStatus, EventOption
from snu_toto.app.likes.models import EventLike
from snu_toto.app.bets.models import Bet
from snu_toto.app.users.models import User, UserRole, SocialType
from snu_toto.app.core.security import get_password_hash
from snu_toto.app.events.services import EventServices
from snu_toto.app.events.repositories import EventRepositories
from redis.asyncio import Redis


class EventBuilder:
    def __init__(self, event_service: EventServices, session: AsyncSession):
        self.event_service = event_service
        self.session = session
    
    async def create_event(
        self, creator_id: str, title: str, options: list[str], status: EventStatus,
        start_offset: timedelta, end_offset: timedelta, is_eligible: bool = True,
        like_users: list[User] = None, bet_users: list[tuple[User, str, int]] = None
    ) -> Event:
        now = get_kst_now()
        start_at = now + start_offset
        end_at = now + end_offset
        
        # READY: created_at은 start_at보다 3일 전
        # OPEN/CLOSED: created_at은 start_at보다 1시간 전 (start_at이 과거여도 제약조건 만족)
        if status == EventStatus.READY:
            created_at = start_at - timedelta(days=3)
        else:
            created_at = start_at - timedelta(hours=1)
        
        event = Event(
            event_id=str(uuid.uuid4()), creator_id=creator_id, title=title,
            description="test", status=status, created_at=created_at,
            start_at=start_at, end_at=end_at, is_eligible=is_eligible
        )
        self.session.add(event)
        await self.session.flush()
        
        # 옵션 생성
        opts = []
        for idx, name in enumerate(options):
            opt = EventOption(option_id=str(uuid.uuid4()), event_id=event.event_id, name=name, order=idx, participant_count=0, option_total_amount=0)
            self.session.add(opt)
            opts.append(opt)
        await self.session.flush()
        
        # 좋아요
        if like_users:
            for user in like_users:
                self.session.add(EventLike(like_id=str(uuid.uuid4()), event_id=event.event_id, user_id=user.user_id))
                event.like_count += 1
            await self.session.flush()
        
        # 베팅
        if bet_users and status == EventStatus.OPEN:
            option_map = {opt.name: opt for opt in opts}
            for user, opt_name, amount in bet_users:
                if opt_name in option_map and user.points >= amount:
                    opt = option_map[opt_name]
                    self.session.add(Bet(bet_id=str(uuid.uuid4()), user_id=user.user_id, event_id=event.event_id, option_id=opt.option_id, amount=amount))
                    user.points -= amount
                    opt.participant_count += 1
                    opt.option_total_amount += amount
            await self.session.flush()
        
        # Redis 스케줄러에 등록 → start_at/end_at 시간에 자동 상태 변경
        # - start_at 도달: READY → OPEN (is_eligible=True) / CANCELLED (is_eligible=False)
        # - end_at 도달: OPEN → CLOSED
        await self.event_service._add_to_event_scheduler(event.event_id, event.start_at, event.end_at)
        return event


class UserBuilder:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_batch(self, count: int = 6) -> list[User]:
        users = []
        admin = User(
            user_id=str(uuid.uuid4()), email="admin@snu.ac.kr", nickname="관리자",
            hashed_password=get_password_hash("test123!"), points=50000,
            role=UserRole.ADMIN, is_verified=True, is_snu_verified=True, social_type=SocialType.LOCAL
        )
        self.session.add(admin)
        users.append(admin)
        
        for i in range(1, count):
            user = User(
                user_id=str(uuid.uuid4()), email=f"user{i}@snu.ac.kr", nickname=f"테스트유저{i}",
                hashed_password=get_password_hash("test123!"), points=10000 + i*1000,
                role=UserRole.USER, is_verified=True, is_snu_verified=True, social_type=SocialType.LOCAL
            )
            self.session.add(user)
            users.append(user)
        
        return users


class Seeder:
    def __init__(self, session: AsyncSession, redis: Redis):
        self.session = session
        self.event_service = EventServices(EventRepositories(session), redis)
        self.user_builder = UserBuilder(session)
        self.event_builder = EventBuilder(self.event_service, session)
    
    async def seed(self):
        # 사용자
        users = await self.user_builder.create_batch(6)
        await self.session.commit()
        
        # 이벤트 설정
        now = get_kst_now()
        y20 = now.replace(hour=20, minute=0, second=0, microsecond=0) - timedelta(days=1)
        
        configs = [
            # READY 이벤트: 20:00 선정 대기 (3일 후 시작, is_eligible=False → 선정 필요)
            {
                "title": "READY 3일후시작 좋아요6개 선정예정",
                "opts": ["T1", "Gen.G"],
                "status": EventStatus.READY,
                "start": timedelta(days=3),
                "end": timedelta(days=5),
                "eligible": False,
                "likes": users  # 6명 전부 → 선정 예상
            },
            {
                "title": "READY 3일후시작 좋아요2개 탈락예정",
                "opts": ["팀A", "팀B"],
                "status": EventStatus.READY,
                "start": timedelta(days=3),
                "end": timedelta(days=5),
                "eligible": False,
                "likes": random.sample(users, 2)  # 2명만 → 탈락 예상
            },
            
            # READY 이벤트: 즉시 전환 (1분 후 시작)
            {
                "title": "READY 1분후OPEN 전환",
                "opts": ["맑음", "비"],
                "status": EventStatus.READY,
                "start": timedelta(minutes=1),
                "end": timedelta(days=1),
                "eligible": True,  # 이미 선정됨 → 1분 후 OPEN
                "likes": random.sample(users, 5)
            },
            {
                "title": "READY 1분후CANCELLED 전환",
                "opts": ["옵션1", "옵션2"],
                "status": EventStatus.READY,
                "start": timedelta(minutes=1),
                "end": timedelta(days=1),
                "eligible": False,  # 선정 안됨 → 1분 후 CANCELLED
                "likes": [users[0]]
            },
            
            # OPEN 이벤트: 베팅 진행 중 (다양한 종료 시간)
            {
                "title": "OPEN 1분후종료",
                "opts": ["맨시티", "무승부", "리버풀"],
                "status": EventStatus.OPEN,
                "start": y20 - now,  # 어제 20:00 시작
                "end": timedelta(minutes=1),  # 1분 후 종료
                "likes": random.sample(users, 5),
                "bets": [
                    (u, random.choice(["맨시티", "무승부", "리버풀"]), random.randint(500, 3000))
                    for u in random.sample(users[1:], 3)
                ]
            },
            {
                "title": "OPEN 1시간후종료",
                "opts": ["레이커스", "셀틱스"],
                "status": EventStatus.OPEN,
                "start": y20 - now,  # 어제 20:00 시작
                "end": timedelta(hours=1),  # 1시간 후 종료
                "likes": random.sample(users, 5),
                "bets": [
                    (u, random.choice(["레이커스", "셀틱스"]), random.randint(500, 3000))
                    for u in random.sample(users[1:], 3)
                ]
            },
            {
                "title": "OPEN 1일후종료",
                "opts": ["맑음", "흐림", "비/눈"],
                "status": EventStatus.OPEN,
                "start": timedelta(days=-2),  # 2일 전 시작
                "end": timedelta(days=1),  # 1일 후 종료
                "likes": random.sample(users, 5),
                "bets": [
                    (u, random.choice(["맑음", "흐림", "비/눈"]), random.randint(500, 3000))
                    for u in random.sample(users[1:], 3)
                ]
            },
            
            # CLOSED 이벤트: 이미 종료됨
            {
                "title": "CLOSED 종료된이벤트1",
                "opts": ["홈팀", "원정팀"],
                "status": EventStatus.CLOSED,
                "start": timedelta(days=-2),
                "end": timedelta(hours=-1),
                "likes": random.sample(users, 2)
            },
            {
                "title": "CLOSED 종료된이벤트2",
                "opts": ["홈팀", "원정팀"],
                "status": EventStatus.CLOSED,
                "start": timedelta(days=-2),
                "end": timedelta(hours=-1),
                "likes": random.sample(users, 2)
            },
        ]
        
        # 이벤트 생성
        events = []
        for cfg in configs:
            e = await self.event_builder.create_event(
                creator_id=users[0].user_id, title=cfg["title"], options=cfg["opts"],
                status=cfg["status"], start_offset=cfg["start"], end_offset=cfg["end"],
                is_eligible=cfg.get("eligible", True),
                like_users=cfg.get("likes", []), bet_users=cfg.get("bets", [])
            )
            events.append(e)
        
        await self.session.commit()
        
        # 20:00 자동 선정: 좋아요 상위 3개의 is_eligible을 True로 변경
        # (좋아요 3개 이상인 READY 이벤트만 대상)
        await self.event_service.process_daily_event_selection()
        await self.session.commit()


async def main():
    engine = create_async_engine(DB_SETTINGS.url)
    AsyncSessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    redis = Redis(host="localhost", port=6379, db=0, decode_responses=True)
    
    async with AsyncSessionLocal() as session:
        try:
            seeder = Seeder(session, redis)
            await seeder.seed()
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await redis.close()
            await session.close()
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
