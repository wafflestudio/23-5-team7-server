import filetype
import base64
from redis.asyncio import Redis
from snu_toto.app.bets.settlement.engine import SettlementEngine
from snu_toto.app.events.repositories import EventRepositories
from snu_toto.app.events.exceptions import EventNotFoundError, ImageIndexOutOfBoundsError, ImageTooLargeError, ImageUploadFailedError, InvalidImageFormatError, InvalidStatusTransitionError, InvalidWinnerOptionError, NotClosedEventError, InvalidCursorError
from fastapi import Depends, UploadFile
from typing import Annotated, List
from datetime import datetime
from snu_toto.app.events.models import Event, EventImage, EventStatus, EventOption
from snu_toto.app.events.schemas import EventCreateRequest, EventDetailResponse, EventListResponse, OptionResponse, ImageResponse
from snu_toto.app.events.utils import s3_uploader
from snu_toto.app.auth.dependencies import get_redis
from snu_toto.app.events.websocket import manager

class EventServices:
    def __init__(self, event_repositories: Annotated[EventRepositories, Depends()], redis: Annotated[Redis, Depends(get_redis)]):
        self.event_repositories = event_repositories
        self.redis = redis

    async def create_event(
        self, 
        creator_id: str, 
        data: EventCreateRequest, 
        image_files: List[UploadFile]
    ) -> Event:
        """이벤트 생성"""
        
        # 이미지 인덱스 검증
        self._validate_image_indices(data, len(image_files))
        
        # 이미지 형식/용량 검증
        for file in image_files:
            if file.size > 5 * 1024 * 1024: raise ImageTooLargeError()
            # 파일 바이너리 헤더 검사
            header = await file.read(2048)
            await file.seek(0)
            
            kind = filetype.guess(header)
            if kind is None or kind.mime not in ["image/jpeg", "image/png", "image/webp"]:
                raise InvalidImageFormatError()

        # S3 업로드 (병렬 업로드로 속도 향상)
        import asyncio
        try:
            upload_tasks = [s3_uploader.upload_file(file) for file in image_files]
            image_urls = await asyncio.gather(*upload_tasks)
        except Exception:
            raise ImageUploadFailedError()

        # 객체 조립 및 트랜잭션 처리
        session = self.event_repositories.session
        
        # 이미 트랜잭션이 진행 중인지 확인하여 중복 begin 방지
        if not session.in_transaction():
            async with session.begin():
                created_event = await self._perform_create_event_logic(creator_id, data, image_urls)
                # context manager (begin)에 의해 자동 commit/rollback 발생
        else:
            # 이미 트랜잭션이 시작된 경우
            created_event = await self._perform_create_event_logic(creator_id, data, image_urls)
            await session.flush() # 변경 사항을 DB에 반영하지만 최종 commit은 호출자에게 맡김

        # Redis ZSET에 스케줄 등록
        await self._add_to_event_scheduler(
            created_event.event_id, 
            created_event.start_at, 
            created_event.end_at
        )

        await session.refresh(
            created_event, 
            attribute_names=["options", "images"]
        )
        return created_event
    
    async def _perform_create_event_logic(self, creator_id, data, image_urls) -> Event:
        # Event 객체 생성
        new_event = Event(
            creator_id=creator_id,
            title=data.title,
            description=data.description,
            start_at=data.start_at,
            end_at=data.end_at,
            status=EventStatus.READY
        )

        # 옵션 연결
        for idx, opt_in in enumerate(data.options):
            url = image_urls[opt_in.option_image_index] if opt_in.option_image_index != -1 else None
            new_event.options.append(EventOption(name=opt_in.name, order=idx, option_image_url=url))

        # 이벤트 이미지 연결
        for img_in in data.images:
            new_event.images.append(EventImage(image_url=image_urls[img_in.image_index], display_order=img_in.image_index))

        return await self.event_repositories.create_event(new_event)

    async def _add_to_event_scheduler(self, event_id: str, start_at, end_at):
        """Redis ZSET에 이벤트 시작/종료 시간 등록"""
        # datetime을 timestamp로 변환
        start_ts = int(start_at.timestamp())
        end_ts = int(end_at.timestamp())
        
        # ZADD key score member
        await self.redis.zadd("event:sched:open", {event_id: start_ts})
        await self.redis.zadd("event:sched:close", {event_id: end_ts})

    def _validate_image_indices(self, data: EventCreateRequest, file_count: int):
        """이미지 인덱스가 파일 리스트의 범위를 벗어나는지 확인"""
        # 옵션 이미지 인덱스 검증
        for opt in data.options:
            if opt.option_image_index >= file_count or opt.option_image_index < -1:
                raise ImageIndexOutOfBoundsError()
        
        # 이벤트 이미지 인덱스 검증
        for img in data.images:
            if img.image_index >= file_count or img.image_index < 0:
                raise ImageIndexOutOfBoundsError()
    
    async def update_event_status_auto(self, event_id: str, target_status: EventStatus, expected_status: EventStatus):
        """자동 이벤트 상태 업데이트"""
        session = self.event_repositories.session
        
        if not session.in_transaction():
            async with session.begin():
                return await self.event_repositories.update_status_conditionally(event_id, target_status, expected_status)
        else:
            success = await self.event_repositories.update_status_conditionally(event_id, target_status, expected_status)
            await session.flush()
            return success

    def get_option_details(
        self, 
        option: EventOption,
        total_bet_pool: int
    ) -> OptionResponse:
        """개별 옵션의 배당률을 계산하여 OptionResponse 생성"""
        # 배당률 계산: 전체 풀 / 해당 옵션 베팅 금액
        if option.option_total_amount > 0 and total_bet_pool > 0:
            odds = round(total_bet_pool / option.option_total_amount, 2)
        else:
            odds = 0.0
        
        return OptionResponse(
            option_id=option.option_id,
            name=option.name,
            option_total_amount=option.option_total_amount,
            participant_count=option.participant_count,
            odds=odds,
            is_winner=option.is_winner,
            option_image_url=option.option_image_url
        )

    async def get_event_details(self, event_id: str, user_id: str | None = None) -> EventDetailResponse:
        """이벤트 상세 정보 조회 (옵션, 이미지, 배당률, 좋아요 포함)"""
        event = await self.event_repositories.get_event_by_id(event_id)
        if event is None:
            raise EventNotFoundError()
        
        options = await self.event_repositories.get_options_by_event_id(event_id)
        images = await self.event_repositories.get_images_by_event_id(event_id)

        # total_bet_amount 계산
        total_bet_pool = sum(option.option_total_amount for option in options)

        # total participant 구하기
        total_participants = sum(option.participant_count for option in options)

        # 옵션별 배당률 계산
        option_responses = [
            self.get_option_details(option, total_bet_pool) 
            for option in options
        ]

        # 이미지 응답 생성
        image_responses = [
            ImageResponse(
                image_url=image.image_url
            )
            for image in images
        ]

        # 좋아요 정보 계산
        like_count = event.like_count
        is_liked = None
        if user_id:
            # 로그인 사용자인 경우 좋아요 여부 확인
            from snu_toto.app.likes.repositories import LikeRepository
            like_repo = LikeRepository(self.event_repositories.session)
            existing_like = await like_repo.get_like_by_event_and_user(event_id, user_id)
            is_liked = existing_like is not None

        return EventDetailResponse(
            event_id=event.event_id,
            title=event.title,
            description=event.description,
            status=event.status,
            total_participants=total_participants,
            end_at=event.end_at,
            like_count=like_count,
            is_liked=is_liked,
            options=option_responses,
            images=image_responses
        )
    
    async def get_events(self, status: EventStatus | None = None, user_id: str | None = None) -> List[EventDetailResponse]:
        """이벤트 목록 조회 (각 이벤트의 상세 정보 포함)"""
        events = await self.event_repositories.get_events(status)
        return [await self.get_event_details(event.event_id, user_id) for event in events]
    
    def _encode_cursor(self, end_at: datetime, event_id: str) -> str:
        """커서를 Base64로 인코딩"""
        cursor_str = f"{end_at.isoformat()}|{event_id}"
        return base64.b64encode(cursor_str.encode()).decode()
    
    def _decode_cursor(self, cursor: str) -> tuple[datetime, str]:
        """Base64 커서를 디코딩하여 end_at과 event_id 반환"""
        try:
            decoded = base64.b64decode(cursor.encode()).decode()
            end_at_str, event_id = decoded.split("|")
            end_at = datetime.fromisoformat(end_at_str)
            return end_at, event_id
        except Exception:
            raise InvalidCursorError()
    
    async def get_events_paginated(
        self,
        status: EventStatus | None = None,
        liked: bool | None = None,
        cursor: str | None = None,
        limit: int = 10,
        user_id: str | None = None
    ) -> EventListResponse:
        """커서 기반 페이지네이션으로 이벤트 목록 조회"""
        
        # 커서 디코딩
        cursor_end_at = None
        cursor_event_id = None
        if cursor:
            cursor_end_at, cursor_event_id = self._decode_cursor(cursor)
            
            # 커서로 전달된 이벤트가 존재하는지 확인
            event = await self.event_repositories.get_event_by_id(cursor_event_id)
            if not event:
                raise InvalidCursorError()
        
        # 이벤트 목록 조회 (liked 필터는 repository에서 처리)
        events, has_more = await self.event_repositories.get_events_with_cursor(
            status=status,
            liked=liked,
            user_id=user_id,
            cursor_end_at=cursor_end_at,
            cursor_event_id=cursor_event_id,
            limit=limit
        )
        
        # 이벤트 상세 정보 생성 (좋아요 정보 포함)
        event_details = [await self.get_event_details(event.event_id, user_id) for event in events]
        
        # next_cursor 생성
        next_cursor = None
        if has_more and events:
            last_event = events[-1]
            next_cursor = self._encode_cursor(last_event.end_at, last_event.event_id)
        
        return EventListResponse(
            events=event_details,
            next_cursor=next_cursor,
            has_more=has_more
        )

    
    async def update_event_status(self, event_id: str, new_status: EventStatus) -> None:
        """이벤트 상태 수동 변경 (관리자용)"""
        
        # 이벤트 존재 여부 확인
        event = await self.event_repositories.get_event_by_id(event_id)
        if not event:
            raise EventNotFoundError()

        # 상태 전이 규칙 검사
        current_status = event.status
        if current_status == new_status: # 동일한 상태로 변경하려는 경우 무시 (성공 처리)
            return
        allowed_map = {
            EventStatus.READY: [EventStatus.OPEN, EventStatus.CANCELLED],
            EventStatus.OPEN: [EventStatus.CLOSED, EventStatus.CANCELLED],
            EventStatus.CLOSED: [EventStatus.CANCELLED],
            EventStatus.SETTLED: [],     # 최종 상태
            EventStatus.CANCELLED: []    # 최종 상태
        }
        if new_status not in allowed_map.get(current_status, []):
            raise InvalidStatusTransitionError()
        
        # 상태에 따른 시간 업데이트 값 설정
        update_data = {"status": new_status}
        
        # OPEN으로 변경 시: 시작 시각을 현재로
        if new_status == EventStatus.OPEN:
            update_data["start_at"] = datetime.now()
        
        # CLOSED로 변경 시: 종료 시각을 현재로
        elif new_status == EventStatus.CLOSED:
            update_data["end_at"] = datetime.now()

        session = self.event_repositories.session

        if not session.in_transaction():
            async with session.begin():
                await self.event_repositories.update_event_fields(event_id, update_data)
        else:
            await self.event_repositories.update_event_fields(event_id, update_data)
            await session.flush()
    
    async def settle_event(self, event_id: str, winner_option_ids: List[str]) -> Event:
        """이벤트 결과 확정 및 포인트 정산 실행"""
        session = self.event_repositories.session

        # 정산용 데이터 풀 로드 (Options + Bets + Users)
        event = await self.event_repositories.get_event_for_settlement(event_id)
        if not event:
            raise EventNotFoundError()

        # 이벤트 상태 검증
        if event.status != EventStatus.CLOSED:
            raise NotClosedEventError()

        valid_option_ids = {opt.option_id for opt in event.options}
        for win_id in winner_option_ids:
            if win_id not in valid_option_ids:
                raise InvalidWinnerOptionError()
            
        # 정산 엔진 실행 (트랜잭션 보장)
        engine = SettlementEngine(session)
        
        async def _do_settle():
            await engine.run(event, winner_option_ids)
            return event

        if not session.in_transaction():
            async with session.begin():
                return await _do_settle()
        else:
            result = await _do_settle()
            await session.flush()
            return result

    async def update_odds_and_broadcast(self, event_id: str):
        """배당률 업데이트 및 실시간 브로드캐스트"""
        # 배당률 계산
        updated_event = await self.get_event_details(event_id)
        
        # WebSocket으로 즉시 브로드캐스트
        odds_data = {
            "type": "odds_update",
            "event_id": event_id,
            "options": [
                {
                    "option_id": opt.option_id,
                    "odds": opt.odds
                }
                for opt in updated_event.options
            ]
        }
        
        await manager.broadcast_to_event(event_id, odds_data)