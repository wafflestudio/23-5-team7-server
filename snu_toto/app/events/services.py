from events.repositories import EventRepositories
from events.exceptions import EventNotFoundError
from fastapi import Depends
from typing import Annotated, List
from events.models import EventStatus, EventOption
from events.schemas import EventDetailResponse, OptionResponse, ImageResponse


class EventServices:
    def __init__(self,
                event_repositories: Annotated[EventRepositories, Depends()]
                ):
        self.event_repositories = event_repositories

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
            is_winner=option.is_winner
        )

    async def get_event_details(self, event_id: str) -> EventDetailResponse:
        """이벤트 상세 정보 조회 (옵션, 이미지, 배당률 포함)"""
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
                image_url=image.image_url,
                display_order=image.display_order
            )
            for image in images
        ]

        return EventDetailResponse(
            event_id=event.event_id,
            title=event.title,
            description=event.description,
            status=event.status,
            total_participants=total_participants,
            end_at=event.end_at,
            options=option_responses,
            images=image_responses
        )
    
    async def get_events(self, status: EventStatus | None = None) -> List[EventDetailResponse]:
        """이벤트 목록 조회 (각 이벤트의 상세 정보 포함)"""
        events = await self.event_repositories.get_events(status)
        return [await self.get_event_details(event.event_id) for event in events]
