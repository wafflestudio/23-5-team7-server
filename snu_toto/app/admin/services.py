from typing import Annotated
from fastapi import Depends
from math import ceil

from snu_toto.app.bets.exceptions import EventNotFoundError
from snu_toto.app.events.repositories import EventRepositories
from snu_toto.app.bets.repositories import BetRepositories
from snu_toto.app.bets.schemas import (
    AdminBetListResponse, AdminEventSummary, AdminBetResponse, 
    AdminBetUserResponse, AdminBetOptionResponse, PaginationInfo
)

class AdminServices:
    def __init__(
        self,
        event_repo: Annotated[EventRepositories, Depends()],
        bet_repo: Annotated[BetRepositories, Depends()]
    ):
        self.event_repo = event_repo
        self.bet_repo = bet_repo

    async def get_event_bets_for_admin(
        self, 
        event_id: str, 
        page: int, 
        limit: int
    ) -> AdminBetListResponse:
        # 이벤트 기본 정보 조회 (존재 확인 및 제목 추출)
        event = await self.event_repo.get_event_by_id(event_id)
        if not event:
            raise EventNotFoundError()

        # 통계 데이터 및 베팅 리스트 조회
        summary_data = await self.bet_repo.get_event_summary_for_admin(event_id)
        bets = await self.bet_repo.get_bets_by_event_paginated(event_id, page, limit)

        # 페이지네이션 정보 계산
        total_count = summary_data["total_bet_count"]
        total_pages = ceil(total_count / limit) if total_count > 0 else 1

        # 응답 객체 조립
        return AdminBetListResponse(
            event_info=AdminEventSummary(
                event_id=event.event_id,
                title=event.title,
                total_bet_count=total_count,
                total_bet_amount=summary_data["total_bet_amount"]
            ),
            bets=[
                AdminBetResponse(
                    bet_id=bet.bet_id,
                    user=AdminBetUserResponse(
                        user_id=bet.user.user_id,
                        email=bet.user.email,
                        nickname=bet.user.nickname
                    ),
                    selected_option=AdminBetOptionResponse(
                        option_id=bet.option.option_id,
                        name=bet.option.name
                    ),
                    amount=bet.amount,
                    status=bet.status,
                    created_at=bet.created_at
                ) for bet in bets
            ],
            pagination=PaginationInfo(
                total=total_count,
                current_page=page,
                limit=limit,
                total_pages=total_pages
            )
        )