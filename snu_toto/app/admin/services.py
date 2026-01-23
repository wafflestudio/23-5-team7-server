from typing import Annotated
from fastapi import Depends
from math import ceil

from snu_toto.app.admin.exceptions import SelfRoleChangeDeniedError
from snu_toto.app.bets.exceptions import EventNotFoundError
from snu_toto.app.events.repositories import EventRepositories
from snu_toto.app.bets.repositories import BetRepositories
from snu_toto.app.bets.schemas import (
    AdminBetListResponse, AdminEventSummary, AdminBetResponse, 
    AdminBetUserResponse, AdminBetOptionResponse, PaginationInfo
)
from snu_toto.app.users.exceptions import UserNotFoundError
from snu_toto.app.users.repositories import UserRepository
from snu_toto.app.users.schemas import UserAdminResponse, UserRoleUpdateRequest

class AdminServices:
    def __init__(
        self,
        event_repo: Annotated[EventRepositories, Depends()],
        bet_repo: Annotated[BetRepositories, Depends()],
        user_repo: Annotated[UserRepository, Depends()] # 이것을 추가하면 문제 발생
    ):
        self.event_repo = event_repo
        self.bet_repo = bet_repo
        self.user_repo = user_repo

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
    
    async def update_user_role(
        self, 
        current_admin_id: str, 
        target_user_id: str, 
        data: UserRoleUpdateRequest
    ) -> UserAdminResponse:
        if current_admin_id == target_user_id:
            raise SelfRoleChangeDeniedError()

        user = await self.user_repo.get_by_id(target_user_id)
        if not user:
            raise UserNotFoundError()

        session = self.user_repo.db
        if not session.in_transaction():
            async with session.begin():
                await self.user_repo.update_user_role(target_user_id, data.role)
        else:
            await self.user_repo.update_user_role(target_user_id, data.role)
            await session.flush()
        
        await session.refresh(user)
        
        return UserAdminResponse.model_validate(user)