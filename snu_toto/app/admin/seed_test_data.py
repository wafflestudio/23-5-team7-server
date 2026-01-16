"""
완전한 테스트 데이터 생성 스크립트
- 여러 테스트 사용자 생성
- 다양한 이벤트 생성
- 사용자들의 베팅 데이터 생성
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from snu_toto.app.core.config import DB_SETTINGS
from snu_toto.app.events.models import Event, EventOption, EventImage, EventStatus
from snu_toto.app.users.models import User, UserRole, SocialType, PointHistory, PointReason
from snu_toto.app.bets.models import Bet, BetStatus
from snu_toto.app.core.security import get_password_hash


async def create_test_users(session: AsyncSession) -> list[str]:
    """여러 테스트 유저 생성"""
    
    test_users = [
        {
            "email": "admin@test.com",
            "password": "admin123!",
            "nickname": "관리자",
            "points": 50000,
            "role": UserRole.ADMIN,
            "is_verified": True,
            "is_snu_verified": True,
            "social_type": SocialType.LOCAL
        },
        {
            "email": "user1@snu.ac.kr",
            "password": "user123!",
            "nickname": "서울대생1",
            "points": 15000,
            "role": UserRole.USER,
            "is_verified": True,
            "is_snu_verified": True,
            "social_type": SocialType.LOCAL
        },
        {
            "email": "user2@gmail.com",
            "password": "user123!",
            "nickname": "일반유저1",
            "points": 8000,
            "role": UserRole.USER,
            "is_verified": True,
            "is_snu_verified": False,
            "social_type": SocialType.GOOGLE
        },
        {
            "email": "user3@test.com",
            "password": "user123!",
            "nickname": "초보유저",
            "points": 10000,
            "role": UserRole.USER,
            "is_verified": True,
            "is_snu_verified": False,
            "social_type": SocialType.LOCAL
        },
        {
            "email": "user4@snu.ac.kr",
            "password": "user123!",
            "nickname": "서울대생2",
            "points": 20000,
            "role": UserRole.USER,
            "is_verified": True,
            "is_snu_verified": True,
            "social_type": SocialType.LOCAL
        },
        {
            "email": "user5@test.com",
            "password": "user123!",
            "nickname": "베팅왕",
            "points": 5000,
            "role": UserRole.USER,
            "is_verified": True,
            "is_snu_verified": False,
            "social_type": SocialType.LOCAL
        }
    ]
    
    user_ids = []
    
    for user_data in test_users:
        # 기존 유저 확인
        result = await session.execute(
            select(User).where(User.email == user_data["email"])
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"✓ 기존 유저 사용: {existing_user.email} ({existing_user.nickname})")
            user_ids.append(existing_user.user_id)
            continue
        
        # 새 유저 생성
        user = User(
            user_id=str(uuid.uuid4()),
            email=user_data["email"],
            hashed_password=get_password_hash(user_data["password"]) if user_data["social_type"] == SocialType.LOCAL else None,
            nickname=user_data["nickname"],
            points=user_data["points"],
            role=user_data["role"],
            is_verified=user_data["is_verified"],
            is_snu_verified=user_data["is_snu_verified"],
            social_type=user_data["social_type"],
            social_id=f"google_{user_data['nickname']}" if user_data["social_type"] == SocialType.GOOGLE else None
        )
        session.add(user)
        await session.flush()
        user_ids.append(user.user_id)
        print(f"✓ 유저 생성: {user.email} ({user.nickname}) - {user.points}P")
    
    return user_ids


async def create_test_events(session: AsyncSession, creator_id: str) -> list[Event]:
    """다양한 테스트 이벤트 생성"""
    
    now = datetime.now()
    
    events_data = [
        # 스포츠 - e스포츠
        {
            "title": "2026 LCK 스프링 결승전 승리팀은?",
            "description": "승리 할 것 같은 팀을 고르세요",
            "status": EventStatus.OPEN,
            "start_at": now - timedelta(hours=2),
            "end_at": now + timedelta(days=1),
            "options": [
                {"name": "T1", "option_image_url": None},
                {"name": "Gen.G", "option_image_url": None}
            ],
            "images": []
        },
        {
            "title": "롤드컵 2026 우승팀 예측",
            "description": "이번 롤드컵 우승팀은?",
            "status": EventStatus.OPEN,
            "start_at": now - timedelta(hours=5),
            "end_at": now + timedelta(days=10),
            "options": [
                {"name": "T1", "option_image_url": None},
                {"name": "DK", "option_image_url": None},
                {"name": "JDG", "option_image_url": None}
            ],
            "images": []
        },
        {
            "title": "발로란트 챔피언스 우승팀은?",
            "description": "VCT 챔피언스 우승 예측",
            "status": EventStatus.OPEN,
            "start_at": now - timedelta(hours=3),
            "end_at": now + timedelta(days=5),
            "options": [
                {"name": "DRX", "option_image_url": None},
                {"name": "PRX", "option_image_url": None}
            ],
            "images": []
        },
        
        # 스포츠 - 축구
        {
            "title": "프리미어리그: 맨시티 vs 리버풀 승자는?",
            "description": "승리 할 것 같은 팀을 고르세요",
            "status": EventStatus.OPEN,
            "start_at": now - timedelta(hours=1),
            "end_at": now + timedelta(days=4),
            "options": [
                {"name": "맨시티 승리", "option_image_url": None},
                {"name": "무승부", "option_image_url": None},
                {"name": "리버풀 승리", "option_image_url": None}
            ],
            "images": []
        },
        {
            "title": "2026 월드컵 우승국 예측",
            "description": "어느 나라가 우승할까요?",
            "status": EventStatus.OPEN,
            "start_at": now - timedelta(hours=3),
            "end_at": now + timedelta(days=7),
            "options": [
                {"name": "브라질", "option_image_url": None},
                {"name": "아르헨티나", "option_image_url": None},
                {"name": "프랑스", "option_image_url": None}
            ],
            "images": []
        },
        {
            "title": "챔피언스리그 결승 진출팀은?",
            "description": "UEFA 챔피언스리그 결승",
            "status": EventStatus.OPEN,
            "start_at": now,
            "end_at": now + timedelta(days=8),
            "options": [
                {"name": "레알 마드리드", "option_image_url": None},
                {"name": "바르셀로나", "option_image_url": None}
            ],
            "images": []
        },
        
        # 스포츠 - 야구
        {
            "title": "2026 KBO 우승팀 예측",
            "description": "올해 한국시리즈 우승팀은?",
            "status": EventStatus.OPEN,
            "start_at": now - timedelta(hours=4),
            "end_at": now + timedelta(days=12),
            "options": [
                {"name": "두산", "option_image_url": None},
                {"name": "LG", "option_image_url": None},
                {"name": "키움", "option_image_url": None}
            ],
            "images": []
        },
        
        # 스포츠 - 농구
        {
            "title": "NBA 플레이오프 우승팀은?",
            "description": "2026 NBA 챔피언 예측",
            "status": EventStatus.OPEN,
            "start_at": now - timedelta(hours=2),
            "end_at": now + timedelta(days=9),
            "options": [
                {"name": "레이커스", "option_image_url": None},
                {"name": "셀틱스", "option_image_url": None}
            ],
            "images": []
        },
        
        # 엔터테인먼트
        {
            "title": "2026년 아카데미 작품상은?",
            "description": "올해의 작품상 수상작",
            "status": EventStatus.CLOSED,
            "start_at": now - timedelta(days=30),
            "end_at": now - timedelta(hours=2),
            "options": [
                {"name": "오펜하이머", "option_image_url": None},
                {"name": "킬러스 오브 더 플라워 문", "option_image_url": None},
                {"name": "바비", "option_image_url": None}
            ],
            "images": []
        },
        {
            "title": "넷플릭스 1위 콘텐츠는?",
            "description": "이번 주 넷플릭스 한국 1위",
            "status": EventStatus.OPEN,
            "start_at": now,
            "end_at": now + timedelta(days=3),
            "options": [
                {"name": "킹덤 시즌4", "option_image_url": None},
                {"name": "오징어게임 시즌2", "option_image_url": None}
            ],
            "images": []
        },
        {
            "title": "빌보드 HOT 100 1위는?",
            "description": "다음 주 빌보드 차트 1위 예측",
            "status": EventStatus.OPEN,
            "start_at": now - timedelta(hours=1),
            "end_at": now + timedelta(days=4),
            "options": [
                {"name": "뉴진스", "option_image_url": None},
                {"name": "블랙핑크", "option_image_url": None}
            ],
            "images": []
        },
        
        # 경제/금융
        {
            "title": "다음 주 비트코인 가격은?",
            "description": "1월 23일 비트코인 가격 범위",
            "status": EventStatus.OPEN,
            "start_at": now,
            "end_at": now + timedelta(days=6),
            "options": [
                {"name": "10만 달러 이상", "option_image_url": None},
                {"name": "9만~10만 달러", "option_image_url": None},
                {"name": "8만~9만 달러", "option_image_url": None}
            ],
            "images": []
        },
        {
            "title": "테슬라 주가는 오를까?",
            "description": "다음 주 테슬라 주가 방향",
            "status": EventStatus.OPEN,
            "start_at": now - timedelta(hours=2),
            "end_at": now + timedelta(days=5),
            "options": [
                {"name": "상승", "option_image_url": None},
                {"name": "하락", "option_image_url": None}
            ],
            "images": []
        },
        {
            "title": "코스피 2700 돌파할까?",
            "description": "이번 달 코스피 2700 돌파 여부",
            "status": EventStatus.OPEN,
            "start_at": now,
            "end_at": now + timedelta(days=14),
            "options": [
                {"name": "돌파한다", "option_image_url": None},
                {"name": "돌파 못한다", "option_image_url": None}
            ],
            "images": []
        },
        
        # 날씨
        {
            "title": "이번 주말 날씨는?",
            "description": "서울 기준 토요일 날씨",
            "status": EventStatus.OPEN,
            "start_at": now - timedelta(hours=1),
            "end_at": now + timedelta(days=2),
            "options": [
                {"name": "맑음", "option_image_url": None},
                {"name": "흐림", "option_image_url": None},
                {"name": "비/눈", "option_image_url": None}
            ],
            "images": []
        },
        {
            "title": "다음 주 첫눈이 올까?",
            "description": "서울 기준 1월 23일~30일",
            "status": EventStatus.OPEN,
            "start_at": now,
            "end_at": now + timedelta(days=7),
            "options": [
                {"name": "온다", "option_image_url": None},
                {"name": "안온다", "option_image_url": None}
            ],
            "images": []
        },
        
        # 기술/IT
        {
            "title": "다음 애플 이벤트 날짜는?",
            "description": "차기 애플 제품 발표 시기",
            "status": EventStatus.OPEN,
            "start_at": now,
            "end_at": now + timedelta(days=15),
            "options": [
                {"name": "2월", "option_image_url": None},
                {"name": "3월", "option_image_url": None},
                {"name": "4월 이후", "option_image_url": None}
            ],
            "images": []
        },
        {
            "title": "ChatGPT 유료 구독자 수는?",
            "description": "2026년 6월 기준 예측",
            "status": EventStatus.OPEN,
            "start_at": now - timedelta(hours=3),
            "end_at": now + timedelta(days=20),
            "options": [
                {"name": "1억 명 이상", "option_image_url": None},
                {"name": "5천만~1억 명", "option_image_url": None},
                {"name": "5천만 명 미만", "option_image_url": None}
            ],
            "images": []
        },
        {
            "title": "삼성 갤럭시 S26 출시일은?",
            "description": "갤럭시 S26 공식 출시 시기",
            "status": EventStatus.OPEN,
            "start_at": now,
            "end_at": now + timedelta(days=11),
            "options": [
                {"name": "2월", "option_image_url": None},
                {"name": "3월", "option_image_url": None}
            ],
            "images": []
        },
        
        # 대학/캠퍼스
        {
            "title": "서울대 정시 경쟁률은?",
            "description": "2026학년도 정시 평균 경쟁률",
            "status": EventStatus.OPEN,
            "start_at": now - timedelta(hours=4),
            "end_at": now + timedelta(days=6),
            "options": [
                {"name": "5:1 이상", "option_image_url": None},
                {"name": "4:1~5:1", "option_image_url": None},
                {"name": "4:1 미만", "option_image_url": None}
            ],
            "images": []
        },
        {
            "title": "이번 학기 축제 헤드라이너는?",
            "description": "서울대 봄 축제 메인 가수",
            "status": EventStatus.OPEN,
            "start_at": now,
            "end_at": now + timedelta(days=10),
            "options": [
                {"name": "아이유", "option_image_url": None},
                {"name": "뉴진스", "option_image_url": None},
                {"name": "에스파", "option_image_url": None}
            ],
            "images": []
        }
    ]
    
    created_events = []
    
    for event_data in events_data:
        # created_at은 start_at보다 이전이어야 함
        created_time = event_data["start_at"] - timedelta(hours=24)
        
        event = Event(
            event_id=str(uuid.uuid4()),
            creator_id=creator_id,
            title=event_data["title"],
            description=event_data["description"],
            status=event_data["status"],
            created_at=created_time,
            start_at=event_data["start_at"],
            end_at=event_data["end_at"]
        )
        session.add(event)
        await session.flush()
        
        # 옵션 추가
        for idx, option_data in enumerate(event_data["options"]):
            option = EventOption(
                option_id=str(uuid.uuid4()),
                event_id=event.event_id,
                name=option_data["name"],
                order=idx,
                participant_count=0,
                option_total_amount=0,
                is_winner=None,
                option_image_url=option_data.get("option_image_url")
            )
            session.add(option)
        
        # 이미지 추가
        for idx, image_url in enumerate(event_data["images"]):
            image = EventImage(
                image_id=str(uuid.uuid4()),
                event_id=event.event_id,
                image_url=image_url,
                display_order=idx
            )
            session.add(image)
        
        created_events.append(event)
        print(f"✓ 이벤트 생성: {event.title} ({event.status.value})")
    
    return created_events


async def create_test_bets(session: AsyncSession, user_ids: list[str], events: list[Event]):
    """테스트 베팅 데이터 생성"""
    
    # 이벤트별 옵션 가져오기
    bets_data = []
    
    # 첫 번째 이벤트 (LCK 결승전) - 여러 유저가 베팅
    if len(events) > 0:
        event = events[0]
        result = await session.execute(
            select(EventOption).where(EventOption.event_id == event.event_id)
        )
        options = list(result.scalars().all())
        
        if len(options) >= 2 and len(user_ids) >= 3:
            bets_data.extend([
                {"user_id": user_ids[1], "option": options[0], "amount": 1000},  # 서울대생1 -> T1
                {"user_id": user_ids[2], "option": options[1], "amount": 500},   # 일반유저1 -> Gen.G
                {"user_id": user_ids[3], "option": options[0], "amount": 2000},  # 초보유저 -> T1
                {"user_id": user_ids[4], "option": options[0], "amount": 3000},  # 서울대생2 -> T1
            ])
    
    # 두 번째 이벤트 (프리미어리그) - 다양한 옵션에 베팅
    if len(events) > 1:
        event = events[1]
        result = await session.execute(
            select(EventOption).where(EventOption.event_id == event.event_id)
        )
        options = list(result.scalars().all())
        
        if len(options) >= 3 and len(user_ids) >= 5:
            bets_data.extend([
                {"user_id": user_ids[1], "option": options[0], "amount": 2000},  # 맨시티
                {"user_id": user_ids[2], "option": options[2], "amount": 1500},  # 리버풀
                {"user_id": user_ids[4], "option": options[1], "amount": 1000},  # 무승부
                {"user_id": user_ids[5], "option": options[0], "amount": 3000},  # 맨시티
            ])
    
    # 세 번째 이벤트 (월드컵) - 소액 베팅
    if len(events) > 2:
        event = events[2]
        result = await session.execute(
            select(EventOption).where(EventOption.event_id == event.event_id)
        )
        options = list(result.scalars().all())
        
        if len(options) >= 2 and len(user_ids) >= 4:
            bets_data.extend([
                {"user_id": user_ids[3], "option": options[0], "amount": 500},   # 브라질
                {"user_id": user_ids[4], "option": options[1], "amount": 1000},  # 아르헨티나
            ])
    
    # 베팅 생성
    for bet_data in bets_data:
        # 유저 정보 가져오기
        user_result = await session.execute(
            select(User).where(User.user_id == bet_data["user_id"])
        )
        user = user_result.scalar_one()
        
        if user.points < bet_data["amount"]:
            print(f"  ⚠ {user.nickname} - 포인트 부족으로 베팅 스킵")
            continue
        
        option = bet_data["option"]
        amount = bet_data["amount"]
        
        # 베팅 생성
        bet = Bet(
            bet_id=str(uuid.uuid4()),
            user_id=user.user_id,
            event_id=option.event_id,
            option_id=option.option_id,
            amount=amount,
            status=BetStatus.PENDING,
            created_at=datetime.now()
        )
        session.add(bet)
        
        # 유저 포인트 차감
        user.points -= amount
        
        # 포인트 히스토리 기록
        point_history = PointHistory(
            history_id=str(uuid.uuid4()),
            user_id=user.user_id,
            bet_id=bet.bet_id,
            change_amount=-amount,
            reason=PointReason.BET,
            points_after=user.points
        )
        session.add(point_history)
        
        # 옵션 통계 업데이트
        option.participant_count += 1
        option.option_total_amount += amount
        
        await session.flush()
        
        # 이벤트 정보 가져오기
        event_result = await session.execute(
            select(Event).where(Event.event_id == option.event_id)
        )
        event = event_result.scalar_one()
        
        print(f"  ✓ {user.nickname} -> {event.title[:20]}... / {option.name} / {amount}P")
    
    print(f"\n총 {len(bets_data)}개의 베팅이 생성되었습니다!")


async def seed_all_data():
    """모든 테스트 데이터 삽입"""
    # DB 연결
    engine = create_async_engine(DB_SETTINGS.url)
    AsyncSessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    
    async with AsyncSessionLocal() as session:
        try:
            print("=" * 60)
            print("테스트 데이터 생성 시작")
            print("=" * 60)
            
            # 1. 사용자 생성
            print("\n[1/3] 테스트 사용자 생성 중...")
            user_ids = await create_test_users(session)
            await session.commit()
            
            # 2. 이벤트 생성
            print(f"\n[2/3] 테스트 이벤트 생성 중...")
            events = await create_test_events(session, user_ids[0])  # 관리자가 생성
            await session.commit()
            
            # 3. 베팅 생성
            print(f"\n[3/3] 테스트 베팅 생성 중...")
            await create_test_bets(session, user_ids, events)
            await session.commit()
            
            print("\n" + "=" * 60)
            print("✅ 테스트 데이터 생성 완료!")
            print("=" * 60)
            print(f"  - 사용자: {len(user_ids)}명")
            print(f"  - 이벤트: {len(events)}개")
            print(f"  - 베팅: 진행됨")
            print("=" * 60)
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ 에러 발생: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            await session.close()
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_all_data())
